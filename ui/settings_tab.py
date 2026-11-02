import webbrowser
import customtkinter as ctk
from ai.config import AIConfig
from ai.device_detector import DeviceDetector
from utils.ffmpeg_helper import FFmpegHelper


class SettingsTab(ctk.CTkFrame):
    """Pestaña de configuración de IA, hardware y claves de API."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.config = AIConfig.load()
        self._init_ui()

    def _init_ui(self):
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=20)

        ctk.CTkLabel(
            container,
            text="⚙️ Configuración del Sistema",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", pady=(0, 20))

        # --- SECCIÓN 1: GEMINI API KEY & MODELO ---
        card_api = ctk.CTkFrame(container, corner_radius=10)
        card_api.pack(fill="x", pady=10)

        ctk.CTkLabel(
            card_api,
            text="🔑 Google Gemini AI (Resúmenes Gratuitos)",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 5))

        ctk.CTkLabel(
            card_api,
            text="Gemini se encarga de analizar la transcripción y redactar la crónica de la sesión con estructura roldera.\nEl plan gratuito de Google AI Studio incluye modelos modernos como Gemini 3.5 Flash.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 10))

        key_row = ctk.CTkFrame(card_api, fg_color="transparent")
        key_row.pack(fill="x", padx=20, pady=5)

        self.key_entry = ctk.CTkEntry(
            key_row, width=420, placeholder_text="Pega tu clave AIzaSy...", show="*"
        )
        if self.config.gemini_api_key:
            self.key_entry.insert(0, self.config.gemini_api_key)
        self.key_entry.pack(side="left", padx=(0, 10))

        self.btn_toggle_key = ctk.CTkButton(
            key_row, text="👁️", width=40, command=self._toggle_key_visibility
        )
        self.btn_toggle_key.pack(side="left", padx=5)

        btn_get_key = ctk.CTkButton(
            key_row,
            text="🌐 Obtener API Key Gratis",
            fg_color="#2980b9",
            hover_color="#3498db",
            command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey"),
        )
        btn_get_key.pack(side="left", padx=10)

        # Selector de modelo Gemini
        model_row = ctk.CTkFrame(card_api, fg_color="transparent")
        model_row.pack(fill="x", padx=20, pady=(10, 15))

        ctk.CTkLabel(model_row, text="Modelo Gemini:").pack(side="left", padx=(0, 10))
        self.gemini_model_combo = ctk.CTkComboBox(
            model_row,
            values=[
                "gemini-3.8-flash (Recomendado — Modelo Principal)",
                "gemini-3.5-flash (Rápido y actual)",
                "gemini-3.7-flash (Avanzado)",
                "gemini-3.5-flash-lite (Ligero y veloz)",
            ],
            width=380,
        )
        cur_m = self.config.gemini_model
        for v in self.gemini_model_combo._values:
            if v.startswith(cur_m):
                self.gemini_model_combo.set(v)
                break
        self.gemini_model_combo.pack(side="left")

        # --- SECCIÓN 2: MOTOR DE TRANSCRIPCIÓN LOCAL (WHISPER) ---
        card_whisper = ctk.CTkFrame(container, corner_radius=10)
        card_whisper.pack(fill="x", pady=10)

        ctk.CTkLabel(
            card_whisper,
            text="🎙️ Transcripción Local (Whisper — 100% Gratis)",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 5))

        grid_w = ctk.CTkFrame(card_whisper, fg_color="transparent")
        grid_w.pack(fill="x", padx=20, pady=10)

        # Selector de Hardware: GPU AMD vs CPU
        ctk.CTkLabel(grid_w, text="Dispositivo de Procesamiento:").grid(row=0, column=0, sticky="w", pady=5)
        self.device_combo = ctk.CTkComboBox(
            grid_w,
            values=[
                "gpu (🎮 GPU AMD Radeon RX 470 — Vulkan Acelerado)",
                "cpu (💻 CPU Multinúcleo INT8 — Máxima Estabilidad)",
            ],
            width=420,
        )
        cur_backend = self.config.whisper_backend
        if cur_backend == "gpu":
            self.device_combo.set(self.device_combo._values[0])
        else:
            self.device_combo.set(self.device_combo._values[1])
        grid_w.grid_columnconfigure(1, weight=1)
        self.device_combo.grid(row=0, column=1, sticky="w", pady=5, padx=10)

        # Modelo Whisper
        ctk.CTkLabel(grid_w, text="Modelo Whisper:").grid(row=1, column=0, sticky="w", pady=5)
        self.model_combo = ctk.CTkComboBox(
            grid_w,
            values=[
                "small (Recomendado — Excelente balance y entra en VRAM)",
                "medium (Alta precisión — ~2.5 GB VRAM)",
                "base (Ultrarrápido y ligero)",
                "tiny (Máxima velocidad)",
                "large-v3 (Máxima precisión — Solo CPU recomendado)",
            ],
            width=420,
        )
        current_m = self.config.whisper_model
        for val in self.model_combo._values:
            if val.startswith(current_m):
                self.model_combo.set(val)
                break
        self.model_combo.grid(row=1, column=1, sticky="w", pady=5, padx=10)

        # Idioma
        ctk.CTkLabel(grid_w, text="Idioma de Transcripción:").grid(row=2, column=0, sticky="w", pady=5)
        self.lang_combo = ctk.CTkComboBox(
            grid_w,
            values=[
                "en (Inglés — Recomendado para audio en inglés)",
                "es (Español)",
                "auto (Autodetectar idioma por fragmentos)",
                "pt (Portugués)",
            ],
            width=420,
        )
        cur_lang = self.config.language
        for l in self.lang_combo._values:
            if l.startswith(cur_lang):
                self.lang_combo.set(l)
                break
        self.lang_combo.grid(row=2, column=1, sticky="w", pady=5, padx=10)

        # --- SECCIÓN 3: DIAGNÓSTICO DE HARDWARE & FFMPEG ---
        card_diag = ctk.CTkFrame(container, corner_radius=10)
        card_diag.pack(fill="x", pady=10)

        ctk.CTkLabel(
            card_diag,
            text="💻 Diagnóstico de Hardware y Entorno",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 5))

        diag_info = DeviceDetector.get_info()
        ffmpeg_ver = FFmpegHelper.get_version() or "No detectado en PATH"

        diag_text = (
            f"• Tarjeta Gráfica: {diag_info['gpu_name']}\n"
            f"• Procesador: {diag_info['description']}\n"
            f"• Cuantización CPU: {diag_info['compute_type'].upper()} (aceleración AVX2)\n"
            f"• FFmpeg: {ffmpeg_ver[:60] if ffmpeg_ver else 'No detectado'}\n"
            f"• Protección activa: Fallback automático a CPU si la GPU se queda sin memoria"
        )

        ctk.CTkLabel(
            card_diag,
            text=diag_text,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#2ecc71",
            justify="left",
        ).pack(anchor="w", padx=20, pady=(5, 15))

        # Botón Guardar
        self.btn_save = ctk.CTkButton(
            container,
            text="💾 Guardar Cambios",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#27ae60",
            hover_color="#2ecc71",
            height=45,
            width=200,
            command=self._on_save_clicked,
        )
        self.btn_save.pack(pady=20)

        self.lbl_save_status = ctk.CTkLabel(container, text="", font=ctk.CTkFont(size=13))
        self.lbl_save_status.pack()

    def _toggle_key_visibility(self):
        if self.key_entry.cget("show") == "*":
            self.key_entry.configure(show="")
            self.btn_toggle_key.configure(text="🔒")
        else:
            self.key_entry.configure(show="*")
            self.btn_toggle_key.configure(text="👁️")

    def _on_save_clicked(self):
        new_key = self.key_entry.get().strip()
        selected_model_text = self.model_combo.get()
        model_name = selected_model_text.split(" ")[0]

        selected_gemini_text = self.gemini_model_combo.get()
        gemini_model_name = selected_gemini_text.split(" ")[0]

        selected_device_text = self.device_combo.get()
        backend_name = selected_device_text.split(" ")[0].lower()

        selected_lang_text = self.lang_combo.get()
        lang_code = selected_lang_text.split(" ")[0]

        self.config.gemini_api_key = new_key
        self.config.gemini_model = gemini_model_name
        self.config.whisper_backend = backend_name
        self.config.whisper_model = model_name
        self.config.language = lang_code
        self.config.save_to_env()

        self.lbl_save_status.configure(
            text="✅ Configuración guardada en .env correctamente.", text_color="#2ecc71"
        )
        self.after(3000, lambda: self.lbl_save_status.configure(text=""))
