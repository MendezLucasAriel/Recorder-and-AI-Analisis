@echo off
title D&D Session Recorder & AI Chronicler
cd /d "%~dp0"
python main.py
if errorlevel 1 pause
