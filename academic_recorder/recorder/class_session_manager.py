import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from academic_recorder.models.class_session import ClassSession, ClassSessionMetadata
from recorder.audio_recorder import AudioRecorder
from utils.ffmpeg_helper import FFmpegHelper
from .class_video_recorder import ClassVideoRecorder


class ClassSessionManager:
    """Gestiona el ciclo de vida de las grabaciones de clases universitarias."""

    def __init__(self, classes_dir: Optional[Path] = None):
        if classes_dir is None:
            base_dir = Path(__file__).resolve().parent.parent
            classes_dir = base_dir / "classes"

        self.classes_dir = Path(classes_dir)
        self.classes_dir.mkdir(parents=True, exist_ok=True)

        self.audio_recorder = AudioRecorder()
        self.video_recorder = ClassVideoRecorder()

        self.current_session: Optional[ClassSession] = None
        self._is_recording = False

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def list_sessions(self) -> List[ClassSession]:
        sessions = []
        if not self.classes_dir.exists():
            return sessions

        for folder in self.classes_dir.iterdir():
            if folder.is_dir() and (folder / "session.json").exists():
                try:
                    s = ClassSession(folder)
                    sessions.append(s)
                except Exception:
                    pass

        sessions.sort(key=lambda s: s.metadata.started_at, reverse=True)
        return sessions

    def start_session(
        self,
        subject: str = "Física I",
        professor: str = "",
        discipline: str = "Física",
        record_video: bool = True,
        video_mode: str = "window",
        capture_window_title: Optional[str] = None,
        capture_window_hwnd: Optional[int] = None,
        fps: int = 18,
        resolution: str = "1920x1080",
        mic_index: Optional[int] = None,
        loopback_index: Optional[int] = None,
    ) -> ClassSession:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        safe_subject = "".join(c for c in subject if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
        session_id = f"clase_{safe_subject}_{timestamp}"
        session_folder = self.classes_dir / session_id
        session_folder.mkdir(parents=True, exist_ok=True)

        self.current_session = ClassSession(session_folder)
        self.current_session.metadata.subject = subject
        self.current_session.metadata.professor = professor
        self.current_session.metadata.discipline = discipline
        self.current_session.metadata.started_at = datetime.now().isoformat()
        self.current_session.metadata.has_video = record_video
        self.current_session.metadata.video_fps = fps
        self.current_session.metadata.resolution = resolution

        if record_video:
            self.current_session.metadata.devices_used["video_mode"] = video_mode
            if capture_window_title:
                self.current_session.metadata.devices_used["capture_window"] = capture_window_title

        self.current_session.save_metadata()

        # Iniciar audio (audio del sistema para el profesor + micrófono del alumno)
        self.audio_recorder.start_recording(
            output_wav=self.current_session.audio_file,
            mic_index=mic_index,
            loopback_index=loopback_index,
        )

        # Iniciar video a 1080p @ 15-21 FPS
        if record_video:
            self.video_recorder.start_recording(
                output_mp4=self.current_session.video_file,
                mode=video_mode,
                window_title=capture_window_title,
                window_hwnd=capture_window_hwnd,
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

    def stop_session(self) -> Optional[ClassSession]:
        if not self._is_recording or not self.current_session:
            return None

        try:
            self.audio_recorder.stop()
        except Exception as e:
            print(f"[ClassSessionManager] Error parando audio: {e}")

        try:
            if self.video_recorder.is_recording:
                self.video_recorder.stop()
        except Exception as e:
            print(f"[ClassSessionManager] Error parando video: {e}")

        self.current_session.metadata.ended_at = datetime.now().isoformat()
        try:
            start = datetime.fromisoformat(self.current_session.metadata.started_at)
            end = datetime.fromisoformat(self.current_session.metadata.ended_at)
            self.current_session.metadata.duration_seconds = (end - start).total_seconds()
        except Exception:
            pass

        self.current_session.save_metadata()
        completed = self.current_session
        self.current_session = None
        self._is_recording = False
        return completed

    def import_external_media(
        self,
        media_path: Path,
        subject: str = "Clase Importada",
        professor: str = "",
        discipline: str = "Matemáticas",
    ) -> Optional[ClassSession]:
        media_path = Path(media_path).resolve()
        if not media_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        safe_subject = "".join(c for c in subject if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
        session_id = f"clase_{safe_subject}_{timestamp}_import"
        session_folder = self.classes_dir / session_id
        session_folder.mkdir(parents=True, exist_ok=True)

        session = ClassSession(session_folder)
        session.metadata.subject = subject
        session.metadata.professor = professor
        session.metadata.discipline = discipline
        session.metadata.started_at = datetime.now().isoformat()
        session.metadata.devices_used["imported_from"] = media_path.name
        session.metadata.devices_used["source_path"] = str(media_path)

        success = FFmpegHelper.extract_audio_to_wav(media_path, session.audio_file)
        if not success or not session.audio_file.exists():
            try:
                import shutil
                shutil.rmtree(session_folder)
            except Exception:
                pass
            return None

        duration = FFmpegHelper.get_wav_duration(session.audio_file)
        session.metadata.duration_seconds = duration
        session.metadata.has_audio = True

        video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv", ".m4v"}
        if media_path.suffix.lower() in video_extensions:
            session.metadata.has_video = True
            session.metadata.devices_used["video_mode"] = "external_video"
            try:
                import os
                if not session.video_file.exists():
                    os.link(str(media_path), str(session.video_file))
            except Exception:
                try:
                    import shutil
                    shutil.copy2(str(media_path), str(session.video_file))
                except Exception:
                    pass

        session.metadata.ended_at = datetime.now().isoformat()
        session.save_metadata()
        return session
