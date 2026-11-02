import time
import customtkinter as ctk
from typing import Optional, Callable, List, Dict, Any
from recorder.session_manager import SessionManager
from recorder.audio_recorder import AudioRecorder
from utils.window_list import list_visible_windows


class RecorderTab(ctk.CTkFrame):
    """Pestaña de grabación en vivo para la sesión de D&D."""

    def __init__(self, master, session_manager: SessionManager, on_session_saved: Optional[Callable] = None):
        super().__init__(master, fg_color="transparent")
        self.session_manager = session_manager
        self.on_session_saved = on_session_saved

        self.available_devices = AudioRecorder.get_available_devices()

        self._init_ui()
        self._setup_callbacks()

    def _init_ui(self):
        # Contenedor central
        card = ctk.CTkFrame(self, corner_radius=12, fg_color=("#2b2b2b", "#1e1e1e"))
        card.pack(pady=20, padx=30, fill="both", expand=True)

        # Título
        title_label = ctk.CTkLabel(
            card,
            text="🎙️ Grabador de Sesión D&D",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.pack(pady=(20, 5))

        subtitle = ctk.CTkLabel(
            card,
            text="Captura simultánea de Discord (voces del grupo) + Micrófono (tu voz) + Foundry VTT",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        )
        subtitle.pack(pady=(0, 20))

        # Configuración rápida antes de grabar
        settings_frame = ctk.CTkFrame(card, fg_color="transparent")
        settings_frame.pack(fill="x", padx=40, pady=5)
        settings_frame.grid_columnconfigure(1, weight=1)

        # Nombre de la campaña
        ctk.CTkLabel(settings_frame, text="Nombre de la Campaña:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", pady=5, padx=5
        )
        self.campaign_entry = ctk.CTkEntry(settings_frame, placeholder_text="Ej: La Maldición de Strahd")
        self.campaign_entry.insert(0, "Campaña Principal")
        self.campaign_entry.grid(row=0, column=1, sticky="ew", pady=5, padx=5)

        # Dispositivo de audio del sistema (Discord/Foundry Loopback)
        ctk.CTkLabel(settings_frame, text="Audio Sistema (Discord/Juego):").grid(
            row=1, column=0, sticky="w", pady=5, padx=5
        )
        loopback_names = [f"[{d['index']}] {d['name']}" for d in self.available_devices["loopbacks"]]
        if not loopback_names:
            loopback_names = ["(Default WASAPI Loopback)"]
        self.loopback_combo = ctk.CTkComboBox(settings_frame, values=loopback_names)
        self.loopback_combo.grid(row=1, column=1, sticky="ew", pady=5, padx=5)

        # Micrófono
        ctk.CTkLabel(settings_frame, text="Tu Micrófono:").grid(
            row=2, column=0, sticky="w", pady=5, padx=5
        )
        mic_names = [f"[{d['index']}] {d['name']}" for d in self.available_devices["microphones"]]
        if not mic_names:
            mic_names = ["(Default Mic)"]
        self.mic_combo = ctk.CTkComboBox(settings_frame, values=mic_names)
        self.mic_combo.grid(row=2, column=1, sticky="ew", pady=5, padx=5)

        # Grabar pantalla toggle
        self.record_screen_var = ctk.BooleanVar(value=False)
        self.screen_checkbox = ctk.CTkCheckBox(
            settings_frame,
            text="Grabar video de la sesión (Foundry / Pantalla)",
            variable=self.record_screen_var,
            command=self._on_screen_checkbox_toggled,
        )
        self.screen_checkbox.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 5), padx=5)

        # Panel de opciones de video (Modo y Ventana)
        self.video_options_frame = ctk.CTkFrame(settings_frame, fg_color=("#383838", "#242424"), corner_radius=8)

        # Fila de Modo de video y Framerate
        self.video_mode_var = ctk.StringVar(value="window")
        mode_row = ctk.CTkFrame(self.video_options_frame, fg_color="transparent")
        mode_row.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(mode_row, text="Modo de video:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        self.radio_window = ctk.CTkRadioButton(
            mode_row,
            text="🎯 Ventana específica (Foundry — Inmune a Alt-Tab)",
            variable=self.video_mode_var,
            value="window",
            command=self._on_video_mode_changed,
        )
        self.radio_window.pack(side="left", padx=5)

        self.radio_desktop = ctk.CTkRadioButton(
            mode_row,
            text="🖥️ Pantalla completa",
            variable=self.video_mode_var,
            value="desktop",
            command=self._on_video_mode_changed,
        )
        self.radio_desktop.pack(side="left", padx=15)

        ctk.CTkLabel(mode_row, text="FPS:").pack(side="left", padx=(15, 6))
        self.fps_combo = ctk.CTkSegmentedButton(mode_row, values=["5 FPS (Ligero)", "15 FPS (Fluido)", "20 FPS (HD)"])
        self.fps_combo.set("5 FPS (Ligero)")
        self.fps_combo.pack(side="left")

        # Fila de selección de ventana objetivo
        self.window_select_row = ctk.CTkFrame(self.video_options_frame, fg_color="transparent")
        self.window_select_row.pack(fill="x", padx=10, pady=(4, 6))

        ctk.CTkLabel(self.window_select_row, text="Ventana objetivo:").pack(side="left", padx=(0, 10))
        self.window_combo = ctk.CTkComboBox(self.window_select_row, values=["(Seleccionar ventana)"])
        self.window_combo.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_refresh_windows = ctk.CTkButton(
            self.window_select_row,
            text="🔄",
            width=36,
            height=28,
            command=self._refresh_window_list,
        )
        self.btn_refresh_windows.pack(side="left")

        self.lbl_window_tip = ctk.CTkLabel(
            self.video_options_frame,
            text="💡 Tip: Para grabar Foundry en Chrome/Edge, arrastra la pestaña hacia afuera para que sea una ventana independiente.",
            font=ctk.CTkFont(size=11),
            text_color="#95a5a6",
            anchor="w",
        )
        self.lbl_window_tip.pack(fill="x", padx=10, pady=(0, 6))

        self._windows_cache: List[Dict[str, Any]] = []
        self._refresh_window_list()

        # Cronómetro / Timer
        self.timer_label = ctk.CTkLabel(
            card,
            text="00:00:00",
            font=ctk.CTkFont(size=48, weight="bold"),
            text_color="#e0e0e0",
        )
        self.timer_label.pack(pady=(25, 10))

        # Indicadores VU Meter
        meter_frame = ctk.CTkFrame(card, fg_color="transparent")
        meter_frame.pack(fill="x", padx=60, pady=10)

        # VU Mic
        ctk.CTkLabel(meter_frame, text="Micrófono:", width=90, anchor="e").grid(row=0, column=0, padx=5, pady=3)
        self.mic_meter = ctk.CTkProgressBar(meter_frame, width=300, progress_color="#2ecc71")
        self.mic_meter.set(0)
        self.mic_meter.grid(row=0, column=1, padx=5, pady=3)

        # VU Loopback
        ctk.CTkLabel(meter_frame, text="Discord/Juego:", width=90, anchor="e").grid(row=1, column=0, padx=5, pady=3)
        self.sys_meter = ctk.CTkProgressBar(meter_frame, width=300, progress_color="#3498db")
        self.sys_meter.set(0)
        self.sys_meter.grid(row=1, column=1, padx=5, pady=3)

        # Botones de control
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(pady=25)

        self.btn_record = ctk.CTkButton(
            btn_frame,
            text="⏺️ Iniciar Grabación",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#c0392b",
            hover_color="#e74c3c",
            width=180,
            height=45,
            command=self._on_record_clicked,
        )
        self.btn_record.grid(row=0, column=0, padx=10)

        self.btn_pause = ctk.CTkButton(
            btn_frame,
            text="⏸️ Pausar",
            font=ctk.CTkFont(size=15),
            fg_color="#7f8c8d",
            state="disabled",
            width=120,
            height=45,
            command=self._on_pause_clicked,
        )
        self.btn_pause.grid(row=0, column=1, padx=10)

        self.btn_stop = ctk.CTkButton(
            btn_frame,
            text="⏹️ Finalizar Sesión",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#27ae60",
            hover_color="#2ecc71",
            state="disabled",
            width=160,
            height=45,
            command=self._on_stop_clicked,
        )
        self.btn_stop.grid(row=0, column=2, padx=10)

        # Estado informativo
        self.status_label = ctk.CTkLabel(
            card,
            text="Listo para iniciar sesión.",
            font=ctk.CTkFont(size=13),
            text_color="#95a5a6",
        )
        self.status_label.pack(pady=(0, 15))

    def _setup_callbacks(self):
        # Audio callbacks para actualizar la UI desde los threads de audio
        self.session_manager.audio_recorder.on_duration_update = self._on_duration_update
        self.session_manager.audio_recorder.on_peak_update = self._on_peak_update

    def _on_duration_update(self, seconds: float):
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        self.after(0, lambda: self.timer_label.configure(text=time_str))

    def _on_peak_update(self, mic_peak: float, sys_peak: float):
        # Limitamos a [0, 1]
        m = min(1.0, max(0.0, mic_peak * 1.5))
        s = min(1.0, max(0.0, sys_peak * 1.5))
        self.after(0, lambda: (self.mic_meter.set(m), self.sys_meter.set(s)))

    def _on_screen_checkbox_toggled(self):
        if self.record_screen_var.get():
            self.video_options_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 10), padx=5)
            self._refresh_window_list()
            self._on_video_mode_changed()
        else:
            self.video_options_frame.grid_forget()

    def _on_video_mode_changed(self):
        mode = self.video_mode_var.get()
        if mode == "window":
            self.window_combo.configure(state="normal")
            self.btn_refresh_windows.configure(state="normal")
            self.lbl_window_tip.configure(text_color="#95a5a6")
        else:
            self.window_combo.configure(state="disabled")
            self.btn_refresh_windows.configure(state="disabled")
            self.lbl_window_tip.configure(text_color="#555555")

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

            # Auto-seleccionar si detecta Foundry VTT, Roll20 o navegadores
            preferred = None
            for dv in display_values:
                low = dv.lower()
                if any(k in low for k in ("foundry", "roll20", "chrome", "edge", "firefox", "brave", "opera", "discord")):
                    preferred = dv
                    break

            if preferred:
                self.window_combo.set(preferred)
            elif display_values:
                self.window_combo.set(display_values[0])
        except Exception as e:
            print(f"Error enumerando ventanas: {e}")

    def _get_selected_index(self, combo_text: str) -> Optional[int]:
        if combo_text.startswith("["):
            try:
                idx_str = combo_text[1:].split("]")[0]
                return int(idx_str)
            except Exception:
                pass
        return None

    def _on_record_clicked(self):
        campaign = self.campaign_entry.get().strip() or "Campaña Principal"
        record_screen = self.record_screen_var.get()
        screen_mode = self.video_mode_var.get()
        fps_str = self.fps_combo.get()
        fps = 5
        try:
            fps = int(fps_str.split()[0])
        except Exception:
            fps = 5

        loopback_idx = self._get_selected_index(self.loopback_combo.get())
        mic_idx = self._get_selected_index(self.mic_combo.get())

        selected_win_title = None
        selected_win_hwnd = None
        if record_screen and screen_mode == "window":
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
            campaign_name=campaign,
            record_screen=record_screen,
            screen_mode=screen_mode,
            capture_window_title=selected_win_title,
            capture_window_hwnd=selected_win_hwnd,
            fps=fps,
            mic_index=mic_idx,
            loopback_index=loopback_idx,
        )

        self.btn_record.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="⏸️ Pausar", fg_color="#f39c12")
        self.btn_stop.configure(state="normal")
        self.campaign_entry.configure(state="disabled")
        self.screen_checkbox.configure(state="disabled")
        self.radio_window.configure(state="disabled")
        self.radio_desktop.configure(state="disabled")
        self.fps_combo.configure(state="disabled")
        self.window_combo.configure(state="disabled")
        self.btn_refresh_windows.configure(state="disabled")
        self.loopback_combo.configure(state="disabled")
        self.mic_combo.configure(state="disabled")

        target_desc = f" (Ventana: {selected_win_title[:30]})" if record_screen and screen_mode == "window" and selected_win_title else ""
        self.timer_label.configure(text_color="#e74c3c")
        self.status_label.configure(text=f"🔴 Grabando sesión en vivo... ¡A rolear!{target_desc}", text_color="#e74c3c")

    def _on_pause_clicked(self):
        if self.session_manager.audio_recorder.is_paused:
            self.session_manager.resume_session()
            self.btn_pause.configure(text="⏸️ Pausar", fg_color="#f39c12")
            self.status_label.configure(text="🔴 Grabando sesión en vivo...", text_color="#e74c3c")
        else:
            self.session_manager.pause_session()
            self.btn_pause.configure(text="▶️ Reanudar", fg_color="#2980b9")
            self.status_label.configure(text="⏸️ Sesión pausada (descanso de mesa).", text_color="#f39c12")

    def _on_stop_clicked(self):
        self.status_label.configure(text="Procesando pistas de audio y video finales...", text_color="#3498db")
        self.update_idletasks()

        saved_session = self.session_manager.stop_session()

        self.btn_record.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="⏸️ Pausar", fg_color="#7f8c8d")
        self.btn_stop.configure(state="disabled")
        self.campaign_entry.configure(state="normal")
        self.screen_checkbox.configure(state="normal")
        self.radio_window.configure(state="normal")
        self.radio_desktop.configure(state="normal")
        self.fps_combo.configure(state="normal")
        self._on_video_mode_changed()
        self.loopback_combo.configure(state="normal")
        self.mic_combo.configure(state="normal")

        self.timer_label.configure(text_color="#e0e0e0")
        self.mic_meter.set(0)
        self.sys_meter.set(0)

        if saved_session:
            self.status_label.configure(
                text=f"✅ Sesión guardada: {saved_session.dir.name}. Ve a la pestaña 'Sesiones' para procesar.",
                text_color="#2ecc71",
            )
            if self.on_session_saved:
                self.on_session_saved(saved_session)
        else:
            self.status_label.configure(text="Sesión finalizada.", text_color="#95a5a6")

