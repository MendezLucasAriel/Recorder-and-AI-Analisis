# 🧭 Índice del Proyecto y Guía para Agentes de IA

> **LEER PRIMERO ANTES DE MODIFICAR EL CÓDIGO.**  
> Este documento es el mapa de arquitectura y enrutamiento del proyecto. Su objetivo es permitir que cualquier agente de IA o desarrollador comprenda el sistema en segundos, reduciendo drásticamente el consumo de tokens y evitando la lectura innecesaria de archivos no relacionados con la tarea a realizar.

---

## ⚠️ Protocolo Obligatorio para Agentes

1. **Actualización Obligatoria de este Índice:**  
   Cada vez que realices una modificación, agregado o refactorización en el proyecto, **DEBES documentarla al final de este archivo en la sección [Historial de Actualizaciones](#-historial-de-actualizaciones)** y ajustar las rutas de este índice si hubo cambios estructurales.
2. **Actualización del Stack Tecnológico:**  
   Si incorporas una nueva dependencia, librería, modelo de IA o endpoint externo, **DEBES registrarla obligatoriamente en [`docs/TECH_STACK.md`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/docs/TECH_STACK.md)**.
3. **Preservación del Costo \$0:**  
   No agregar dependencias que requieran suscripciones pagas, APIs con costos fijos ni dependencias no gratuitas. Toda la transcripción debe mantenerse local y los resúmenes deben funcionar bajo el tier gratuito de Google Gemini.

---

## 🎯 Tabla de Enrutamiento Rápido ("¿Dónde toco cada cosa?")

Si necesitas realizar un cambio o solucionar un bug, dirígete directamente al archivo correspondiente:

| Objetivo / Funcionalidad a Modificar | Archivo a Editar | Función / Clase Principal |
| :--- | :--- | :--- |
| **Captura y mezcla de audio (WASAPI)** | [`recorder/audio_recorder.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/recorder/audio_recorder.py) | `AudioRecorder.start_recording()`, `_mix_down()` |
| **Captura de video por ventana (WGC / Foundry)** | [`recorder/window_recorder.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/recorder/window_recorder.py) | `WindowRecorder.start_recording()`, `on_frame_arrived` |
| **Listar / Detectar ventanas del SO** | [`utils/window_list.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/utils/window_list.py) | `list_visible_windows()`, `find_window_by_partial_title()` |
| **Captura de pantalla completa (FFmpeg fallback)** | [`recorder/screen_recorder.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/recorder/screen_recorder.py) | `ScreenRecorder.start_recording()`, `stop()` |
| **Ciclo de vida de sesiones (start/stop/pause)** | [`recorder/session_manager.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/recorder/session_manager.py) | `SessionManager.start_session()`, `stop_session()` |
| **Transcripción GPU AMD RX 470 (Vulkan)** | [`ai/vulkan_transcriber.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/ai/vulkan_transcriber.py) | `VulkanTranscriber.transcribe()` |
| **Transcripción CPU y Fallback automático** | [`ai/transcriber.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/ai/transcriber.py) | `Transcriber.transcribe()` |
| **Prompts de rol y deducción de personajes** | [`ai/prompts.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/ai/prompts.py) | `SUMMARY_SYSTEM_PROMPT`, esquemas JSON |
| **Llamada a Google Gemini / Generación de resumen** | [`ai/summarizer.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/ai/summarizer.py) | `Summarizer.summarize()` |
| **Configuración persistente y lectura de `.env`** | [`ai/config.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/ai/config.py) | `AIConfig.load()`, `save_to_env()` |
| **Detección de hardware de la PC (GPU/CPU)** | [`ai/device_detector.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/ai/device_detector.py) | `DeviceDetector.get_info()` |
| **Estructura de datos (Sesiones, Transcripción, Resumen)**| [`models/session.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/models/session.py) | `Session`, `SessionMetadata`, `SessionSummary` |
| **Pestaña Grabar (Controles, selector de ventana, VU)** | [`ui/recorder_tab.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/ui/recorder_tab.py) | `RecorderTab`, `_on_record_clicked()`, `_refresh_window_list()` |
| **Pestaña Sesiones (Visor de Markdown y transcripción)**| [`ui/sessions_tab.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/ui/sessions_tab.py) | `SessionsTab`, `_run_full_process()`, `_run_transcription_only()`|
| **Importar videos/audios externos (OBS, Discord, etc.)**| [`ui/sessions_tab.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/ui/sessions_tab.py) & [`recorder/session_manager.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/recorder/session_manager.py) | `_on_import_media_clicked()`, `SessionManager.import_external_media()`, `FFmpegHelper.extract_audio_to_wav()` |
| **Pestaña Ajustes (Clave Gemini, selector GPU/CPU)** | [`ui/settings_tab.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/ui/settings_tab.py) | `SettingsTab`, `_on_save_clicked()` |
| **Ventana principal y cierre seguro de la app** | [`ui/app.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/ui/app.py) | `App`, protocolo `WM_DELETE_WINDOW`, `_on_close()` |

---

## 🌳 Árbol Completo del Repositorio Comentado

```
DND Recorder/
├── index.md                    # [ESTE ARCHIVO] Mapa de navegación y directivas para agentes de IA
├── README.md                   # Documentación general de usuario y guía de instalación rápida
├── requirements.txt            # Dependencias oficiales de Python
├── main.py                     # Punto de entrada de la aplicación de escritorio
├── run.bat                     # Lanzador directo de un clic para Windows
├── .env                        # Credenciales (Gemini API Key), modelo activo y backend de hardware
├── .env.example                # Plantilla de variables de entorno de ejemplo
├── docs/
│   └── TECH_STACK.md           # Ficha técnica exhaustiva de dependencias, modelos, endpoints y arquitectura
├── bin/
│   └── vulkan/                 # Binarios compilados en C++ de whisper.cpp para aceleración AMD Vulkan
│       ├── whisper-cli.exe     # Motor ejecutable de Whisper CLI
│       ├── ggml-vulkan.dll     # Capa de aceleración GPU Vulkan 1.3
│       └── models/             # Modelos GGML descargados (ggml-small.en.bin, ggml-tiny.bin)
├── recorder/                   # Módulo de captura en vivo
│   ├── __init__.py             # Exporta AudioRecorder, ScreenRecorder, WindowRecorder, SessionManager
│   ├── audio_recorder.py       # Captura dual WASAPI Loopback (Discord/Foundry) + Micrófono y mezcla a WAV
│   ├── window_recorder.py      # Captura de ventana bloqueada con Windows Graphics Capture (WGC) + OpenCV
│   ├── screen_recorder.py      # Captura de pantalla completa con FFmpeg gdigrab (Modo fallback)
│   └── session_manager.py      # Gestor del ciclo de vida de sesiones, orquestador de grabadores y metadata
├── ai/                         # Módulo de Inteligencia Artificial y Transcripción
│   ├── config.py               # Gestión tipada de configuraciones sincronizadas con .env
│   ├── device_detector.py      # Detección de especificaciones de hardware (AMD RX 470 / Cores CPU)
│   ├── prompts.py              # Prompts con deducción semántica de personajes, roles y combate D&D
│   ├── summarizer.py           # Cliente Google Gemini con retry ante HTTP 503 y parseo JSON resiliente
│   ├── transcriber.py          # Envoltorio híbrido de transcripción con fallback automático GPU -> CPU
│   └── vulkan_transcriber.py   # Controlador de whisper-cli en Vulkan con lectura unificada anti-deadlock
├── models/
│   └── session.py              # Dataclasses de sesión, metadatos, transcripciones y resúmenes estructurados
├── ui/                         # Interfaz gráfica desarrollada en CustomTkinter
│   ├── app.py                  # Ventana principal, pestañas superiores y protocolo de cierre seguro
│   ├── recorder_tab.py         # Pestaña "Grabar": controles, selección de ventana y medidores VU
│   ├── sessions_tab.py         # Pestaña "Sesiones y Resúmenes": reprocesamiento, visor de Markdown y tiempos
│   └── settings_tab.py         # Pestaña "Ajustes": configuración de API keys, modelos e idiomas
├── utils/
│   ├── ffmpeg_helper.py        # Detección y verificación de rutas de ejecutables FFmpeg en Windows
│   └── window_list.py          # Utilidad Win32 (ctypes EnumWindows) para listar y filtrar ventanas del SO
└── sessions/                   # Directorio donde se almacenan las sesiones grabadas (session_YYYY-MM-DD_HHMMSS/)
```

---

## ⚠️ Trampas Técnicas Conocidas (Known Gotchas)

Si vas a modificar el código, presta atención a estos detalles para evitar reintroducir bugs del pasado:

1. **Deadlock de Tuberías en Windows (`subprocess.PIPE`):**  
   Al ejecutar `whisper-cli.exe` u otros subprocesos en Windows, **NUNCA** crees pipes separados para `stdout` y `stderr` si no los vas a consumir de forma concurrente en hilos separados. Windows tiene un búfer de solo 4 KB; cuando se llena, el subproceso se congela indefinidamente.  
   *Solución aplicada:* Usar `stdout=subprocess.PIPE, stderr=subprocess.STDOUT` y leer con `iter(process.stdout.readline, "")`.
2. **Preservación de Flags de Metadatos (`save_metadata()`):**  
   En [`models/session.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/models/session.py), `save_metadata()` debe evaluar `self.metadata.has_screen = self.metadata.has_screen or self.screen_file.exists()`. Si se asigna directamente `exists()`, al arrancar la sesión se sobrescribe `has_screen` con `False` porque el video aún no se creó en disco en ese milisegundo.
3. **GPU AMD RX 470 en Python 3.14:**  
   La arquitectura Polaris de la RX 470 **no** tiene soporte oficial de ROCm en Windows, y `torch-directml` no soporta Python 3.14. Por esta razón, la aceleración gráfica funciona **exclusivamente a través de Vulkan 1.3 vía `whisper.cpp`**. No intentes instalar PyTorch con DirectML.
4. **Cierre de Ventana de la App (`WM_DELETE_WINDOW`):**  
   En [`ui/app.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/ui/app.py), está configurado un protocolo de intercepción de cierre para que si el usuario cierra la ventana desde la "X", se ejecute `stop_session()` y se terminen los subprocesos de captura (evitando que queden procesos huérfanos grabando en segundo plano).

---

## 📝 Historial de Actualizaciones

> Registra aquí cada cambio significativo indicando fecha, agente/autor y descripción concisa.

* **2026-10-24:**
  * Paridad y mejoras en la selección de ventanas inspiradas en `academic_recorder`:
    * Dropdown de selección de ventana con ancho expansivo dinámico (`fill="x", expand=True`) y columna redimensionable (`grid_columnconfigure(1, weight=1)`), evitando el truncamiento de títulos largos.
    * Inicialización y refresco automático de ventanas visibles al cargar la interfaz (`_init_ui()`), poblando la caché inmediatamente.
    * Auto-detección multivariable ampliada con prioridad para VTTs y navegadores (`foundry`, `roll20`, `chrome`, `edge`, `firefox`, `brave`, `opera`, `discord`).
    * Selector interactivo de tasa de cuadros (Framerate Segmented Button: `5 FPS (Ligero)`, `15 FPS (Fluido)`, `20 FPS (HD)`), integrado con `SessionManager` y los motores de captura.
    * Escalado nítido con preservación de relación de aspecto (`aspect-ratio scaling`) en `WindowRecorder` para evitar distorsión en cuadrículas, mapas y fichas.
* **2026-10-05:**
  * Implementada la importación y procesamiento de videos y audios ya grabados (OBS, Discord, Windows Game Bar, etc.) sin re-renderizar video.
  * Añadido `FFmpegHelper.extract_audio_to_wav()` para demuxing y conversión ultrarrápida a 16 kHz Mono PCM 16-bit WAV.
  * Añadido `FFmpegHelper.get_wav_duration()` para cálculo instantáneo de duración mediante el módulo estándar `wave`.
  * Implementado `SessionManager.import_external_media()` para ingesta automática de sesiones externas con hardlinking opcional de video y preservación de metadatos de origen.
  * Añadido botón "📥 Importar Video / Audio Externo" y diálogo modal moderno `CampaignInputDialog` en `ui/sessions_tab.py`, ejecutando la extracción en un hilo secundario sin congelar la UI.
* **2026-09-30:**  
  * Creado `index.md` como mapa exhaustivo del repositorio y guía de optimización de tokens para agentes de IA.
  * Creado [`docs/TECH_STACK.md`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/docs/TECH_STACK.md) con la documentación técnica formal de dependencias, modelos, arquitectura y endpoints.
* **2026-09-29:**  
  * Implementado `WindowRecorder` utilizando la **Windows Graphics Capture API** (`windows-capture` + OpenCV) para grabar exclusivamente la ventana de Foundry VTT, inmune a Alt-Tab y superposiciones.
  * Creada utilidad `utils/window_list.py` para listar ventanas visibles de Windows vía `EnumWindows`.
  * Actualizada pestaña `ui/recorder_tab.py` con selector de modos ("Ventana específica" vs "Pantalla completa") y menú desplegable de ventanas con auto-detección de Foundry.
* **2026-09-27:**  
  * Implementado soporte de aceleración por GPU AMD Radeon RX 470 mediante `whisper.cpp` con backend Vulkan 1.3 (`ai/vulkan_transcriber.py`).
  * Solucionado pipe deadlock en Windows unificando `stderr` con `stdout` para lectura no bloqueante de transcripción en tiempo real.
  * Añadida deducción semántica por contexto en los prompts de Gemini ([`ai/prompts.py`](file:///C:/Users/teenc/Documents/antigravity/DND%20Recorder/ai/prompts.py)) para identificar jugadores, personajes y clases automáticamente.
  * Añadido protocolo `WM_DELETE_WINDOW` y corregido bug de retención de procesos huérfanos en `ScreenRecorder.stop()`.
