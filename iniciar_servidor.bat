@echo off
chcp 65001 >nul
title Proyecto Ali - Servidor Probador Virtual
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\iniciar_servidor.ps1"
pause
