"""
Prompts especializados para transcripción y resúmenes de clases universitarias
de Física y Matemáticas, con soporte de fórmulas en LaTeX, glosario técnico bilingüe
y marcas de tiempo cronológicas precisas para cada concepto.
"""

# Vocabularios de sesgo inicial para Whisper (initial_prompt)
WHISPER_INITIAL_PROMPTS = {
    "Física": (
        "Clase universitaria de física teórica y aplicada en español. "
        "Terminología: cinemática, dinámica, leyes de Newton, trabajo y energía, conservación del momento lineal y angular, "
        "gravitación universal, cuerpo rígido, momento de inercia, oscilaciones armónicas, termodinámica, primer y segundo principio, "
        "entropía, ciclos termodinámicos, electromagnetismo, ley de Coulomb, campo eléctrico, potencial electrostático, "
        "ley de Gauss, ley de Biot-Savart, ley de Ampère, ley de Faraday-Lenz, ecuaciones de Maxwell en forma diferencial e integral, "
        "divergencia, rotacional, gradiente, laplaciano, vector de Poynting, ondas electromagnéticas, óptica ondulatoria, "
        "relatividad especial, transformaciones de Lorentz, dilatación temporal, cuadrivectores, tensor métrico, "
        "mecánica cuántica, ecuación de Schrödinger, hamiltoniano, lagrangiano, principio de indeterminación de Heisenberg, "
        "función de onda, producto interno de Dirac bra-ket, operadores hermíticos, autovalores, conmutador, espín, bosones y fermiones."
    ),
    "Matemáticas": (
        "Clase universitaria de matemáticas en español. "
        "Terminología: cálculo diferencial e integral en una y varias variables, límites, derivadas parciales, "
        "matriz jacobiana, matriz hessiana, extremos relativos y multiplicadores de Lagrange, integrales dobles y triples, "
        "cambio de variables con determinante jacobiano, integrales de línea y superficie, campo vectorial conservativo, "
        "función potencial, teorema de Green, teorema de Stokes, teorema de Gauss de la divergencia, ecuaciones diferenciales "
        "ordinarias de primer y segundo orden, transformada de Laplace, series de Fourier, convolución, "
        "álgebra lineal, espacios y subespacios vectoriales, independencia lineal, bases, dimensión, transformación lineal, "
        "núcleo e imagen, matriz de cambio de base, determinante, traza, valores propios, autovalores, vectores propios, autovectores, "
        "polinomio característico, diagonalización, descomposición en valores singulares SVD, producto interno euclidiano, "
        "Gram-Schmidt, álgebra abstracta, grupos, anillos, cuerpos, topología y espacios métricos."
    ),
    "General": (
        "Clase universitaria de ciencias exactas e ingeniería en español. "
        "Cálculo, física, álgebra lineal, métodos numéricos, ecuaciones diferenciales, matrices, vectores, derivadas, integrales, "
        "teoremas, demostraciones, leyes físicas, unidades del Sistema Internacional, constantes fundamentales."
    ),
}

