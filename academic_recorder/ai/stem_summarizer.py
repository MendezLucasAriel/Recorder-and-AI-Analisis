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
        ai_provider: Optional[str] = None,
        local_api_base: Optional[str] = None,
        local_model_name: Optional[str] = None,
        **kwargs,
    ):
        cfg = AcademicConfig.load()
        self.ai_provider = ai_provider or cfg.ai_provider or "gemini"
        self.local_api_base = local_api_base or cfg.local_api_base or "http://localhost:1234/v1"
        self.local_model_name = local_model_name or cfg.local_model_name or "google/gemma-4-12b-qat"
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
        formatted_transcript = transcript.format_with_timestamps(interval_seconds=15.0)
        if not formatted_transcript.strip():
            formatted_transcript = transcript.full_text

        prompt = STEM_USER_PROMPT_TEMPLATE.format(
            subject=subject,
            professor=professor or "Titular de Cátedra",
            discipline=discipline,
            transcript_with_timestamps=formatted_transcript,
        )

        if self.ai_provider == "local":
            return self._summarize_local(
                prompt=prompt,
                subject=subject,
                professor=professor,
                discipline=discipline,
                on_status=on_status,
            )

        if not self.api_key:
            raise ValueError(
                "No se encontró la Gemini API Key. Configúrala en Ajustes o en el archivo .env."
            )

        if on_status:
            on_status(f"Conectando con Gemini ({self.model}) para estructurar apuntes...")

        client = genai.Client(api_key=self.api_key)

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

    def _summarize_local(
        self,
        prompt: str,
        subject: str,
        professor: str,
        discipline: str,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> ClassSummary:
        import requests

        endpoint = f"{self.local_api_base.rstrip('/')}/chat/completions"
        if on_status:
            on_status(f"Conectando con LM Studio ({self.local_model_name}) en {self.local_api_base}...")

        messages = [
            {"role": "system", "content": STEM_SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": self.local_model_name,
            "messages": messages,
            "temperature": 0.3,
        }

        if on_status:
            on_status(f"Generando apuntes de clase en local con {self.local_model_name}...")

        resp = None
        try:
            payload_json = dict(payload)
            payload_json["response_format"] = {"type": "json_object"}
            resp = requests.post(endpoint, json=payload_json, timeout=600)
            if resp.status_code != 200:
                resp = requests.post(endpoint, json=payload, timeout=600)
        except Exception:
            try:
                resp = requests.post(endpoint, json=payload, timeout=600)
            except Exception as e_inner:
                raise ConnectionError(
                    f"No se pudo conectar al servidor de LM Studio en {endpoint}.\n"
                    f"Verifica que LM Studio esté abierto con el Local Server activado (puerto 1234).\n"
                    f"Detalle: {e_inner}"
                )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Error en respuesta de LM Studio (HTTP {resp.status_code}): {resp.text}\n"
                f"Verifica que el modelo '{self.local_model_name}' esté cargado en LM Studio."
            )

        res_data = resp.json()
        raw_text = res_data.get("choices", [{}])[0].get("message", {}).get("content", "") or "{}"

        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)

        data = None
        brace_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if brace_match:
            try:
                data = json.loads(brace_match.group(1))
            except Exception:
                pass

        if not data:
            data = json.loads(cleaned)

        summary = ClassSummary.from_dict(data)
        summary.subject = subject
        summary.professor = professor
        summary.discipline = discipline

        if on_status:
            on_status(f"🎉 ¡Apuntes generados con éxito en local usando {self.local_model_name}!")
        return summary
