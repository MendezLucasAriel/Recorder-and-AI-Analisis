import json
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
        # 1. SECCIÓN MOTOR DE INTELIGENCIA ARTIFICIAL (GEMINI / LM STUDIO LOCAL)
        # =========================================================================
        sec_ai = ctk.CTkFrame(scroll, fg_color=("#333333", "#252525"), corner_radius=8)
        sec_ai.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(
            sec_ai, text="🤖 Motor de IA para Apuntes y Resúmenes", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=15, pady=(12, 4))

        ctk.CTkLabel(
            sec_ai,
            text="Elige entre Google Gemini (procesamiento en la nube) o LM Studio / Localhost (100% privado en tu hardware local).",
            font=ctk.CTkFont(size=11),
            text_color="#95a5a6",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        # Fila Proveedor de IA
        prov_row = ctk.CTkFrame(sec_ai, fg_color="transparent")
        prov_row.pack(fill="x", padx=15, pady=(0, 12))

        ctk.CTkLabel(prov_row, text="Proveedor de IA:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        self.combo_ai_provider = ctk.CTkComboBox(
            prov_row,
            values=[
                "gemini (Google Gemini — Nube)",
                "local (LM Studio / Localhost — 100% Local)",
            ],
            command=self._on_provider_change,
            width=380,
        )
        self.combo_ai_provider.pack(side="left")

        # --- Contenedor Gemini ---
        self.frame_gemini = ctk.CTkFrame(sec_ai, fg_color="transparent")
        self.frame_gemini.pack(fill="x", padx=15, pady=(0, 10))

        key_row = ctk.CTkFrame(self.frame_gemini, fg_color="transparent")
        key_row.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(key_row, text="Gemini API Key:").pack(side="left", padx=(0, 10))
        self.entry_api_key = ctk.CTkEntry(
            key_row, placeholder_text="Pega tu clave AIzaSy...", width=320, show="*"
        )
        self.entry_api_key.pack(side="left", padx=(0, 8))

        self.btn_toggle_key = ctk.CTkButton(
            key_row, text="👁️", width=38, command=self._toggle_key_visibility
        )
        self.btn_toggle_key.pack(side="left", padx=(0, 8))

        btn_get_key = ctk.CTkButton(
            key_row,
            text="🌐 Obtener API Key",
            fg_color="#2980b9",
            hover_color="#3498db",
            command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey"),
        )
        btn_get_key.pack(side="left")

        model_row = ctk.CTkFrame(self.frame_gemini, fg_color="transparent")
        model_row.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(model_row, text="Modelo Gemini:").pack(side="left", padx=(0, 10))
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

        # --- Contenedor LM Studio / Local ---
        self.frame_local = ctk.CTkFrame(sec_ai, fg_color="transparent")

        local_url_row = ctk.CTkFrame(self.frame_local, fg_color="transparent")
        local_url_row.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(local_url_row, text="URL Servidor:").pack(side="left", padx=(0, 10))
        self.entry_local_url = ctk.CTkEntry(
            local_url_row, placeholder_text="http://localhost:1234/v1", width=280
        )
        self.entry_local_url.pack(side="left", padx=(0, 8))

        self.btn_detect_local = ctk.CTkButton(
            local_url_row,
            text="🔄 Detectar Modelos",
            fg_color="#16a085",
            hover_color="#1abc9c",
            command=self._detect_local_models,
        )
        self.btn_detect_local.pack(side="left")

        local_model_row = ctk.CTkFrame(self.frame_local, fg_color="transparent")
        local_model_row.pack(fill="x", pady=(0, 5))

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
        self.combo_local_model.pack(side="left")

        self.lbl_local_status = ctk.CTkLabel(
            self.frame_local, text="", font=ctk.CTkFont(size=11), text_color="#bdc3c7"
        )
        self.lbl_local_status.pack(anchor="w", pady=(2, 5))

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
        raw_gpu = DeviceDetector.get_gpu_name()
        self.combo_device = ctk.CTkComboBox(
            grid_w,
            values=[
                f"gpu (🎮 GPU {raw_gpu} — Vulkan Acelerado)",
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

    def _on_provider_change(self, choice=None):
        val = self.combo_ai_provider.get()
        if val.startswith("local"):
            self.frame_gemini.pack_forget()
            self.frame_local.pack(fill="x", padx=15, pady=(0, 10))
        else:
            self.frame_local.pack_forget()
            self.frame_gemini.pack(fill="x", padx=15, pady=(0, 10))

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

    def _load_values(self):
        # Proveedor de IA
        prov = getattr(self.cfg, "ai_provider", "gemini") or "gemini"
        if prov == "local":
            self.combo_ai_provider.set("local (LM Studio / Localhost — 100% Local)")
        else:
            self.combo_ai_provider.set("gemini (Google Gemini — Nube)")
        self._on_provider_change()

        local_url = getattr(self.cfg, "local_api_base", "http://localhost:1234/v1") or "http://localhost:1234/v1"
        self.entry_local_url.delete(0, "end")
        self.entry_local_url.insert(0, local_url)

        local_mod = getattr(self.cfg, "local_model_name", "google/gemma-4-12b-qat") or "google/gemma-4-12b-qat"
        self.combo_local_model.set(local_mod)

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
        prov_raw = self.combo_ai_provider.get()
        self.cfg.ai_provider = "local" if prov_raw.startswith("local") else "gemini"
        self.cfg.local_api_base = self.entry_local_url.get().strip() or "http://localhost:1234/v1"
        self.cfg.local_model_name = self.combo_local_model.get().strip() or "google/gemma-4-12b-qat"

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
