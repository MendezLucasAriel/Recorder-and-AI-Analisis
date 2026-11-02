import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional
from utils.ffmpeg_helper import FFmpegHelper


class ScreenRecorder:
    """
    Graba la pantalla usando FFmpeg (gdigrab) a bajo framerate (5 fps) y resolución ligera
    para guardar referencia visual de mapas de Foundry sin consumir CPU ni disco en exceso.
    """

    def __init__(self):
        self.is_recording = False
        self._process: Optional[subprocess.Popen] = None
        self.output_path: Optional[Path] = None

    def start_recording(
        self,
        output_mp4: Path,
        fps: int = 5,
        resolution: str = "1280x720",
    ) -> bool:
        ffmpeg_bin = FFmpegHelper.get_ffmpeg_path()
        if not ffmpeg_bin:
            print("FFmpeg no disponible para grabación de pantalla.")
            return False

        self.output_path = Path(output_mp4)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            ffmpeg_bin,
            "-y",
            "-f", "gdigrab",
            "-framerate", str(fps),
            "-i", "desktop",
            "-s", resolution,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "30",
            "-pix_fmt", "yuv420p",
            str(self.output_path),
        ]

        try:
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.is_recording = True
            return True
        except Exception as e:
            print(f"Error iniciando grabación de pantalla: {e}")
            self.is_recording = False
            return False

    def stop(self) -> Optional[Path]:
        if not self.is_recording or not self._process:
            return None

        self.is_recording = False
        pid = self._process.pid
        try:
            # 1. Intentar salida limpia con 'q' + EOF
            if self._process.stdin:
                try:
                    self._process.stdin.write(b"q\n")
                    self._process.stdin.flush()
                    self._process.stdin.close()
                except Exception:
                    pass
            self._process.wait(timeout=8.0)
        except Exception:
            # 2. Si no respondió a 'q', terminar proceso
            try:
                self._process.terminate()
                self._process.wait(timeout=3.0)
            except Exception:
                try:
                    self._process.kill()
                    self._process.wait(timeout=2.0)
                except Exception:
                    pass

        # 3. Garantía en Windows: si por alguna razón sigue vivo, forzar taskkill
        if self._process and self._process.poll() is None:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3.0,
                )
            except Exception:
                pass

        self._process = None
        return self.output_path
