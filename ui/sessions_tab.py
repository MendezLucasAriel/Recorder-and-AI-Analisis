import os
import subprocess
import threading
import time
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from typing import Optional, List

import customtkinter as ctk
from models.session import Session
from recorder.session_manager import SessionManager
from ai.transcriber import Transcriber
from ai.summarizer import Summarizer
from ai.config import AIConfig


class CampaignInputDialog(ctk.CTkToplevel):
    """Diálogo modal moderno para ingresar el nombre de la campaña al importar."""

    def __init__(self, master, default_campaign: str):
        super().__init__(master)
        self.title("Importar Sesión")
        self.geometry("450x220")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.result: Optional[str] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text="📥 Importar Sesión Multimedia",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 5), sticky="w")

        ctk.CTkLabel(
            self,
            text="Nombre de la campaña para esta sesión:",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        ).grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 12), sticky="w")

        self.entry = ctk.CTkEntry(self, width=410, font=ctk.CTkFont(size=13))
        self.entry.insert(0, default_campaign)
        self.entry.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)

        btn_ok = ctk.CTkButton(
            self,
            text="Aceptar",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#27ae60",
            hover_color="#2ecc71",
            command=self._on_ok,
            width=120,
        )
        btn_ok.grid(row=3, column=0, padx=(20, 10), pady=(0, 20), sticky="e")

        btn_cancel = ctk.CTkButton(
            self,
            text="Cancelar",
            fg_color="#7f8c8d",
            hover_color="#95a5a6",
            command=self._on_cancel,
            width=100,
        )
        btn_cancel.grid(row=3, column=1, padx=(10, 20), pady=(0, 20), sticky="w")

        self.entry.bind("<Return>", lambda e: self._on_ok())
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Modal
        self.grab_set()
        self.wait_window(self)

    def _on_ok(self):
        val = self.entry.get().strip()
        self.result = val if val else "Sesión Importada"
        self.grab_release()
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()


