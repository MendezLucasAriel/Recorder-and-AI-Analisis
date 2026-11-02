# 🎓 Academic Recorder — Asistente de Clases Universitarias

Aplicación de escritorio en Python para grabar clases universitarias (online o presenciales), capturar video nítido en **1080p a 15-21 FPS** (ideal para fórmulas matemáticas y pizarras), transcribir con reconocimiento fonético adaptado a **Física y Matemáticas**, y generar apuntes de estudio estructurados con **fórmulas en LaTeX**, glosario técnico y **marcas de tiempo interactivas que saltan al video 5 segundos antes**.

---

## 🚀 Inicio Rápido

1. Haz doble clic en `run_academic.bat` o ejecuta desde la terminal:
   ```bash
   python academic_recorder/main.py
   ```
2. En la pestaña **⚙️ Ajustes y Materias**:
   - Pega tu clave gratuita de Google Gemini (desde [aistudio.google.com](https://aistudio.google.com/app/apikey)).
   - Elige tu disciplina predeterminada (`⚛️ Física` o `📐 Matemáticas`).
   - Puedes personalizar los términos técnicos científicos en el editor de vocabulario para que Whisper no confunda palabras complejas de tu materia.
   - Guarda los cambios.
3. En la pestaña **🎙️ Grabar Clase**:
   - Escribe el nombre de la materia (ej: *Física II*, *Álgebra Lineal*, *Cálculo III*).
   - Selecciona si vas a grabar la **Ventana de la clase** (Teams, Google Meet, Zoom, visor de PDF, navegador) o **Pantalla completa**.
   - Elige el framerate: **18 FPS** (óptimo para diapositivas con texto y fórmulas).
   - Haz clic en **⏺️ Iniciar Clase**.
4. Al terminar la clase, haz clic en **⏹️ Finalizar Clase**.
5. Ve a la pestaña **📚 Mis Clases y Apuntes**:
   - Haz clic en **⚡ Procesar Completo** para transcribir el audio y generar los apuntes con Gemini.
   - En la pestaña **⏱️ Saltos en el Video (-5s)**, haz clic en cualquier tema para abrir el video exactamente **5 segundos antes** de que el profesor comience a hablar de ese punto.

---

## 🌟 Características Principales

- **Video 1080p a 15-21 FPS**: Optimizado para diapositivas de clases virtuales. Texto y subíndices de fórmulas 100% legibles con mínimo peso en disco y bajo uso de CPU/GPU.
- **Modo Ventana Inmune a Alt-Tab**: Graba únicamente la ventana de Teams, Zoom o tu visor de diapositivas mediante Windows Graphics Capture (WGC). Si abres otra ventana por encima, no se verá en la grabación.
- **Presets Especializados para STEM**:
  - **Física**: Mecánica, termodinámica, electromagnetismo, ondas, cuántica, relatividad, ecuaciones de Maxwell, hamiltoniano, lagrangiano.
  - **Matemáticas**: Cálculo multivariable, álgebra lineal, espacios vectoriales, tensores, ecuaciones diferenciales, teoremas de Green/Stokes/Gauss.
- **Traducción y Glosario Técnico**: Detecta anglicismos y tecnicismos usados por el docente y los traduce a términos estándar en español con su definición formal.
- **Fórmulas en LaTeX**: Todas las ecuaciones y deducciones matemáticas quedan formateadas en notación LaTeX estándar (\(...\) y \[...\]).
- **Reproducción Sincronizada (-5 Segundos)**: Cada punto de estudio y ejercicio resuelto incluye su minuto de inicio. Al hacer clic en `▶️ [MM:SS] (-5s)`, el video se abre con un margen de 5 segundos previos para que no te pierdas la introducción del profesor.
- **Importador Multimedia**: ¿Tienes una clase grabada en Teams, Zoom o Drive? Puedes importarla directamente con el botón **📥 Importar Video / Audio Externo**.
