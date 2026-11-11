import os
import re
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Optional, List, Dict, Any

import customtkinter as ctk

from academic_recorder.ai.stem_config import AcademicConfig
from academic_recorder.ai.stem_summarizer import StemSummarizer
from academic_recorder.ai.stem_transcriber import StemTranscriber
from academic_recorder.models.class_session import ClassSession, ClassSummary
from academic_recorder.recorder.class_session_manager import ClassSessionManager
from academic_recorder.utils.video_player import VideoPlayerHelper, parse_timestamp_to_seconds


class ClassImportDialog(ctk.CTkToplevel):
    """Diálogo modal para importar grabaciones externas (Zoom, Teams, Meet o Drive)."""

    def __init__(self, master, default_subject: str):
        super().__init__(master)
        self.title("Importar Clase Externa")
        self.geometry("480x280")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.result: Optional[Dict[str, str]] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)

        ctk.CTkLabel(
            self,
            text="📥 Importar Video o Audio de Clase",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 10), sticky="w")

        ctk.CTkLabel(self, text="Materia / Asignatura:").grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.entry_subj = ctk.CTkEntry(self, width=260)
        self.entry_subj.insert(0, default_subject)
        self.entry_subj.grid(row=1, column=1, padx=(0, 20), pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Docente:").grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.entry_prof = ctk.CTkEntry(self, width=260)
        self.entry_prof.grid(row=2, column=1, padx=(0, 20), pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Disciplina:").grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.combo_disc = ctk.CTkComboBox(self, values=["Física", "Matemáticas", "General"], width=260)
        self.combo_disc.set("Física" if "física" in default_subject.lower() else "Matemáticas")
        self.combo_disc.grid(row=3, column=1, padx=(0, 20), pady=5, sticky="ew")

        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.grid(row=4, column=0, columnspan=2, pady=(20, 15))

        btn_ok = ctk.CTkButton(
            btn_bar, text="Aceptar", fg_color="#27ae60", hover_color="#2ecc71", width=120, command=self._on_ok
        )
        btn_ok.pack(side="left", padx=10)

        btn_cancel = ctk.CTkButton(
            btn_bar, text="Cancelar", fg_color="#7f8c8d", hover_color="#95a5a6", width=100, command=self._on_cancel
        )
        btn_cancel.pack(side="left", padx=10)

        self.grab_set()
        self.wait_window(self)

    def _on_ok(self):
        self.result = {
            "subject": self.entry_subj.get().strip() or "Clase Importada",
            "professor": self.entry_prof.get().strip(),
            "discipline": self.combo_disc.get(),
        }
        self.grab_release()
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()


class ClassesTab(ctk.CTkFrame):
    """Pestaña para gestionar clases universitarias, consultar apuntes y reproducir sincronizado."""

    def __init__(self, master, session_manager: ClassSessionManager):
        super().__init__(master, fg_color="transparent")
        self.session_manager = session_manager
        self.selected_session: Optional[ClassSession] = None
        self.is_processing = False

        self._init_ui()
        self.refresh_session_list()

    def _init_ui(self):
        self.grid_columnconfigure(0, weight=1, minsize=310)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        # --- PANEL IZQUIERDO: LISTA DE CLASES ---
        left_panel = ctk.CTkFrame(self, corner_radius=10)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        left_header = ctk.CTkFrame(left_panel, fg_color="transparent")
        left_header.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            left_header, text="📚 Mis Clases Grabadas", font=ctk.CTkFont(size=17, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            left_header, text="🔄", width=34, height=28, command=self.refresh_session_list
        ).pack(side="right")

        self.btn_import_media = ctk.CTkButton(
            left_panel,
            text="📥 Importar Video / Audio Externo",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2980b9",
            hover_color="#3498db",
            height=32,
            command=self._on_import_media_clicked,
        )
        self.btn_import_media.pack(fill="x", padx=10, pady=(4, 8))

        self.session_list_scroll = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        self.session_list_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # --- PANEL DERECHO: APUNTES, REPRODUCTOR Y PROCESAMIENTO ---
        self.right_panel = ctk.CTkFrame(self, corner_radius=10)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)

        # Encabezado
        self.detail_header = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.detail_header.pack(fill="x", padx=15, pady=(12, 4))

        self.lbl_class_title = ctk.CTkLabel(
            self.detail_header,
            text="Selecciona una clase de la lista",
            font=ctk.CTkFont(size=19, weight="bold"),
            anchor="w",
        )
        self.lbl_class_title.pack(side="left", fill="x", expand=True)

        self.btn_play_video = ctk.CTkButton(
            self.detail_header,
            text="▶️ Ver Video",
            width=100,
            fg_color="#27ae60",
            hover_color="#2ecc71",
            command=self._on_play_full_video_clicked,
            state="disabled",
        )
        self.btn_play_video.pack(side="right", padx=4)

        self.btn_open_folder = ctk.CTkButton(
            self.detail_header,
            text="📁 Carpeta",
            width=90,
            command=self._on_open_folder_clicked,
            state="disabled",
        )
        self.btn_open_folder.pack(side="right", padx=4)

        # Banner de Metadata
        self.meta_frame = ctk.CTkFrame(self.right_panel, fg_color=("#333333", "#252525"), corner_radius=8)
        self.meta_frame.pack(fill="x", padx=15, pady=4)

        self.lbl_meta_info = ctk.CTkLabel(
            self.meta_frame,
            text="Materia: -- | Duración: -- | Video: -- | Apuntes: --",
            font=ctk.CTkFont(size=12),
            text_color="#bdc3c7",
        )
        self.lbl_meta_info.pack(padx=10, pady=5, anchor="w")

        # Barra de progreso
        self.progress_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=15, pady=(2, 6))

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=10)
        self.progress_bar.pack(fill="x", pady=(3, 2))
        self.progress_bar.set(0)

        self.lbl_process_status = ctk.CTkLabel(
            self.progress_frame,
            text="Listo para procesar la clase.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        )
        self.lbl_process_status.pack(fill="x")

        # Botones de procesamiento
        action_bar = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        action_bar.pack(fill="x", padx=15, pady=4)

        self.btn_process_all = ctk.CTkButton(
            action_bar,
            text="⚡ Procesar Completo (Whisper STEM + Apuntes Gemini)",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#8e44ad",
            hover_color="#9b59b6",
            height=36,
            command=self._on_process_all_clicked,
            state="disabled",
        )
        self.btn_process_all.pack(side="left", padx=(0, 8))

        self.btn_transcribe_only = ctk.CTkButton(
            action_bar,
            text="📝 Solo Transcribir (Whisper)",
            height=36,
            command=self._on_transcribe_clicked,
            state="disabled",
        )
        self.btn_transcribe_only.pack(side="left", padx=4)

        self.btn_summarize_only = ctk.CTkButton(
            action_bar,
            text="🤖 Solo Apuntes (Gemini)",
            height=36,
            command=self._on_summarize_clicked,
            state="disabled",
        )
        self.btn_summarize_only.pack(side="left", padx=4)

        # Tabview: 1. Resumen y Fórmulas, 2. Índice Sincronizado, 3. Transcripción
        self.content_tabs = ctk.CTkTabview(self.right_panel)
        self.content_tabs.pack(fill="both", expand=True, padx=15, pady=(4, 12))

        self.tab_summary = self.content_tabs.add("📋 Apuntes y Fórmulas")
        self.tab_timeline = self.content_tabs.add("⏱️ Saltos en el Video (-5s)")
        self.tab_transcript = self.content_tabs.add("📝 Transcripción Completa")

        # Vista 1: Resumen y Fórmulas
        self.txt_summary = ctk.CTkTextbox(self.tab_summary, font=ctk.CTkFont(size=13), wrap="word")
        self.txt_summary.pack(fill="both", expand=True, padx=5, pady=5)

        summary_bottom = ctk.CTkFrame(self.tab_summary, fg_color="transparent")
        summary_bottom.pack(fill="x", pady=(4, 0))

        self.btn_copy_summary = ctk.CTkButton(
            summary_bottom, text="📋 Copiar Apuntes", width=140, command=self._copy_summary_to_clipboard
        )
        self.btn_copy_summary.pack(side="left", padx=5)

        # Vista 2: Timeline interactivo con botones que saltan 5 segundos antes al video
        self.timeline_scroll = ctk.CTkScrollableFrame(self.tab_timeline, fg_color="transparent")
        self.timeline_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Vista 3: Transcripción
        self.txt_transcript = ctk.CTkTextbox(self.tab_transcript, font=ctk.CTkFont(size=13), wrap="word")
        self.txt_transcript.pack(fill="both", expand=True, padx=5, pady=5)

    def refresh_session_list(self):
        for widget in self.session_list_scroll.winfo_children():
            widget.destroy()

        sessions = self.session_manager.list_sessions()
        if not sessions:
            lbl = ctk.CTkLabel(
                self.session_list_scroll,
                text="No hay clases grabadas aún.\n¡Graba tu primera clase en la pestaña 'Grabar'!",
                text_color="gray",
                justify="center",
            )
            lbl.pack(pady=40)
            return

        for s in sessions:
            card = ctk.CTkFrame(self.session_list_scroll, corner_radius=6, fg_color=("#3a3a3a", "#2b2b2b"))
            card.pack(fill="x", pady=4, padx=2)

            started = s.metadata.started_at[:16].replace("T", " ")
            dur_min = int(s.metadata.duration_seconds // 60)
            disc_icon = "⚛️" if s.metadata.discipline == "Física" else "📐"
            title = f"{disc_icon} {s.metadata.subject} ({dur_min} min)"

            btn = ctk.CTkButton(
                card,
                text=f"{title}\n📅 {started}",
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
                fg_color="transparent",
                hover_color=("#4a4a4a", "#353535"),
                command=lambda sess=s: self.select_session(sess),
            )
            btn.pack(fill="x", padx=5, pady=3)

            # Badges
            b_str = "Estado: "
            b_str += "🔊 Audio " if s.audio_file.exists() else ""
            b_str += "🖥️ 1080p " if s.video_file.exists() else ""
            b_str += "📝 Transcripción " if s.transcript_json.exists() else ""
            b_str += "✅ Apuntes" if s.summary_md.exists() else ""

            ctk.CTkLabel(
                card,
                text=b_str,
                font=ctk.CTkFont(size=10),
                text_color="#95a5a6",
                anchor="w",
            ).pack(fill="x", padx=10, pady=(0, 4))

    def select_session(self, session: ClassSession):
        self.selected_session = session
        self.btn_open_folder.configure(state="normal")
        self.btn_play_video.configure(state="normal" if session.video_file.exists() else "disabled")
        self.btn_process_all.configure(state="normal")
        self.btn_transcribe_only.configure(state="normal")
        self.btn_summarize_only.configure(state="normal" if session.transcript_json.exists() else "disabled")

        dur_min = int(session.metadata.duration_seconds // 60)
        started = session.metadata.started_at[:16].replace("T", " ")
        prof_str = f" | Prof: {session.metadata.professor}" if session.metadata.professor else ""
        self.lbl_class_title.configure(text=f"🎓 {session.metadata.subject} ({session.metadata.discipline}){prof_str}")

        self.lbl_meta_info.configure(
            text=f"Fecha: {started} | Duración: {dur_min} min | Video 1080p: {'✅' if session.video_file.exists() else '❌'} | Transcripción: {'✅' if session.transcript_json.exists() else '❌'} | Apuntes: {'✅' if session.summary_md.exists() else '❌'}"
        )

        self._load_session_content()

    def _load_session_content(self):
        if not self.selected_session:
            return

        # 1. Cargar Resumen Markdown
        self.txt_summary.delete("1.0", "end")
        if self.selected_session.summary_md.exists():
            try:
                with open(self.selected_session.summary_md, "r", encoding="utf-8") as f:
                    self.txt_summary.insert("1.0", f.read())
            except Exception as e:
                self.txt_summary.insert("1.0", f"Error leyendo apuntes: {e}")
        else:
            self.txt_summary.insert("1.0", "Apuntes no generados aún. Haz clic en 'Procesar Completo' o 'Solo Apuntes'.")

        # 2. Cargar Transcripción
        self.txt_transcript.delete("1.0", "end")
        if self.selected_session.transcript_txt.exists():
            try:
                with open(self.selected_session.transcript_txt, "r", encoding="utf-8") as f:
                    self.txt_transcript.insert("1.0", f.read())
            except Exception as e:
                self.txt_transcript.insert("1.0", f"Error leyendo transcripción: {e}")
        else:
            self.txt_transcript.insert("1.0", "Transcripción no disponible aún. Haz clic en 'Procesar Completo'.")

        # 3. Construir lista interactiva de saltos de video
        for widget in self.timeline_scroll.winfo_children():
            widget.destroy()

        summary = self.selected_session.load_summary()
        if summary and (summary.timeline_index or summary.study_bullet_points):
            has_video = self.selected_session.video_file.exists()
            tip_text = (
                "💡 Haz clic en cualquier botón de tiempo para abrir el video 5 segundos antes de que empiece a hablar el profesor."
                if has_video
                else "⚠️ Esta clase no tiene archivo de video grabado."
            )
            ctk.CTkLabel(
                self.timeline_scroll,
                text=tip_text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#f39c12" if has_video else "gray",
                anchor="w",
            ).pack(fill="x", padx=10, pady=(5, 10))

            # Sección de temas clave con marcas de tiempo
            items_to_render = []
            if summary.timeline_index:
                for idx_item in summary.timeline_index:
                    t = idx_item.get("time", idx_item.get("timestamp", "00:00"))
                    topic = idx_item.get("topic", "")
                    items_to_render.append((t, topic, "Bloque Temático"))

            if summary.study_bullet_points:
                for pt in summary.study_bullet_points:
                    t = pt.get("time", pt.get("timestamp", "00:00"))
                    topic = pt.get("topic", "")
                    expl = pt.get("explanation", "")
                    desc = f"{topic}: {expl}" if topic else expl
                    items_to_render.append((t, desc, "Punto de Estudio"))

            for time_str, desc, category in items_to_render:
                row = ctk.CTkFrame(self.timeline_scroll, corner_radius=6, fg_color=("#383838", "#232323"))
                row.pack(fill="x", pady=3, padx=5)

                sec = parse_timestamp_to_seconds(time_str)
                btn_play = ctk.CTkButton(
                    row,
                    text=f"▶️ [{time_str}] (-5s)",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color="#2980b9",
                    hover_color="#3498db",
                    width=110,
                    height=28,
                    state="normal" if has_video else "disabled",
                    command=lambda s=sec: self._play_at_seconds(s),
                )
                btn_play.pack(side="left", padx=8, pady=5)

                ctk.CTkLabel(
                    row,
                    text=desc,
                    font=ctk.CTkFont(size=12),
                    anchor="w",
                    justify="left",
                    wraplength=550,
                ).pack(side="left", fill="x", expand=True, padx=5, pady=5)
        else:
            lbl = ctk.CTkLabel(
                self.timeline_scroll,
                text="No hay índice cronológico generado aún.\nGenera los apuntes con Gemini para ver los botones de salto temporal.",
                text_color="gray",
                justify="center",
            )
            lbl.pack(pady=40)

    def _play_at_seconds(self, seconds: float):
        if not self.selected_session or not self.selected_session.video_file.exists():
            return
        cfg = AcademicConfig.load()
        lead_time = cfg.video_lead_time_sec  # 5 segundos por defecto
        VideoPlayerHelper.play_at(self.selected_session.video_file, seconds, lead_time=lead_time)

    def _on_play_full_video_clicked(self):
        if self.selected_session and self.selected_session.video_file.exists():
            VideoPlayerHelper.play_at(self.selected_session.video_file, 0.0, lead_time=0.0)

    def _on_open_folder_clicked(self):
        if self.selected_session and self.selected_session.dir.exists():
            os.startfile(str(self.selected_session.dir))

    def _copy_summary_to_clipboard(self):
        text = self.txt_summary.get("1.0", "end-1c")
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.btn_copy_summary.configure(text="✅ ¡Copiado!")
            self.after(2000, lambda: self.btn_copy_summary.configure(text="📋 Copiar Apuntes"))

    def _on_import_media_clicked(self):
        if self.is_processing:
            return

        file_path = filedialog.askopenfilename(
            title="Seleccionar Video o Audio de Clase Universitaria",
            filetypes=[
                (
                    "Archivos Multimedia",
                    "*.mp4 *.mkv *.avi *.mov *.webm *.wmv *.flv *.m4v *.wav *.mp3 *.m4a *.flac *.ogg *.aac",
                ),
                ("Videos de Clase", "*.mp4 *.mkv *.avi *.mov *.webm *.wmv *.flv *.m4v"),
                ("Audios de Clase", "*.wav *.mp3 *.m4a *.flac *.ogg *.aac"),
                ("Todos los archivos", "*.*"),
            ],
        )

        if not file_path:
            return

        media_path = Path(file_path)
        default_subject = media_path.stem

        dialog = ClassImportDialog(self, default_subject=default_subject)
        if not dialog.result:
            return

        info = dialog.result
        self.btn_import_media.configure(state="disabled")
        self.progress_bar.set(0.3)
        self.lbl_process_status.configure(
            text=f"📥 Extrayendo y optimizando pista de audio de '{media_path.name}'...",
            text_color="#3498db",
        )

        threading.Thread(
            target=self._run_import_thread,
            args=(media_path, info["subject"], info["professor"], info["discipline"]),
            daemon=True,
        ).start()

    def _run_import_thread(self, media_path: Path, subject: str, professor: str, discipline: str):
        session = self.session_manager.import_external_media(
            media_path=media_path,
            subject=subject,
            professor=professor,
            discipline=discipline,
        )
        self.after(0, lambda: self._on_import_completed(session))

    def _on_import_completed(self, session: Optional[ClassSession]):
        self.btn_import_media.configure(state="normal")
        self.progress_bar.set(0)

        if session:
            self.refresh_session_list()
            self.select_session(session)
            dur_mins = session.metadata.duration_seconds / 60.0
            self.lbl_process_status.configure(
                text=f"✅ Clase importada: {session.metadata.subject} ({dur_mins:.1f} min). ¡Lista para procesar!",
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
        cfg = AcademicConfig.load()

        try:
            # 1. Transcripción con Whisper STEM si no existe
            if not session.transcript_json.exists():
                init_prompt = cfg.get_effective_initial_prompt()
                self._update_status(f"Transcribiendo con sesgo de {session.metadata.discipline}...", 0.05)
                transcriber = StemTranscriber(
                    model_name=cfg.whisper_model,
                    backend=cfg.whisper_backend,
                    device=cfg.whisper_device,
                    compute_type=cfg.whisper_compute_type,
                    language=cfg.language,
                    initial_prompt=init_prompt,
                )

                def on_progress(p, seg_text, eta):
                    mins_eta = int(eta // 60)
                    secs_eta = int(eta % 60)
                    eta_str = f" | ETA: {mins_eta}m {secs_eta}s" if eta > 0 else ""
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
                self._update_status(f"Transcripción lista en {m}m {s}s. Conectando con Gemini...", 0.72)
            else:
                self._update_status("Transcripción existente encontrada. Cargando...", 0.6)
                transcript = session.load_transcript()

            # 2. Resumen y apuntes con IA (Gemini o LM Studio)
            prov_label = f"LM Studio ({cfg.local_model_name})" if getattr(cfg, "ai_provider", "gemini") == "local" else f"Gemini ({cfg.gemini_model})"
            self._update_status(f"Estructurando fórmulas en LaTeX, marcas de tiempo y glosario con {prov_label}...", 0.76)
            summarizer = StemSummarizer(api_key=cfg.gemini_api_key)
            summary = summarizer.summarize(
                transcript=transcript,
                subject=session.metadata.subject,
                professor=session.metadata.professor,
                discipline=session.metadata.discipline,
                on_status=lambda s: self._update_status(s, 0.88),
            )
            session.save_summary(summary)

            self._update_status("🎉 ¡Apuntes generados con éxito! Listos para estudiar.", 1.0)
            self.after(0, self._load_session_content)
            self.after(0, self.refresh_session_list)

        except Exception as e:
            self._update_status(f"❌ Error: {e}", 0.0)
        finally:
            self._set_ui_processing_state(False)

    def _run_transcription_only(self):
        self._set_ui_processing_state(True)
        session = self.selected_session
        cfg = AcademicConfig.load()
        try:
            init_prompt = cfg.get_effective_initial_prompt()
            self._update_status(f"Transcribiendo con sesgo de {session.metadata.discipline}...", 0.05)
            transcriber = StemTranscriber(
                model_name=cfg.whisper_model,
                backend=cfg.whisper_backend,
                device=cfg.whisper_device,
                compute_type=cfg.whisper_compute_type,
                language=cfg.language,
                initial_prompt=init_prompt,
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
            self._update_status(f"✅ Transcripción completada en {m}m {s}s.", 1.0)
            self.after(0, self._load_session_content)
            self.after(0, self.refresh_session_list)
        except Exception as e:
            self._update_status(f"❌ Error: {e}", 0.0)
        finally:
            self._set_ui_processing_state(False)

    def _run_summarization_only(self):
        self._set_ui_processing_state(True)
        session = self.selected_session
        cfg = AcademicConfig.load()
        try:
            transcript = session.load_transcript()
            if not transcript:
                raise ValueError("No hay transcripción disponible. Transcribe primero.")

            prov_label = f"LM Studio ({cfg.local_model_name})" if getattr(cfg, "ai_provider", "gemini") == "local" else f"Gemini ({cfg.gemini_model})"
            self._update_status(f"Estructurando fórmulas en LaTeX y glosario con {prov_label}...", 0.3)
            summarizer = StemSummarizer(api_key=cfg.gemini_api_key)
            summary = summarizer.summarize(
                transcript=transcript,
                subject=session.metadata.subject,
                professor=session.metadata.professor,
                discipline=session.metadata.discipline,
                on_status=lambda s: self._update_status(s, 0.7),
            )
            session.save_summary(summary)
            self._update_status("✅ Apuntes generados con éxito.", 1.0)
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
