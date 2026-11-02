# 🎲 D&D Session Recorder & AI Chronicler

Aplicación de escritorio en Python diseñada para grabar sesiones de rol online (ej. **Foundry VTT + Discord**) y generar crónicas y resúmenes narrativos detallados con Inteligencia Artificial.

**Costo de operación: \$0** (Transcripción 100% local acelerada por tu tarjeta gráfica AMD RX 470 o CPU + Resúmenes con el plan gratuito de Google Gemini).

---

## 🚀 Inicio Rápido

1. Haz doble clic en `run.bat` o ejecuta:
   ```bash
   python main.py
   ```
2. En la pestaña **⚙️ Ajustes**:
   - Pega tu clave gratuita de Google Gemini (puedes obtener una en [aistudio.google.com](https://aistudio.google.com/app/apikey)).
   - Elige tu dispositivo de procesamiento preferido:
     - `🎮 GPU AMD Radeon RX 470 (Vulkan)` (Hasta 3x más rápido aprovechando los 211 GB/s de tu memoria GDDR5).
     - `💻 CPU Multinúcleo INT8` (Máxima estabilidad y sin límite de VRAM).
   - Configura el idioma de transcripción (`en` para partidas en inglés, `es` para español o `auto`).
   - Haz clic en **Guardar Cambios**.
3. En la pestaña **🎙️ Grabar**:
   - Ingresa el nombre de la campaña.
   - Verifica los dispositivos seleccionados:
     - **Audio Sistema (Discord/Juego)**: tu dispositivo Loopback (por defecto tus auriculares).
     - **Tu Micrófono**: tu micrófono habitual.
     - *(Opcional)* Marca "Grabar también pantalla" para guardar un video ligero (5 FPS) de tus mapas de Foundry.
   - Haz clic en **⏺️ Iniciar Grabación**.
4. Al terminar la partida, haz clic en **⏹️ Finalizar Sesión**.
5. La app te llevará automáticamente a **📜 Sesiones y Resúmenes**.
   - Haz clic en **⚡ Procesar Completo** para transcribir el audio en tu PC y generar el resumen con Gemini.

---

## 🌟 Características

- **Aceleración por GPU AMD (Vulkan)**: Integración con motor nativo Vulkan que aprovecha los 211 GB/s de ancho de banda de la AMD Radeon RX 470, con **protección de fallback automático a CPU** en caso de falta de memoria VRAM.
- **Captura Dual Simultánea**: Graba las voces de tus compañeros en Discord y la música/efectos de Foundry VTT a través de WASAPI Loopback, al mismo tiempo que captura tu propia voz con tu micrófono, mezclándolas con balance adecuado a 16 kHz mono.
- **Grabación Opcional de Pantalla**: FFmpeg captura la pantalla a 5 FPS y compresión ligera, ideal para recordar la posición en los mapas sin saturar espacio en disco.
- **Resumen Especializado en D&D**: El prompt de Gemini extrae:
  - 📖 Resumen narrativo cronológico.
  - ⚔️ Combates y encuentros (enemigos, tácticas, resultados).
  - 🗣️ Interacciones y acuerdos con NPCs.
  - 📍 Lugares descubiertos y visitados.
  - 🎒 Botín, tesoros y objetos mágicos obtenidos.
  - 📌 Cabos sueltos y misiones pendientes para la próxima sesión.
  - ✨ Momentos memorables, pifias y tiradas épicas (Nat 20s).
- **Exportación Fácil**: Copia el resumen en formato Markdown con un solo clic o abre la carpeta de la sesión para ver los audios y transcripciones generadas.

---

## 📁 Estructura de Archivos

```
nifty-pasteur/
├── main.py                     # Punto de entrada de la aplicación
├── run.bat                     # Lanzador para Windows
├── requirements.txt            # Dependencias de Python
├── .env                        # Configuración, modelo y API Key de Gemini
├── bin/
│   └── vulkan/                 # Binarios de whisper.cpp compilados con Vulkan para AMD
│       ├── whisper-cli.exe
│       ├── ggml-vulkan.dll
│       └── models/             # Modelos GGML descargados (small, base, etc.)
├── recorder/
│   ├── audio_recorder.py       # Captura dual WASAPI Loopback + Micrófono
│   ├── screen_recorder.py      # Captura de pantalla ligera con FFmpeg
│   └── session_manager.py      # Gestión del ciclo de vida de sesiones
├── ai/
│   ├── config.py               # Gestión de configuración persistente
│   ├── device_detector.py      # Diagnóstico de GPU RX 470 y CPU
│   ├── transcriber.py          # Transcriptor híbrido con fallback
│   ├── vulkan_transcriber.py   # Motor Whisper acelerado en Vulkan
│   ├── summarizer.py           # Generación de resúmenes con Gemini 3.5 Flash
│   └── prompts.py              # Prompts especializados para rol
├── models/
│   └── session.py              # Modelos de datos para sesiones y resúmenes
├── ui/
│   ├── app.py                  # Ventana principal CustomTkinter
│   ├── recorder_tab.py         # Vista de grabación y vúmetros
│   ├── sessions_tab.py         # Historial, visor de resumen y transcripción
│   └── settings_tab.py         # Ajustes de IA, GPU/CPU y diagnóstico
└── sessions/                   # Carpeta donde se guardan tus grabaciones
```
