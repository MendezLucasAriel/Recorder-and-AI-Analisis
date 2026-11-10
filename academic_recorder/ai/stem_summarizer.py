import json
import os
import re
import time
from typing import Optional, Callable
from google import genai
from google.genai import types

from academic_recorder.models.class_session import ClassSummary, Transcript
from .stem_config import AcademicConfig
from .stem_prompts import STEM_SYSTEM_INSTRUCTION, STEM_USER_PROMPT_TEMPLATE


class StemSummarizer:
    """
    Genera resúmenes estructurados y apuntes de estudio para clases universitarias
    utilizando Google Gemini, con fórmulas en LaTeX, glosario técnico y marcas de tiempo [MM:SS].
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs,
    ):
        cfg = AcademicConfig.load()
        self.api_key = api_key or cfg.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        chosen_model = model_name or model or cfg.gemini_model or "gemini-3.8-flash"
        self.model = chosen_model
        self.model_name = chosen_model

    def summarize(
        self,
        transcript: Transcript,
        subject: str = "Física I",
        professor: str = "",
        discipline: str = "Física",
        on_status: Optional[Callable[[str], None]] = None,
    ) -> ClassSummary:
        if not self.api_key:
            raise ValueError(
                "No se encontró la Gemini API Key. Configúrala en Ajustes o en el archivo .env."
            )

        if on_status:
            on_status(f"Conectando con Gemini ({self.model}) para estructurar apuntes...")

        client = genai.Client(api_key=self.api_key)

        # Formatear la transcripción con marcas de tiempo en bloques de ~15 segundos
        formatted_transcript = transcript.format_with_timestamps(interval_seconds=15.0)
        if not formatted_transcript.strip():
            formatted_transcript = transcript.full_text

        prompt = STEM_USER_PROMPT_TEMPLATE.format(
            subject=subject,
            professor=professor or "Titular de Cátedra",
            discipline=discipline,
            transcript_with_timestamps=formatted_transcript,
        )

        if on_status:
            on_status("Analizando contenido científico, deduciendo fórmulas en LaTeX y glosario...")

        # Lista de modelos con fallback (usando gemini-3.8-flash como principal)
        models_to_try = [self.model, "gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.8-flash-lite"]
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
                            system_instruction=STEM_SYSTEM_INSTRUCTION,
                            response_mime_type="application/json",
                            temperature=0.3,  # Baja temperatura para máxima precisión técnica y fidelidad a las marcas de tiempo
                        ),
                    )
                    raw_text = response.text or "{}"
                    cleaned = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.MULTILINE)
                    cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)

                    data = json.loads(cleaned)
                    summary = ClassSummary.from_dict(data)
                    summary.subject = subject
                    summary.professor = professor
                    summary.discipline = discipline

                    if on_status:
                        on_status(f"¡Apuntes generados con éxito usando {model_name}!")
                    return summary

                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    if "503" in err_str or "UNAVAILABLE" in err_str:
                        if on_status:
                            on_status("Servidores con alta demanda (503). Reintentando en 3s...")
                        time.sleep(3)
                        continue
                    else:
                        if on_status:
                            on_status(f"Reintentando con modelo alternativo ({model_name} falló)...")
                        break

        raise RuntimeError(f"Error generando resumen académico con Gemini: {last_error}")
