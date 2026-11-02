import customtkinter as ctk

from work_recorder.recorder.work_session_manager import WorkSessionManager
from .record_tab import WorkRecorderTab
from .meetings_tab import MeetingsTab
from .settings_tab import WorkSettingsTab


class WorkRecorderApp(ctk.CTk):
    """Ventana principal de Work Recorder para reuniones corporativas y profesionales."""

    def __init__(self):
        super().__init__()

        self.title("Work Recorder — Grabador y Minutas Inteligentes para Reuniones")
        self.geometry("1120x740")
        self.minsize(980, 640)

        # Configuración visual moderna (Dark mode por defecto)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.session_manager = WorkSessionManager()

        self._init_ui()

    def _init_ui(self):
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=12, pady=12)

        tab_record = self.tabview.add("🎙️ Grabar Reunión")
        tab_meetings = self.tabview.add("💼 Mis Reuniones y Minutas")
        tab_settings = self.tabview.add("⚙️ Ajustes y Modelos")

        # 1. Pestaña de reuniones y minutas (instanciar primero para callback)
        self.meetings_tab = MeetingsTab(tab_meetings, session_manager=self.session_manager)
        self.meetings_tab.pack(fill="both", expand=True)

        # 2. Pestaña de grabación en vivo
        self.record_tab = WorkRecorderTab(
            tab_record,
            session_manager=self.session_manager,
            on_session_saved=self._on_session_saved,
        )
        self.record_tab.pack(fill="both", expand=True)

        # 3. Pestaña de ajustes
        self.settings_tab = WorkSettingsTab(tab_settings)
        self.settings_tab.pack(fill="both", expand=True)

        # Iniciar en la pestaña de grabación
        self.tabview.set("🎙️ Grabar Reunión")

    def _on_session_saved(self, session):
        """Al terminar de grabar una reunión, refresca la lista y salta a la vista de detalles."""
        self.meetings_tab.refresh_session_list()
        self.meetings_tab.select_session(session)
        self.tabview.set("💼 Mis Reuniones y Minutas")
