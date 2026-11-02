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
        """
        Agrupa los segmentos en bloques cronológicos con marca de tiempo [MM:SS]
        para que el modelo de IA pueda relacionar con precisión cada concepto.
        """
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
class ClassSummary:
    """Modelo estructurado para el resumen académico y apuntes de estudio."""
    title: str = ""
    subject: str = "Clase Universitaria"
    professor: str = ""
    discipline: str = "Matemáticas"  # "Física", "Matemáticas", "General"
    overview: str = ""
    timeline_index: List[Dict[str, Any]] = field(default_factory=list)
    study_bullet_points: List[Dict[str, Any]] = field(default_factory=list)
    key_formulas: List[Dict[str, str]] = field(default_factory=list)
    technical_glossary: List[Dict[str, str]] = field(default_factory=list)
    solved_exercises: List[Dict[str, Any]] = field(default_factory=list)
    exam_review_questions: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClassSummary":
        if not isinstance(data, dict):
            return cls(overview=str(data))

        return cls(
            title=str(data.get("title") or "Apuntes de Clase"),
            subject=str(data.get("subject") or "Materia"),
            professor=str(data.get("professor") or ""),
            discipline=str(data.get("discipline") or "Matemáticas"),
            overview=str(data.get("overview") or data.get("summary") or ""),
            timeline_index=list(data.get("timeline_index") or []),
            study_bullet_points=list(data.get("study_bullet_points") or data.get("bullet_points") or []),
            key_formulas=list(data.get("key_formulas") or data.get("formulas") or []),
            technical_glossary=list(data.get("technical_glossary") or data.get("glossary") or []),
            solved_exercises=list(data.get("solved_exercises") or data.get("exercises") or []),
            exam_review_questions=list(data.get("exam_review_questions") or data.get("questions") or []),
            created_at=str(data.get("created_at") or datetime.now().isoformat()),
        )

    def to_markdown(self) -> str:
        md = [f"# 🎓 {self.title or 'Apuntes de Clase'}\n"]
        md.append(f"**Materia:** {self.subject} | **Disciplina:** {self.discipline}")
        if self.professor:
            md.append(f"**Docente:** {self.professor}")
        md.append(f"**Fecha:** {self.created_at[:10]}\n")

        if self.overview:
            md.append("## 📖 Resumen General de la Clase")
            md.append(self.overview + "\n")

        if self.timeline_index:
            md.append("## ⏱️ Índice Temático Cronológico")
            for item in self.timeline_index:
                t = item.get("time", item.get("timestamp", "00:00"))
                topic = item.get("topic", item.get("title", ""))
                md.append(f"- **`[{t}]`** {topic}")
            md.append("")

        if self.study_bullet_points:
            md.append("## 📝 Puntos Clave de Estudio (con minuto de inicio)")
            for pt in self.study_bullet_points:
                t = pt.get("time", pt.get("timestamp", "00:00"))
                topic = pt.get("topic", "")
                explanation = pt.get("explanation", pt.get("details", ""))
                formula = pt.get("formula", "")
                header = f"- **`[{t}]` {topic}:** " if topic else f"- **`[{t}]`** "
                line = f"{header}{explanation}"
                if formula:
                    line += f"\n  - *Fórmula asociada:* `{formula}`"
                md.append(line)
            md.append("")

        if self.key_formulas:
            md.append("## 📐 Teoremas y Fórmulas Explicadas (LaTeX)")
            for f in self.key_formulas:
                name = f.get("name", "Fórmula")
                latex = f.get("latex", "")
                meaning = f.get("explanation", f.get("meaning", ""))
                md.append(f"### {name}")
                if latex:
                    md.append(f"$${latex}$$\n")
                if meaning:
                    md.append(f"- **Significado físico/matemático:** {meaning}")
                md.append("")

        if self.technical_glossary:
            md.append("## 📖 Glosario y Traducción de Términos Técnicos")
            for item in self.technical_glossary:
                term = item.get("term", "")
                trans = item.get("translation_or_synonym", item.get("standard_term", ""))
                definition = item.get("definition", "")
                context = item.get("context", "")
                term_str = f"**{term}**"
                if trans and trans.lower() != term.lower():
                    term_str += f" *(Trad: {trans})*"
                md.append(f"- {term_str}: {definition}")
                if context:
                    md.append(f"  - *Uso en clase:* {context}")
            md.append("")

        if self.solved_exercises:
            md.append("## 💡 Ejercicios y Demostraciones Resueltas")
            for ex in self.solved_exercises:
                t = ex.get("time", "00:00")
                name = ex.get("title", ex.get("problem", "Ejercicio"))
                steps = ex.get("steps", "")
                result = ex.get("result", "")
                md.append(f"### `[{t}]` {name}")
                if steps:
                    md.append(f"**Desarrollo:**\n{steps}")
                if result:
                    md.append(f"**Resultado:** {result}")
                md.append("")

        if self.exam_review_questions:
            md.append("## ❓ Preguntas Clave para Repaso de Examen")
            for q in self.exam_review_questions:
                md.append(f"- [ ] {q}")
            md.append("")

        return "\n".join(md)


@dataclass
class ClassSessionMetadata:
    id: str
    subject: str = "Materia"
    professor: str = ""
    discipline: str = "Matemáticas"
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: Optional[str] = None
    duration_seconds: float = 0.0
    has_audio: bool = True
    has_video: bool = False
    has_transcript: bool = False
    has_summary: bool = False
    video_fps: int = 18
    resolution: str = "1920x1080"
    devices_used: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClassSessionMetadata":
        return cls(**data)


class ClassSession:
    """Representa una clase grabada o importada almacenada en disco."""
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

    def _load_metadata(self) -> ClassSessionMetadata:
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    return ClassSessionMetadata.from_dict(json.load(f))
            except Exception:
                pass
        return ClassSessionMetadata(id=self.dir.name)

    def save_metadata(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.metadata.has_audio = self.metadata.has_audio or self.audio_file.exists()
        self.metadata.has_video = self.metadata.has_video or self.video_file.exists()
        self.metadata.has_transcript = self.transcript_json.exists()
        self.metadata.has_summary = self.summary_md.exists()
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata.to_dict(), f, indent=2, ensure_ascii=False)

    def save_transcript(self, transcript: Transcript) -> None:
        with open(self.transcript_json, "w", encoding="utf-8") as f:
            json.dump(transcript.to_dict(), f, indent=2, ensure_ascii=False)
        with open(self.transcript_txt, "w", encoding="utf-8") as f:
            f.write(transcript.full_text)
        self.metadata.has_transcript = True
        self.save_metadata()

    def load_transcript(self) -> Optional[Transcript]:
        if not self.transcript_json.exists():
            return None
        with open(self.transcript_json, "r", encoding="utf-8") as f:
            return Transcript.from_dict(json.load(f))

    def save_summary(self, summary: ClassSummary) -> None:
        with open(self.summary_json, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2, ensure_ascii=False)
        with open(self.summary_md, "w", encoding="utf-8") as f:
            f.write(summary.to_markdown())
        self.metadata.has_summary = True
        self.save_metadata()

    def load_summary(self) -> Optional[ClassSummary]:
        if self.summary_json.exists():
            with open(self.summary_json, "r", encoding="utf-8") as f:
                return ClassSummary.from_dict(json.load(f))
        return None
