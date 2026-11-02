import webbrowser
import customtkinter as ctk

from academic_recorder.ai.stem_config import AcademicConfig
from academic_recorder.ai.stem_prompts import WHISPER_INITIAL_PROMPTS
from ai.device_detector import DeviceDetector
from utils.ffmpeg_helper import FFmpegHelper


class ClassSettingsTab(ctk.CTkFrame):
    """Pestaña de configuración de IA, prompts científicos, hardware y preferencias de video."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.cfg = AcademicConfig.load()

        self._init_ui()
        self._load_values()

    def _init_ui(self):
        scroll = ctk.CTkScrollableFrame(self, corner_radius=12, fg_color=("#2b2b2b", "#1e1e1e"))
        scroll.pack(fill="both", expand=True, padx=25, pady=15)

        title = ctk.CTkLabel(
            scroll,
            text="⚙️ Ajustes Académicos y Modelos de IA",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.pack(pady=(15, 5), anchor="w", padx=20)

        subtitle = ctk.CTkLabel(
            scroll,
            text="Configura tus credenciales, el motor de transcripción (GPU/CPU y modelo Whisper), vocabularios STEM y reproducción sincronizada.",
            font=ctk.CTkFont(size=12),
            text_color="#bdc3c7",
        )
        subtitle.pack(pady=(0, 15), anchor="w", padx=20)

        # =========================================================================
        # 1. SECCIÓN GEMINI API
        # =========================================================================
        sec_gemini = ctk.CTkFrame(scroll, fg_color=("#333333", "#252525"), corner_radius=8)
        sec_gemini.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(
            sec_gemini, text="🤖 Google Gemini AI (Resúmenes y Apuntes)", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=15, pady=(12, 4))

        ctk.CTkLabel(
            sec_gemini,
            text="Gemini estructura los apuntes para examen con fórmulas en LaTeX, glosario técnico y marcas de tiempo cronológicas.",
            font=ctk.CTkFont(size=11),
            text_color="#95a5a6",
        ).pack(anchor="w", padx=15, pady=(0, 8))

        # API Key row
        key_row = ctk.CTkFrame(sec_gemini, fg_color="transparent")
        key_row.pack(fill="x", padx=15, pady=(0, 10))

        self.entry_api_key = ctk.CTkEntry(
            key_row, placeholder_text="Pega tu clave AIzaSy...", width=400, show="*"
        )
        self.entry_api_key.pack(side="left", padx=(0, 8))

        self.btn_toggle_key = ctk.CTkButton(
            key_row, text="👁️", width=38, command=self._toggle_key_visibility
        )
        self.btn_toggle_key.pack(side="left", padx=(0, 8))

        btn_get_key = ctk.CTkButton(
            key_row,
            text="🌐 Obtener API Key Gratis",
            fg_color="#2980b9",
            hover_color="#3498db",
            command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey"),
        )
        btn_get_key.pack(side="left")

        # Modelo Gemini row
        model_row = ctk.CTkFrame(sec_gemini, fg_color="transparent")
        model_row.pack(fill="x", padx=15, pady=(0, 14))

        ctk.CTkLabel(model_row, text="Modelo de IA:").pack(side="left", padx=(0, 10))
        self.combo_gemini_model = ctk.CTkComboBox(
            model_row,
            values=[
                "gemini-3.8-flash (Recomendado — Modelo Principal)",
                "gemini-3.8-flash-lite (Ligero y veloz)",
                "gemini-3.5-flash (Alternativo)",
            ],
            width=380,
        )
        self.combo_gemini_model.pack(side="left")

        # =========================================================================
        # 2. SECCIÓN MOTOR DE TRANSCRIPCIÓN LOCAL (WHISPER: GPU / CPU Y MODELO)
        # =========================================================================
        sec_whisper = ctk.CTkFrame(scroll, fg_color=("#333333", "#252525"), corner_radius=8)
        sec_whisper.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(
            sec_whisper, text="🎙️ Motor de Transcripción Local (Whisper)", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=15, pady=(12, 4))

        ctk.CTkLabel(
            sec_whisper,
            text="La transcripción se ejecuta localmente en tu equipo sin costo. Puedes alternar entre GPU (Vulkan) y CPU INT8.",
            font=ctk.CTkFont(size=11),
            text_color="#95a5a6",
        ).pack(anchor="w", padx=15, pady=(0, 8))

        grid_w = ctk.CTkFrame(sec_whisper, fg_color="transparent")
        grid_w.pack(fill="x", padx=15, pady=(0, 10))
        grid_w.grid_columnconfigure(1, weight=1)

        # 1. Selector de Dispositivo (GPU vs CPU)
        ctk.CTkLabel(grid_w, text="Dispositivo de Procesamiento:").grid(row=0, column=0, sticky="w", pady=5)
        self.combo_device = ctk.CTkComboBox(
            grid_w,
            values=[
                "gpu (🎮 GPU AMD Radeon RX 470 — Vulkan Acelerado)",
                "cpu (💻 CPU Multinúcleo INT8 — Máxima Estabilidad)",
            ],
            width=430,
        )
        self.combo_device.grid(row=0, column=1, sticky="w", pady=5, padx=10)

        # 2. Selector de Modelo Whisper
        ctk.CTkLabel(grid_w, text="Modelo Whisper:").grid(row=1, column=0, sticky="w", pady=5)
        self.combo_whisper_model = ctk.CTkComboBox(
            grid_w,
            values=[
                "medium (Recomendado STEM — Alta precisión en términos técnicos)",
                "small (Rápido y balanceado — Menor uso de memoria)",
                "base (Ultrarrápido y ligero)",
                "tiny (Máxima velocidad)",
                "large-v3 (Máxima precisión — Recomendado en CPU)",
            ],
            width=430,
        )
        self.combo_whisper_model.grid(row=1, column=1, sticky="w", pady=5, padx=10)

        # 3. Selector de Idioma
        ctk.CTkLabel(grid_w, text="Idioma de Transcripción:").grid(row=2, column=0, sticky="w", pady=5)
        self.combo_lang = ctk.CTkComboBox(
            grid_w,
            values=[
                "es (Español — Dictado estándar de clases)",
                "en (Inglés)",
                "auto (Autodetectar idioma)",
            ],
            width=430,
        )
        self.combo_lang.grid(row=2, column=1, sticky="w", pady=5, padx=10)

        # Diagnóstico de Hardware y FFmpeg
        hw_info = DeviceDetector.get_info()
        ffmpeg_ver = FFmpegHelper.get_version() or "No detectado en PATH"
        diag_box = ctk.CTkFrame(sec_whisper, fg_color=("#282828", "#1c1c1c"), corner_radius=6)
        diag_box.pack(fill="x", padx=15, pady=(0, 8))

        diag_text = (
            f"• Hardware: {hw_info['gpu_name']}\n"
            f"• CPU: {hw_info['description']}\n"
            f"• Cuantización: {hw_info['compute_type'].upper()} (AVX2 multinúcleo)\n"
            f"• FFmpeg: {ffmpeg_ver[:60] if ffmpeg_ver else 'No detectado'}\n"
            f"• Protección activa: Fallback automático a CPU si la GPU se satura"
        )
        ctk.CTkLabel(
            diag_box,
            text=diag_text,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#2ecc71",
            justify="left",
            anchor="w",
        ).pack(anchor="w", padx=12, pady=8)

        btn_dl = ctk.CTkButton(
            sec_whisper,
            text="📥 Abrir Descargador de Modelos GPU (.bat)",
            fg_color="#34495e",
            hover_color="#415b76",
            height=30,
            command=self._open_downloader_bat,
        )
        btn_dl.pack(anchor="w", padx=15, pady=(0, 12))

        # =========================================================================
        # 3. SECCIÓN VOCABULARIO CIENTÍFICO Y PROMPTS STEM (FÍSICA / MATEMÁTICAS)
        # =========================================================================
        sec_stem = ctk.CTkFrame(scroll, fg_color=("#333333", "#252525"), corner_radius=8)
        sec_stem.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(
            sec_stem, text="📐 Vocabulario Científico y Sesgo para Whisper", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=15, pady=(12, 4))

        ctk.CTkLabel(
            sec_stem,
            text="Whisper utiliza este texto como referencia fonética inicial para no confundir términos complejos (ej. laplaciano, hamiltoniano).",
            font=ctk.CTkFont(size=11),
            text_color="#95a5a6",
        ).pack(anchor="w", padx=15, pady=(0, 8))

        disc_row = ctk.CTkFrame(sec_stem, fg_color="transparent")
        disc_row.pack(fill="x", padx=15, pady=(0, 8))

        ctk.CTkLabel(disc_row, text="Preset de Disciplina:").pack(side="left", padx=(0, 10))
        self.combo_discipline = ctk.CTkComboBox(
            disc_row,
            values=["Física", "Matemáticas", "General"],
            command=self._on_discipline_preset_changed,
            width=180,
        )
        self.combo_discipline.pack(side="left", padx=(0, 15))

        btn_reset_prompt = ctk.CTkButton(
            disc_row,
            text="Restaurar Vocabulario por Defecto",
            width=220,
            fg_color="#7f8c8d",
            hover_color="#95a5a6",
            command=self._reset_prompt_to_preset,
        )
        btn_reset_prompt.pack(side="left")

        ctk.CTkLabel(
            sec_stem, text="Vocabulario técnico activo (editable):", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=15, pady=(4, 2))

        self.txt_prompt = ctk.CTkTextbox(sec_stem, height=100, font=ctk.CTkFont(size=12), wrap="word")
        self.txt_prompt.pack(fill="x", padx=15, pady=(0, 12))

        # =========================================================================
        # 4. SECCIÓN REPRODUCCIÓN SINCRONIZADA Y VIDEO 1080P
        # =========================================================================
        sec_video = ctk.CTkFrame(scroll, fg_color=("#333333", "#252525"), corner_radius=8)
        sec_video.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(
            sec_video, text="⏱️ Reproducción Sincronizada y Video 1080p", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=15, pady=(12, 4))

        lead_row = ctk.CTkFrame(sec_video, fg_color="transparent")
        lead_row.pack(fill="x", padx=15, pady=(4, 12))

        ctk.CTkLabel(lead_row, text="Anticipación al saltar al video:").pack(side="left", padx=(0, 10))
        self.combo_lead_time = ctk.CTkComboBox(
            lead_row, values=["3 segundos antes", "5 segundos antes", "8 segundos antes", "10 segundos antes"], width=190
        )
        self.combo_lead_time.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(lead_row, text="Framerate predeterminado:").pack(side="left", padx=(10, 10))
        self.combo_fps = ctk.CTkComboBox(lead_row, values=["15 FPS", "18 FPS", "21 FPS"], width=130)
        self.combo_fps.pack(side="left")

        # =========================================================================
        # BOTÓN GUARDAR CAMBIOS
        # =========================================================================
        btn_save = ctk.CTkButton(
            scroll,
            text="💾 Guardar Cambios",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#27ae60",
            hover_color="#2ecc71",
            height=44,
            command=self._save_settings,
        )
        btn_save.pack(pady=15, padx=20, fill="x")

        self.lbl_save_status = ctk.CTkLabel(scroll, text="", font=ctk.CTkFont(size=13))
        self.lbl_save_status.pack(pady=(0, 10))

    def _open_downloader_bat(self):
        import os
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent.parent
        bat_path = root / "descargar_modelo_gpu.bat"
        if bat_path.exists():
            os.startfile(str(bat_path))

    def _toggle_key_visibility(self):
        if self.entry_api_key.cget("show") == "*":
            self.entry_api_key.configure(show="")
            self.btn_toggle_key.configure(text="🔒")
        else:
            self.entry_api_key.configure(show="*")
            self.btn_toggle_key.configure(text="👁️")

    def _load_values(self):
        # Gemini API
        if self.cfg.gemini_api_key:
            self.entry_api_key.insert(0, self.cfg.gemini_api_key)

        cur_gm = self.cfg.gemini_model
        self.combo_gemini_model.set(self.combo_gemini_model._values[0])
        for val in self.combo_gemini_model._values:
            if val.startswith(cur_gm):
                self.combo_gemini_model.set(val)
                break

        # Dispositivo Whisper (GPU vs CPU)
        cur_backend = self.cfg.whisper_backend
        if cur_backend == "gpu":
            self.combo_device.set(self.combo_device._values[0])
        else:
            self.combo_device.set(self.combo_device._values[1])

        # Modelo Whisper
        cur_wm = self.cfg.whisper_model
        for val in self.combo_whisper_model._values:
            if val.startswith(cur_wm):
                self.combo_whisper_model.set(val)
                break

        # Idioma
        cur_lang = self.cfg.language
        for val in self.combo_lang._values:
            if val.startswith(cur_lang):
                self.combo_lang.set(val)
                break

        # Disciplina y prompt
        self.combo_discipline.set(self.cfg.discipline)
        active_prompt = self.cfg.get_effective_initial_prompt()
        self.txt_prompt.delete("1.0", "end")
        self.txt_prompt.insert("1.0", active_prompt)

        # Lead time
        sec = int(self.cfg.video_lead_time_sec)
        self.combo_lead_time.set(f"{sec} segundos antes")

        # FPS
        self.combo_fps.set(f"{self.cfg.video_fps} FPS")

    def _on_discipline_preset_changed(self, choice: str):
        preset_text = WHISPER_INITIAL_PROMPTS.get(choice, WHISPER_INITIAL_PROMPTS["General"])
        self.txt_prompt.delete("1.0", "end")
        self.txt_prompt.insert("1.0", preset_text)

    def _reset_prompt_to_preset(self):
        disc = self.combo_discipline.get()
        preset_text = WHISPER_INITIAL_PROMPTS.get(disc, WHISPER_INITIAL_PROMPTS["General"])
        self.txt_prompt.delete("1.0", "end")
        self.txt_prompt.insert("1.0", preset_text)
        self.lbl_save_status.configure(text="Vocabulario restablecido al valor predeterminado del preset.", text_color="#3498db")

    def _save_settings(self):
        self.cfg.gemini_api_key = self.entry_api_key.get().strip()

        # Extraer nombres limpios de los combos
        selected_gemini = self.combo_gemini_model.get().split()[0]
        self.cfg.gemini_model = selected_gemini

        selected_dev = self.combo_device.get().split()[0].lower()
        self.cfg.whisper_backend = selected_dev

        selected_wm = self.combo_whisper_model.get().split()[0]
        self.cfg.whisper_model = selected_wm

        selected_lang = self.combo_lang.get().split()[0]
        self.cfg.language = selected_lang

        self.cfg.discipline = self.combo_discipline.get().strip()
        self.cfg.custom_initial_prompt = self.txt_prompt.get("1.0", "end-1c").strip()

        lead_str = self.combo_lead_time.get()
        try:
            self.cfg.video_lead_time_sec = float(lead_str.split()[0])
        except Exception:
            self.cfg.video_lead_time_sec = 5.0

        fps_str = self.combo_fps.get()
        try:
            self.cfg.video_fps = int(fps_str.split()[0])
        except Exception:
            self.cfg.video_fps = 18

        self.cfg.save()

        # Si se ingresó API key, actualizar también en variable de entorno
        if self.cfg.gemini_api_key:
            try:
                import os
                os.environ["GEMINI_API_KEY"] = self.cfg.gemini_api_key
            except Exception:
                pass

        self.lbl_save_status.configure(text="✅ ¡Configuración guardada exitosamente!", text_color="#2ecc71")
        self.after(3000, lambda: self.lbl_save_status.configure(text=""))
