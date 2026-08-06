@echo off
setlocal EnableExtensions
title Ascent Steel Forecast - Desktop Installer
cd /d "%~dp0"

echo.
echo  Ascent Building Systems - Desktop Installer
echo  -------------------------------------------
echo.

REM If user opened from inside zip, %~dp0 may be a temp dir without the ico.
REM VBS will download the icon from GitHub if needed.
if exist "%~dp0Install-Ascent-Steel-Desktop.vbs" (
  wscript //nologo "%~dp0Install-Ascent-Steel-Desktop.vbs"
  if not errorlevel 1 goto endok
)

echo VBS failed — trying PowerShell fallback...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-Ascent-Steel-Desktop.ps1"
if errorlevel 1 (
  echo.
  echo Still failed. Do this:
  echo  1. Close this window
  echo  2. Right-click the ZIP - Extract All - Extract
  echo  3. Open the new folder
  echo  4. Double-click Install-Ascent-Steel-Desktop.vbs
  echo.
  pause
  exit /b 1
)

:endok
echo.
echo Success. Check your Desktop for "Ascent US Steel Forecast".
echo.
pause
