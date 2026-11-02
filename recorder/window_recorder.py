import os
import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from windows_capture import WindowsCapture, Frame, InternalCaptureControl, CaptureControl
from utils.window_list import find_window_by_partial_title


class WindowRecorder:
    """
    Graba exclusivamente una ventana seleccionada (por ejemplo, Foundry VTT)
    utilizando la Windows Graphics Capture API (WGC).
    
    Ventajas clave:
    - Es inmune a superposiciones y Alt-Tab: solo graba la superficie de la ventana elegida.
    - Cero interferencia si abres Discord, un bloc de notas o cualquier app encima.
    - Rate limiting configurable (por defecto 5 FPS) para mantener archivos ligeros.
    """

    CAPTURE_MODE = "window"

    def __init__(self):
        self.is_recording = False
        self.output_path: Optional[Path] = None
        self._control: Optional[CaptureControl] = None
        self._writer: Optional[cv2.VideoWriter] = None
        self._lock = threading.Lock()
        
        self._fps: int = 5
        self._last_frame_time: float = 0.0
        self._target_interval: float = 0.20
        self._out_dimensions: Optional[tuple[int, int]] = None
        self._frames_written: int = 0
        self._window_name: str = ""

    def start_recording(
        self,
        output_mp4: Path,
        window_title: Optional[str] = None,
        window_hwnd: Optional[int] = None,
        fps: int = 5,
        resolution: str = "1280x720",
    ) -> bool:
        """
        Inicia la captura bloqueada de la ventana seleccionada con WGC.
        """
        self.output_path = Path(output_mp4)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._fps = max(1, fps)
        self._target_interval = 1.0 / float(self._fps)
        self._last_frame_time = 0.0
        self._frames_written = 0
        self._out_dimensions = None

        # Resolver dimensiones objetivo
        target_w, target_h = (1280, 720)
        if "x" in resolution:
            try:
                parts = resolution.split("x")
                target_w, target_h = int(parts[0]), int(parts[1])
            except Exception:
                pass

        # Resolver ventana si se dio un título parcial
        resolved_hwnd = window_hwnd
        resolved_name = window_title

        if resolved_hwnd is None and window_title:
            matched = find_window_by_partial_title(window_title)
            if matched:
                resolved_hwnd = matched["hwnd"]
                resolved_name = matched["title"]

        self._window_name = resolved_name or (f"HWND:{resolved_hwnd}" if resolved_hwnd else "Ventana Desconocida")

        try:
            # Configurar WindowsCapture con WGC
            # draw_border=False elimina el borde amarillo en Windows 11
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
                print("Error: No se especificó ventana para WindowRecorder.")
                return False

            @capture.event
            def on_frame_arrived(frame: Frame, capture_control: InternalCaptureControl):
                if not self.is_recording:
                    return

                now = time.time()
                # Rate limiting al framerate configurado
                if now - self._last_frame_time < self._target_interval:
                    return

                self._last_frame_time = now

                try:
                    # Convertir a formato BGR
                    bgr_frame = frame.convert_to_bgr()
                    raw_img = bgr_frame.frame_buffer

                    with self._lock:
                        # Inicializar VideoWriter con el primer frame
                        if self._writer is None:
                            h, w, _ = raw_img.shape
                            scale = min(target_w / float(w), target_h / float(h))
                            if scale > 1.0 or scale < 0.95:
                                out_w = int(w * scale)
                                out_h = int(h * scale)
                            else:
                                out_w, out_h = w, h

                            # Asegurar dimensiones pares para códecs de video
                            out_w = out_w if out_w % 2 == 0 else out_w - 1
                            out_h = out_h if out_h % 2 == 0 else out_h - 1
                            self._out_dimensions = (out_w, out_h)

                            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                            self._writer = cv2.VideoWriter(
                                str(self.output_path),
                                fourcc,
                                float(self._fps),
                                (out_w, out_h),
                            )

                        out_w, out_h = self._out_dimensions
                        if raw_img.shape[1] != out_w or raw_img.shape[0] != out_h:
                            resized = cv2.resize(raw_img, (out_w, out_h), interpolation=cv2.INTER_AREA)
                            self._writer.write(resized)
                        else:
                            self._writer.write(raw_img)

                        self._frames_written += 1

                except Exception as ex:
                    # Si la ventana se minimiza o cambia de tamaño momentáneamente
                    pass

            @capture.event
            def on_closed():
                with self._lock:
                    if self._writer:
                        self._writer.release()
                        self._writer = None
                self.is_recording = False

            # Iniciar hilo de captura nativo en segundo plano
            self._control = capture.start_free_threaded()
            self.is_recording = True
            print(f"[WindowRecorder] Grabando ventana: '{self._window_name}' -> {self.output_path.name}")
            return True

        except Exception as e:
            print(f"[WindowRecorder] Error iniciando grabación de ventana: {e}")
            self.is_recording = False
            return False

    def stop(self) -> Optional[Path]:
        """
        Detiene la captura de la ventana y finaliza el archivo MP4.
        """
        if not self.is_recording and not self._writer:
            return None

        self.is_recording = False

        # Detener hilo de WGC
        if self._control:
            try:
                self._control.stop()
                self._control.wait()
            except Exception as e:
                print(f"[WindowRecorder] Advertencia deteniendo control WGC: {e}")
            self._control = None

        # Cerrar VideoWriter
        with self._lock:
            if self._writer:
                try:
                    self._writer.release()
                except Exception as e:
                    print(f"[WindowRecorder] Error al cerrar VideoWriter: {e}")
                self._writer = None

        print(f"[WindowRecorder] Grabación finalizada. Frames escritos: {self._frames_written}")
        return self.output_path
