import os
import re
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional, List, Dict, Any

import customtkinter as ctk

from work_recorder.ai.work_config import WorkConfig
from work_recorder.ai.work_summarizer import WorkSummarizer
from work_recorder.ai.work_transcriber import WorkTranscriber
from work_recorder.models.meeting_session import MeetingSession, MeetingSummary
from work_recorder.recorder.work_session_manager import WorkSessionManager
from work_recorder.utils.video_player import VideoPlayerHelper, parse_timestamp_to_seconds


class MeetingImportDialog(ctk.CTkToplevel):
    """Diálogo modal para importar grabaciones externas (Teams, Zoom, Meet, Slack o grabadoras)."""

    def __init__(self, master, default_name: str):
        super().__init__(master)
        self.title("Importar Grabación de Reunión")
        self.geometry("490x300")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.result: Optional[Dict[str, str]] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)

        ctk.CTkLabel(
            self,
            text="📥 Importar Video o Audio de Reunión",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 12), sticky="w")

        ctk.CTkLabel(self, text="Asunto / Reunión:").grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.entry_name = ctk.CTkEntry(self, width=280)
        self.entry_name.insert(0, default_name)
        self.entry_name.grid(row=1, column=1, padx=(0, 20), pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Tipo de Reunión:").grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.combo_type = ctk.CTkComboBox(
            self,
            values=[
                "Sync / Daily",
                "Reunión con Cliente",
                "Planificación / Sprint",
                "1-on-1 / Feedback",
                "Estratégica / Dirección",
                "Retrospectiva",
                "Técnica / Arquitectura",
                "General",
            ],
            width=280,
        )
        self.combo_type.set("Sync / Daily")
        self.combo_type.grid(row=2, column=1, padx=(0, 20), pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Participantes (opc.):").grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.entry_parts = ctk.CTkEntry(self, width=280, placeholder_text="Ej: Martín, Laura, Lucas, Cliente")
        self.entry_parts.grid(row=3, column=1, padx=(0, 20), pady=5, sticky="ew")

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
            "meeting_name": self.entry_name.get().strip() or "Reunión Importada",
            "meeting_type": self.combo_type.get(),
            "participants": self.entry_parts.get().strip(),
        }
        self.grab_release()
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()


