import json
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from models.session import Session, SessionMetadata
from utils.ffmpeg_helper import FFmpegHelper
from .audio_recorder import AudioRecorder
from .screen_recorder import ScreenRecorder
from .window_recorder import WindowRecorder


class SessionManager:
    """Gestiona el ciclo de vida de las sesiones y la orquestación de grabadores."""

    def __init__(self, sessions_dir: Path = Path("sessions")):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        self.audio_recorder = AudioRecorder()
        self.screen_recorder = ScreenRecorder()
        self.window_recorder = WindowRecorder()

        self.current_session: Optional[Session] = None
        self._is_recording = False

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def list_sessions(self) -> List[Session]:
        """Devuelve todas las sesiones guardadas ordenadas de más reciente a más antigua."""
        sessions = []
        if not self.sessions_dir.exists():
            return sessions

        for session_folder in self.sessions_dir.iterdir():
            if session_folder.is_dir() and (session_folder / "session.json").exists():
                try:
                    s = Session(session_folder)
                    sessions.append(s)
                except Exception:
                    pass

        # Ordenar por started_at descendente
        sessions.sort(key=lambda s: s.metadata.started_at, reverse=True)
        return sessions

    def start_session(
        self,
        campaign_name: str = "Campaña Principal",
        record_screen: bool = False,
        screen_mode: str = "window",
        capture_window_title: Optional[str] = None,
        capture_window_hwnd: Optional[int] = None,
        fps: int = 5,
        resolution: str = "1280x720",
        mic_index: Optional[int] = None,
        loopback_index: Optional[int] = None,
    ) -> Session:
        """Inicia una nueva sesión y la grabación correspondiente."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        session_id = f"session_{timestamp}"
        session_folder = self.sessions_dir / session_id
        session_folder.mkdir(parents=True, exist_ok=True)

        self.current_session = Session(session_folder)
        self.current_session.metadata.campaign = campaign_name
        self.current_session.metadata.started_at = datetime.now().isoformat()
        self.current_session.metadata.has_screen = record_screen
        if record_screen:
            self.current_session.metadata.devices_used["screen_mode"] = screen_mode
            if capture_window_title:
                self.current_session.metadata.devices_used["capture_window"] = capture_window_title
        self.current_session.save_metadata()

        # Iniciar audio
        self.audio_recorder.start_recording(
            output_wav=self.current_session.audio_file,
            mic_index=mic_index,
            loopback_index=loopback_index,
        )

        # Iniciar video si fue solicitado
        if record_screen:
            if screen_mode == "window" and (capture_window_title or capture_window_hwnd):
                started = self.window_recorder.start_recording(
                    output_mp4=self.current_session.screen_file,
                    window_title=capture_window_title,
                    window_hwnd=capture_window_hwnd,
                    fps=fps,
                    resolution=resolution,
                )
                if not started:
                    print("[SessionManager] Fallback a grabación de escritorio completo...")
                    self.screen_recorder.start_recording(
                        output_mp4=self.current_session.screen_file,
                        fps=fps,
                        resolution=resolution,
                    )
            else:
                self.screen_recorder.start_recording(
                    output_mp4=self.current_session.screen_file,
                    fps=fps,
                    resolution=resolution,
                )

        self._is_recording = True
        return self.current_session

    def pause_session(self) -> None:
        if self._is_recording:
            self.audio_recorder.pause()

    def resume_session(self) -> None:
        if self._is_recording:
            self.audio_recorder.resume()

    def stop_session(self) -> Optional[Session]:
        """Detiene la grabación y finaliza la sesión."""
        if not self._is_recording or not self.current_session:
            return None

        # Detener audio
        try:
            self.audio_recorder.stop()
        except Exception as e:
            print(f"Error deteniendo grabador de audio: {e}")

        # Detener video si estaba activo (en cualquiera de los dos grabadores)
        try:
            if self.window_recorder.is_recording:
                self.window_recorder.stop()
        except Exception as e:
            print(f"Error deteniendo grabador de ventana: {e}")

        try:
            if self.screen_recorder.is_recording:
                self.screen_recorder.stop()
        except Exception as e:
            print(f"Error deteniendo grabador de pantalla: {e}")

        self.current_session.metadata.ended_at = datetime.now().isoformat()
        # Calcular duración
        try:
            start = datetime.fromisoformat(self.current_session.metadata.started_at)
            end = datetime.fromisoformat(self.current_session.metadata.ended_at)
            self.current_session.metadata.duration_seconds = (end - start).total_seconds()
        except Exception:
            pass

        self.current_session.save_metadata()
        completed_session = self.current_session
        self.current_session = None
        self._is_recording = False

        return completed_session

    def import_external_media(
        self,
        media_path: Path,
        campaign_name: Optional[str] = None,
    ) -> Optional[Session]:
        """
        Importa un archivo de video o audio externo, extrae la pista de audio a 16 kHz Mono
        con FFmpeg y crea una sesión estándar lista para transcribir y resumir.
        """
        media_path = Path(media_path)
        if not media_path.exists():
            print(f"[SessionManager] Archivo no encontrado: {media_path}")
            return None

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        session_id = f"session_{timestamp}_imported"
        session_folder = self.sessions_dir / session_id
        session_folder.mkdir(parents=True, exist_ok=True)

        session = Session(session_folder)
        final_campaign = campaign_name.strip() if campaign_name and campaign_name.strip() else media_path.stem
        session.metadata.campaign = final_campaign
        session.metadata.started_at = datetime.now().isoformat()
        session.metadata.devices_used["imported_from"] = media_path.name
        session.metadata.devices_used["source_path"] = str(media_path.resolve())

        # Extraer y optimizar audio a audio.wav
        success = FFmpegHelper.extract_audio_to_wav(media_path, session.audio_file)
        if not success or not session.audio_file.exists():
            print(f"[SessionManager] Falló la extracción de audio para: {media_path}")
            try:
                import shutil
                shutil.rmtree(session_folder)
            except Exception:
                pass
            return None

        # Obtener duración del WAV generado
        duration = FFmpegHelper.get_wav_duration(session.audio_file)
        session.metadata.duration_seconds = duration
        session.metadata.has_audio = True

        # Verificar si es un archivo de video
        video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv", ".m4v"}
        is_video = media_path.suffix.lower() in video_extensions
        if is_video:
            session.metadata.has_screen = True
            session.metadata.devices_used["screen_mode"] = "external_video"
            # Intentar crear un enlace duro (hardlink) en NTFS para tener screen.mp4 sin duplicar espacio
            try:
                import os
                if not session.screen_file.exists():
                    os.link(str(media_path.resolve()), str(session.screen_file))
            except Exception:
                pass

        session.metadata.ended_at = datetime.now().isoformat()
        session.save_metadata()
        return session

