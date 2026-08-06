#Requires -Version 5.0
<#
.SYNOPSIS
  Desktop shortcut with the steel I-beam icon (not the Edge browser badge).

.DESCRIPTION
  Writes a .lnk that launches the forecast in Edge/Chrome app mode (--app=)
  and pins our multi-size I-beam .ico as the shortcut image.
#>
$ErrorActionPreference = "Stop"

$AppName  = "Ascent US Steel Forecast"
$AppUrl   = "https://ascent-steel-forecast-cnz5m3zmygunxam6xrnubz.streamlit.app/"
$IconUrl  = "https://raw.githubusercontent.com/SpiderForce-Star/ascent-steel-forecast/main/desktop/Ascent-Steel-Forecast.ico"
$LocalDir = Join-Path $env:LOCALAPPDATA "AscentSteelForecast"
$IconPath = Join-Path $LocalDir "Ascent-Steel-Forecast.ico"
$Desktop  = [Environment]::GetFolderPath("Desktop")
$LnkPath  = Join-Path $Desktop "$AppName.lnk"

Write-Host ""
Write-Host "  Ascent Building Systems — Desktop installer" -ForegroundColor Cyan
Write-Host "  -------------------------------------------" -ForegroundColor DarkGray
Write-Host ""

New-Item -ItemType Directory -Force -Path $LocalDir | Out-Null

$Beside = Join-Path $PSScriptRoot "Ascent-Steel-Forecast.ico"
if (Test-Path $Beside) {
  Copy-Item -Force $Beside $IconPath
  Write-Host "  [ok] Using local I-beam icon" -ForegroundColor Green
} else {
  Write-Host "  [..] Downloading steel I-beam icon..." -ForegroundColor Yellow
  Invoke-WebRequest -Uri $IconUrl -OutFile $IconPath -UseBasicParsing
  Write-Host "  [ok] Icon saved to $IconPath" -ForegroundColor Green
}

function Find-Browser {
  $candidates = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
  )
  foreach ($p in $candidates) {
    if ($p -and (Test-Path $p)) { return $p }
  }
  return $null
}

$browser = Find-Browser
Write-Host "  [..] Creating desktop shortcut with I-beam icon..." -ForegroundColor Yellow

$Wsh = New-Object -ComObject WScript.Shell
$Sc  = $Wsh.CreateShortcut($LnkPath)
$Sc.Description = "US Steel Cost 2-Year Forecast — Ascent Building Systems"
$Sc.WorkingDirectory = $LocalDir
$Sc.IconLocation = "$IconPath,0"

if ($browser) {
  # App mode: dedicated window + our custom .ico on the shortcut
  $Sc.TargetPath = $browser
  $Sc.Arguments = "--app=$AppUrl"
  Write-Host "  [ok] Browser: $browser (app mode)" -ForegroundColor Green
} else {
  # Fallback: open default handler; icon still ours
  $Sc.TargetPath = "$env:WINDIR\System32\cmd.exe"
  $Sc.Arguments = "/c start `"`" `"$AppUrl`""
  $Sc.WindowStyle = 7
  Write-Host "  [ok] Using default browser fallback" -ForegroundColor Yellow
}

$Sc.Save()

# Refresh icon cache hint (best-effort)
try {
  $shell = New-Object -ComObject Shell.Application
  $shell.NameSpace($Desktop).ParseName("$AppName.lnk").InvokeVerb("refresh") 2>$null
} catch {}

Write-Host "  [ok] Shortcut created:" -ForegroundColor Green
Write-Host "       $LnkPath" -ForegroundColor White
Write-Host ""
Write-Host "  You should see the steel I-beam — not the Edge logo." -ForegroundColor Cyan
Write-Host "  If Windows still shows a browser badge, right-click the shortcut →" -ForegroundColor DarkGray
Write-Host "  Properties → Change Icon → browse to:" -ForegroundColor DarkGray
Write-Host "  $IconPath" -ForegroundColor White
Write-Host ""

try {
  $open = Read-Host "  Open the forecast now? (Y/n)"
  if ($open -eq "" -or $open -match '^[Yy]') {
    if ($browser) {
      Start-Process -FilePath $browser -ArgumentList "--app=$AppUrl"
    } else {
      Start-Process $AppUrl
    }
  }
} catch {}
