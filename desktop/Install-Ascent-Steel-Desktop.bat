@echo off
title Ascent Steel Forecast — Desktop Installer
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-Ascent-Steel-Desktop.ps1"
if errorlevel 1 pause
