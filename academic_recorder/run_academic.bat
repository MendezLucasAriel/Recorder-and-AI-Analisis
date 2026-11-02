@echo off
title Academic Recorder - Clases Universitarias
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo Ocurrio un error al ejecutar Academic Recorder.
    pause
)
