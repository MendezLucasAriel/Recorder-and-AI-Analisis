import json
import os
import re
import time
from typing import Optional, Callable
from google import genai
from google.genai import types

from work_recorder.models.meeting_session import MeetingSummary, Transcript
from .work_config import WorkConfig
from .work_prompts import WORK_SYSTEM_INSTRUCTION, WORK_USER_PROMPT_TEMPLATE


class WorkSummarizer:
    """
    Genera minutas ejecutivas, tareas y síntesis de reuniones con Gemini 3.8 Flash.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs,
    ):
        cfg = WorkConfig.load()
        self.api_key = api_key or cfg.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        chosen_model = model_name or model or cfg.gemini_model or "gemini-3.8-flash"
        self.model = chosen_model
        self.model_name = chosen_model

    def summarize(
        self,
        transcript: Transcript,
        meeting_name: str = "Reunión de Trabajo",
        meeting_type: str = "General",
        participants: str = "",
        on_status: Optional[Callable[[str], None]] = None,
    ) -> MeetingSummary:
        if not self.api_key:
            raise ValueError(
                "No se encontró la Gemini API Key. Configúrala en la pestaña de Ajustes o en el archivo .env."
            )

        if on_status:
            on_status(f"Conectando con Gemini ({self.model}) para redactar la minuta...")

        client = genai.Client(api_key=self.api_key)

        formatted_transcript = transcript.format_with_timestamps(interval_seconds=20.0)
        if not formatted_transcript.strip():
            formatted_transcript = transcript.full_text

        prompt = WORK_USER_PROMPT_TEMPLATE.format(
            meeting_name=meeting_name,
            meeting_type=meeting_type,
            participants=participants or "Participantes de la reunión",
            transcript_with_timestamps=formatted_transcript,
        )

        if on_status:
            on_status("Analizando temas tratados, acuerdos y tareas pendientes (Action Items)...")

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
                            system_instruction=WORK_SYSTEM_INSTRUCTION,
                            response_mime_type="application/json",
                            temperature=0.3,
                        ),
                    )
                    raw_text = response.text or "{}"
                    cleaned = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.MULTILINE)
                    cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)

                    data = json.loads(cleaned)
                    summary = MeetingSummary.from_dict(data)
                    summary.meeting_type = meeting_type

                    if on_status:
                        on_status(f"¡Minuta ejecutiva generada con éxito usando {model_name}!")
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

        raise RuntimeError(f"Error generando minuta con Gemini: {last_error}")
