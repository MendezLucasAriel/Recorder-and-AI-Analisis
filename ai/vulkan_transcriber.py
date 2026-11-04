import json
import os
import re
import subprocess
import time
import urllib.request
from collections import deque
from pathlib import Path
from typing import Callable, Optional

from models.session import Transcript, TranscriptSegment


# URLs directas de modelos GGML optimizados para whisper.cpp
GGML_MODEL_URLS = {
    "tiny": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
    "tiny.en": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin",
    "base": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
    "base.en": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin",
    "small": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
    "small.en": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin",
    "medium": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium-q5_0.bin",
    "medium-q5_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium-q5_0.bin",
    "medium.en": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.en.bin",
    "large-v3": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-q5_0.bin",
    "large-v3-q5_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-q5_0.bin",
}


class VulkanTranscriber:
    """
    Transcriptor de Whisper acelerado por GPU AMD (Vulkan) mediante whisper.cpp.
    Aprovecha el ancho de banda GDDR5 de la AMD Radeon RX 470 para transcripciones
    significativamente más veloces.
    """

    def __init__(self, model_name: str = "small", language: str = "en", initial_prompt: Optional[str] = None):
        self.project_root = Path(__file__).resolve().parent.parent
        self.bin_dir = self.project_root / "bin" / "vulkan"
        self.exe_path = self.bin_dir / "whisper-cli.exe"

        # Priorizar C:\whisper\models si existe; de lo contrario bin/vulkan/models
        shared_dir = Path(r"C:\whisper\models")
        if shared_dir.exists():
            self.models_dir = shared_dir
        else:
            self.models_dir = self.bin_dir / "models"
            self.models_dir.mkdir(parents=True, exist_ok=True)

        self.model_name = self._resolve_model_name(model_name, language)
        self.language = language
        self.initial_prompt = initial_prompt

    @staticmethod
    def _resolve_model_name(name: str, language: str) -> str:
        clean = name.lower().split(" ")[0].strip()
        # Si el audio es inglés y el usuario eligió un modelo base/small/medium, preferir .en para máxima velocidad
        if language == "en" and not clean.endswith(".en") and f"{clean}.en" in GGML_MODEL_URLS:
            return f"{clean}.en"
        # Para GPUs AMD sin FP16 nativo (Polaris RX 470/570), medium debe usar medium-q5_0 (539 MB)
        if clean in ("medium", "medium-q5_0"):
            return "medium-q5_0"
        if clean in ("large", "large-v3", "large-v3-q5_0"):
            return "large-v3-q5_0"
        if clean in GGML_MODEL_URLS:
            return clean
        return "small"

    @classmethod
    def is_available(cls) -> bool:
        project_root = Path(__file__).resolve().parent.parent
        exe = project_root / "bin" / "vulkan" / "whisper-cli.exe"
        return exe.exists()

    def _ensure_model_downloaded(self, on_status: Optional[Callable[[str], None]] = None) -> Path:
        # 1. Buscar en C:\whisper\models
        shared_file = Path(r"C:\whisper\models") / f"ggml-{self.model_name}.bin"
        if shared_file.exists() and shared_file.stat().st_size > 1024 * 1024:
            return shared_file

        # 2. Buscar en la carpeta local de modelos del proyecto
        local_file = self.bin_dir / "models" / f"ggml-{self.model_name}.bin"
        if local_file.exists() and local_file.stat().st_size > 1024 * 1024:
            return local_file

        # 3. Si no existe, descargar en C:\whisper\models (si es posible) o en bin\vulkan\models
        dest_dir = Path(r"C:\whisper\models")
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            target_file = dest_dir / f"ggml-{self.model_name}.bin"
        except Exception:
            dest_dir = self.bin_dir / "models"
            dest_dir.mkdir(parents=True, exist_ok=True)
            target_file = local_file

        url = GGML_MODEL_URLS.get(self.model_name, GGML_MODEL_URLS["small"])
        if on_status:
            on_status(f"Descargando modelo GPU 'ggml-{self.model_name}.bin' (~539 MB)...")

        temp_dest = target_file.with_suffix(".tmp")
        try:
            urllib.request.urlretrieve(url, temp_dest)
            temp_dest.replace(target_file)
            if on_status:
                on_status(f"Modelo 'ggml-{self.model_name}.bin' descargado con éxito.")
            return target_file
        except Exception as e:
            if temp_dest.exists():
                temp_dest.unlink(missing_ok=True)
            raise RuntimeError(f"Error descargando modelo {self.model_name}: {e}")

    def transcribe(
        self,
        audio_path: Path,
        on_progress: Optional[Callable[[float, str, float], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> Transcript:
        audio_path = Path(audio_path).resolve()
        if not audio_path.exists():
            raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")

        if not self.exe_path.exists():
            raise FileNotFoundError(f"No se encontró el ejecutable Vulkan en: {self.exe_path}")

        model_path = self._ensure_model_downloaded(on_status)

        from ai.device_detector import DeviceDetector
        raw_gpu = DeviceDetector.get_gpu_name()

        if on_status:
            on_status(f"Iniciando transcripción en GPU {raw_gpu} (Vulkan) con '{self.model_name}'...")

        output_json_base = audio_path.with_name(f"{audio_path.stem}_vulkan_out")
        expected_json = Path(f"{output_json_base}.json")
        expected_json.unlink(missing_ok=True)

        lang_arg = self.language if self.language and self.language != "auto" else "auto"

        cmd = [
            str(self.exe_path),
            "-m", str(model_path),
            "-f", str(audio_path),
            "-l", lang_arg,
            "-dev", "0",          # GPU 0
            "-oj",                # Salida JSON
            "-of", str(output_json_base),
            "-pp",                # Imprimir progreso en stderr
            "--flash-attn",       # Flash attention para acelerar en GPU
            "-nf",                # Evitar bucles de alucinación por temperature fallback
        ]

        if self.initial_prompt and self.initial_prompt.strip():
            # Evitar condicionar audio en inglés con un prompt en español para prevenir bucles de alucinación
            is_spanish_prompt = any(w in self.initial_prompt.lower() for w in ["reunión", "clase", "materia", "física", "matemáticas", "trabajo"])
            if lang_arg == "en" and is_spanish_prompt:
                pass
            else:
                cmd.extend(["--prompt", self.initial_prompt.strip()])

        start_time = time.time()
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        last_progress = 0.0
        current_text = ""
        output_tail = deque(maxlen=25)

        for raw_line in iter(process.stdout.readline, ""):
            line = raw_line.strip()
            if not line:
                continue

            output_tail.append(line)

            # Si es un segmento de texto: [00:00:00.000 --> 00:00:08.460] texto
            if "-->" in line:
                parts = line.split("]", 1)
                if len(parts) > 1:
                    current_text = parts[1].strip()
                    if on_progress and last_progress > 0:
                        elapsed = time.time() - start_time
                        eta = max(0.0, (elapsed / last_progress) - elapsed) if last_progress > 0.03 else 0.0
                        on_progress(last_progress, current_text, eta)

            # Si es una línea de progreso: "progress = 45%"
            match = re.search(r"progress\s*=\s*(\d+)%", line)
            if match:
                percent = int(match.group(1))
                progress = min(1.0, max(0.01, percent / 100.0))
                elapsed = time.time() - start_time
                if progress > 0.03:
                    eta = max(0.0, (elapsed / progress) - elapsed)
                else:
                    eta = 0.0
                last_progress = progress
                if on_progress:
                    on_progress(progress, current_text, eta)

        returncode = process.wait()
        if returncode != 0:
            err_output = "\n".join(output_tail)
            raise RuntimeError(f"Whisper Vulkan falló con código {returncode}: {err_output}")

        if not expected_json.exists():
            raise RuntimeError(f"No se generó el archivo de transcripción JSON en {expected_json}")

        try:
            with open(expected_json, "r", encoding="utf-8") as f:
                data = json.load(f)

            segments = []
            transcription_data = data.get("transcription", [])
            for item in transcription_data:
                text = item.get("text", "").strip()
                if not text:
                    continue
                # whisper.cpp timestamps están en formato ms o offsets
                offsets = item.get("offsets", {})
                from_ms = offsets.get("from", 0)
                to_ms = offsets.get("to", 0)
                start_sec = round(from_ms / 1000.0, 2)
                end_sec = round(to_ms / 1000.0, 2)

                segments.append(
                    TranscriptSegment(
                        start=start_sec,
                        end=end_sec,
                        text=text,
                    )
                )

            total_dur = segments[-1].end if segments else 0.0
            return Transcript(
                segments=segments,
                language=self.language,
                duration=total_dur,
            )
        finally:
            expected_json.unlink(missing_ok=True)
