# 💼 Work Recorder — Asistente Inteligente de Reuniones y Minutas

**Work Recorder** es una aplicación de escritorio diseñada para profesionales, programadores y equipos de trabajo. Graba reuniones de plataformas como Microsoft Teams, Google Meet, Zoom o Slack, capturando tanto el audio de la llamada como tu micrófono, con opción de grabar la pantalla o ventana de la presentación. 

Posteriormente, transcribe el audio de forma local con Whisper y utiliza **Gemini 3.8 Flash** para extraer una minuta ejecutiva profesional con:
- **Resumen Ejecutivo** de la reunión.
- **Acuerdos y Decisiones Clave**.
- **Tareas y Compromisos (Action Items)** con responsable, fecha límite y prioridad.
- **Agenda y Saltos Cronológicos en Video/Audio**: saltos interactivos directos a los momentos clave con un clic (con anticipación automática de 3 segundos).
- **Transcripción Completa** con marcas de tiempo.

---

## 🚀 Inicio Rápido

Para iniciar la aplicación, ejecuta el lanzador directo desde la raíz del proyecto:
```bat
run_work.bat
```
O dentro de la carpeta `work_recorder`:
```bat
run_work.bat
```

---

## ✨ Características Principales

### 1. Grabación Dual de Audio y Captura de Pantalla
- **Audio Dual:** Graba simultáneamente lo que escuchas por auriculares o altavoces (la llamada de Teams/Meet/Zoom) y tu propio micrófono en pistas sincronizadas.
- **Video Opcional:** Graba la ventana de la llamada o el escritorio completo a 15–30 FPS para documentar presentaciones de diapositivas, demostraciones de código o diagramas.

### 2. Modos de Procesamiento Flexibles
- **⚡ Procesar Completo:** Transcribe el audio con Whisper (Vulkan GPU o CPU INT8) y genera inmediatamente la minuta con Gemini 3.8 Flash.
- **📝 Solo Transcribir (100% Offline y Gratis):** Si no deseas usar la API de Gemini o tu empresa requiere total confidencialidad interna, puedes generar únicamente la transcripción completa de forma local en tu equipo sin salir a internet.
- **🤖 Generar Minuta:** Si ya cuentas con la transcripción, genera o regenera la minuta ejecutiva y tareas sin volver a transcribir.

### 3. Minuta Estructurada para Negocios
La minuta generada se presenta en varias pestañas intuitivas:
- **📋 Minuta Ejecutiva:** Formato Markdown listo para copiar y pegar en Slack, Teams, Notion, Jira o correo electrónico.
- **✅ Tareas y Compromisos:** Tarjetas visuales de cada tarea pendiente con etiqueta de prioridad (Alta 🔴, Media 🟡, Baja 🟢), persona asignada y fecha estimada de entrega.
- **⏱️ Agenda y Saltos (-3s):** Botones cronológicos `▶️ [MM:SS]` que abren tu reproductor multimedia (VLC, ffplay o el predeterminado) exactamente 3 segundos antes del momento en que se debatió ese punto.
- **📝 Transcripción Completa:** El registro textual palabra por palabra con marcas temporales.

### 4. Soporte de Jerga y Acrónimos Corporativos
Whisper incluye un sesgo fonético configurado con términos habituales del mundo del trabajo, tecnología y gestión:
- *Jira, Confluence, Pull Request, PR, Sprint, Backlog, Deploy, Release, Staging, QA, Refactor, Microservicios, Docker, Kubernetes, AWS, GCP, Frontend, Backend, API, Endpoints, KPI, OKR, ROI, Roadmap, Stakeholders, Daily, Retro, Standup, SLA...*
Puedes personalizar o agregar tus propios acrónimos de empresa desde la pestaña **⚙️ Ajustes y Modelos**.

### 5. Importación de Grabaciones Externas
¿Tu reunión ya fue grabada por Teams, Meet, Zoom o guardada en un archivo de audio/video (`.mp4`, `.mkv`, `.wav`, `.m4a`, etc.)?
Haz clic en **📥 Importar Video / Audio Externo** para cargarla, transcribirla y extraer la minuta en minutos.

---

## ⚙️ Configuración y Requisitos

En la pestaña **⚙️ Ajustes y Modelos**:
- **Clave API de Gemini:** Puedes utilizar cualquier clave de [Google AI Studio](https://aistudio.google.com/app/apikey).
- **Modelo Gemini:** Configurado por defecto en `gemini-3.8-flash`.
- **Motor Whisper:** Alterna entre GPU (`gpu` con aceleración Vulkan en AMD Radeon RX 470) o CPU (`cpu` INT8 multinúcleo).
- **Modelo Whisper:** `medium` (recomendado), `small`, `base` o `large-v3`.
- **Idioma:** Español (`es`), inglés (`en`) o autodetección.
