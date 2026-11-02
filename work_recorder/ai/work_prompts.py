"""
Prompts especializados para minutas y resúmenes ejecutivos de reuniones de trabajo,
llamadas con clientes, syncs de equipo y planificación de proyectos.
"""

WHISPER_WORK_INITIAL_PROMPT = (
    "Reunión de trabajo corporativa, videollamada de equipo, sync, daily, sprint planning, "
    "gestión de proyectos, desarrollo, producto, clientes, entregables, objetivos, métricas, "
    "plazos, requerimientos, tareas, acuerdos, decisiones, presupuesto, roadmap, backlog, "
    "responsables, fechas límite, feedback, producción, despliegue, arquitectura."
)

WORK_SYSTEM_INSTRUCTION = """
Eres un asistente ejecutivo y secretario de actas corporativas de alto nivel.
Tu tarea es analizar la transcripción de una reunión de trabajo o llamada profesional (con marcas de tiempo [MM:SS]) y generar una minuta ejecutiva clara, accionable y estructurada.

Pautas fundamentales:
1. SÍNTESIS EJECUTIVA PRECISA:
   - Extrae el objetivo central de la reunión y los temas de negocio/técnicos tratados sin divagaciones.
   - Separa las conversaciones informales o de cortesía del contenido sustancial de trabajo.

2. MARCAS DE TIEMPO CRONOLÓGICAS [MM:SS]:
   - En la sección de agenda_topics y en los key_points, indica el minuto exacto ([MM:SS]) donde comenzó a tratarse cada tema o acuerdo.

3. ACCIONES Y TAREAS (ACTION ITEMS):
   - Identifica con total claridad los compromisos adquiridos: QUÉ hay que hacer, QUIÉN es el responsable (si se mencionó) y CUÁL es la fecha límite o contexto (deadline).

4. DECISIONES CLAVE:
   - Destaca explícitamente los acuerdos aprobados, cambios de rumbo o definiciones acordadas por el equipo.

5. TONO Y FORMATO:
   - Tono formal, claro y profesional en español.
   - Devuelve estrictamente la respuesta en formato JSON válido según la estructura requerida.
"""

WORK_USER_PROMPT_TEMPLATE = """
A continuación tienes la transcripción de la reunión de trabajo:

Reunión: {meeting_name}
Tipo: {meeting_type}
Participantes / Equipo: {participants}

--- TRANSCRIPCIÓN CON MARCAS DE TIEMPO ---
{transcript_with_timestamps}
--- FIN DE LA TRANSCRIPCIÓN ---

Genera la minuta ejecutiva en formato JSON con la siguiente estructura exacta:
{{
  "title": "Título descriptivo y profesional de la reunión",
  "meeting_type": "{meeting_type}",
  "participants": [
    "Nombre de persona o rol identificado"
  ],
  "overview": "Resumen ejecutivo de 1 a 3 párrafos explicando el propósito de la reunión, contexto general y conclusiones principales.",
  "agenda_topics": [
    {{
      "time": "MM:SS",
      "topic": "Título del tema abordado",
      "summary": "Resumen conciso de lo discutido en este bloque"
    }}
  ],
  "decisions": [
    "Decisión o acuerdo clave 1",
    "Decisión o acuerdo clave 2"
  ],
  "action_items": [
    {{
      "task": "Descripción clara de la tarea a realizar",
      "assignee": "Persona responsable o área (ej: Juan, Front-End, Por definir)",
      "deadline": "Plazo o fecha estimada (ej: Próximo viernes, Esta semana, Sin fecha)"
    }}
  ],
  "key_points": [
    {{
      "time": "MM:SS",
      "topic": "Aspecto destacado o discusión relevante",
      "details": "Detalles esenciales para el seguimiento"
    }}
  ],
  "pending_questions": [
    "Tema abierto, duda o asunto pendiente para la próxima reunión"
  ]
}}
"""
