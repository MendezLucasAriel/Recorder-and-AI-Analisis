import customtkinter as ctk
from pathlib import Path
from recorder.session_manager import SessionManager
from .recorder_tab import RecorderTab
from .sessions_tab import SessionsTab
from .settings_tab import SettingsTab


class App(ctk.CTk):
    """Ventana principal de la aplicación D&D Session Recorder & AI Summarizer."""

    def __init__(self):
        super().__init__()

        # Configuración estética global
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("🎲 D&D Session Recorder & AI Chronicler")
        self.geometry("1100x720")
        self.minsize(900, 600)

        # Session Manager común
        sessions_path = Path(__file__).resolve().parent.parent / "sessions"
        self.session_manager = SessionManager(sessions_dir=sessions_path)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._init_ui()

    def _init_ui(self):
        # Header superior con branding
        header = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color=("#1f1f1f", "#141414"))
        header.pack(fill="x", side="top")

        lbl_logo = ctk.CTkLabel(
            header,
            text="⚔️ D&D CHRONICLER",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#e74c3c",
        )
        lbl_logo.pack(side="left", padx=20, pady=10)

        lbl_slogan = ctk.CTkLabel(
            header,
            text="Foundry VTT + Discord Session Recorder & AI Summarizer",
            font=ctk.CTkFont(size=12),
            text_color="#7f8c8d",
        )
        lbl_slogan.pack(side="left", padx=5, pady=10)

        # Tabview principal
        self.tabview = ctk.CTkTabview(self, corner_radius=8)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        tab_recorder = self.tabview.add("🎙️ Grabar")
        tab_sessions = self.tabview.add("📜 Sesiones y Resúmenes")
        tab_settings = self.tabview.add("⚙️ Ajustes")

        # Inicializar vistas dentro de sus tabs
        self.sessions_view = SessionsTab(tab_sessions, session_manager=self.session_manager)
        self.sessions_view.pack(fill="both", expand=True)

        self.recorder_view = RecorderTab(
            tab_recorder,
            session_manager=self.session_manager,
            on_session_saved=self._on_session_saved,
        )
        self.recorder_view.pack(fill="both", expand=True)

        self.settings_view = SettingsTab(tab_settings)
        self.settings_view.pack(fill="both", expand=True)

    def _on_session_saved(self, saved_session):
        # Actualizar la lista en la pestaña de sesiones y seleccionarla
        self.sessions_view.refresh_session_list()
        self.sessions_view.select_session(saved_session)
        # Cambiar a la pestaña de sesiones automáticamente
        self.tabview.set("📜 Sesiones y Resúmenes")

    def _on_close(self):
        try:
            if self.session_manager.is_recording:
                self.session_manager.stop_session()
        except Exception:
            pass
        self.destroy()
