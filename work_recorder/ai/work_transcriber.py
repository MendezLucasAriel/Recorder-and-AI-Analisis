import time
from pathlib import Path
from typing import Callable, Optional

from faster_whisper import WhisperModel
from work_recorder.models.meeting_session import Transcript, TranscriptSegment
from ai.device_detector import DeviceDetector
from ai.vulkan_transcriber import VulkanTranscriber


class WorkTranscriber:
    """
    Transcriptor optimizado para reuniones de trabajo corporativas, llamadas y syncs.
    """

    def __init__(
        self,
        model_name: str = "medium",
        backend: str = "gpu",
        device: str = "auto",
        compute_type: str = "auto",
        language: str = "es",
        initial_prompt: Optional[str] = None,
    ):
        self.model_name = model_name
        self.backend = backend.lower().strip()
        self.language = language
        self.initial_prompt = initial_prompt

        profile = DeviceDetector.get_profile()
        self.device = profile.device if device == "auto" else device
        self.compute_type = profile.compute_type if compute_type == "auto" else compute_type
        self.cpu_threads = profile.cpu_threads

        self._cpu_model: Optional[WhisperModel] = None

    def _load_cpu_model(self, on_status: Optional[Callable[[str], None]] = None) -> WhisperModel:
        if self._cpu_model is None:
            if on_status:
                on_status(f"Cargando modelo CPU '{self.model_name}' (INT8)...")
            clean_name = self.model_name.replace(".en", "")
            self._cpu_model = WhisperModel(
                model_size_or_path=clean_name,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
            )
        return self._cpu_model

    def transcribe(
        self,
        audio_path: Path,
        on_progress: Optional[Callable[[float, str, float], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> Transcript:
        if self.backend == "gpu" and VulkanTranscriber.is_available():
            try:
                vulkan = VulkanTranscriber(
                    model_name=self.model_name,
                    language=self.language,
                    initial_prompt=self.initial_prompt,
                )
                raw_transcript = vulkan.transcribe(
                    audio_path=audio_path,
                    on_progress=on_progress,
                    on_status=on_status,
                )
                return Transcript.from_dict(raw_transcript.to_dict())
            except Exception as e:
                print(f"[WorkTranscriber] Error en Vulkan GPU: {e}")
                if on_status:
                    on_status(f"⚠️ GPU AMD no pudo procesar ({e}). Usando CPU como respaldo...")
                time.sleep(1)

        return self._transcribe_cpu(audio_path, on_progress, on_status)

    def _transcribe_cpu(
        self,
        audio_path: Path,
        on_progress: Optional[Callable[[float, str, float], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> Transcript:
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")

        model = self._load_cpu_model(on_status)

        if on_status:
            on_status("Transcribiendo audio de la reunión con Whisper...")

        start_wall_time = time.time()
        lang_arg = self.language if self.language and self.language != "auto" else "es"

        segments_gen, info = model.transcribe(
            str(audio_path),
            language=lang_arg,
            initial_prompt=self.initial_prompt,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=400),
            beam_size=5,
        )

        total_audio_duration = info.duration if info and info.duration > 0 else 1.0
        transcript_segments = []

        for segment in segments_gen:
            text = segment.text.strip()
            if not text:
                continue

            seg_obj = TranscriptSegment(
                start=round(segment.start, 2),
                end=round(segment.end, 2),
                text=text,
            )
            transcript_segments.append(seg_obj)

            progress = min(1.0, max(0.01, segment.end / total_audio_duration))
            elapsed = time.time() - start_wall_time
            if progress > 0.05:
                estimated_total_time = elapsed / progress
                eta = max(0.0, estimated_total_time - elapsed)
            else:
                eta = 0.0

            if on_progress:
                on_progress(progress, text, eta)

        if on_status:
            on_status("Transcripción de la reunión completada.")

        return Transcript(
            segments=transcript_segments,
            language=info.language if info else self.language,
            duration=total_audio_duration,
        )
