# 📚 Arquitectura Técnica, Modelos, Dependencias y Endpoints

Este documento detalla la totalidad del stack tecnológico, los modelos de Inteligencia Artificial, las dependencias y los protocolos de comunicación utilizados por **D&D Session Recorder & AI Chronicler**.

---

## 1. Principios de Diseño
1. **Costo Operativo \$0:** Utilización exclusiva de cómputo local acelerado por hardware del usuario y tiers gratuitos de APIs de IA sin costos ocultos.
2. **Privacidad Local:** Las grabaciones de audio, video y la transcripción completa se procesan y almacenan 100% de manera local. Únicamente el texto de la transcripción se envía a la API de resumen.
3. **Resiliencia ante Fallos de Hardware:** Todo mecanismo acelerado por GPU (Vulkan) cuenta con un circuito de **fallback automático a CPU** garantizando que la aplicación nunca colapse por falta de VRAM.
4. **Desacoplamiento Modular:** Separación estricta entre capa de grabación (`recorder/`), inteligencia artificial (`ai/`), modelos de datos (`models/`) e interfaz gráfica (`ui/`).

---

## 2. Stack Tecnológico Completo

| Capa | Tecnología / Biblioteca | Versión | Justificación Técnica |
| :--- | :--- | :--- | :--- |
| **Runtime** | Python | `3.14.7 64-bit` | Entorno de ejecución principal en Windows 11. |
| **Frontend Desktop (GUI)** | CustomTkinter | `>=5.2.0` | Capa gráfica moderna en modo oscuro sobre Tkinter nativo, soporte de temas y widgets estilizados. |
| **Captura de Audio** | PyAudioWPatch | `>=0.2.12.8` | Fork de PyAudio que expone la Windows Audio Session API (WASAPI) para capturar streams Loopback del sistema y micrófonos de forma asíncrona. |
| **Procesamiento de Audio** | NumPy & SciPy | `>=1.24.0`, `>=1.11.0` | Conversión de buffers de audio a punto flotante, alineación matemática, normalización dinámica y remuestreo de 48 kHz a 16 kHz mono. |
| **Captura de Video (Ventana)** | windows-capture | `>=2.0.0` | Bindings en Rust de la **Windows Graphics Capture API (WGC)** nativa de Windows 10/11. Captura directamente el buffer de la GPU de una ventana (`HWND`), siendo inmune a superposiciones y Alt-Tab. |
| **Codificación de Video** | OpenCV (`cv2`) | `>=4.8.0` | Creación de contenedores MP4 (`cv2.VideoWriter` con códec `mp4v`), control de framerate (5 FPS) y reescalado proporcional a 720p. |
| **Captura de Video (Desktop)** | FFmpeg (Gyan build) | `9.0.1+` | Motor de captura de respaldo (fallback) mediante dispositivo `gdigrab` a nivel de escritorio completo. |
| **ASR Local en GPU** | whisper.cpp (Vulkan 1.3) | `v1.0.0` | Implementación en C++ de Whisper optimizada con backend Vulkan (`ggml-vulkan.dll`). Permite inferencia rápida en GPUs AMD Polaris (RX 470) con Flash Attention. |
| **ASR Local en CPU** | faster-whisper | `>=1.0.0` | Motor de respaldo para CPU basado en CTranslate2 con cuantización `INT8` multihilo. |
| **LLM & Razonamiento** | Google GenAI SDK | `>=1.0.0` | SDK oficial de Google para interactuar con la familia de modelos Gemini (`gemini-3.5-flash`). |
| **Variables de Entorno** | python-dotenv | `>=1.0.0` | Carga de credenciales y parámetros de configuración persistentes desde `.env`. |
| **Manejo de Imágenes** | Pillow (PIL) | `>=10.0.0` | Soporte auxiliar para renderizado de íconos y assets en la GUI. |

---

## 3. Modelos de Inteligencia Artificial

### A. Reconocimiento de Voz / Transcripción (ASR Local)
* **Motor GPU (`ai/vulkan_transcriber.py`):**
  * `ggml-small.en.bin` (~465 MB): Modelo predeterminado para sesiones en inglés. Consumo de VRAM ~1.2 GB (ideal para placas de 4 GB).
  * `ggml-tiny.en.bin` / `ggml-tiny.bin` (~77 MB): Modelos ultraligeros de mínima huella de memoria.
  * Formato: Pesos cuantizados GGML para `whisper.cpp`.
* **Motor CPU (`ai/transcriber.py`):**
  * Whisper `small` / `base` / `tiny` convertidos a formato CTranslate2 con cuantización `INT8`, ejecutados en 8 threads de CPU.

### B. Razonamiento, Deducción Semántica y Resumen (Cloud)
* **Modelo LLM Predeterminado:** `gemini-3.5-flash` (configurable en `.env` a `gemini-3.7-flash` o `gemini-3.5-flash-lite`).
* **Ventana de Contexto:** Hasta 1.000.000 de tokens (permite procesar sesiones de más de 4 horas en una sola llamada).
* **Técnica de Deducción Semántica por Contexto:**
  * Al no disponer de canales de audio aislados por jugador en la llamada de Discord, el modelo analiza el *diálogo cruzado* de la transcripción para:
    1. Identificar a los personajes jugadores (PJs) a partir de los nombres con los que se llaman.
    2. Deducir sus clases de personaje según las habilidades, tiradas y conjuros empleados (*Green-Flame Blade*, *Action Surge*, *Hold Person*).
    3. Identificar al Dungeon Master por su rol en las descripciones del entorno y control de enemigos.
  * Genera una salida estructurada mediante validación de esquema JSON tipado antes de redactar la crónica cronológica.

---

## 4. Subsistemas y Funcionamiento Interno

