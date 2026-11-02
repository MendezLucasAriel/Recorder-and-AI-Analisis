import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()


@dataclass
class AIConfig:
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    whisper_backend: str = "cpu"       # "cpu" o "gpu" (AMD RX 470)
    whisper_model: str = "small"
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"
    language: str = "en"
    campaign_name: str = "Mi Campaña D&D"

    @classmethod
    def load(cls) -> "AIConfig":
        return cls(
            gemini_api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
            gemini_model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash").strip(),
            whisper_backend=os.environ.get("WHISPER_BACKEND", "cpu").strip().lower(),
            whisper_model=os.environ.get("WHISPER_MODEL", "small").strip(),
            whisper_device=os.environ.get("WHISPER_DEVICE", "auto").strip(),
            whisper_compute_type=os.environ.get("WHISPER_COMPUTE_TYPE", "auto").strip(),
            language=os.environ.get("TRANSCRIPTION_LANGUAGE", "en").strip(),
            campaign_name=os.environ.get("DEFAULT_CAMPAIGN_NAME", "Mi Campaña D&D").strip(),
        )

    def save_to_env(self, env_path: Path = _env_path) -> None:
        lines = [
            f"GEMINI_API_KEY={self.gemini_api_key}",
            f"GEMINI_MODEL={self.gemini_model}",
            f"WHISPER_BACKEND={self.whisper_backend}",
            f"WHISPER_MODEL={self.whisper_model}",
            f"WHISPER_DEVICE={self.whisper_device}",
            f"WHISPER_COMPUTE_TYPE={self.whisper_compute_type}",
            f"TRANSCRIPTION_LANGUAGE={self.language}",
            f"DEFAULT_CAMPAIGN_NAME={self.campaign_name}",
        ]
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        os.environ["GEMINI_API_KEY"] = self.gemini_api_key
        os.environ["GEMINI_MODEL"] = self.gemini_model
        os.environ["WHISPER_BACKEND"] = self.whisper_backend
        os.environ["WHISPER_MODEL"] = self.whisper_model
        os.environ["WHISPER_DEVICE"] = self.whisper_device
        os.environ["WHISPER_COMPUTE_TYPE"] = self.whisper_compute_type
        os.environ["TRANSCRIPTION_LANGUAGE"] = self.language
        os.environ["DEFAULT_CAMPAIGN_NAME"] = self.campaign_name
