import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from utils.ffmpeg_helper import FFmpegHelper


def parse_timestamp_to_seconds(ts_str: str) -> float:
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
    """Lanza la reproducción de video posicionada en el segundo indicado."""

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
        ffplay = shutil.which("ffplay")
        if ffplay:
            return ffplay

        ffmpeg = FFmpegHelper.get_ffmpeg_path()
        if ffmpeg:
            candidate = Path(ffmpeg).with_name("ffplay.exe")
            if candidate.exists():
                return str(candidate)

        return None

    @classmethod
    def play_at(cls, video_path: Path, timestamp_seconds: float, lead_time: float = 3.0) -> bool:
        video_path = Path(video_path).resolve()
        if not video_path.exists():
            print(f"[VideoPlayer] Video no encontrado: {video_path}")
            return False

        target_sec = max(0.0, float(timestamp_seconds) - float(lead_time))

        # 1. VLC
        vlc_bin = cls.get_vlc_path()
        if vlc_bin:
            try:
                cmd = [vlc_bin, f"--start-time={int(target_sec)}", str(video_path)]
                subprocess.Popen(cmd)
                return True
            except Exception:
                pass

        # 2. ffplay
        ffplay_bin = cls.get_ffplay_path()
        if ffplay_bin:
            try:
                cmd = [ffplay_bin, "-ss", f"{target_sec:.2f}", "-window_title", f"Reunión: {video_path.name}", str(video_path)]
                subprocess.Popen(cmd)
                return True
            except Exception:
                pass

        # 3. Fallback reproductor de sistema
        try:
            os.startfile(str(video_path))
            return True
        except Exception:
            return False
