import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from .stem_prompts import WHISPER_INITIAL_PROMPTS


@dataclass
class AcademicConfig:
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    ai_provider: str = "gemini"  # "gemini" o "local" (LM Studio / Ollama)
    local_api_base: str = "http://localhost:1234/v1"
    local_model_name: str = "google/gemma-4-12b-qat"
    discipline: str = "Física"  # "Física", "Matemáticas", "General"
    whisper_model: str = "medium"
    whisper_backend: str = "gpu"  # "gpu" (Vulkan) o "cpu" (INT8)
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"
    language: str = "es"
    video_fps: int = 18
    video_resolution: str = "1920x1080"
    video_lead_time_sec: float = 5.0
    custom_initial_prompt: str = ""

    @classmethod
    def get_config_file(cls) -> Path:
        base_dir = Path(__file__).resolve().parent.parent
        return base_dir / "academic_settings.json"

    @classmethod
    def load(cls) -> "AcademicConfig":
        config_file = cls.get_config_file()

        # Cargar API key de .env si existe en el proyecto
        env_key = os.environ.get("GEMINI_API_KEY", "")
        if not env_key:
            root_env = Path(__file__).resolve().parent.parent.parent / ".env"
            if root_env.exists():
                try:
                    with open(root_env, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip().startswith("GEMINI_API_KEY="):
                                env_key = line.strip().split("=", 1)[1].strip()
                                break
                except Exception:
                    pass

        cfg = cls(gemini_api_key=env_key)

        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if hasattr(cfg, k):
                            setattr(cfg, k, v)
                    if not cfg.gemini_api_key and env_key:
                        cfg.gemini_api_key = env_key
            except Exception:
                pass

        return cfg

    def save(self) -> None:
        config_file = self.get_config_file()
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

    def get_effective_initial_prompt(self) -> str:
        if self.custom_initial_prompt and self.custom_initial_prompt.strip():
            return self.custom_initial_prompt.strip()
        return WHISPER_INITIAL_PROMPTS.get(self.discipline, WHISPER_INITIAL_PROMPTS["General"])
