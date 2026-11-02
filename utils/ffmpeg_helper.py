import os
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Optional, List, Dict


class FFmpegHelper:
    """Helper para verificar y ejecutar comandos de FFmpeg."""

    @staticmethod
    def get_ffmpeg_path() -> Optional[str]:
        # 1. Check if ffmpeg is in PATH
        path = shutil.which("ffmpeg")
        if path:
            return path

        # 2. Check common Gyan/winget installation paths
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("ProgramFiles", "")
        possible_paths = [
            Path(local_app_data) / "Microsoft" / "WinGet" / "Packages",
            Path(program_files) / "FFmpeg",
            Path("C:/ffmpeg/bin/ffmpeg.exe"),
        ]

        for base in possible_paths:
            if base.exists():
                if base.is_file() and base.name.lower() == "ffmpeg.exe":
                    return str(base)
                # Search for ffmpeg.exe in subdirs
                matches = list(base.glob("**/ffmpeg.exe"))
                if matches:
                    return str(matches[0])

        return None

    @classmethod
    def is_available(cls) -> bool:
        return cls.get_ffmpeg_path() is not None

    @classmethod
    def get_version(cls) -> Optional[str]:
        ffmpeg = cls.get_ffmpeg_path()
        if not ffmpeg:
            return None
        try:
            res = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True, check=True)
            first_line = res.stdout.splitlines()[0] if res.stdout else ""
            return first_line
        except Exception:
            return None

    @classmethod
    def extract_audio_to_wav(cls, input_media_path: Path, output_wav_path: Path) -> bool:
        """
        Extrae la pista de audio de cualquier contenedor de video o audio y la convierte
        directamente a 16 kHz Mono PCM 16-bit WAV (formato ideal para Whisper).
        """
        ffmpeg = cls.get_ffmpeg_path()
        if not ffmpeg:
            print("[FFmpegHelper] FFmpeg no disponible para extracción de audio.")
            return False

        output_wav_path = Path(output_wav_path)
        output_wav_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            ffmpeg,
            "-y",
            "-i", str(input_media_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(output_wav_path),
        ]

        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return output_wav_path.exists() and output_wav_path.stat().st_size > 0
        except Exception as e:
            print(f"[FFmpegHelper] Error extrayendo audio con FFmpeg: {e}")
            return False

    @staticmethod
    def get_wav_duration(wav_path: Path) -> float:
        """Obtiene la duración exacta en segundos de un archivo WAV de forma instantánea sin cargar el audio."""
        try:
            with wave.open(str(wav_path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return float(frames) / float(rate)
        except Exception:
            pass
        return 0.0
