import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class TranscriptSegment:
    start: float  # seconds
    end: float    # seconds
    text: str
    speaker: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptSegment":
        return cls(**data)


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
class SessionSummary:
    title: str = ""
    overview: str = ""
    party_members: List[Dict[str, str]] = field(default_factory=list)
    key_events: List[str] = field(default_factory=list)
    combat_encounters: List[Dict[str, Any]] = field(default_factory=list)
    npc_interactions: List[Dict[str, str]] = field(default_factory=list)
    locations_visited: List[str] = field(default_factory=list)
    loot_and_rewards: List[str] = field(default_factory=list)
    quest_hooks: List[str] = field(default_factory=list)
    memorable_moments: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionSummary":
        if not isinstance(data, dict):
            return cls(overview=str(data))

        overview = data.get("overview") or data.get("narrative_summary") or data.get("summary") or ""
        title = data.get("title") or data.get("session_title") or "Crónica de Sesión D&D"
        party_members = data.get("party_members") or data.get("characters") or data.get("players") or []
        key_events = data.get("key_events") or data.get("events") or []
        combat_encounters = data.get("combat_encounters") or data.get("combats") or []
        npc_interactions = data.get("npc_interactions") or data.get("npcs") or []
        locations_visited = data.get("locations_visited") or data.get("locations") or []
        loot_and_rewards = data.get("loot_and_rewards") or data.get("loot") or []
        quest_hooks = data.get("quest_hooks") or data.get("hooks") or []
        memorable_moments = data.get("memorable_moments") or data.get("quotes") or []
        created_at = data.get("created_at") or datetime.now().isoformat()

        return cls(
            title=str(title),
            overview=str(overview),
            party_members=list(party_members) if isinstance(party_members, list) else [],
            key_events=list(key_events) if isinstance(key_events, list) else [str(key_events)],
            combat_encounters=list(combat_encounters) if isinstance(combat_encounters, list) else [],
            npc_interactions=list(npc_interactions) if isinstance(npc_interactions, list) else [],
            locations_visited=list(locations_visited) if isinstance(locations_visited, list) else [],
            loot_and_rewards=list(loot_and_rewards) if isinstance(loot_and_rewards, list) else [],
            quest_hooks=list(quest_hooks) if isinstance(quest_hooks, list) else [],
            memorable_moments=list(memorable_moments) if isinstance(memorable_moments, list) else [],
            created_at=str(created_at),
        )

    def to_markdown(self) -> str:
        md = [f"# 🎲 {self.title or 'Resumen de Sesión D&D'}\n"]
        md.append(f"**Fecha de generación:** {self.created_at[:10]}\n")

        if self.party_members:
            md.append("## 🧙‍♂️ Personajes y Participantes (Deducción por Contexto)")
            for member in self.party_members:
                name = member.get("name", "Personaje")
                char_class = member.get("class_or_role", member.get("role", ""))
                summary = member.get("actions_summary", member.get("summary", ""))
                role_str = f" *({char_class})*" if char_class else ""
                md.append(f"- **{name}**{role_str}: {summary}")
            md.append("")

        if self.overview:
            md.append("## 📖 Resumen General")
            md.append(self.overview + "\n")

        if self.key_events:
            md.append("## ⚔️ Acontecimientos Clave")
            for event in self.key_events:
                md.append(f"- {event}")
            md.append("")

        if self.combat_encounters:
            md.append("## 🛡️ Combates y Encuentros")
            for enc in self.combat_encounters:
                name = enc.get("name", "Encuentro")
                enemies = enc.get("enemies", "Desconocido")
                outcome = enc.get("outcome", "Victoria")
                details = enc.get("details", "")
                md.append(f"### {name}")
                md.append(f"- **Enemigos:** {enemies}")
                md.append(f"- **Resultado:** {outcome}")
                if details:
                    md.append(f"- **Detalles:** {details}")
                md.append("")

        if self.npc_interactions:
            md.append("## 🗣️ Interacciones y NPCs")
            for npc in self.npc_interactions:
                name = npc.get("npc", "NPC")
                notes = npc.get("summary", "")
                md.append(f"- **{name}:** {notes}")
            md.append("")

        if self.locations_visited:
            md.append("## 📍 Lugares Visitados")
            for loc in self.locations_visited:
                md.append(f"- {loc}")
            md.append("")

        if self.loot_and_rewards:
            md.append("## 🎒 Botín y Recompensas")
            for item in self.loot_and_rewards:
                md.append(f"- {item}")
            md.append("")

        if self.quest_hooks:
            md.append("## 📌 Misiones y Asuntos Pendientes")
            for q in self.quest_hooks:
                md.append(f"- [ ] {q}")
            md.append("")

        if self.memorable_moments:
            md.append("## ✨ Momentos Memorables y Roleplay")
            for m in self.memorable_moments:
                md.append(f"- {m}")
            md.append("")

        return "\n".join(md)


@dataclass
class SessionMetadata:
    id: str
    campaign: str = "Campaña Principal"
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: Optional[str] = None
    duration_seconds: float = 0.0
    has_audio: bool = True
    has_screen: bool = False
    has_transcript: bool = False
    has_summary: bool = False
    devices_used: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMetadata":
        return cls(**data)


class Session:
    """Representa una sesión completa guardada en disco."""
    def __init__(self, session_dir: Path):
        self.dir = Path(session_dir)
        self.metadata_file = self.dir / "session.json"
        self.audio_file = self.dir / "audio.wav"
        self.screen_file = self.dir / "screen.mp4"
        self.transcript_json = self.dir / "transcript.json"
        self.transcript_txt = self.dir / "transcript.txt"
        self.summary_md = self.dir / "summary.md"
        self.summary_json = self.dir / "summary.json"

        self.metadata = self._load_metadata()

    def _load_metadata(self) -> SessionMetadata:
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    return SessionMetadata.from_dict(json.load(f))
            except Exception:
                pass
        return SessionMetadata(id=self.dir.name)

    def save_metadata(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.metadata.has_audio = self.metadata.has_audio or self.audio_file.exists()
        self.metadata.has_screen = self.metadata.has_screen or self.screen_file.exists()
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

    def save_summary(self, summary: SessionSummary) -> None:
        with open(self.summary_json, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2, ensure_ascii=False)
        with open(self.summary_md, "w", encoding="utf-8") as f:
            f.write(summary.to_markdown())
        self.metadata.has_summary = True
        self.save_metadata()

    def load_summary(self) -> Optional[SessionSummary]:
        if self.summary_json.exists():
            with open(self.summary_json, "r", encoding="utf-8") as f:
                return SessionSummary.from_dict(json.load(f))
        return None
