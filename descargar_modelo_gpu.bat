@echo off
title Descargador de Modelos Whisper para GPU AMD (Vulkan)
cd /d "%~dp0"

:: Carpeta centralizada preferida: C:\whisper\models
set "TARGET_DIR=C:\whisper\models"
if not exist "%TARGET_DIR%" (
    mkdir "%TARGET_DIR%" 2>nul
    if not exist "%TARGET_DIR%" (
        echo [Aviso] No se pudo crear C:\whisper\models (permisos en C:\).
        echo Usando carpeta local: %~dp0bin\vulkan\models
        set "TARGET_DIR=%~dp0bin\vulkan\models"
        if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
    )
)

:menu
cls
echo ========================================================
echo   Descargador de Modelos Whisper para GPU AMD (Vulkan)
echo ========================================================
echo  Carpeta de destino: %TARGET_DIR%
echo ========================================================
echo.
echo Presiona el numero del modelo que deseas descargar:
echo.
echo  [1] medium-q5_0 (539 MB)   - RECOMENDADO: Alta precision para RX 470
echo  [2] small       (487 MB)   - Rapido y muy balanceado
echo  [3] tiny        (77 MB)    - Ultra rapido (para pruebas)
echo  [4] large-v3-q5_0 (1.08 GB)- Maxima precision absoluta
echo  [5] Salir
echo.

choice /C 12345 /N /M "Presiona una tecla (1, 2, 3, 4 o 5): "

if errorlevel 5 goto salir
if errorlevel 4 goto desc_large
if errorlevel 3 goto desc_tiny
if errorlevel 2 goto desc_small
if errorlevel 1 goto desc_medium

:desc_medium
echo.
echo ========================================================
echo Descargando ggml-medium-q5_0.bin (~539 MB) desde Hugging Face...
echo Destino: %TARGET_DIR%\ggml-medium-q5_0.bin
echo ========================================================
echo.
curl.exe -L --progress-bar -o "%TARGET_DIR%\ggml-medium-q5_0.bin" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium-q5_0.bin"
goto fin

:desc_small
echo.
echo ========================================================
echo Descargando ggml-small.bin (~487 MB) desde Hugging Face...
echo Destino: %TARGET_DIR%\ggml-small.bin
echo ========================================================
echo.
curl.exe -L --progress-bar -o "%TARGET_DIR%\ggml-small.bin" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"
goto fin

:desc_tiny
echo.
echo ========================================================
echo Descargando ggml-tiny.bin (~77 MB) desde Hugging Face...
echo Destino: %TARGET_DIR%\ggml-tiny.bin
echo ========================================================
echo.
curl.exe -L --progress-bar -o "%TARGET_DIR%\ggml-tiny.bin" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin"
goto fin

:desc_large
echo.
echo ========================================================
echo Descargando ggml-large-v3-q5_0.bin (~1.08 GB) desde Hugging Face...
echo Destino: %TARGET_DIR%\ggml-large-v3-q5_0.bin
echo ========================================================
echo.
curl.exe -L --progress-bar -o "%TARGET_DIR%\ggml-large-v3-q5_0.bin" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-q5_0.bin"
goto fin

:fin
if errorlevel 1 (
    echo.
    echo ========================================================
    echo [ERROR] Ocurrio un fallo durante la descarga.
    echo Revisa tu conexion a internet e intenta nuevamente.
    echo ========================================================
) else (
    echo.
    echo ========================================================
    echo [EXITO] Modelo descargado correctamente en:
    echo        %TARGET_DIR%\
    echo Listo para usar en DND, Academic y Work Recorder.
    echo ========================================================
)
echo.
pause
goto menu

:salir
exit /b