STEM_SYSTEM_INSTRUCTION = """
Eres un profesor titular universitario y asistente pedagógico de élite especializado en ciencias exactas (Física y Matemáticas).
Tu tarea es analizar la transcripción de una clase universitaria (con marcas de tiempo [MM:SS]) y crear un resumen de estudio exhaustivo, riguroso y perfectamente estructurado para los alumnos.

Pautas fundamentales de calidad académica:
1. MARCAS DE TIEMPO EXACTAS [MM:SS]:
   - En cada punto clave de estudio (study_bullet_points), en el índice temático y en los ejercicios resueltos, DEBES indicar el minuto y segundo exacto ([MM:SS]) en el cual el docente comenzó a abordar ese concepto o problema según la transcripción.
   - Si un tema se explica entre [12:35] y [18:40], el punto de estudio debe indicar time: "12:35".

2. RIGOR MATEMÁTICO Y FORMULACIÓN EN LATEX:
   - Toda expresión, igualdad, ley física o teorema debe redactarse en notación LaTeX estándar.
   - En las fórmulas destacadas (key_formulas), usa formato LaTeX limpio (ej: "\\nabla \\times \\vec{E} = -\\frac{\\partial \\vec{B}}{\\partial t}", "\\int_a^b f(x) dx = F(b) - F(a)").
   - Explica con claridad el significado físico o matemático de cada variable y las condiciones de validez del teorema.

3. TRADUCCIÓN Y GLOSARIO DE TÉRMINOS TÉCNICOS:
   - Detecta tecnicismos, jerga científica o anglicismos utilizados por el docente (ej: "eigenvalues", "curl", "steady state", "cross product", "boundary conditions", "hamiltonian", "null space", "mesh", "gradient descent", etc.).
   - Tradúcelos a su término formal estandarizado en español de la bibliografía académica universitaria ("autovalores/valores propios", "rotacional", "régimen estacionario", "producto vectorial", "condiciones de contorno/frontera", "hamiltoniano", "núcleo", etc.).
   - Explica su definición concisa y el contexto en que se aplicó durante la clase.

4. RESOLUCIÓN PASO A PASO DE EJERCICIOS Y DEMOSTRACIONES:
   - Si el profesor resolvió un ejercicio o demostró un teorema en la pizarra, extrae el planteamiento, los pasos matemáticos principales en LaTeX y el resultado final.

5. TONO Y FORMATO:
   - Redacta en español formal y pedagógico.
   - Devuelve estrictamente la respuesta en formato JSON válido con la estructura solicitada.
"""

STEM_USER_PROMPT_TEMPLATE = """
A continuación tienes la transcripción de la clase universitaria con marcas de tiempo cronológicas:

Materia: {subject}
Docente: {professor}
Disciplina: {discipline}

--- TRANSCRIPCIÓN DE LA CLASE CON TIEMPOS ---
{transcript_with_timestamps}
--- FIN DE LA TRANSCRIPCIÓN ---

Genera los apuntes completos de estudio en formato JSON con la siguiente estructura:
{{
  "title": "Título descriptivo del tema central de la clase",
  "subject": "{subject}",
  "professor": "{professor}",
  "discipline": "{discipline}",
  "overview": "Resumen ejecutivo pedagógico de 2 a 3 párrafos que sintetice los conceptos fundamentales explicados y los objetivos de la clase.",
  "timeline_index": [
    {{
      "time": "MM:SS",
      "topic": "Nombre del bloque temático o sección de la clase"
    }}
  ],
  "study_bullet_points": [
    {{
      "time": "MM:SS",
      "topic": "Concepto o subtítulo clave",
      "explanation": "Explicación conceptual completa, detallada y comprensible para estudiar para el examen.",
      "formula": "Fórmula matemática principal asociada en LaTeX (opcional si aplica)"
    }}
  ],
  "key_formulas": [
    {{
      "name": "Nombre de la Ley, Teorema o Ecuación",
      "latex": "Expresión en LaTeX limpio",
      "explanation": "Significado de las variables, unidades y condiciones de aplicación"
    }}
  ],
  "technical_glossary": [
    {{
      "term": "Término técnico o en inglés mencionado",
      "translation_or_synonym": "Traducción formal o término estándar en español",
      "definition": "Definición rigurosa del concepto",
      "context": "Cómo lo utilizó el profesor en esta clase"
    }}
  ],
  "solved_exercises": [
    {{
      "time": "MM:SS",
      "title": "Título del ejercicio o demostración",
      "problem": "Enunciado o problema planteado",
      "steps": "Desarrollo paso a paso en LaTeX y texto",
      "result": "Resultado o conclusión final"
    }}
  ],
  "exam_review_questions": [
    "Pregunta de examen 1 sobre un concepto clave visto en clase",
    "Pregunta de examen 2 para autoevaluación"
  ]
}}
"""
