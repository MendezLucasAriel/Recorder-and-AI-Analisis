import io
import math
import os
import struct
import threading
import time
import wave
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pyaudiowpatch as pyaudio
from scipy import signal


class AudioRecorder:
    """
    Graba simultáneamente audio del sistema (WASAPI Loopback = Discord + Foundry)
    y micrófono del usuario, mezclándolos en un único archivo WAV (16kHz, mono, PCM 16-bit)
    óptimo para Whisper.
    """

    def __init__(self):
        self.is_recording = False
        self.is_paused = False
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        self.output_path: Optional[Path] = None
        self._loopback_temp_path: Optional[Path] = None
        self._mic_temp_path: Optional[Path] = None

        # Callbacks para la UI (nivel de pico 0.0 - 1.0 y duración en seg)
        self.on_peak_update: Optional[Callable[[float, float], None]] = None  # (mic_peak, loopback_peak)
        self.on_duration_update: Optional[Callable[[float], None]] = None    # duration_seconds

        self._start_time: float = 0.0
        self._total_paused_time: float = 0.0
        self._pause_start_time: float = 0.0

        self._mic_peak: float = 0.0
        self._loopback_peak: float = 0.0

    @staticmethod
    def get_available_devices() -> Dict[str, List[Dict[str, any]]]:
        """Devuelve los dispositivos disponibles de micrófono y loopback usando WASAPI."""
        mics = []
        loopbacks = []

        with pyaudio.PyAudio() as p:
            try:
                wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
                wasapi_idx = wasapi_info["index"]
            except Exception:
                wasapi_idx = None

            for i in range(p.get_device_count()):
                try:
                    dev = p.get_device_info_by_index(i)
                except Exception:
                    continue

                # Filtrar solo dispositivos WASAPI si está disponible
                if wasapi_idx is not None and dev.get("hostApi") != wasapi_idx:
                    continue

                if dev.get("maxInputChannels", 0) > 0:
                    item = {
                        "index": dev["index"],
                        "name": dev["name"],
                        "channels": dev["maxInputChannels"],
                        "sample_rate": int(dev["defaultSampleRate"]),
                        "is_loopback": dev.get("isLoopbackDevice", False),
                    }
                    if dev.get("isLoopbackDevice", False):
                        loopbacks.append(item)
                    else:
                        mics.append(item)

        return {"microphones": mics, "loopbacks": loopbacks}

    def start_recording(
        self,
        output_wav: Path,
        mic_index: Optional[int] = None,
        loopback_index: Optional[int] = None,
    ) -> None:
        if self.is_recording:
            return

        self.output_path = Path(output_wav)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        self._loopback_temp_path = self.output_path.with_name(f"{self.output_path.stem}_system_temp.wav")
        self._mic_temp_path = self.output_path.with_name(f"{self.output_path.stem}_mic_temp.wav")

        self.is_recording = True
        self.is_paused = False
        self._stop_event.clear()
        self._start_time = time.time()
        self._total_paused_time = 0.0

        # Iniciar worker en un hilo dedicado
        self._worker_thread = threading.Thread(
            target=self._recording_loop,
            args=(mic_index, loopback_index),
            daemon=True,
        )
        self._worker_thread.start()

    def _recording_loop(self, mic_index: Optional[int], loopback_index: Optional[int]):
        p = pyaudio.PyAudio()
        stream_loop = None
        stream_mic = None
        wf_loop = None
        wf_mic = None

        try:
            # 1. Configurar Loopback
            loop_dev = None
            if loopback_index is not None:
                loop_dev = p.get_device_info_by_index(loopback_index)
            else:
                try:
                    loop_dev = p.get_default_wasapi_loopback()
                except Exception:
                    pass

            if loop_dev:
                loop_channels = loop_dev["maxInputChannels"]
                loop_sr = int(loop_dev["defaultSampleRate"])
                wf_loop = wave.open(str(self._loopback_temp_path), "wb")
                wf_loop.setnchannels(loop_channels)
                wf_loop.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                wf_loop.setframerate(loop_sr)

                stream_loop = p.open(
                    format=pyaudio.paInt16,
                    channels=loop_channels,
                    rate=loop_sr,
                    input=True,
                    input_device_index=loop_dev["index"],
                    frames_per_buffer=1024,
                )

            # 2. Configurar Micrófono
            mic_dev = None
            if mic_index is not None:
                mic_dev = p.get_device_info_by_index(mic_index)
            else:
                # Buscar micrófono WASAPI por defecto
                try:
                    wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
                    for i in range(p.get_device_count()):
                        d = p.get_device_info_by_index(i)
                        if d["hostApi"] == wasapi_info["index"] and not d.get("isLoopbackDevice", False) and d["maxInputChannels"] > 0:
                            mic_dev = d
                            break
                except Exception:
                    pass
                if not mic_dev:
                    try:
                        mic_dev = p.get_default_input_device_info()
                    except Exception:
                        pass

            if mic_dev:
                mic_channels = mic_dev["maxInputChannels"]
                mic_sr = int(mic_dev["defaultSampleRate"])
                wf_mic = wave.open(str(self._mic_temp_path), "wb")
                wf_mic.setnchannels(mic_channels)
                wf_mic.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                wf_mic.setframerate(mic_sr)

                stream_mic = p.open(
                    format=pyaudio.paInt16,
                    channels=mic_channels,
                    rate=mic_sr,
                    input=True,
                    input_device_index=mic_dev["index"],
                    frames_per_buffer=1024,
                )

            # Bucle principal de lectura
            last_monitor_time = time.time()
            while not self._stop_event.is_set():
                if self.is_paused:
                    time.sleep(0.05)
                    continue

                if stream_loop:
                    try:
                        data_loop = stream_loop.read(1024, exception_on_overflow=False)
                        wf_loop.writeframes(data_loop)
                        samples_loop = np.frombuffer(data_loop, dtype=np.int16)
                        if len(samples_loop) > 0:
                            self._loopback_peak = float(np.max(np.abs(samples_loop))) / 32768.0
                    except Exception:
                        pass

                if stream_mic:
                    try:
                        data_mic = stream_mic.read(1024, exception_on_overflow=False)
                        wf_mic.writeframes(data_mic)
                        samples_mic = np.frombuffer(data_mic, dtype=np.int16)
                        if len(samples_mic) > 0:
                            self._mic_peak = float(np.max(np.abs(samples_mic))) / 32768.0
                    except Exception:
                        pass

                # Monitor callbacks cada ~50ms
                now = time.time()
                if now - last_monitor_time >= 0.05:
                    last_monitor_time = now
                    elapsed = now - self._start_time - self._total_paused_time
                    if self.on_duration_update:
                        self.on_duration_update(elapsed)
                    if self.on_peak_update:
                        self.on_peak_update(self._mic_peak, self._loopback_peak)
                    self._mic_peak = max(0.0, self._mic_peak * 0.85)
                    self._loopback_peak = max(0.0, self._loopback_peak * 0.85)

        except Exception as e:
            print(f"Error en bucle de grabación: {e}")
        finally:
            if stream_loop is not None:
                try:
                    stream_loop.stop_stream()
                    stream_loop.close()
                except Exception:
                    pass
            if wf_loop is not None:
                try:
                    wf_loop.close()
                except Exception:
                    pass

            if stream_mic is not None:
                try:
                    stream_mic.stop_stream()
                    stream_mic.close()
                except Exception:
                    pass
            if wf_mic is not None:
                try:
                    wf_mic.close()
                except Exception:
                    pass

            p.terminate()

    def pause(self) -> None:
        if self.is_recording and not self.is_paused:
            self.is_paused = True
            self._pause_start_time = time.time()

    def resume(self) -> None:
        if self.is_recording and self.is_paused:
            self.is_paused = False
            self._total_paused_time += time.time() - self._pause_start_time

    def stop(self) -> Path:
        """Detiene la grabación y mezcla las pistas en audio.wav a 16kHz mono."""
        if not self.is_recording:
            return self.output_path

        self.is_recording = False
        self.is_paused = False
        self._stop_event.set()

        if self._worker_thread:
            self._worker_thread.join(timeout=3.0)

        # Mezclar pistas a mono 16kHz
        self._mix_down(
            loopback_path=self._loopback_temp_path,
            mic_path=self._mic_temp_path,
            output_path=self.output_path,
        )

        return self.output_path

    @staticmethod
    def _read_wav_to_float_mono(wav_path: Optional[Path], target_sr: int = 16000) -> Optional[np.ndarray]:
        if not wav_path or not wav_path.exists() or os.path.getsize(wav_path) < 100:
            return None

        try:
            with wave.open(str(wav_path), "rb") as wf:
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                sr = wf.getframerate()
                n_frames = wf.getnframes()
                raw_data = wf.readframes(n_frames)

            if sample_width != 2:
                return None

            audio = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0

            if channels > 1:
                audio = audio.reshape(-1, channels)
                audio = np.mean(audio, axis=1)

            # Resample a 16kHz si es necesario
            if sr != target_sr and len(audio) > 0:
                num_samples = int(len(audio) * target_sr / sr)
                audio = signal.resample(audio, num_samples)

            return audio
        except Exception as e:
            print(f"Error procesando {wav_path}: {e}")
            return None

    def _mix_down(
        self,
        loopback_path: Optional[Path],
        mic_path: Optional[Path],
        output_path: Path,
        target_sr: int = 16000,
    ) -> None:
        """Mezcla loopback + mic en un único archivo WAV 16kHz mono."""
        sys_audio = self._read_wav_to_float_mono(loopback_path, target_sr)
        mic_audio = self._read_wav_to_float_mono(mic_path, target_sr)

        final_audio = None
        if sys_audio is not None and mic_audio is not None:
            max_len = max(len(sys_audio), len(mic_audio))
            sys_padded = np.zeros(max_len, dtype=np.float32)
            mic_padded = np.zeros(max_len, dtype=np.float32)
            sys_padded[:len(sys_audio)] = sys_audio
            mic_padded[:len(mic_audio)] = mic_audio
            # Mezcla equilibrada
            final_audio = (sys_padded * 0.7) + (mic_padded * 0.8)
        elif sys_audio is not None:
            final_audio = sys_audio
        elif mic_audio is not None:
            final_audio = mic_audio

        if final_audio is None or len(final_audio) == 0:
            final_audio = np.zeros(target_sr, dtype=np.float32)

        # Normalización suave para evitar clipping
        max_val = np.max(np.abs(final_audio))
        if max_val > 0.95:
            final_audio = final_audio / max_val * 0.95

        int16_audio = (final_audio * 32767.0).clip(-32768, 32767).astype(np.int16)

        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(target_sr)
            wf.writeframes(int16_audio.tobytes())

        # Limpiar temporales
        try:
            if loopback_path and loopback_path.exists():
                loopback_path.unlink(missing_ok=True)
            if mic_path and mic_path.exists():
                mic_path.unlink(missing_ok=True)
        except Exception:
            pass
