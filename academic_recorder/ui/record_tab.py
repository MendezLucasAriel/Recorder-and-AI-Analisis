import time
from typing import Optional, Callable, List, Dict, Any
import customtkinter as ctk

from academic_recorder.recorder.class_session_manager import ClassSessionManager
from recorder.audio_recorder import AudioRecorder
from utils.window_list import list_visible_windows


class ClassRecorderTab(ctk.CTkFrame):
    """Pestaña de grabación en vivo para clases universitarias de Física y Matemáticas."""

    def __init__(self, master, session_manager: ClassSessionManager, on_session_saved: Optional[Callable] = None):
        super().__init__(master, fg_color="transparent")
        self.session_manager = session_manager
        self.on_session_saved = on_session_saved

        self.available_devices = AudioRecorder.get_available_devices()
        self._windows_cache: List[Dict[str, Any]] = []

        self._init_ui()
        self._setup_callbacks()

    def _init_ui(self):
        # Card contenedor principal
        card = ctk.CTkFrame(self, corner_radius=12, fg_color=("#2b2b2b", "#1e1e1e"))
        card.pack(pady=15, padx=25, fill="both", expand=True)

        # Encabezado
        title_label = ctk.CTkLabel(
            card,
            text="🎓 Grabador de Clases Universitarias",
            font=ctk.CTkFont(size=23, weight="bold"),
        )
        title_label.pack(pady=(15, 3))

        subtitle = ctk.CTkLabel(
            card,
            text="Captura en alta nitidez 1080p (15-21 FPS) con audio dual (voz del docente + tu micrófono)",
            font=ctk.CTkFont(size=12),
            text_color="#bdc3c7",
        )
        subtitle.pack(pady=(0, 15))

        # Panel de ajustes de la clase
        settings_frame = ctk.CTkFrame(card, fg_color="transparent")
        settings_frame.pack(fill="x", padx=30, pady=5)
        settings_frame.grid_columnconfigure(1, weight=1)

        # 1. Materia y Profesor
        ctk.CTkLabel(settings_frame, text="Materia / Asignatura:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", pady=4, padx=5
        )
        self.entry_subject = ctk.CTkEntry(settings_frame, placeholder_text="Ej: Física II, Álgebra Lineal, Análisis Matemático")
        self.entry_subject.insert(0, "Física II")
        self.entry_subject.grid(row=0, column=1, sticky="ew", pady=4, padx=5)

        ctk.CTkLabel(settings_frame, text="Docente / Cátedra:").grid(
            row=1, column=0, sticky="w", pady=4, padx=5
        )
        self.entry_professor = ctk.CTkEntry(settings_frame, placeholder_text="Ej: Dr. González / Cátedra A")
        self.entry_professor.grid(row=1, column=1, sticky="ew", pady=4, padx=5)

        # 2. Disciplina (Física / Matemáticas / General)
        ctk.CTkLabel(settings_frame, text="Disciplina / Preset:", font=ctk.CTkFont(weight="bold")).grid(
            row=2, column=0, sticky="w", pady=6, padx=5
        )
        self.discipline_var = ctk.StringVar(value="Física")
        disc_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        disc_frame.grid(row=2, column=1, sticky="w", pady=6, padx=5)

        self.radio_fisica = ctk.CTkRadioButton(
            disc_frame, text="⚛️ Física", variable=self.discipline_var, value="Física"
        )
        self.radio_fisica.pack(side="left", padx=(0, 15))

        self.radio_mate = ctk.CTkRadioButton(
            disc_frame, text="📐 Matemáticas", variable=self.discipline_var, value="Matemáticas"
        )
        self.radio_mate.pack(side="left", padx=15)

        self.radio_gen = ctk.CTkRadioButton(
            disc_frame, text="🔬 General STEM", variable=self.discipline_var, value="General"
        )
        self.radio_gen.pack(side="left", padx=15)

        # 3. Dispositivos de Audio
        ctk.CTkLabel(settings_frame, text="Audio Docente (Sistema):").grid(
            row=3, column=0, sticky="w", pady=4, padx=5
        )
        loopback_names = [f"[{d['index']}] {d['name']}" for d in self.available_devices["loopbacks"]]
        if not loopback_names:
            loopback_names = ["(Default WASAPI Loopback)"]
        self.loopback_combo = ctk.CTkComboBox(settings_frame, values=loopback_names)
        self.loopback_combo.grid(row=3, column=1, sticky="ew", pady=4, padx=5)

        ctk.CTkLabel(settings_frame, text="Tu Micrófono (Preguntas):").grid(
            row=4, column=0, sticky="w", pady=4, padx=5
        )
        mic_names = [f"[{d['index']}] {d['name']}" for d in self.available_devices["microphones"]]
        if not mic_names:
            mic_names = ["(Default Mic)"]
        self.mic_combo = ctk.CTkComboBox(settings_frame, values=mic_names)
        self.mic_combo.grid(row=4, column=1, sticky="ew", pady=4, padx=5)

        # 4. Grabación de Video 1080p
        self.record_video_var = ctk.BooleanVar(value=True)
        self.chk_video = ctk.CTkCheckBox(
            settings_frame,
            text="Grabar video de la clase a 1080p (Pizarras y Diapositivas)",
            variable=self.record_video_var,
            font=ctk.CTkFont(weight="bold"),
            command=self._on_video_chk_toggled,
        )
        self.chk_video.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 4), padx=5)

        # Opciones avanzadas de Video
        self.video_panel = ctk.CTkFrame(settings_frame, fg_color=("#383838", "#242424"), corner_radius=8)
        self.video_panel.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(2, 6), padx=5)

        # Fila de Modo y Framerate
        row_v1 = ctk.CTkFrame(self.video_panel, fg_color="transparent")
        row_v1.pack(fill="x", padx=10, pady=(6, 4))

        ctk.CTkLabel(row_v1, text="Modo de captura:").pack(side="left", padx=(0, 10))
        self.video_mode_var = ctk.StringVar(value="window")

        self.rad_win = ctk.CTkRadioButton(
            row_v1,
            text="🎯 Ventana de la clase (Inmune a Alt-Tab)",
            variable=self.video_mode_var,
            value="window",
            command=self._on_video_mode_changed,
        )
        self.rad_win.pack(side="left", padx=5)

        self.rad_desk = ctk.CTkRadioButton(
            row_v1,
            text="🖥️ Pantalla completa",
            variable=self.video_mode_var,
            value="desktop",
            command=self._on_video_mode_changed,
        )
        self.rad_desk.pack(side="left", padx=15)

        ctk.CTkLabel(row_v1, text="Framerate:").pack(side="left", padx=(15, 6))
        self.fps_combo = ctk.CTkSegmentedButton(row_v1, values=["15 FPS", "18 FPS", "21 FPS"])
        self.fps_combo.set("18 FPS")
        self.fps_combo.pack(side="left")

        # Fila de selección de ventana
        self.row_v2 = ctk.CTkFrame(self.video_panel, fg_color="transparent")
        self.row_v2.pack(fill="x", padx=10, pady=(4, 6))

        ctk.CTkLabel(self.row_v2, text="Ventana objetivo:").pack(side="left", padx=(0, 10))
        self.window_combo = ctk.CTkComboBox(self.row_v2, values=["(Seleccionar ventana)"], width=380)
        self.window_combo.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_refresh_win = ctk.CTkButton(
            self.row_v2, text="🔄", width=36, height=28, command=self._refresh_window_list
        )
        self.btn_refresh_win.pack(side="left")

        self._refresh_window_list()

        # Cronómetro
        self.lbl_timer = ctk.CTkLabel(
            card,
            text="00:00:00",
            font=ctk.CTkFont(size=44, weight="bold"),
            text_color="#e0e0e0",
        )
        self.lbl_timer.pack(pady=(12, 4))

        # Vúmetros
        vumeter_frame = ctk.CTkFrame(card, fg_color="transparent")
        vumeter_frame.pack(fill="x", padx=60, pady=4)

        ctk.CTkLabel(vumeter_frame, text="Docente:", width=75, anchor="e").grid(row=0, column=0, padx=5, pady=2)
        self.sys_meter = ctk.CTkProgressBar(vumeter_frame, width=280, progress_color="#3498db")
        self.sys_meter.set(0)
        self.sys_meter.grid(row=0, column=1, padx=5, pady=2)

        ctk.CTkLabel(vumeter_frame, text="Micrófono:", width=75, anchor="e").grid(row=1, column=0, padx=5, pady=2)
        self.mic_meter = ctk.CTkProgressBar(vumeter_frame, width=280, progress_color="#2ecc71")
        self.mic_meter.set(0)
        self.mic_meter.grid(row=1, column=1, padx=5, pady=2)

        # Botones de control
        btn_bar = ctk.CTkFrame(card, fg_color="transparent")
        btn_bar.pack(pady=15)

        self.btn_record = ctk.CTkButton(
            btn_bar,
            text="⏺️ Iniciar Clase",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#c0392b",
            hover_color="#e74c3c",
            width=170,
            height=42,
            command=self._on_record_clicked,
        )
        self.btn_record.grid(row=0, column=0, padx=8)

        self.btn_pause = ctk.CTkButton(
            btn_bar,
            text="⏸️ Pausar",
            font=ctk.CTkFont(size=14),
            fg_color="#7f8c8d",
            state="disabled",
            width=110,
            height=42,
            command=self._on_pause_clicked,
        )
        self.btn_pause.grid(row=0, column=1, padx=8)

        self.btn_stop = ctk.CTkButton(
            btn_bar,
            text="⏹️ Finalizar Clase",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#27ae60",
            hover_color="#2ecc71",
            state="disabled",
            width=160,
            height=42,
            command=self._on_stop_clicked,
        )
        self.btn_stop.grid(row=0, column=2, padx=8)

        # Estado informativo
        self.lbl_status = ctk.CTkLabel(
            card,
            text="Listo para iniciar grabación de clase.",
            font=ctk.CTkFont(size=12),
            text_color="#95a5a6",
        )
        self.lbl_status.pack(pady=(0, 10))

    def _setup_callbacks(self):
        self.session_manager.audio_recorder.on_duration_update = self._on_duration_update
        self.session_manager.audio_recorder.on_peak_update = self._on_peak_update

    def _on_duration_update(self, seconds: float):
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        self.after(0, lambda: self.lbl_timer.configure(text=time_str))

    def _on_peak_update(self, mic_peak: float, sys_peak: float):
        m = min(1.0, max(0.0, mic_peak * 1.5))
        s = min(1.0, max(0.0, sys_peak * 1.5))
        self.after(0, lambda: (self.mic_meter.set(m), self.sys_meter.set(s)))

    def _on_video_chk_toggled(self):
        if self.record_video_var.get():
            self.video_panel.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(2, 6), padx=5)
            self._refresh_window_list()
        else:
            self.video_panel.grid_forget()

    def _on_video_mode_changed(self):
        mode = self.video_mode_var.get()
        if mode == "window":
            self.window_combo.configure(state="normal")
            self.btn_refresh_win.configure(state="normal")
        else:
            self.window_combo.configure(state="disabled")
            self.btn_refresh_win.configure(state="disabled")

    def _refresh_window_list(self):
        try:
            windows = list_visible_windows()
            self._windows_cache = windows
            if not windows:
                self.window_combo.configure(values=["(No se detectaron ventanas abiertas)"])
                self.window_combo.set("(No se detectaron ventanas abiertas)")
                return

            display_values = [f"[{w['hwnd']}] {w['title']}" for w in windows]
            self.window_combo.configure(values=display_values)

            # Auto-seleccionar si detecta Zoom, Teams, Meet o PDF
            preferred = None
            for dv in display_values:
                low = dv.lower()
                if any(k in low for k in ("zoom", "teams", "meet", "acrobat", "sumatra", "edge", "chrome", "firefox")):
                    preferred = dv
                    break

            if preferred:
                self.window_combo.set(preferred)
            elif display_values:
                self.window_combo.set(display_values[0])
        except Exception as e:
            print(f"[ClassRecorderTab] Error refrescando ventanas: {e}")

    def _get_selected_index(self, combo_text: str) -> Optional[int]:
        if combo_text.startswith("["):
            try:
                idx_str = combo_text[1:].split("]")[0]
                return int(idx_str)
            except Exception:
                pass
        return None

    def _on_record_clicked(self):
        subject = self.entry_subject.get().strip() or "Clase de Ciencias"
        professor = self.entry_professor.get().strip()
        discipline = self.discipline_var.get()
        record_video = self.record_video_var.get()
        video_mode = self.video_mode_var.get()
        fps_str = self.fps_combo.get()
        fps = int(fps_str.split()[0]) if "FPS" in fps_str else 18

        loopback_idx = self._get_selected_index(self.loopback_combo.get())
        mic_idx = self._get_selected_index(self.mic_combo.get())

        selected_win_title = None
        selected_win_hwnd = None
        if record_video and video_mode == "window":
            selected_text = self.window_combo.get().strip()
            if selected_text.startswith("[") and "]" in selected_text:
                try:
                    hwnd_str = selected_text[1:].split("]")[0]
                    selected_win_hwnd = int(hwnd_str)
                    selected_win_title = selected_text.split("]", 1)[1].strip()
                except Exception:
                    pass
            if not selected_win_title:
                selected_win_title = selected_text

        self.session_manager.start_session(
            subject=subject,
            professor=professor,
            discipline=discipline,
            record_video=record_video,
            video_mode=video_mode,
            capture_window_title=selected_win_title,
            capture_window_hwnd=selected_win_hwnd,
            fps=fps,
            resolution="1920x1080",
            mic_index=mic_idx,
            loopback_index=loopback_idx,
        )

        self.btn_record.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="⏸️ Pausar", fg_color="#f39c12")
        self.btn_stop.configure(state="normal")
        self.entry_subject.configure(state="disabled")
        self.entry_professor.configure(state="disabled")
        self.radio_fisica.configure(state="disabled")
        self.radio_mate.configure(state="disabled")
        self.radio_gen.configure(state="disabled")
        self.chk_video.configure(state="disabled")
        self.rad_win.configure(state="disabled")
        self.rad_desk.configure(state="disabled")
        self.fps_combo.configure(state="disabled")
        self.window_combo.configure(state="disabled")
        self.btn_refresh_win.configure(state="disabled")
        self.loopback_combo.configure(state="disabled")
        self.mic_combo.configure(state="disabled")

        self.lbl_timer.configure(text_color="#e74c3c")
        target_info = f" ({video_mode} @ {fps} FPS)" if record_video else " (Solo audio)"
        self.lbl_status.configure(
            text=f"🔴 Grabando clase de {subject} ({discipline}){target_info}...",
            text_color="#e74c3c",
        )

    def _on_pause_clicked(self):
        if self.session_manager.audio_recorder.is_paused:
            self.session_manager.resume_session()
            self.btn_pause.configure(text="⏸️ Pausar", fg_color="#f39c12")
            self.lbl_status.configure(text="🔴 Grabando clase en vivo...", text_color="#e74c3c")
        else:
            self.session_manager.pause_session()
            self.btn_pause.configure(text="▶️ Reanudar", fg_color="#2980b9")
            self.lbl_status.configure(text="⏸️ Clase pausada (recreo / intervalo).", text_color="#f39c12")

    def _on_stop_clicked(self):
        self.lbl_status.configure(text="Guardando pistas de audio y video 1080p...", text_color="#3498db")
        self.update_idletasks()

        saved = self.session_manager.stop_session()

        self.btn_record.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="⏸️ Pausar", fg_color="#7f8c8d")
        self.btn_stop.configure(state="disabled")
        self.entry_subject.configure(state="normal")
        self.entry_professor.configure(state="normal")
        self.radio_fisica.configure(state="normal")
        self.radio_mate.configure(state="normal")
        self.radio_gen.configure(state="normal")
        self.chk_video.configure(state="normal")
        self.rad_win.configure(state="normal")
        self.rad_desk.configure(state="normal")
        self.fps_combo.configure(state="normal")
        self._on_video_mode_changed()
        self.loopback_combo.configure(state="normal")
        self.mic_combo.configure(state="normal")

        self.lbl_timer.configure(text_color="#e0e0e0")
        self.mic_meter.set(0)
        self.sys_meter.set(0)

        if saved:
            self.lbl_status.configure(
                text=f"✅ Clase guardada: {saved.metadata.subject}. Abre la pestaña 'Mis Clases' para procesar.",
                text_color="#2ecc71",
            )
            if self.on_session_saved:
                self.on_session_saved(saved)
        else:
            self.lbl_status.configure(text="Grabación finalizada.", text_color="#95a5a6")
