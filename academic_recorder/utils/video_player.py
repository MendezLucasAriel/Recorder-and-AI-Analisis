import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from utils.ffmpeg_helper import FFmpegHelper


def parse_timestamp_to_seconds(ts_str: str) -> float:
    """
    Convierte cadenas como '[14:25]', '14:25', '01:14:25' a segundos (float).
    """
    cleaned = re.sub(r"[\[\]\(\)\s]", "", str(ts_str))
    parts = cleaned.split(":")
    try:
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        return float(cleaned)
    except ValueError:
        return 0.0


class VideoPlayerHelper:
    """
    Lanza la reproducción de video posicionada exactamente en el segundo solicitado
    con un margen previo configurable (por defecto 5 segundos antes) para contextualizar la explicación.
    """

    LEAD_TIME_SECONDS = 5.0

    @staticmethod
    def get_vlc_path() -> Optional[str]:
        path = shutil.which("vlc")
        if path:
            return path
        candidates = [
            Path("C:/Program Files/VideoLAN/VLC/vlc.exe"),
            Path("C:/Program Files (x86)/VideoLAN/VLC/vlc.exe"),
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return None

    @staticmethod
    def get_ffplay_path() -> Optional[str]:
        # 1. PATH directo
        ffplay = shutil.which("ffplay")
        if ffplay:
            return ffplay

        # 2. Junto a ffmpeg
        ffmpeg = FFmpegHelper.get_ffmpeg_path()
        if ffmpeg:
            candidate = Path(ffmpeg).with_name("ffplay.exe")
            if candidate.exists():
                return str(candidate)

        return None

    @classmethod
    def play_at(cls, video_path: Path, timestamp_seconds: float, lead_time: float = 5.0) -> bool:
        """
        Abre el reproductor de video en max(0, timestamp_seconds - lead_time) segundos.
        Prioridad:
        1. VLC con bandera --start-time
        2. ffplay con bandera -ss
        3. Reproductor nativo de Windows (os.startfile)
        """
        video_path = Path(video_path).resolve()
        if not video_path.exists():
            print(f"[VideoPlayer] Video no encontrado: {video_path}")
            return False

        target_sec = max(0.0, float(timestamp_seconds) - float(lead_time))

        # 1. Intentar VLC
        vlc_bin = cls.get_vlc_path()
        if vlc_bin:
            try:
                cmd = [vlc_bin, f"--start-time={int(target_sec)}", str(video_path)]
                subprocess.Popen(cmd)
                print(f"[VideoPlayer] Lanzado VLC en {target_sec:.1f}s: {video_path.name}")
                return True
            except Exception as e:
                print(f"[VideoPlayer] Error lanzando VLC: {e}")

        # 2. Intentar ffplay
        ffplay_bin = cls.get_ffplay_path()
        if ffplay_bin:
            try:
                # ffplay -ss posiciona instantáneamente
                cmd = [ffplay_bin, "-ss", f"{target_sec:.2f}", "-window_title", f"Clase: {video_path.name}", str(video_path)]
                subprocess.Popen(cmd)
                print(f"[VideoPlayer] Lanzado ffplay en {target_sec:.1f}s: {video_path.name}")
                return True
            except Exception as e:
                print(f"[VideoPlayer] Error lanzando ffplay: {e}")

        # 3. Fallback: Reproductor predeterminado de Windows
        try:
            os.startfile(str(video_path))
            print(f"[VideoPlayer] Abierto con reproductor predeterminado (objetivo: {target_sec:.1f}s)")
            return True
        except Exception as e:
            print(f"[VideoPlayer] Error abriendo archivo: {e}")
            return False
