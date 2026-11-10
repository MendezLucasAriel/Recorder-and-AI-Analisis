import json
import os
import re
import time
from typing import Optional, Callable
from google import genai
from google.genai import types

from models.session import SessionSummary, Transcript
from .config import AIConfig
from .prompts import DND_SYSTEM_INSTRUCTION, DND_USER_PROMPT_TEMPLATE


class Summarizer:
    """
    Genera resúmenes estructurados de D&D a partir de transcripciones
    utilizando la API gratuita de Gemini con reintentos y tolerancia a alta demanda (503).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs,
    ):
        cfg = AIConfig.load()
        self.api_key = api_key or cfg.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        chosen_model = model_name or model or cfg.gemini_model or "gemini-3.8-flash"
        self.model = chosen_model
        self.model_name = chosen_model

    def summarize(
        self,
        transcript: Transcript,
        campaign_name: str = "Campaña D&D",
        previous_summary: Optional[str] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> SessionSummary:
        if not self.api_key:
            raise ValueError(
                "No se encontró la Gemini API Key. Configúrala en la pestaña de Ajustes o en el archivo .env."
            )

        if on_status:
            on_status(f"Conectando con Gemini API ({self.model})...")

        client = genai.Client(api_key=self.api_key)

        prev_context = ""
        if previous_summary:
            prev_context = f"Contexto de la sesión anterior:\n{previous_summary}\n"

        prompt = DND_USER_PROMPT_TEMPLATE.format(
            campaign_name=campaign_name,
            previous_context=prev_context,
            transcript_text=transcript.full_text,
        )

        if on_status:
            on_status("Gemini está analizando la sesión y redactando la crónica...")

        # Lista de modelos con fallback automático
        models_to_try = [self.model, "gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.8-flash-lite", "gemini-3.7-flash"]
        seen = set()
        unique_models = []
        for m in models_to_try:
            if m not in seen:
                seen.add(m)
                unique_models.append(m)

        last_error = None

        for model_name in unique_models:
            for attempt in range(2):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=DND_SYSTEM_INSTRUCTION,
                            response_mime_type="application/json",
                            temperature=0.7,
                        ),
                    )
                    raw_text = response.text or "{}"
                    cleaned = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.MULTILINE)
                    cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)

                    data = json.loads(cleaned)
                    summary = SessionSummary.from_dict(data)

                    if on_status:
                        on_status(f"¡Resumen generado con éxito usando {model_name}!")
                    return summary

                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    if "503" in err_str or "UNAVAILABLE" in err_str:
                        if on_status:
                            on_status(f"Servidores de Google con alta demanda (503). Reintentando en 3s...")
                        time.sleep(3)
                        continue
                    else:
                        if on_status:
                            on_status(f"Reintentando con modelo alternativo ({model_name} falló)...")
                        break

        raise RuntimeError(f"Error generando resumen con Gemini: {last_error}")
