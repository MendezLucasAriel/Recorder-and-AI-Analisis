import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional, Tuple

import cv2
from windows_capture import WindowsCapture, Frame, InternalCaptureControl, CaptureControl
from utils.ffmpeg_helper import FFmpegHelper
from utils.window_list import find_window_by_partial_title


class WorkVideoRecorder:
    """
    Grabador ligero de pantalla o ventana para reuniones de trabajo (compartir pantalla, demos, diapositivas).
    """

    def __init__(self):
        self.is_recording = False
        self.output_path: Optional[Path] = None
        self.mode: str = "window"
        self.fps: int = 15
        self.resolution: str = "1920x1080"

        self._wgc_control: Optional[CaptureControl] = None
        self._cv2_writer: Optional[cv2.VideoWriter] = None
        self._lock = threading.Lock()
        self._last_frame_time: float = 0.0
        self._target_interval: float = 1.0 / 15.0
        self._out_dimensions: Optional[Tuple[int, int]] = None
        self._frames_written: int = 0
        self._window_name: str = ""

        self._ffmpeg_process: Optional[subprocess.Popen] = None

    def start_recording(
        self,
        output_mp4: Path,
        mode: str = "window",
        window_title: Optional[str] = None,
        window_hwnd: Optional[int] = None,
        fps: int = 15,
        resolution: str = "1920x1080",
    ) -> bool:
        self.output_path = Path(output_mp4).resolve()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.mode = mode
        self.fps = max(5, min(fps, 30))
        self.resolution = resolution
        self._target_interval = 1.0 / float(self.fps)
        self._last_frame_time = 0.0
        self._frames_written = 0
        self._out_dimensions = None

        if mode == "window" and (window_title or window_hwnd):
            started = self._start_window_capture(window_title, window_hwnd)
            if started:
                return True
            print("[WorkVideoRecorder] Fallback automático a modo desktop...")

        return self._start_desktop_capture()

    def _start_window_capture(
        self, window_title: Optional[str], window_hwnd: Optional[int]
    ) -> bool:
        resolved_hwnd = window_hwnd
        resolved_name = window_title

        if resolved_hwnd is None and window_title:
            matched = find_window_by_partial_title(window_title)
            if matched:
                resolved_hwnd = matched["hwnd"]
                resolved_name = matched["title"]

        self._window_name = resolved_name or (f"HWND:{resolved_hwnd}" if resolved_hwnd else "Ventana Desconocida")

        try:
            if resolved_hwnd:
                capture = WindowsCapture(
                    cursor_capture=True,
                    draw_border=False,
                    window_hwnd=int(resolved_hwnd),
                )
            elif resolved_name:
                capture = WindowsCapture(
                    cursor_capture=True,
                    draw_border=False,
                    window_name=resolved_name,
                )
            else:
                return False

            target_w, target_h = (1920, 1080)
            if "x" in self.resolution:
                try:
                    parts = self.resolution.split("x")
                    target_w, target_h = int(parts[0]), int(parts[1])
                except Exception:
                    pass

            @capture.event
            def on_frame_arrived(frame: Frame, capture_control: InternalCaptureControl):
                if not self.is_recording:
                    return

                now = time.time()
                if now - self._last_frame_time < self._target_interval:
                    return

                self._last_frame_time = now

                try:
                    bgr_frame = frame.convert_to_bgr()
                    raw_img = bgr_frame.frame_buffer

                    with self._lock:
                        if self._cv2_writer is None:
                            h, w, _ = raw_img.shape
                            scale = min(target_w / float(w), target_h / float(h))
                            if scale > 1.0 or scale < 0.95:
                                out_w = int(w * scale)
                                out_h = int(h * scale)
                            else:
                                out_w, out_h = w, h

                            out_w = out_w if out_w % 2 == 0 else out_w - 1
                            out_h = out_h if out_h % 2 == 0 else out_h - 1
                            self._out_dimensions = (out_w, out_h)

                            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                            self._cv2_writer = cv2.VideoWriter(
                                str(self.output_path),
                                fourcc,
                                float(self.fps),
                                (out_w, out_h),
                            )

                        out_w, out_h = self._out_dimensions
                        if raw_img.shape[1] != out_w or raw_img.shape[0] != out_h:
                            resized = cv2.resize(raw_img, (out_w, out_h), interpolation=cv2.INTER_AREA)
                            self._cv2_writer.write(resized)
                        else:
                            self._cv2_writer.write(raw_img)

                        self._frames_written += 1
                except Exception:
                    pass

            @capture.event
            def on_closed():
                with self._lock:
                    if self._cv2_writer:
                        self._cv2_writer.release()
                        self._cv2_writer = None
                self.is_recording = False

            self._wgc_control = capture.start_free_threaded()
            self.is_recording = True
            return True

        except Exception as e:
            print(f"[WorkVideoRecorder] Error iniciando WGC: {e}")
            self.is_recording = False
            return False

    def _start_desktop_capture(self) -> bool:
        ffmpeg_bin = FFmpegHelper.get_ffmpeg_path()
        if not ffmpeg_bin:
            return False

        cmd = [
            ffmpeg_bin,
            "-y",
            "-f", "gdigrab",
            "-framerate", str(self.fps),
            "-i", "desktop",
            "-s", self.resolution,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "26",
            "-pix_fmt", "yuv420p",
            str(self.output_path),
        ]

        try:
            self._ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.is_recording = True
            return True
        except Exception as e:
            print(f"[WorkVideoRecorder] Error iniciando FFmpeg: {e}")
            self.is_recording = False
            return False

    def stop(self) -> Optional[Path]:
        if not self.is_recording and not self._cv2_writer and not self._ffmpeg_process:
            return None

        self.is_recording = False

        if self._wgc_control:
            try:
                self._wgc_control.stop()
                self._wgc_control.wait()
            except Exception:
                pass
            self._wgc_control = None

        with self._lock:
            if self._cv2_writer:
                try:
                    self._cv2_writer.release()
                except Exception:
                    pass
                self._cv2_writer = None

        if self._ffmpeg_process:
            pid = self._ffmpeg_process.pid
            try:
                if self._ffmpeg_process.stdin:
                    try:
                        self._ffmpeg_process.stdin.write(b"q\n")
                        self._ffmpeg_process.stdin.flush()
                        self._ffmpeg_process.stdin.close()
                    except Exception:
                        pass
                self._ffmpeg_process.wait(timeout=5.0)
            except Exception:
                try:
                    self._ffmpeg_process.terminate()
                    self._ffmpeg_process.wait(timeout=2.0)
                except Exception:
                    try:
                        self._ffmpeg_process.kill()
                    except Exception:
                        pass

            if self._ffmpeg_process and self._ffmpeg_process.poll() is None:
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=2.0,
                    )
                except Exception:
                    pass
            self._ffmpeg_process = None

        return self.output_path
