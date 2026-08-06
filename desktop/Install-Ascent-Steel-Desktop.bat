@echo off
setlocal
title Ascent Steel Forecast - Desktop Installer
cd /d "%~dp0"

REM Prefer VBS (no encoding issues)
if exist "%~dp0Install-Ascent-Steel-Desktop.vbs" (
  wscript //nologo "%~dp0Install-Ascent-Steel-Desktop.vbs"
  if not errorlevel 1 goto done
)

REM Fallback: ASCII-only PowerShell (no smart quotes, no regex)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$name='Ascent US Steel Forecast';" ^
  "$url='https://ascent-steel-forecast-cnz5m3zmygunxam6xrnubz.streamlit.app/';" ^
  "$dir=Join-Path $env:LOCALAPPDATA 'AscentSteelForecast';" ^
  "New-Item -ItemType Directory -Force -Path $dir | Out-Null;" ^
  "$icoSrc=Join-Path $PSScriptRoot 'Ascent-Steel-Forecast.ico';" ^
  "if (-not (Test-Path $icoSrc)) { $icoSrc=Join-Path (Get-Location) 'Ascent-Steel-Forecast.ico' };" ^
  "if (-not (Test-Path $icoSrc)) { $icoSrc=Join-Path $PSScriptRoot '..\Ascent-Steel-Forecast.ico' };" ^
  "$ico=Join-Path $dir 'Ascent-Steel-Forecast.ico';" ^
  "if (Test-Path $icoSrc) { Copy-Item -Force $icoSrc $ico } else { throw 'Missing Ascent-Steel-Forecast.ico next to installer' };" ^
  "$edge=${env:ProgramFiles(x86)}+'\Microsoft\Edge\Application\msedge.exe';" ^
  "if (-not (Test-Path $edge)) { $edge=$env:ProgramFiles+'\Microsoft\Edge\Application\msedge.exe' };" ^
  "$chrome=$env:ProgramFiles+'\Google\Chrome\Application\chrome.exe';" ^
  "$browser=$null; if (Test-Path $edge) { $browser=$edge } elseif (Test-Path $chrome) { $browser=$chrome };" ^
  "$lnk=Join-Path ([Environment]::GetFolderPath('Desktop')) ($name+'.lnk');" ^
  "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut($lnk);" ^
  "$s.IconLocation=$ico+',0'; $s.Description='US Steel Cost 2-Year Forecast'; $s.WorkingDirectory=$dir;" ^
  "if ($browser) { $s.TargetPath=$browser; $s.Arguments=('--app='+$url) } else { $s.TargetPath=$env:WINDIR+'\System32\cmd.exe'; $s.Arguments=('/c start \"\" \"'+$url+'\"'); $s.WindowStyle=7 };" ^
  "$s.Save();" ^
  "Write-Host ('Created: '+$lnk); Write-Host 'Steel I-beam icon applied.'"

if errorlevel 1 (
  echo.
  echo Install failed. Manual fix:
  echo  1. Right-click Desktop - New - Shortcut
  echo  2. Paste: https://ascent-steel-forecast-cnz5m3zmygunxam6xrnubz.streamlit.app/
  echo  3. Name it: Ascent US Steel Forecast
  echo  4. Right-click shortcut - Properties - Change Icon
  echo  5. Browse to Ascent-Steel-Forecast.ico in this folder
  echo.
  pause
  exit /b 1
)

:done
echo.
echo Done. Check your Desktop for "Ascent US Steel Forecast".
echo.
pause