class MeetingsTab(ctk.CTkFrame):
    """Pestaña para gestionar reuniones de trabajo, minutas ejecutivas, tareas y reproducción sincronizada."""

    def __init__(self, master, session_manager: WorkSessionManager):
        super().__init__(master, fg_color="transparent")
        self.session_manager = session_manager
        self.selected_session: Optional[MeetingSession] = None
        self.is_processing = False

        self._init_ui()
        self.refresh_session_list()

    def _init_ui(self):
        self.grid_columnconfigure(0, weight=1, minsize=320)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        # =========================================================================
        # PANEL IZQUIERDO: LISTA DE REUNIONES
        # =========================================================================
        left_panel = ctk.CTkFrame(self, corner_radius=10)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        left_header = ctk.CTkFrame(left_panel, fg_color="transparent")
        left_header.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            left_header, text="💼 Reuniones y Minutas", font=ctk.CTkFont(size=17, weight="bold")
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

        # =========================================================================
        # PANEL DERECHO: DETALLES, MINUTA, TAREAS Y TRANSCRIPCIÓN
        # =========================================================================
        self.right_panel = ctk.CTkFrame(self, corner_radius=10)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)

        # Encabezado superior
        self.detail_header = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.detail_header.pack(fill="x", padx=15, pady=(12, 4))

        self.lbl_meeting_title = ctk.CTkLabel(
            self.detail_header,
            text="Selecciona una reunión de la lista",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        )
        self.lbl_meeting_title.pack(side="left", fill="x", expand=True)

        self.btn_play_video = ctk.CTkButton(
            self.detail_header,
            text="▶️ Ver Grabación",
            width=110,
            fg_color="#27ae60",
            hover_color="#2ecc71",
            command=self._on_play_full_video_clicked,
            state="disabled",
        )
        self.btn_play_video.pack(side="right", padx=4)

        self.btn_open_folder = ctk.CTkButton(
            self.detail_header,
            text="📁 Carpeta",
            width=80,
            command=self._on_open_folder_clicked,
            state="disabled",
        )
        self.btn_open_folder.pack(side="right", padx=4)

        self.btn_delete_session = ctk.CTkButton(
            self.detail_header,
            text="🗑️",
            width=36,
            fg_color="#c0392b",
            hover_color="#e74c3c",
            command=self._on_delete_session_clicked,
            state="disabled",
        )
        self.btn_delete_session.pack(side="right", padx=4)

        # Banner de Metadata
        self.meta_frame = ctk.CTkFrame(self.right_panel, fg_color=("#333333", "#252525"), corner_radius=8)
        self.meta_frame.pack(fill="x", padx=15, pady=4)

        self.lbl_meta_info = ctk.CTkLabel(
            self.meta_frame,
            text="Tipo: -- | Fecha: -- | Duración: -- | Participantes: --",
            font=ctk.CTkFont(size=12),
            text_color="#bdc3c7",
        )
        self.lbl_meta_info.pack(padx=10, pady=5, anchor="w")

        # Barra de progreso y estado
        self.progress_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=15, pady=(2, 6))

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=8)
        self.progress_bar.pack(fill="x", pady=(3, 2))
        self.progress_bar.set(0)

        self.lbl_process_status = ctk.CTkLabel(
            self.progress_frame,
            text="Listo para procesar la reunión.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        )
        self.lbl_process_status.pack(fill="x")

        # Barra de acciones (Procesar Completo, Solo Transcribir, Solo Minuta)
        action_bar = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        action_bar.pack(fill="x", padx=15, pady=4)

        self.btn_process_all = ctk.CTkButton(
            action_bar,
            text="⚡ Procesar Completo (Whisper + Minuta IA)",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#8e44ad",
            hover_color="#9b59b6",
            height=34,
            command=self._on_process_all_clicked,
            state="disabled",
        )
        self.btn_process_all.pack(side="left", padx=(0, 6))

        self.btn_transcribe_only = ctk.CTkButton(
            action_bar,
            text="📝 Solo Transcribir (Whisper Local)",
            height=34,
            command=self._on_transcribe_clicked,
            state="disabled",
        )
        self.btn_transcribe_only.pack(side="left", padx=4)

        self.btn_summarize_only = ctk.CTkButton(
            action_bar,
            text="🤖 Generar Minuta (Gemini)",
            height=34,
            command=self._on_summarize_clicked,
            state="disabled",
        )
        self.btn_summarize_only.pack(side="left", padx=4)

        # Tabview principal del detalle
        self.content_tabs = ctk.CTkTabview(self.right_panel)
        self.content_tabs.pack(fill="both", expand=True, padx=15, pady=(4, 12))

        self.tab_summary = self.content_tabs.add("📋 Minuta Ejecutiva")
        self.tab_actions = self.content_tabs.add("✅ Tareas y Compromisos")
        self.tab_timeline = self.content_tabs.add("⏱️ Agenda y Saltos (-3s)")
        self.tab_transcript = self.content_tabs.add("📝 Transcripción Completa")

        # ---------------------------------------------------------------------
        # Vista 1: Minuta Ejecutiva (Markdown + botones de exportar/copiar)
        # ---------------------------------------------------------------------
        self.txt_summary = ctk.CTkTextbox(self.tab_summary, font=ctk.CTkFont(size=13), wrap="word")
        self.txt_summary.pack(fill="both", expand=True, padx=5, pady=5)

        summary_bottom = ctk.CTkFrame(self.tab_summary, fg_color="transparent")
        summary_bottom.pack(fill="x", pady=(4, 0))

        self.btn_copy_summary = ctk.CTkButton(
            summary_bottom, text="📋 Copiar Minuta", width=140, command=self._copy_summary_to_clipboard
        )
        self.btn_copy_summary.pack(side="left", padx=5)

        self.btn_export_md = ctk.CTkButton(
            summary_bottom,
            text="💾 Guardar como Archivo .md",
            width=170,
            fg_color="#34495e",
            hover_color="#415b76",
            command=self._export_markdown_file,
        )
        self.btn_export_md.pack(side="left", padx=5)

        # ---------------------------------------------------------------------
        # Vista 2: Tareas y Compromisos (Action Items)
        # ---------------------------------------------------------------------
        self.actions_scroll = ctk.CTkScrollableFrame(self.tab_actions, fg_color="transparent")
        self.actions_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # ---------------------------------------------------------------------
        # Vista 3: Agenda y Saltos en Video
        # ---------------------------------------------------------------------
        self.timeline_scroll = ctk.CTkScrollableFrame(self.tab_timeline, fg_color="transparent")
        self.timeline_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # ---------------------------------------------------------------------
        # Vista 4: Transcripción Completa
        # ---------------------------------------------------------------------
        self.txt_transcript = ctk.CTkTextbox(self.tab_transcript, font=ctk.CTkFont(size=12), wrap="word")
        self.txt_transcript.pack(fill="both", expand=True, padx=5, pady=5)

        transcript_bottom = ctk.CTkFrame(self.tab_transcript, fg_color="transparent")
        transcript_bottom.pack(fill="x", pady=(4, 0))

        self.btn_copy_transcript = ctk.CTkButton(
            transcript_bottom, text="📋 Copiar Transcripción", width=160, command=self._copy_transcript_to_clipboard
        )
        self.btn_copy_transcript.pack(side="left", padx=5)

    def refresh_session_list(self):
        for widget in self.session_list_scroll.winfo_children():
            widget.destroy()

        sessions = self.session_manager.list_sessions()
        if not sessions:
            lbl = ctk.CTkLabel(
                self.session_list_scroll,
                text="No hay reuniones grabadas aún.\nUsa la pestaña 'Grabar Reunión'\no importa un archivo externo.",
                text_color="gray",
                justify="center",
            )
            lbl.pack(pady=30)
            return

        for s in sessions:
            card = ctk.CTkFrame(self.session_list_scroll, corner_radius=8, fg_color=("#333333", "#222222"))
            card.pack(fill="x", pady=4, padx=3)
            card.bind("<Button-1>", lambda event, sess=s: self.select_session(sess))

            # Header tarjeta
            t_row = ctk.CTkFrame(card, fg_color="transparent")
            t_row.pack(fill="x", padx=8, pady=(6, 2))
            t_row.bind("<Button-1>", lambda event, sess=s: self.select_session(sess))

            title = ctk.CTkLabel(
                t_row,
                text=s.metadata.meeting_name,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
            )
            title.pack(side="left", fill="x", expand=True)
            title.bind("<Button-1>", lambda event, sess=s: self.select_session(sess))

            # Subtítulo (tipo, fecha, duración)
            date_short = s.metadata.started_at[:10] if s.metadata.started_at else "--"
            dur_min = int(s.metadata.duration_seconds // 60) if s.metadata.duration_seconds > 0 else 0
            dur_str = f"{dur_min} min" if dur_min > 0 else "<1 min"

            sub_label = ctk.CTkLabel(
                card,
                text=f"{s.metadata.meeting_type} • {date_short} ({dur_str})",
                font=ctk.CTkFont(size=11),
                text_color="#95a5a6",
                anchor="w",
            )
            sub_label.pack(fill="x", padx=8, pady=(0, 2))
            sub_label.bind("<Button-1>", lambda event, sess=s: self.select_session(sess))

            # Badges
            b_row = ctk.CTkFrame(card, fg_color="transparent")
            b_row.pack(fill="x", padx=8, pady=(0, 6))
            b_row.bind("<Button-1>", lambda event, sess=s: self.select_session(sess))

            has_vid = s.video_file.exists()
            has_tr = s.transcript_json.exists()
            has_sum = s.summary_md.exists()

            badges = [
                ("🎙️ Audio", "#27ae60"),
                ("📹 Video", "#9b59b6" if has_vid else "#555555"),
                ("📝 Transcripción", "#2980b9" if has_tr else "#555555"),
                ("📋 Minuta", "#f39c12" if has_sum else "#555555"),
            ]
            for b_text, b_color in badges:
                b_lbl = ctk.CTkLabel(
                    b_row,
                    text=b_text,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    text_color="white",
                    fg_color=b_color,
                    corner_radius=4,
                )
                b_lbl.pack(side="left", padx=(0, 4))
                b_lbl.bind("<Button-1>", lambda event, sess=s: self.select_session(sess))

    def select_session(self, session: MeetingSession):
        self.selected_session = session
        self.btn_open_folder.configure(state="normal")
        self.btn_delete_session.configure(state="normal")
        self.btn_play_video.configure(state="normal" if (session.video_file.exists() or session.audio_file.exists()) else "disabled")
        self.btn_process_all.configure(state="normal")
        self.btn_transcribe_only.configure(state="normal")
        self.btn_summarize_only.configure(state="normal" if session.transcript_json.exists() else "disabled")

        dur_min = int(session.metadata.duration_seconds // 60)
        started = session.metadata.started_at[:16].replace("T", " ") if session.metadata.started_at else "--"
        parts_str = f" | Participantes: {session.metadata.participants_str}" if session.metadata.participants_str else ""

        self.lbl_meeting_title.configure(text=f"💼 {session.metadata.meeting_name} ({session.metadata.meeting_type})")
        self.lbl_meta_info.configure(
            text=f"Fecha: {started} | Duración: {dur_min} min{parts_str} | Video: {'✅' if session.video_file.exists() else '❌'} | Transcripción: {'✅' if session.transcript_json.exists() else '❌'} | Minuta: {'✅' if session.summary_md.exists() else '❌'}"
        )

        self._load_session_content()

    def _load_session_content(self):
        if not self.selected_session:
            return

        # 1. Cargar Minuta Ejecutiva Markdown
        self.txt_summary.delete("1.0", "end")
        if self.selected_session.summary_md.exists():
            try:
                with open(self.selected_session.summary_md, "r", encoding="utf-8") as f:
                    self.txt_summary.insert("1.0", f.read())
            except Exception as e:
                self.txt_summary.insert("1.0", f"Error leyendo minuta: {e}")
        else:
            self.txt_summary.insert("1.0", "Minuta no generada aún.\nHaz clic en '⚡ Procesar Completo' o '🤖 Generar Minuta' si ya tienes la transcripción.")

        # 2. Cargar Transcripción Completa
        self.txt_transcript.delete("1.0", "end")
        if self.selected_session.transcript_txt.exists():
            try:
                with open(self.selected_session.transcript_txt, "r", encoding="utf-8") as f:
                    self.txt_transcript.insert("1.0", f.read())
            except Exception as e:
                self.txt_transcript.insert("1.0", f"Error leyendo transcripción: {e}")
        elif self.selected_session.transcript_json.exists():
            try:
                tr = self.selected_session.load_transcript()
                if tr:
                    self.txt_transcript.insert("1.0", tr.full_text)
            except Exception as e:
                self.txt_transcript.insert("1.0", f"Error cargando transcripción: {e}")
        else:
            self.txt_transcript.insert("1.0", "Transcripción no disponible aún.\nHaz clic en '⚡ Procesar Completo' o '📝 Solo Transcribir'.")

        # 3. Cargar Tareas y Compromisos (Action Items)
        for w in self.actions_scroll.winfo_children():
            w.destroy()

        summary = self.selected_session.load_summary()
        if summary and summary.action_items:
            ctk.CTkLabel(
                self.actions_scroll,
                text=f"Total de Compromisos Identificados: {len(summary.action_items)}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#3498db",
                anchor="w",
            ).pack(fill="x", padx=10, pady=(4, 8))

            priority_colors = {
                "alta": "#e74c3c",
                "media": "#f39c12",
                "baja": "#27ae60",
            }

            for idx, item in enumerate(summary.action_items, 1):
                task = item.get("task", "")
                assignee = item.get("assignee", "No especificado")
                deadline = item.get("deadline", "Sin definir")
                prio = str(item.get("priority", "media")).lower()
                prio_color = priority_colors.get(prio, "#7f8c8d")

                item_card = ctk.CTkFrame(self.actions_scroll, corner_radius=6, fg_color=("#383838", "#252525"))
                item_card.pack(fill="x", pady=4, padx=5)

                top_line = ctk.CTkFrame(item_card, fg_color="transparent")
                top_line.pack(fill="x", padx=10, pady=(6, 2))

                ctk.CTkLabel(
                    top_line,
                    text=f"#{idx}  {task}",
                    font=ctk.CTkFont(size=13, weight="bold"),
                    anchor="w",
                    justify="left",
                    wraplength=600,
                ).pack(side="left", fill="x", expand=True)

                ctk.CTkLabel(
                    top_line,
                    text=f"Prioridad: {prio.capitalize()}",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    text_color="white",
                    fg_color=prio_color,
                    corner_radius=4,
                    padx=6,
                    pady=2,
                ).pack(side="right")

                bottom_line = ctk.CTkFrame(item_card, fg_color="transparent")
                bottom_line.pack(fill="x", padx=10, pady=(2, 6))

                ctk.CTkLabel(
                    bottom_line,
                    text=f"👤 Asignado: {assignee}   |   📅 Plazo: {deadline}",
                    font=ctk.CTkFont(size=11),
                    text_color="#bdc3c7",
                    anchor="w",
                ).pack(side="left")
        else:
            lbl_actions = ctk.CTkLabel(
                self.actions_scroll,
                text="No hay compromisos estructurados aún.\nGenera la minuta ejecutiva para extraer automáticamente tareas, responsables y plazos.",
                text_color="gray",
                justify="center",
            )
            lbl_actions.pack(pady=40)

        # 4. Cargar Agenda y Saltos en Video
        for w in self.timeline_scroll.winfo_children():
            w.destroy()

        if summary and summary.topics_timeline:
            has_media = self.selected_session.video_file.exists() or self.selected_session.audio_file.exists()
            tip_text = (
                "💡 Haz clic en cualquier timestamp para saltar en el reproductor 3 segundos antes de que se mencione el tema."
                if has_media
                else "⚠️ Esta reunión no tiene archivo multimedia para reproducir."
            )
            ctk.CTkLabel(
                self.timeline_scroll,
                text=tip_text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#f39c12" if has_media else "gray",
                anchor="w",
            ).pack(fill="x", padx=10, pady=(5, 10))

            for item in summary.topics_timeline:
                time_str = item.get("timestamp", "00:00")
                topic = item.get("topic", "")
                kpoints = item.get("key_points", "")
                desc = f"{topic}: {kpoints}" if topic and kpoints else (topic or kpoints)

                row = ctk.CTkFrame(self.timeline_scroll, corner_radius=6, fg_color=("#383838", "#232323"))
                row.pack(fill="x", pady=3, padx=5)

                sec = parse_timestamp_to_seconds(time_str)
                btn_play = ctk.CTkButton(
                    row,
                    text=f"▶️ [{time_str}] (-3s)",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color="#2980b9",
                    hover_color="#3498db",
                    width=110,
                    height=28,
                    state="normal" if has_media else "disabled",
                    command=lambda s=sec: self._play_at_seconds(s),
                )
                btn_play.pack(side="left", padx=8, pady=6)

                ctk.CTkLabel(
                    row,
                    text=desc,
                    font=ctk.CTkFont(size=12),
                    anchor="w",
                    justify="left",
                    wraplength=550,
                ).pack(side="left", fill="x", expand=True, padx=5, pady=6)
        else:
            lbl_tl = ctk.CTkLabel(
                self.timeline_scroll,
                text="No hay temas cronológicos generados aún.\nGenera la minuta ejecutiva para ver los saltos temporales a cada tema.",
                text_color="gray",
                justify="center",
            )
            lbl_tl.pack(pady=40)

    def _play_at_seconds(self, seconds: float):
        if not self.selected_session:
            return
        target_file = self.selected_session.video_file if self.selected_session.video_file.exists() else self.selected_session.audio_file
        if not target_file.exists():
            return
        cfg = WorkConfig.load()
        lead = cfg.video_lead_time_sec  # 3.0 segundos
        VideoPlayerHelper.play_at(target_file, seconds, lead_time=lead)

    def _on_play_full_video_clicked(self):
        if not self.selected_session:
            return
        target_file = self.selected_session.video_file if self.selected_session.video_file.exists() else self.selected_session.audio_file
        if target_file.exists():
            VideoPlayerHelper.play_at(target_file, 0.0, lead_time=0.0)

    def _on_open_folder_clicked(self):
        if self.selected_session and self.selected_session.folder.exists():
            os.startfile(str(self.selected_session.folder))

    def _on_delete_session_clicked(self):
        if not self.selected_session or self.is_processing:
            return
        name = self.selected_session.metadata.meeting_name
        ans = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Seguro que deseas eliminar la reunión '{name}' y todos sus archivos asociados?",
            parent=self,
        )
        if ans:
            try:
                import shutil
                shutil.rmtree(self.selected_session.folder)
                self.selected_session = None
                self.refresh_session_list()
                self.lbl_meeting_title.configure(text="Selecciona una reunión de la lista")
                self.lbl_meta_info.configure(text="Tipo: -- | Fecha: -- | Duración: -- | Participantes: --")
                self.txt_summary.delete("1.0", "end")
                self.txt_transcript.delete("1.0", "end")
                for w in self.actions_scroll.winfo_children():
                    w.destroy()
                for w in self.timeline_scroll.winfo_children():
                    w.destroy()
                self.btn_open_folder.configure(state="disabled")
                self.btn_delete_session.configure(state="disabled")
                self.btn_play_video.configure(state="disabled")
                self.btn_process_all.configure(state="disabled")
                self.btn_transcribe_only.configure(state="disabled")
                self.btn_summarize_only.configure(state="disabled")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar la carpeta: {e}", parent=self)

    def _copy_summary_to_clipboard(self):
        text = self.txt_summary.get("1.0", "end-1c")
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.btn_copy_summary.configure(text="✅ ¡Copiado!")
            self.after(2000, lambda: self.btn_copy_summary.configure(text="📋 Copiar Minuta"))

    def _copy_transcript_to_clipboard(self):
        text = self.txt_transcript.get("1.0", "end-1c")
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.btn_copy_transcript.configure(text="✅ ¡Copiado!")
            self.after(2000, lambda: self.btn_copy_transcript.configure(text="📋 Copiar Transcripción"))

    def _export_markdown_file(self):
        text = self.txt_summary.get("1.0", "end-1c")
        if not text:
            return
        default_name = f"Minuta_{self.selected_session.metadata.meeting_name if self.selected_session else 'Reunion'}.md"
        dest = filedialog.asksaveasfilename(
            title="Guardar Minuta Ejecutiva en Markdown",
            defaultextension=".md",
            initialfile=default_name,
            filetypes=[("Archivos Markdown", "*.md"), ("Archivos de texto", "*.txt")],
        )
        if dest:
            try:
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(text)
                messagebox.showinfo("Exportación exitosa", f"Minuta guardada en:\n{dest}", parent=self)
            except Exception as e:
                messagebox.showerror("Error al guardar", str(e), parent=self)

    def _on_import_media_clicked(self):
        if self.is_processing:
            return

        file_path = filedialog.askopenfilename(
            title="Seleccionar Video o Audio de Reunión de Trabajo",
            filetypes=[
                (
                    "Archivos Multimedia",
                    "*.mp4 *.mkv *.avi *.mov *.webm *.wmv *.flv *.m4v *.wav *.mp3 *.m4a *.flac *.ogg *.aac",
                ),
                ("Videos de Reunión", "*.mp4 *.mkv *.avi *.mov *.webm *.wmv *.flv *.m4v"),
                ("Audios de Reunión", "*.wav *.mp3 *.m4a *.flac *.ogg *.aac"),
                ("Todos los archivos", "*.*"),
            ],
        )

        if not file_path:
            return

        media_path = Path(file_path)
        default_name = media_path.stem.replace("_", " ").replace("-", " ")

        dialog = MeetingImportDialog(self, default_name=default_name)
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
            args=(media_path, info["meeting_name"], info["meeting_type"], info["participants"]),
            daemon=True,
        ).start()

    def _run_import_thread(self, media_path: Path, meeting_name: str, meeting_type: str, participants: str):
        session = self.session_manager.import_external_media(
            media_path=media_path,
            meeting_name=meeting_name,
            meeting_type=meeting_type,
            participants=participants,
        )
        self.after(0, lambda: self._on_import_completed(session))

    def _on_import_completed(self, session: Optional[MeetingSession]):
        self.btn_import_media.configure(state="normal")
        self.progress_bar.set(0)

        if session:
            self.refresh_session_list()
            self.select_session(session)
            dur_mins = session.metadata.duration_seconds / 60.0
            self.lbl_process_status.configure(
                text=f"✅ Reunión importada: {session.metadata.meeting_name} ({dur_mins:.1f} min). ¡Lista para procesar!",
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

    def _update_status(self, text: str, progress: float):
        def _apply():
            self.lbl_process_status.configure(text=text, text_color="#3498db" if progress < 1.0 else "#2ecc71")
            self.progress_bar.set(progress)
        self.after(0, _apply)

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
        cfg = WorkConfig.load()

        try:
            # 1. Transcripción con Whisper si no existe
            if not session.transcript_json.exists():
                init_prompt = cfg.get_effective_initial_prompt()
                self._update_status(f"Iniciando transcripción Whisper ({cfg.whisper_model})...", 0.05)
                transcriber = WorkTranscriber(
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
                self._update_status(f"Transcripción finalizada en {m}m {s}s. Conectando con Gemini...", 0.72)
            else:
                self._update_status("Transcripción existente encontrada. Cargando...", 0.6)
                transcript = session.load_transcript()

            # 2. Resumen y Minuta con Gemini
            self._update_status(f"Generando minuta ejecutiva y tareas con {cfg.gemini_model}...", 0.76)
            summarizer = WorkSummarizer(api_key=cfg.gemini_api_key, model_name=cfg.gemini_model)
            summary = summarizer.summarize(
                transcript=transcript,
                meeting_name=session.metadata.meeting_name,
                meeting_type=session.metadata.meeting_type,
                participants=session.metadata.participants_str,
                on_status=lambda s: self._update_status(s, 0.88),
            )
            session.save_summary(summary)

            self._update_status("🎉 ¡Minuta y tareas generadas con éxito!", 1.0)
            self.after(0, self._load_session_content)
            self.after(0, self.refresh_session_list)

        except Exception as e:
            self._update_status(f"❌ Error: {e}", 0.0)
        finally:
            self._set_ui_processing_state(False)

    def _run_transcription_only(self):
        self._set_ui_processing_state(True)
        session = self.selected_session
        cfg = WorkConfig.load()

        try:
            init_prompt = cfg.get_effective_initial_prompt()
            self._update_status(f"Transcribiendo localmente ({cfg.whisper_model} en {cfg.whisper_backend})...", 0.05)
            transcriber = WorkTranscriber(
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
                self._update_status(f"Transcribiendo ({int(p*100)}%){eta_str}: {seg_text[:60]}...", p * 0.95)

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

            self._update_status(f"✅ Transcripción local finalizada en {m}m {s}s.", 1.0)
            self.after(0, self._load_session_content)
            self.after(0, self.refresh_session_list)

        except Exception as e:
            self._update_status(f"❌ Error en transcripción: {e}", 0.0)
        finally:
            self._set_ui_processing_state(False)

    def _run_summarization_only(self):
        self._set_ui_processing_state(True)
        session = self.selected_session
        cfg = WorkConfig.load()

        try:
            if not session.transcript_json.exists():
                raise FileNotFoundError("No hay archivo transcript.json para esta reunión. Transcríbela primero.")

            transcript = session.load_transcript()
            self._update_status(f"Generando minuta ejecutiva con {cfg.gemini_model}...", 0.2)
            summarizer = WorkSummarizer(api_key=cfg.gemini_api_key, model_name=cfg.gemini_model)
            summary = summarizer.summarize(
                transcript=transcript,
                meeting_name=session.metadata.meeting_name,
                meeting_type=session.metadata.meeting_type,
                participants=session.metadata.participants_str,
                on_status=lambda s: self._update_status(s, 0.6),
            )
            session.save_summary(summary)

            self._update_status("🎉 ¡Minuta y tareas generadas exitosamente!", 1.0)
            self.after(0, self._load_session_content)
            self.after(0, self.refresh_session_list)

        except Exception as e:
            self._update_status(f"❌ Error en minuta: {e}", 0.0)
        finally:
            self._set_ui_processing_state(False)