class SessionsTab(ctk.CTkFrame):
    """Pestaña para gestionar, procesar y visualizar sesiones de D&D."""

    def __init__(self, master, session_manager: SessionManager):
        super().__init__(master, fg_color="transparent")
        self.session_manager = session_manager
        self.selected_session: Optional[Session] = None
        self.is_processing = False

        self._init_ui()
        self.refresh_session_list()

    def _init_ui(self):
        # Grid layout: 2 columnas (lista a la izquierda, detalles a la derecha)
        self.grid_columnconfigure(0, weight=1, minsize=300)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        # --- PANEL IZQUIERDO: LISTA DE SESIONES ---
        left_panel = ctk.CTkFrame(self, corner_radius=10)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        left_header = ctk.CTkFrame(left_panel, fg_color="transparent")
        left_header.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            left_header, text="📜 Historial de Sesiones", font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            left_header, text="🔄", width=36, height=28, command=self.refresh_session_list
        ).pack(side="right")

        # Botón para importar video o audio externo
        self.btn_import_media = ctk.CTkButton(
            left_panel,
            text="📥 Importar Video / Audio Externo",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2980b9",
            hover_color="#3498db",
            height=34,
            command=self._on_import_media_clicked,
        )
        self.btn_import_media.pack(fill="x", padx=10, pady=(4, 8))

        self.session_list_scroll = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        self.session_list_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # --- PANEL DERECHO: DETALLE Y PROCESAMIENTO ---
        self.right_panel = ctk.CTkFrame(self, corner_radius=10)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)

        # Header detalle
        self.detail_header = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.detail_header.pack(fill="x", padx=15, pady=(15, 5))

        self.lbl_session_title = ctk.CTkLabel(
            self.detail_header,
            text="Selecciona una sesión de la lista",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        self.lbl_session_title.pack(side="left", fill="x", expand=True)

        # Botón abrir carpeta
        self.btn_open_folder = ctk.CTkButton(
            self.detail_header,
            text="📁 Abrir Carpeta",
            width=120,
            command=self._on_open_folder_clicked,
            state="disabled",
        )
        self.btn_open_folder.pack(side="right", padx=5)

        # Metadata banner
        self.meta_frame = ctk.CTkFrame(self.right_panel, fg_color=("#333333", "#252525"), corner_radius=8)
        self.meta_frame.pack(fill="x", padx=15, pady=5)

        self.lbl_meta_info = ctk.CTkLabel(
            self.meta_frame,
            text="Duración: -- | Campaña: -- | Estado: --",
            font=ctk.CTkFont(size=12),
            text_color="#bdc3c7",
        )
        self.lbl_meta_info.pack(padx=10, pady=6, anchor="w")

        # Barra de progreso y estado
        self.progress_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=15, pady=(5, 10))

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=12)
        self.progress_bar.pack(fill="x", pady=(5, 2))
        self.progress_bar.set(0)

        self.lbl_process_status = ctk.CTkLabel(
            self.progress_frame,
            text="Listo para procesar.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        self.lbl_process_status.pack(fill="x")

        # Botones de acción principales
        action_bar = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        action_bar.pack(fill="x", padx=15, pady=5)

        self.btn_process_all = ctk.CTkButton(
            action_bar,
            text="⚡ Procesar Completo (Transcribir + Resumir con IA)",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#8e44ad",
            hover_color="#9b59b6",
            height=38,
            command=self._on_process_all_clicked,
            state="disabled",
        )
        self.btn_process_all.pack(side="left", padx=(0, 10))

        self.btn_transcribe_only = ctk.CTkButton(
            action_bar,
            text="📝 Solo Transcribir (Whisper)",
            height=38,
            command=self._on_transcribe_clicked,
            state="disabled",
        )
        self.btn_transcribe_only.pack(side="left", padx=5)

        self.btn_summarize_only = ctk.CTkButton(
            action_bar,
            text="🤖 Solo Resumen (Gemini)",
            height=38,
            command=self._on_summarize_clicked,
            state="disabled",
        )
        self.btn_summarize_only.pack(side="left", padx=5)

        # Tabview para ver Resumen vs Transcripción
        self.content_tabs = ctk.CTkTabview(self.right_panel)
        self.content_tabs.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        self.tab_summary = self.content_tabs.add("📋 Resumen D&D")
        self.tab_transcript = self.content_tabs.add("📝 Transcripción Completa")

        # Vista de Resumen
        self.txt_summary = ctk.CTkTextbox(self.tab_summary, font=ctk.CTkFont(size=13), wrap="word")
        self.txt_summary.pack(fill="both", expand=True, padx=5, pady=5)

        # Botones de resumen
        summary_bottom = ctk.CTkFrame(self.tab_summary, fg_color="transparent")
        summary_bottom.pack(fill="x", pady=(5, 0))

        self.btn_copy_summary = ctk.CTkButton(
            summary_bottom, text="📋 Copiar al Portapapeles", width=160, command=self._copy_summary_to_clipboard
        )
        self.btn_copy_summary.pack(side="left", padx=5)

        # Vista de Transcripción
        self.txt_transcript = ctk.CTkTextbox(self.tab_transcript, font=ctk.CTkFont(size=13), wrap="word")
        self.txt_transcript.pack(fill="both", expand=True, padx=5, pady=5)

    def refresh_session_list(self):
        for widget in self.session_list_scroll.winfo_children():
            widget.destroy()

        sessions = self.session_manager.list_sessions()
        if not sessions:
            lbl = ctk.CTkLabel(
                self.session_list_scroll,
                text="No hay sesiones grabadas aún.\n¡Graba tu primera partida en la pestaña 'Grabar'!",
                text_color="gray",
                justify="center",
            )
            lbl.pack(pady=40)
            return

        for s in sessions:
            card = ctk.CTkFrame(self.session_list_scroll, corner_radius=6, fg_color=("#3a3a3a", "#2b2b2b"))
            card.pack(fill="x", pady=4, padx=2)

            # Nombre de la sesión / Campaña
            started = s.metadata.started_at[:16].replace("T", " ")
            duration_min = int(s.metadata.duration_seconds // 60)
            title = f"{s.metadata.campaign} ({duration_min} min)"

            btn = ctk.CTkButton(
                card,
                text=f"🎲 {title}\n📅 {started}",
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
                fg_color="transparent",
                hover_color=("#4a4a4a", "#353535"),
                command=lambda sess=s: self.select_session(sess),
            )
            btn.pack(fill="x", padx=5, pady=3)

            # Badges de estado
            badge_str = "Status: "
            badge_str += "🔊 Audio " if s.audio_file.exists() else ""
            badge_str += "🖥️ Video " if s.screen_file.exists() else ""
            badge_str += "📝 Transcripción " if s.transcript_json.exists() else ""
            badge_str += "✅ Resumen" if s.summary_md.exists() else ""

            ctk.CTkLabel(
                card,
                text=badge_str,
                font=ctk.CTkFont(size=10),
                text_color="#95a5a6",
                anchor="w",
            ).pack(fill="x", padx=10, pady=(0, 4))

    def select_session(self, session: Session):
        self.selected_session = session
        self.btn_open_folder.configure(state="normal")
        self.btn_process_all.configure(state="normal")
        self.btn_transcribe_only.configure(state="normal")
        self.btn_summarize_only.configure(state="normal" if session.transcript_json.exists() else "disabled")

        dur_min = int(session.metadata.duration_seconds // 60)
        started = session.metadata.started_at[:16].replace("T", " ")
        self.lbl_session_title.configure(text=f"🎲 {session.metadata.campaign} — {session.dir.name}")
        self.lbl_meta_info.configure(
            text=f"Fecha: {started} | Duración: {dur_min} min | Audio: {'✅' if session.audio_file.exists() else '❌'} | Transcripción: {'✅' if session.transcript_json.exists() else '❌'} | Resumen: {'✅' if session.summary_md.exists() else '❌'}"
        )

        self._load_session_content()

    def _load_session_content(self):
        if not self.selected_session:
            return

        # Cargar Resumen
        self.txt_summary.delete("1.0", "end")
        if self.selected_session.summary_md.exists():
            try:
                with open(self.selected_session.summary_md, "r", encoding="utf-8") as f:
                    self.txt_summary.insert("1.0", f.read())
            except Exception as e:
                self.txt_summary.insert("1.0", f"Error leyendo resumen: {e}")
        else:
            self.txt_summary.insert("1.0", "Resumen no generado aún. Haz clic en 'Procesar Completo' o 'Solo Resumen'.")

        # Cargar Transcripción
        self.txt_transcript.delete("1.0", "end")
        if self.selected_session.transcript_txt.exists():
            try:
                with open(self.selected_session.transcript_txt, "r", encoding="utf-8") as f:
                    self.txt_transcript.insert("1.0", f.read())
            except Exception as e:
                self.txt_transcript.insert("1.0", f"Error leyendo transcripción: {e}")
        else:
            self.txt_transcript.insert("1.0", "Transcripción no disponible aún. Haz clic en 'Procesar Completo'.")

    def _on_open_folder_clicked(self):
        if self.selected_session and self.selected_session.dir.exists():
            os.startfile(str(self.selected_session.dir))

    def _copy_summary_to_clipboard(self):
        text = self.txt_summary.get("1.0", "end-1c")
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.btn_copy_summary.configure(text="✅ ¡Copiado!")
            self.after(2000, lambda: self.btn_copy_summary.configure(text="📋 Copiar al Portapapeles"))

    def _on_import_media_clicked(self):
        if self.is_processing:
            return

        file_path = filedialog.askopenfilename(
            title="Seleccionar Video o Audio de la Sesión",
            filetypes=[
                (
                    "Archivos Multimedia",
                    "*.mp4 *.mkv *.avi *.mov *.webm *.wmv *.flv *.m4v *.wav *.mp3 *.m4a *.flac *.ogg *.aac",
                ),
                ("Videos", "*.mp4 *.mkv *.avi *.mov *.webm *.wmv *.flv *.m4v"),
                ("Audios", "*.wav *.mp3 *.m4a *.flac *.ogg *.aac"),
                ("Todos los archivos", "*.*"),
            ],
        )

        if not file_path:
            return

        media_path = Path(file_path)
        default_campaign = media_path.stem

        # Cuadro de diálogo modal para confirmar o editar el nombre de la campaña
        dialog = CampaignInputDialog(self, default_campaign=default_campaign)
        campaign_name = dialog.result
        if campaign_name is None:
            return

        # Iniciar importación en hilo secundario para no congelar la UI
        self.btn_import_media.configure(state="disabled")
        self.progress_bar.set(0.3)
        self.lbl_process_status.configure(
            text=f"📥 Extrayendo y optimizando pista de audio con FFmpeg de '{media_path.name}'...",
            text_color="#3498db",
        )

        threading.Thread(
            target=self._run_import_thread,
            args=(media_path, campaign_name),
            daemon=True,
        ).start()

    def _run_import_thread(self, media_path: Path, campaign_name: str):
        session = self.session_manager.import_external_media(media_path, campaign_name=campaign_name)
        self.after(0, lambda: self._on_import_completed(session))

    def _on_import_completed(self, session: Optional[Session]):
        self.btn_import_media.configure(state="normal")
        self.progress_bar.set(0)

        if session:
            self.refresh_session_list()
            self.select_session(session)
            dur_mins = session.metadata.duration_seconds / 60.0
            self.lbl_process_status.configure(
                text=f"✅ Sesión importada: {session.metadata.campaign} ({dur_mins:.1f} min). ¡Lista para procesar!",
                text_color="#2ecc71",
            )
        else:
            self.lbl_process_status.configure(
                text="❌ Error importando archivo. Verifica que contenga una pista de audio válida.",
                text_color="#e74c3c",
            )

    def _set_ui_processing_state(self, is_processing: bool):
        self.is_processing = is_processing
        state = "disabled" if is_processing else "normal"
        self.btn_process_all.configure(state=state)
        self.btn_transcribe_only.configure(state=state)
        self.btn_summarize_only.configure(state=state)
        self.btn_import_media.configure(state=state)

    def _on_process_all_clicked(self):
        if not self.selected_session or self.is_processing:
            return
        threading.Thread(target=self._run_full_process, daemon=True).start()

    def _on_transcribe_clicked(self):
        if not self.selected_session or self.is_processing:
            return
        threading.Thread(target=self._run_transcription_only, daemon=True).start()

    def _on_summarize_clicked(self):
        if not self.selected_session or self.is_processing:
            return
        threading.Thread(target=self._run_summarization_only, daemon=True).start()

    def _run_full_process(self):
        self._set_ui_processing_state(True)
        session = self.selected_session
        cfg = AIConfig.load()

        try:
            # 1. Transcripción con Whisper si no existe
            if not session.transcript_json.exists():
                device_desc = "GPU AMD RX 470 (Vulkan)" if cfg.whisper_backend == "gpu" else "CPU (INT8)"
                self._update_status(f"Iniciando transcripción en {device_desc}...", 0.05)
                transcriber = Transcriber(
                    model_name=cfg.whisper_model,
                    backend=cfg.whisper_backend,
                    device=cfg.whisper_device,
                    compute_type=cfg.whisper_compute_type,
                    language=cfg.language,
                )

                def on_progress(p, seg_text, eta):
                    mins_eta = int(eta // 60)
                    secs_eta = int(eta % 60)
                    eta_str = f" | ETA: {mins_eta}m {secs_eta}s" if eta > 0 else ""
                    # Mapear 0..1 a 0..0.7 en la barra de progreso
                    self._update_status(f"Transcribiendo ({int(p*100)}%){eta_str}: {seg_text[:60]}...", p * 0.7)

                t_start = time.time()
                transcript = transcriber.transcribe(
                    session.audio_file,
                    on_progress=on_progress,
                    on_status=lambda s: self._update_status(s, 0.1),
                )
                session.save_transcript(transcript)
                elapsed = time.time() - t_start
                m = int(elapsed // 60)
                s = int(elapsed % 60)
                dur_str = f"{m}m {s}s" if m > 0 else f"{s}s"
                self._update_status(f"Transcripción completada en {dur_str}. Conectando con Gemini...", 0.72)
            else:
                self._update_status("Transcripción existente encontrada. Cargando...", 0.6)
                transcript = session.load_transcript()

            # 2. Resumen con Gemini
            self._update_status("Conectando con Gemini para generar la crónica D&D...", 0.75)
            summarizer = Summarizer(api_key=cfg.gemini_api_key)
            summary = summarizer.summarize(
                transcript=transcript,
                campaign_name=session.metadata.campaign,
                on_status=lambda s: self._update_status(s, 0.85),
            )
            session.save_summary(summary)

            self._update_status("🎉 ¡Proceso finalizado! Resumen y transcripción listos.", 1.0)
            self.after(0, self._load_session_content)
            self.after(0, self.refresh_session_list)

        except Exception as e:
            self._update_status(f"❌ Error: {e}", 0.0)
        finally:
            self._set_ui_processing_state(False)

    def _run_transcription_only(self):
        self._set_ui_processing_state(True)
        session = self.selected_session
        cfg = AIConfig.load()
        try:
            device_desc = "GPU AMD RX 470 (Vulkan)" if cfg.whisper_backend == "gpu" else "CPU (INT8)"
            self._update_status(f"Iniciando transcripción en {device_desc}...", 0.05)
            transcriber = Transcriber(
                model_name=cfg.whisper_model,
                backend=cfg.whisper_backend,
                device=cfg.whisper_device,
                compute_type=cfg.whisper_compute_type,
                language=cfg.language,
            )

            def on_progress(p, seg_text, eta):
                mins_eta = int(eta // 60)
                secs_eta = int(eta % 60)
                eta_str = f" | ETA: {mins_eta}m {secs_eta}s" if eta > 0 else ""
                self._update_status(f"Transcribiendo ({int(p*100)}%){eta_str}: {seg_text[:60]}...", p)

            t_start = time.time()
            transcript = transcriber.transcribe(
                session.audio_file,
                on_progress=on_progress,
                on_status=lambda s: self._update_status(s, 0.1),
            )
            session.save_transcript(transcript)
            elapsed = time.time() - t_start
            m = int(elapsed // 60)
            s = int(elapsed % 60)
            dur_str = f"{m}m {s}s" if m > 0 else f"{s}s"
            self._update_status(f"✅ Transcripción completada en {dur_str} con {device_desc}.", 1.0)
            self.after(0, self._load_session_content)
            self.after(0, self.refresh_session_list)
        except Exception as e:
            self._update_status(f"❌ Error: {e}", 0.0)
        finally:
            self._set_ui_processing_state(False)

    def _run_summarization_only(self):
        self._set_ui_processing_state(True)
        session = self.selected_session
        cfg = AIConfig.load()
        try:
            transcript = session.load_transcript()
            if not transcript:
                raise ValueError("No hay transcripción disponible para resumir. Transcribe primero.")

            self._update_status("Generando resumen con Gemini...", 0.3)
            summarizer = Summarizer(api_key=cfg.gemini_api_key)
            summary = summarizer.summarize(
                transcript=transcript,
                campaign_name=session.metadata.campaign,
                on_status=lambda s: self._update_status(s, 0.7),
            )
            session.save_summary(summary)
            self._update_status("✅ Resumen generado con éxito.", 1.0)
            self.after(0, self._load_session_content)
            self.after(0, self.refresh_session_list)
        except Exception as e:
            self._update_status(f"❌ Error: {e}", 0.0)
        finally:
            self._set_ui_processing_state(False)

    def _update_status(self, text: str, progress: float):
        self.after(0, lambda: (
            self.lbl_process_status.configure(text=text),
            self.progress_bar.set(progress),
        ))
