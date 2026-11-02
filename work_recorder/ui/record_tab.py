from typing import Optional, Callable, List, Dict, Any
import customtkinter as ctk

from work_recorder.recorder.work_session_manager import WorkSessionManager
from recorder.audio_recorder import AudioRecorder
from utils.window_list import list_visible_windows


class WorkRecorderTab(ctk.CTkFrame):
    """Pestaña de grabación en vivo para reuniones de trabajo y llamadas corporativas."""

    def __init__(self, master, session_manager: WorkSessionManager, on_session_saved: Optional[Callable] = None):
        super().__init__(master, fg_color="transparent")
        self.session_manager = session_manager
        self.on_session_saved = on_session_saved

        self.available_devices = AudioRecorder.get_available_devices()
        self._windows_cache: List[Dict[str, Any]] = []

        self._init_ui()
        self._setup_callbacks()

    def _init_ui(self):
        card = ctk.CTkFrame(self, corner_radius=12, fg_color=("#2b2b2b", "#1e1e1e"))
        card.pack(pady=15, padx=25, fill="both", expand=True)

        title_label = ctk.CTkLabel(
            card,
            text="💼 Grabador de Reuniones y Llamadas de Trabajo",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title_label.pack(pady=(15, 3))

        subtitle = ctk.CTkLabel(
            card,
            text="Captura audio dual (llamada en Teams/Meet/Zoom + tu micrófono) y genera minutas con tareas claras.",
            font=ctk.CTkFont(size=12),
            text_color="#bdc3c7",
        )
        subtitle.pack(pady=(0, 15))

        settings_frame = ctk.CTkFrame(card, fg_color="transparent")
        settings_frame.pack(fill="x", padx=30, pady=5)
        settings_frame.grid_columnconfigure(1, weight=1)

        # 1. Asunto / Nombre de la reunión
        ctk.CTkLabel(settings_frame, text="Asunto / Reunión:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", pady=4, padx=5
        )
        self.entry_name = ctk.CTkEntry(settings_frame, placeholder_text="Ej: Sync Semanal de Producto, Definición de Alcance Cliente X")
        self.entry_name.insert(0, "Sync de Equipo")
        self.entry_name.grid(row=0, column=1, sticky="ew", pady=4, padx=5)

        # 2. Tipo de reunión
        ctk.CTkLabel(settings_frame, text="Tipo de Reunión:").grid(
            row=1, column=0, sticky="w", pady=4, padx=5
        )
        self.combo_type = ctk.CTkComboBox(
            settings_frame,
            values=[
                "Sync / Daily",
                "Reunión con Cliente",
                "Planificación / Sprint",
                "1-on-1 / Feedback",
                "Estratégica / Dirección",
                "General",
            ],
            width=260,
        )
        self.combo_type.set("Sync / Daily")
        self.combo_type.grid(row=1, column=1, sticky="w", pady=4, padx=5)

        # 3. Participantes
        ctk.CTkLabel(settings_frame, text="Participantes (opcional):").grid(
            row=2, column=0, sticky="w", pady=4, padx=5
        )
        self.entry_participants = ctk.CTkEntry(settings_frame, placeholder_text="Ej: Martín, Sofía, Lucas, Cliente")
        self.entry_participants.grid(row=2, column=1, sticky="ew", pady=4, padx=5)

        # 4. Audio
        ctk.CTkLabel(settings_frame, text="Audio Llamada (Sistema):").grid(
            row=3, column=0, sticky="w", pady=4, padx=5
        )
        loopback_names = [f"[{d['index']}] {d['name']}" for d in self.available_devices["loopbacks"]]
        if not loopback_names:
            loopback_names = ["(Default WASAPI Loopback)"]
        self.loopback_combo = ctk.CTkComboBox(settings_frame, values=loopback_names)
        self.loopback_combo.grid(row=3, column=1, sticky="ew", pady=4, padx=5)

        ctk.CTkLabel(settings_frame, text="Tu Micrófono:").grid(
            row=4, column=0, sticky="w", pady=4, padx=5
        )
        mic_names = [f"[{d['index']}] {d['name']}" for d in self.available_devices["microphones"]]
        if not mic_names:
            mic_names = ["(Default Mic)"]
        self.mic_combo = ctk.CTkComboBox(settings_frame, values=mic_names)
        self.mic_combo.grid(row=4, column=1, sticky="ew", pady=4, padx=5)

        # 5. Video opcional
        self.record_video_var = ctk.BooleanVar(value=False)
        self.chk_video = ctk.CTkCheckBox(
            settings_frame,
            text="Grabar pantalla compartida / demo (Video ligero 15 FPS)",
            variable=self.record_video_var,
            font=ctk.CTkFont(weight="bold"),
            command=self._on_video_chk_toggled,
        )
        self.chk_video.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 4), padx=5)

        self.video_panel = ctk.CTkFrame(settings_frame, fg_color=("#383838", "#242424"), corner_radius=8)

        row_v = ctk.CTkFrame(self.video_panel, fg_color="transparent")
        row_v.pack(fill="x", padx=10, pady=(6, 4))

        ctk.CTkLabel(row_v, text="Modo:").pack(side="left", padx=(0, 10))
        self.video_mode_var = ctk.StringVar(value="window")

        self.rad_win = ctk.CTkRadioButton(
            row_v,
            text="🎯 Ventana (Teams, Meet, Zoom, Slack)",
            variable=self.video_mode_var,
            value="window",
            command=self._on_video_mode_changed,
        )
        self.rad_win.pack(side="left", padx=5)

        self.rad_desk = ctk.CTkRadioButton(
            row_v,
            text="🖥️ Pantalla completa",
            variable=self.video_mode_var,
            value="desktop",
            command=self._on_video_mode_changed,
        )
        self.rad_desk.pack(side="left", padx=15)

        row_w = ctk.CTkFrame(self.video_panel, fg_color="transparent")
        row_w.pack(fill="x", padx=10, pady=(4, 6))

        ctk.CTkLabel(row_w, text="Ventana objetivo:").pack(side="left", padx=(0, 10))
        self.window_combo = ctk.CTkComboBox(row_w, values=["(Seleccionar ventana)"], width=380)
        self.window_combo.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_refresh_win = ctk.CTkButton(
            row_w, text="🔄", width=36, height=28, command=self._refresh_window_list
        )
        self.btn_refresh_win.pack(side="left")

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

        ctk.CTkLabel(vumeter_frame, text="Llamada:", width=75, anchor="e").grid(row=0, column=0, padx=5, pady=2)
        self.sys_meter = ctk.CTkProgressBar(vumeter_frame, width=280, progress_color="#3498db")
        self.sys_meter.set(0)
        self.sys_meter.grid(row=0, column=1, padx=5, pady=2)

        ctk.CTkLabel(vumeter_frame, text="Tu Voz:", width=75, anchor="e").grid(row=1, column=0, padx=5, pady=2)
        self.mic_meter = ctk.CTkProgressBar(vumeter_frame, width=280, progress_color="#2ecc71")
        self.mic_meter.set(0)
        self.mic_meter.grid(row=1, column=1, padx=5, pady=2)

        # Botones de control
        btn_bar = ctk.CTkFrame(card, fg_color="transparent")
        btn_bar.pack(pady=15)

        self.btn_record = ctk.CTkButton(
            btn_bar,
            text="⏺️ Iniciar Grabación",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#c0392b",
            hover_color="#e74c3c",
            width=180,
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
            text="⏹️ Finalizar Reunión",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#27ae60",
            hover_color="#2ecc71",
            state="disabled",
            width=170,
            height=42,
            command=self._on_stop_clicked,
        )
        self.btn_stop.grid(row=0, column=2, padx=8)

        self.lbl_status = ctk.CTkLabel(
            card,
            text="Listo para grabar reunión.",
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
        self.after(0, lambda: self.lbl_timer.configure(text=f"{hrs:02d}:{mins:02d}:{secs:02d}"))

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

            preferred = None
            for dv in display_values:
                low = dv.lower()
                if any(k in low for k in ("teams", "zoom", "meet", "slack", "chrome", "edge")):
                    preferred = dv
                    break

            if preferred:
                self.window_combo.set(preferred)
            elif display_values:
                self.window_combo.set(display_values[0])
        except Exception:
            pass

    def _get_selected_index(self, combo_text: str) -> Optional[int]:
        if combo_text.startswith("["):
            try:
                idx_str = combo_text[1:].split("]")[0]
                return int(idx_str)
            except Exception:
                pass
        return None

    def _on_record_clicked(self):
        name = self.entry_name.get().strip() or "Reunión de Trabajo"
        m_type = self.combo_type.get()
        participants = self.entry_participants.get().strip()
        record_video = self.record_video_var.get()
        video_mode = self.video_mode_var.get()

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
            meeting_name=name,
            meeting_type=m_type,
            participants=participants,
            record_video=record_video,
            video_mode=video_mode,
            capture_window_title=selected_win_title,
            capture_window_hwnd=selected_win_hwnd,
            fps=15,
            mic_index=mic_idx,
            loopback_index=loopback_idx,
        )

        self.btn_record.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="⏸️ Pausar", fg_color="#f39c12")
        self.btn_stop.configure(state="normal")
        self.entry_name.configure(state="disabled")
        self.combo_type.configure(state="disabled")
        self.entry_participants.configure(state="disabled")
        self.chk_video.configure(state="disabled")
        self.rad_win.configure(state="disabled")
        self.rad_desk.configure(state="disabled")
        self.window_combo.configure(state="disabled")
        self.btn_refresh_win.configure(state="disabled")
        self.loopback_combo.configure(state="disabled")
        self.mic_combo.configure(state="disabled")

        self.lbl_timer.configure(text_color="#e74c3c")
        self.lbl_status.configure(
            text=f"🔴 Grabando '{name}' ({m_type})...",
            text_color="#e74c3c",
        )

    def _on_pause_clicked(self):
        if self.session_manager.audio_recorder.is_paused:
            self.session_manager.resume_session()
            self.btn_pause.configure(text="⏸️ Pausar", fg_color="#f39c12")
            self.lbl_status.configure(text="🔴 Grabando reunión en vivo...", text_color="#e74c3c")
        else:
            self.session_manager.pause_session()
            self.btn_pause.configure(text="▶️ Reanudar", fg_color="#2980b9")
            self.lbl_status.configure(text="⏸️ Grabación pausada.", text_color="#f39c12")

    def _on_stop_clicked(self):
        self.lbl_status.configure(text="Guardando reunión...", text_color="#3498db")
        self.update_idletasks()

        saved = self.session_manager.stop_session()

        self.btn_record.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="⏸️ Pausar", fg_color="#7f8c8d")
        self.btn_stop.configure(state="disabled")
        self.entry_name.configure(state="normal")
        self.combo_type.configure(state="normal")
        self.entry_participants.configure(state="normal")
        self.chk_video.configure(state="normal")
        self.rad_win.configure(state="normal")
        self.rad_desk.configure(state="normal")
        self._on_video_mode_changed()
        self.loopback_combo.configure(state="normal")
        self.mic_combo.configure(state="normal")

        self.lbl_timer.configure(text_color="#e0e0e0")
        self.mic_meter.set(0)
        self.sys_meter.set(0)

        if saved:
            self.lbl_status.configure(
                text=f"✅ Reunión guardada: {saved.metadata.meeting_name}. Ve a 'Reuniones y Minutas' para procesar.",
                text_color="#2ecc71",
            )
            if self.on_session_saved:
                self.on_session_saved(saved)
        else:
            self.lbl_status.configure(text="Grabación finalizada.", text_color="#95a5a6")
