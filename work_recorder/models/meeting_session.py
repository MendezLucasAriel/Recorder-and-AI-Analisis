import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class TranscriptSegment:
    start: float  # segundos
    end: float    # segundos
    text: str
    speaker: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptSegment":
        return cls(**data)

    @property
    def start_formatted(self) -> str:
        mins = int(self.start // 60)
        secs = int(self.start % 60)
        return f"{mins:02d}:{secs:02d}"


@dataclass
class Transcript:
    segments: List[TranscriptSegment] = field(default_factory=list)
    language: str = "es"
    duration: float = 0.0

    @property
    def full_text(self) -> str:
        return " ".join(seg.text for seg in self.segments)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "language": self.language,
            "duration": self.duration,
            "segments": [seg.to_dict() for seg in self.segments],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transcript":
        segments = [TranscriptSegment.from_dict(s) for s in data.get("segments", [])]
        return cls(
            segments=segments,
            language=data.get("language", "es"),
            duration=data.get("duration", 0.0),
        )

    def format_with_timestamps(self, interval_seconds: float = 20.0) -> str:
        if not self.segments:
            return ""

        lines = []
        current_block_start = -1.0
        current_block_texts = []

        for seg in self.segments:
            if current_block_start < 0:
                current_block_start = seg.start

            current_block_texts.append(seg.text)

            if (seg.end - current_block_start) >= interval_seconds:
                mins = int(current_block_start // 60)
                secs = int(current_block_start % 60)
                ts_str = f"[{mins:02d}:{secs:02d}]"
                lines.append(f"{ts_str} {' '.join(current_block_texts)}")
                current_block_start = -1.0
                current_block_texts = []

        if current_block_texts:
            mins = int(max(0.0, current_block_start) // 60)
            secs = int(max(0.0, current_block_start) % 60)
            ts_str = f"[{mins:02d}:{secs:02d}]"
            lines.append(f"{ts_str} {' '.join(current_block_texts)}")

        return "\n".join(lines)


@dataclass
class MeetingSummary:
    """Modelo estructurado para minutas de reuniones y notas de trabajo corporativas."""
    title: str = ""
    meeting_type: str = "Reunión de Trabajo"
    participants: List[str] = field(default_factory=list)
    overview: str = ""
    agenda_topics: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    action_items: List[Dict[str, str]] = field(default_factory=list)
    key_points: List[Dict[str, Any]] = field(default_factory=list)
    pending_questions: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def topics_timeline(self) -> List[Dict[str, Any]]:
        """Combina agenda_topics y key_points para navegación cronológica en video."""
        res = []
        for it in self.agenda_topics:
            t = it.get("time", it.get("timestamp", "00:00"))
            topic = it.get("topic", "")
            summary = it.get("summary", it.get("details", ""))
            res.append({"timestamp": t, "topic": topic, "key_points": summary})
        for it in self.key_points:
            t = it.get("time", it.get("timestamp", "00:00"))
            topic = it.get("topic", "")
            details = it.get("details", it.get("point", ""))
            res.append({"timestamp": t, "topic": topic, "key_points": details})
        return res

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MeetingSummary":
        if not isinstance(data, dict):
            return cls(overview=str(data))

        return cls(
            title=str(data.get("title") or "Minuta de Reunión"),
            meeting_type=str(data.get("meeting_type") or "Reunión de Trabajo"),
            participants=list(data.get("participants") or []),
            overview=str(data.get("overview") or data.get("summary") or ""),
            agenda_topics=list(data.get("agenda_topics") or data.get("topics") or []),
            decisions=list(data.get("decisions") or []),
            action_items=list(data.get("action_items") or data.get("tasks") or []),
            key_points=list(data.get("key_points") or data.get("points") or []),
            pending_questions=list(data.get("pending_questions") or data.get("next_steps") or []),
            created_at=str(data.get("created_at") or datetime.now().isoformat()),
        )

    def to_markdown(self) -> str:
        md = [f"# 📋 Minuta: {self.title or 'Reunión de Trabajo'}\n"]
        md.append(f"**Tipo:** {self.meeting_type} | **Fecha:** {self.created_at[:10]}")
        if self.participants:
            md.append(f"**Participantes identificados:** {', '.join(self.participants)}")
        md.append("")

        if self.overview:
            md.append("## 📌 Resumen Ejecutivo")
            md.append(self.overview + "\n")

        if self.agenda_topics:
            md.append("## ⏱️ Temas Tratados (Línea de Tiempo)")
            for item in self.agenda_topics:
                t = item.get("time", item.get("timestamp", "00:00"))
                topic = item.get("topic", item.get("title", ""))
                summary = item.get("summary", item.get("details", ""))
                line = f"- **`[{t}]` {topic}**"
                if summary:
                    line += f": {summary}"
                md.append(line)
            md.append("")

        if self.decisions:
            md.append("## 🎯 Acuerdos y Decisiones Clave")
            for d in self.decisions:
                md.append(f"- ✅ {d}")
            md.append("")

        if self.action_items:
            md.append("## ✅ Compromisos y Tareas Pendientes (Action Items)")
            for item in self.action_items:
                task = item.get("task", item.get("description", ""))
                assignee = item.get("assignee", item.get("responsible", ""))
                deadline = item.get("deadline", item.get("due_date", ""))
                
                parts = [f"- [ ] **{task}**"]
                meta = []
                if assignee:
                    meta.append(f"Responsable: {assignee}")
                if deadline:
                    meta.append(f"Plazo: {deadline}")
                if meta:
                    parts.append(f" *({', '.join(meta)})*")
                md.append("".join(parts))
            md.append("")

        if self.key_points:
            md.append("## 💡 Puntos y Discusiones Destacadas")
            for pt in self.key_points:
                t = pt.get("time", "")
                header = f"- **`[{t}]` " if t else "- **"
                topic = pt.get("topic", "")
                desc = pt.get("details", pt.get("point", ""))
                md.append(f"{header}{topic}:** {desc}")
            md.append("")

        if self.pending_questions:
            md.append("## ❓ Puntos Abiertos y Próximos Pasos")
            for q in self.pending_questions:
                md.append(f"- ⏳ {q}")
            md.append("")

        return "\n".join(md)


@dataclass
class MeetingSessionMetadata:
    id: str
    meeting_name: str = "Reunión de Trabajo"
    meeting_type: str = "General"
    participants_str: str = ""
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: Optional[str] = None
    duration_seconds: float = 0.0
    has_audio: bool = True
    has_video: bool = False
    has_transcript: bool = False
    has_summary: bool = False
    devices_used: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MeetingSessionMetadata":
        return cls(**data)


class MeetingSession:
    """Representa una sesión de reunión de trabajo almacenada en disco."""
    def __init__(self, session_dir: Path):
        self.dir = Path(session_dir)
        self.metadata_file = self.dir / "session.json"
        self.audio_file = self.dir / "audio.wav"
        self.video_file = self.dir / "video.mp4"
        self.transcript_json = self.dir / "transcript.json"
        self.transcript_txt = self.dir / "transcript.txt"
        self.summary_md = self.dir / "summary.md"
        self.summary_json = self.dir / "summary.json"

        self.metadata = self._load_metadata()

    @property
    def folder(self) -> Path:
        """Alias conveniente para la carpeta de la sesión."""
        return self.dir

    def _load_metadata(self) -> MeetingSessionMetadata:
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    return MeetingSessionMetadata.from_dict(json.load(f))
            except Exception:
                pass
        return MeetingSessionMetadata(id=self.dir.name)

    def save_metadata(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.metadata.has_audio = self.metadata.has_audio or self.audio_file.exists()
        self.metadata.has_video = self.metadata.has_video or self.video_file.exists()
        self.metadata.has_transcript = self.transcript_json.exists()
        self.metadata.has_summary = self.summary_md.exists()
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata.to_dict(), f, indent=2, ensure_ascii=False)

    def load_transcript(self) -> Optional[Transcript]:
        if not self.transcript_json.exists():
            return None
        try:
            with open(self.transcript_json, "r", encoding="utf-8") as f:
                return Transcript.from_dict(json.load(f))
        except Exception:
            return None

    def save_transcript(self, transcript: Transcript) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.transcript_json, "w", encoding="utf-8") as f:
            json.dump(transcript.to_dict(), f, indent=2, ensure_ascii=False)

        with open(self.transcript_txt, "w", encoding="utf-8") as f:
            f.write(transcript.format_with_timestamps(interval_seconds=15.0))

        self.metadata.has_transcript = True
        self.save_metadata()

    def load_summary(self) -> Optional[MeetingSummary]:
        if not self.summary_json.exists():
            return None
        try:
            with open(self.summary_json, "r", encoding="utf-8") as f:
                return MeetingSummary.from_dict(json.load(f))
        except Exception:
            return None

    def save_summary(self, summary: MeetingSummary) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.summary_json, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2, ensure_ascii=False)

        with open(self.summary_md, "w", encoding="utf-8") as f:
            f.write(summary.to_markdown())

        self.metadata.has_summary = True
        self.save_metadata()
