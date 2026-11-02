import webbrowser
import customtkinter as ctk

from work_recorder.ai.work_config import WorkConfig
from work_recorder.ai.work_prompts import WHISPER_WORK_INITIAL_PROMPT
from ai.device_detector import DeviceDetector
from utils.ffmpeg_helper import FFmpegHelper


class WorkSettingsTab(ctk.CTkFrame):
    """Pestaña de configuración de IA corporativa, motor Whisper, hardware y preferencias de video."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.cfg = WorkConfig.load()

        self._init_ui()
        self._load_values()

    def _init_ui(self):
        scroll = ctk.CTkScrollableFrame(self, corner_radius=12, fg_color=("#2b2b2b", "#1e1e1e"))
        scroll.pack(fill="both", expand=True, padx=25, pady=15)

        title = ctk.CTkLabel(
            scroll,
            text="⚙️ Ajustes de Trabajo y Modelos de IA",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.pack(pady=(15, 5), anchor="w", padx=20)

        subtitle = ctk.CTkLabel(
            scroll,
            text="Configura tus credenciales de Gemini, el motor de transcripción local Whisper (GPU Vulkan / CPU INT8) y preferencias corporativas.",
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
            sec_gemini, text="🤖 Google Gemini AI (Minutas Ejecutivas y Tareas)", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=15, pady=(12, 4))

        ctk.CTkLabel(
            sec_gemini,
            text="Gemini analiza la transcripción de la llamada, extrae compromisos (Action Items) con responsables y plazos, y resume acuerdos clave.",
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
            text="La transcripción se ejecuta localmente en tu equipo sin costo ni envío de audio a la nube. Puedes alternar entre GPU (Vulkan) y CPU INT8.",
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
                "medium (Recomendado — Excelente balance de precisión corporativa)",
                "small (Rápido y liviano — Menor uso de memoria)",
                "base (Ultrarrápido)",
                "tiny (Máxima velocidad)",
                "large-v3 (Máxima precisión — Mayor consumo)",
            ],
            width=430,
        )
        self.combo_whisper_model.grid(row=1, column=1, sticky="w", pady=5, padx=10)

        # 3. Selector de Idioma
        ctk.CTkLabel(grid_w, text="Idioma de Transcripción:").grid(row=2, column=0, sticky="w", pady=5)
        self.combo_lang = ctk.CTkComboBox(
            grid_w,
            values=[
                "es (Español — Reuniones y llamadas en español)",
                "en (Inglés)",
                "auto (Autodetectar idioma)",
            ],
            width=430,
        )
        self.combo_lang.grid(row=2, column=1, sticky="w", pady=5, padx=10)

        # Diagnóstico de Hardware
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
        # 3. SECCIÓN VOCABULARIO CORPORATIVO Y JERGA LABORAL
        # =========================================================================
        sec_work = ctk.CTkFrame(scroll, fg_color=("#333333", "#252525"), corner_radius=8)
        sec_work.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(
            sec_work, text="💼 Jerga Laboral y Vocabulario Corporativo", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=15, pady=(12, 4))

        ctk.CTkLabel(
            sec_work,
            text="Whisper utiliza esta lista de términos para transcribir correctamente acrónimos corporativos, herramientas y jerga técnica sin confundirlos.",
            font=ctk.CTkFont(size=11),
            text_color="#95a5a6",
        ).pack(anchor="w", padx=15, pady=(0, 8))

        prompt_bar = ctk.CTkFrame(sec_work, fg_color="transparent")
        prompt_bar.pack(fill="x", padx=15, pady=(0, 6))

        btn_reset_prompt = ctk.CTkButton(
            prompt_bar,
            text="Restablecer Vocabulario Corporativo por Defecto",
            width=280,
            fg_color="#7f8c8d",
            hover_color="#95a5a6",
            command=self._reset_prompt_to_default,
        )
        btn_reset_prompt.pack(side="left")

        ctk.CTkLabel(
            sec_work, text="Vocabulario de referencia (editable):", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=15, pady=(4, 2))

        self.txt_prompt = ctk.CTkTextbox(sec_work, height=90, font=ctk.CTkFont(size=12), wrap="word")
        self.txt_prompt.pack(fill="x", padx=15, pady=(0, 12))

        # =========================================================================
        # 4. SECCIÓN REUNIONES Y VIDEO
        # =========================================================================
        sec_video = ctk.CTkFrame(scroll, fg_color=("#333333", "#252525"), corner_radius=8)
        sec_video.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(
            sec_video, text="⏱️ Preferencias de Grabación y Reproducción", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=15, pady=(12, 4))

        row_v = ctk.CTkFrame(sec_video, fg_color="transparent")
        row_v.pack(fill="x", padx=15, pady=(4, 12))

        ctk.CTkLabel(row_v, text="Tipo de reunión predeterminado:").pack(side="left", padx=(0, 8))
        self.combo_default_type = ctk.CTkComboBox(
            row_v,
            values=[
                "Sync / Daily",
                "Reunión con Cliente",
                "Planificación / Sprint",
                "1-on-1 / Feedback",
                "Estratégica / Dirección",
                "General",
            ],
            width=180,
        )
        self.combo_default_type.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(row_v, text="Anticipación al saltar al video:").pack(side="left", padx=(5, 8))
        self.combo_lead_time = ctk.CTkComboBox(
            row_v, values=["3 segundos antes", "5 segundos antes", "8 segundos antes"], width=160
        )
        self.combo_lead_time.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(row_v, text="Framerate:").pack(side="left", padx=(5, 8))
        self.combo_fps = ctk.CTkComboBox(row_v, values=["15 FPS", "20 FPS", "24 FPS", "30 FPS"], width=110)
        self.combo_fps.pack(side="left")

        # =========================================================================
        # BOTÓN GUARDAR CAMBIOS
        # =========================================================================
        self.btn_save = ctk.CTkButton(
            scroll,
            text="💾 Guardar Cambios",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#27ae60",
            hover_color="#2ecc71",
            height=44,
            command=self._save_settings,
        )
        self.btn_save.pack(pady=15, padx=20, fill="x")

        self.lbl_save_status = ctk.CTkLabel(scroll, text="", font=ctk.CTkFont(size=12))
        self.lbl_save_status.pack(pady=(0, 15))

    def _toggle_key_visibility(self):
        if self.entry_api_key.cget("show") == "*":
            self.entry_api_key.configure(show="")
            self.btn_toggle_key.configure(text="🔒")
        else:
            self.entry_api_key.configure(show="*")
            self.btn_toggle_key.configure(text="👁️")

    def _reset_prompt_to_default(self):
        self.txt_prompt.delete("1.0", "end")
        self.txt_prompt.insert("1.0", WHISPER_WORK_INITIAL_PROMPT)

    def _open_downloader_bat(self):
        import os
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent.parent
        bat_path = root / "descargar_modelo_gpu.bat"
        if bat_path.exists():
            os.startfile(str(bat_path))

    def _load_values(self):
        if self.cfg.gemini_api_key:
            self.entry_api_key.delete(0, "end")
            self.entry_api_key.insert(0, self.cfg.gemini_api_key)

        model_val = self.cfg.gemini_model
        for val in self.combo_gemini_model.cget("values"):
            if model_val in val:
                self.combo_gemini_model.set(val)
                break

        backend = self.cfg.whisper_backend
        if backend == "gpu":
            self.combo_device.set("gpu (🎮 GPU AMD Radeon RX 470 — Vulkan Acelerado)")
        else:
            self.combo_device.set("cpu (💻 CPU Multinúcleo INT8 — Máxima Estabilidad)")

        w_model = self.cfg.whisper_model
        for val in self.combo_whisper_model.cget("values"):
            if val.startswith(w_model):
                self.combo_whisper_model.set(val)
                break

        lang = self.cfg.language
        for val in self.combo_lang.cget("values"):
            if val.startswith(lang):
                self.combo_lang.set(val)
                break

        if self.cfg.meeting_type_default:
            self.combo_default_type.set(self.cfg.meeting_type_default)

        lead = int(self.cfg.video_lead_time_sec)
        self.combo_lead_time.set(f"{lead} segundos antes")

        fps = self.cfg.video_fps
        self.combo_fps.set(f"{fps} FPS")

        prompt = self.cfg.get_effective_initial_prompt()
        self.txt_prompt.delete("1.0", "end")
        self.txt_prompt.insert("1.0", prompt)

    def _save_settings(self):
        self.cfg.gemini_api_key = self.entry_api_key.get().strip()

        model_raw = self.combo_gemini_model.get()
        if "gemini-3.8-flash-lite" in model_raw:
            self.cfg.gemini_model = "gemini-3.8-flash-lite"
        elif "gemini-3.5-flash" in model_raw:
            self.cfg.gemini_model = "gemini-3.5-flash"
        else:
            self.cfg.gemini_model = "gemini-3.8-flash"

        dev_raw = self.combo_device.get()
        self.cfg.whisper_backend = "gpu" if dev_raw.startswith("gpu") else "cpu"

        w_raw = self.combo_whisper_model.get().split()[0]
        self.cfg.whisper_model = w_raw

        lang_raw = self.combo_lang.get().split()[0]
        self.cfg.language = lang_raw

        self.cfg.meeting_type_default = self.combo_default_type.get()

        lead_raw = self.combo_lead_time.get()
        try:
            self.cfg.video_lead_time_sec = float(lead_raw.split()[0])
        except Exception:
            self.cfg.video_lead_time_sec = 3.0

        fps_raw = self.combo_fps.get()
        try:
            self.cfg.video_fps = int(fps_raw.split()[0])
        except Exception:
            self.cfg.video_fps = 15

        self.cfg.custom_initial_prompt = self.txt_prompt.get("1.0", "end-1c").strip()

        self.cfg.save()

        self.lbl_save_status.configure(text="✅ Configuración guardada correctamente en work_settings.json", text_color="#2ecc71")
        self.after(3000, lambda: self.lbl_save_status.configure(text=""))
