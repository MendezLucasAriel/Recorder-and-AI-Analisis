import customtkinter as ctk

from academic_recorder.recorder.class_session_manager import ClassSessionManager
from .record_tab import ClassRecorderTab
from .classes_tab import ClassesTab
from .settings_tab import ClassSettingsTab


class AcademicRecorderApp(ctk.CTk):
    """Ventana principal de Academic Recorder."""

    def __init__(self):
        super().__init__()

        self.title("Academic Recorder — Asistente de Clases Universitarias (Física y Matemáticas)")
        self.geometry("1100x720")
        self.minsize(980, 640)

        # Configuración visual moderna (Dark mode por defecto)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.session_manager = ClassSessionManager()

        self._init_ui()

    def _init_ui(self):
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=12, pady=12)

        tab_record = self.tabview.add("🎙️ Grabar Clase")
        tab_classes = self.tabview.add("📚 Mis Clases y Apuntes")
        tab_settings = self.tabview.add("⚙️ Ajustes y Materias")

        # 1. Pestaña de clases (instanciar primero para callbacks)
        self.classes_tab = ClassesTab(tab_classes, session_manager=self.session_manager)
        self.classes_tab.pack(fill="both", expand=True)

        # 2. Pestaña de grabación
        self.record_tab = ClassRecorderTab(
            tab_record,
            session_manager=self.session_manager,
            on_session_saved=self._on_session_saved,
        )
        self.record_tab.pack(fill="both", expand=True)

        # 3. Pestaña de ajustes
        self.settings_tab = ClassSettingsTab(tab_settings)
        self.settings_tab.pack(fill="both", expand=True)

        # Iniciar en la pestaña de grabación
        self.tabview.set("🎙️ Grabar Clase")

    def _on_session_saved(self, session):
        """Al terminar de grabar, refresca la lista y cambia a Mis Clases."""
        self.classes_tab.refresh_session_list()
        self.classes_tab.select_session(session)
        self.tabview.set("📚 Mis Clases y Apuntes")