### 1. Grabación en Vivo (`recorder/`)
* **Audio Dual (`recorder/audio_recorder.py`):**
  * Levanta dos streams simultáneos con `PyAudioWPatch`: uno para el dispositivo Loopback WASAPI (Discord y Foundry VTT) y otro para el micrófono.
  * Al detener la sesión, `_mix_down()` une las pistas, normaliza los picos de audio y exporta `audio.wav` en formato estándar 16 kHz Mono.
* **Video Bloqueado por Ventana (`recorder/window_recorder.py`):**
  * Inicia un hilo de captura WGC con `windows-capture` vinculado al `HWND` de la ventana seleccionada.
  * Aplica rate-limiting a 5 FPS descartando frames excedentes y reescala con OpenCV a un máximo de 1280x720 para generar `screen.mp4`.
* **Video de Escritorio (`recorder/screen_recorder.py`):**
  * Invoca `ffmpeg.exe` con `-f gdigrab -i desktop` a 5 FPS con codificación `ultrafast`. Se utiliza como fallback si la ventana seleccionada deja de estar disponible.
* **Orquestador (`recorder/session_manager.py`):**
  * Coordina el inicio, pausa y finalización sincronizada de los grabadores de audio y video. Escribe y actualiza los metadatos en `session.json`.

### 2. Ingesta de Medios Externos (`utils/ffmpeg_helper.py` + `recorder/session_manager.py`)
* **Demuxing y Optimización de Audio:**
  * `FFmpegHelper.extract_audio_to_wav()` extrae la pista sonora de videos (`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.flv`) o audios (`.mp3`, `.m4a`, `.flac`, `.wav`, etc.) y la convierte directamente a 16 kHz Mono PCM 16-bit WAV (`-vn -acodec pcm_s16le -ar 16000 -ac 1`).
  * Ejecución no interactiva y ultrarrápida (demuxing puro sin recodificación de video, tardando apenas ~3-5 segundos para archivos de varias horas).
* **Gestión de Almacenamiento Eficiente:**
  * `SessionManager.import_external_media()` inicializa una carpeta `sessions/session_YYYY-MM-DD_HHMMSS_imported/`.
  * Si el archivo de entrada es un video y reside en la misma unidad, crea un *hardlink* a `screen.mp4` para tener acceso visual en el visor sin duplicar espacio de disco (0 bytes adicionales). Guarda la referencia del archivo original en `metadata.devices_used["source_path"]`.

### 3. Transcripción Híbrida (`ai/`)
* **`ai/vulkan_transcriber.py`:**
  * Ejecuta `bin/vulkan/whisper-cli.exe` pasando `-dev 0` (GPU AMD Radeon RX 470), `--flash-attn`, el modelo GGML y los flags de exportación JSON.
  * **Mecanismo anti-deadlock:** Unifica `stderr` y `stdout` en una sola lectura continua en tiempo real mediante generadores (`iter(process.stdout.readline, "")`), evitando que el búfer de tuberías de Windows (4 KB) se sature y congele el proceso.
* **`ai/transcriber.py`:**
  * Administrador de fallback. Si el backend GPU genera cualquier excepción o código de error distinto de 0, commuta instantáneamente al motor CPU sin abortar el flujo del usuario.

### 3. Generación de Resúmenes (`ai/summarizer.py`)
* Conecta con la API de Google Gemini utilizando el cliente oficial `google-genai`.
* Aplica control de reintentos con backoff exponencial ante respuestas HTTP 503 (servidor temporalmente saturado en el tier gratuito).
* Procesa la respuesta JSON estructurada y la vuelca en `summary.md` y `summary.json`.

---

## 5. Endpoints y Comunicaciones de Red

El proyecto **no incluye ningún servidor central propio ni servicios de telemetría**. Las únicas conexiones de red son:

1. **Google Gemini API:**
   * **Endpoint:** `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
   * **Método:** POST con cabecera de autorización mediante API Key.
   * **Tráfico:** Exclusivamente texto (prompt de instrucciones + transcripción de la sesión). Cero envío de audio o video binario a la nube.
2. **Hugging Face Hub (Descargas de Modelos):**
   * **Endpoint:** `https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{model}.bin`
   * **Método:** GET HTTPS público.
   * **Tráfico:** Descarga única al inicializar un modelo GGML si no existe previamente en la carpeta `bin/vulkan/models/`.

---

## 6. Estructura de Persistencia en Disco

Cada sesión grabada es totalmente autónoma y se almacena en `sessions/session_YYYY-MM-DD_HHMMSS/`:

| Archivo | Tipo | Propósito |
| :--- | :--- | :--- |
| `session.json` | JSON | Metadatos de la sesión: campaña, marcas temporales, duración y dispositivos usados. |
| `audio.wav` | Audio WAV (16kHz Mono) | Audio master unificado de Discord + micrófono. |
| `screen.mp4` | Video H.264 (5 FPS) | Video opcional de la ventana de Foundry VTT o escritorio completo. |
| `transcript.json` | JSON | Transcripción estructurada por segmentos con marcas de tiempo (inicio/fin) y texto. |
| `transcript.txt` | Texto plano | Transcripción completa en texto continuo para lectura rápida. |
| `summary.json` | JSON | Resumen estructurado: participantes, eventos, combates, botín, misiones pendientes. |
| `summary.md` | Markdown | Crónica formateada con estilo roldero y emojis, lista para copiar o exportar. |

---

## 7. Protocolo de Mantenimiento Tecnológico
* Si se incorpora una nueva librería, motor de inferencia o servicio externo, **este documento (`docs/TECH_STACK.md`) debe actualizarse obligatoriamente**.
* Si se modifica la estructura de archivos o módulos del proyecto, **debe actualizarse en concordancia el archivo `index.md`**.
