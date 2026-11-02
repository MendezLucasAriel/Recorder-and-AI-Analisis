@echo off
title Work Recorder - Minutas y Reuniones de Trabajo
cd /d "%~dp0"
python work_recorder\main.py
if errorlevel 1 (
    echo.
    echo Ocurrio un error al ejecutar Work Recorder.
    pause
)
