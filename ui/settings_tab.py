import json
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
            text="🤖 Motor de Inteligencia Artificial (Crónicas y Resúmenes)",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 5))

        ctk.CTkLabel(
            card_api,
            text="Elige entre Google Gemini (procesamiento en la nube) o LM Studio / Localhost (100% privado en tu hardware local).",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 10))

        # Fila Proveedor
        prov_row = ctk.CTkFrame(card_api, fg_color="transparent")
        prov_row.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(prov_row, text="Proveedor de IA:").pack(side="left", padx=(0, 10))
        self.ai_prov_combo = ctk.CTkComboBox(
            prov_row,
            values=[
                "gemini (Google Gemini — Nube)",
                "local (LM Studio / Localhost — 100% Local)",
            ],
            command=self._on_ai_provider_change,
            width=380,
        )
        self.ai_prov_combo.pack(side="left")

        # --- Contenedor Gemini ---
        self.frame_gemini = ctk.CTkFrame(card_api, fg_color="transparent")
        self.frame_gemini.pack(fill="x", padx=20, pady=5)

        key_row = ctk.CTkFrame(self.frame_gemini, fg_color="transparent")
        key_row.pack(fill="x", pady=5)

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
            text="🌐 Obtener API Key",
            fg_color="#2980b9",
            hover_color="#3498db",
            command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey"),
        )
        btn_get_key.pack(side="left", padx=10)

        # Selector de modelo Gemini
        model_row = ctk.CTkFrame(self.frame_gemini, fg_color="transparent")
        model_row.pack(fill="x", pady=(10, 5))

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

        # --- Contenedor Local / LM Studio ---
        self.frame_local = ctk.CTkFrame(card_api, fg_color="transparent")

        local_url_row = ctk.CTkFrame(self.frame_local, fg_color="transparent")
        local_url_row.pack(fill="x", pady=5)

        ctk.CTkLabel(local_url_row, text="URL Servidor Local:").pack(side="left", padx=(0, 10))
        self.entry_local_url = ctk.CTkEntry(
            local_url_row, placeholder_text="http://localhost:1234/v1", width=280
        )
        self.entry_local_url.insert(0, getattr(self.config, "local_api_base", "http://localhost:1234/v1") or "http://localhost:1234/v1")
        self.entry_local_url.pack(side="left", padx=(0, 10))

        self.btn_detect_local = ctk.CTkButton(
            local_url_row,
            text="🔄 Detectar Modelos",
            fg_color="#16a085",
            hover_color="#1abc9c",
            command=self._detect_local_models,
        )
        self.btn_detect_local.pack(side="left")

        local_model_row = ctk.CTkFrame(self.frame_local, fg_color="transparent")
        local_model_row.pack(fill="x", pady=(10, 5))

        ctk.CTkLabel(local_model_row, text="Modelo Local:").pack(side="left", padx=(0, 10))
        self.combo_local_model = ctk.CTkComboBox(
            local_model_row,
            values=[
                "google/gemma-4-12b-qat",
                "meta-llama-3.1-8b-instruct-abliterated",
                "qwen2.5-7b-instruct",
                "qwen/qwen2.5-coder-14b",
            ],
            width=380,
        )
        cur_lmod = getattr(self.config, "local_model_name", "google/gemma-4-12b-qat") or "google/gemma-4-12b-qat"
        self.combo_local_model.set(cur_lmod)
        self.combo_local_model.pack(side="left")

        self.lbl_local_status = ctk.CTkLabel(
            self.frame_local, text="", font=ctk.CTkFont(size=11), text_color="#2ecc71"
        )
        self.lbl_local_status.pack(anchor="w", pady=(2, 5))

        cur_prov = getattr(self.config, "ai_provider", "gemini") or "gemini"
        if cur_prov == "local":
            self.ai_prov_combo.set("local (LM Studio / Localhost — 100% Local)")
            self.frame_gemini.pack_forget()
            self.frame_local.pack(fill="x", padx=20, pady=5)
        else:
            self.ai_prov_combo.set("gemini (Google Gemini — Nube)")
            self.frame_local.pack_forget()
            self.frame_gemini.pack(fill="x", padx=20, pady=5)

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

        # Selector de Hardware: GPU vs CPU
        ctk.CTkLabel(grid_w, text="Dispositivo de Procesamiento:").grid(row=0, column=0, sticky="w", pady=5)
        raw_gpu = DeviceDetector.get_gpu_name()
        self.device_combo = ctk.CTkComboBox(
            grid_w,
            values=[
                f"gpu (🎮 GPU {raw_gpu} — Vulkan Acelerado)",
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

    def _on_ai_provider_change(self, choice=None):
        val = self.ai_prov_combo.get()
        if val.startswith("local"):
            self.frame_gemini.pack_forget()
            self.frame_local.pack(fill="x", padx=20, pady=5)
        else:
            self.frame_local.pack_forget()
            self.frame_gemini.pack(fill="x", padx=20, pady=5)

    def _detect_local_models(self):
        url = self.entry_local_url.get().strip().rstrip("/")
        if not url.endswith("/v1"):
            url = f"{url}/v1"
        models_url = f"{url}/models"
        self.lbl_local_status.configure(text="Conectando con LM Studio...", text_color="#f1c40f")
        self.update_idletasks()
        try:
            import urllib.request
            req = urllib.request.Request(models_url)
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                if models:
                    self.combo_local_model.configure(values=models)
                    curr = self.combo_local_model.get()
                    if curr not in models:
                        self.combo_local_model.set(models[0])
                    self.lbl_local_status.configure(
                        text=f"✅ Conectado exitosamente. Se detectaron {len(models)} modelo(s).",
                        text_color="#2ecc71",
                    )
                else:
                    self.lbl_local_status.configure(
                        text="⚠️ Servidor conectado, pero no se encontraron modelos descargados.",
                        text_color="#e67e22",
                    )
        except Exception as e:
            self.lbl_local_status.configure(
                text=f"❌ No se pudo conectar a {models_url}. Verifica que LM Studio tenga el Local Server ON.",
                text_color="#e74c3c",
            )

    def _on_save_clicked(self):
        prov_text = self.ai_prov_combo.get()
        self.config.ai_provider = "local" if prov_text.startswith("local") else "gemini"
        self.config.local_api_base = self.entry_local_url.get().strip() or "http://localhost:1234/v1"
        self.config.local_model_name = self.combo_local_model.get().strip() or "google/gemma-4-12b-qat"

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
