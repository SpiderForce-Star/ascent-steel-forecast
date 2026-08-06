# Ascent US Steel Forecast - desktop shortcut with I-beam icon
# ASCII-only. No prompts. Safe for Windows PowerShell 5+.
$ErrorActionPreference = "Stop"

$AppName  = "Ascent US Steel Forecast"
$AppUrl   = "https://ascent-steel-forecast-cnz5m3zmygunxam6xrnubz.streamlit.app/"
$LocalDir = Join-Path $env:LOCALAPPDATA "AscentSteelForecast"
$IconPath = Join-Path $LocalDir "Ascent-Steel-Forecast.ico"
$Desktop  = [Environment]::GetFolderPath("Desktop")
$LnkPath  = Join-Path $Desktop ($AppName + ".lnk")

New-Item -ItemType Directory -Force -Path $LocalDir | Out-Null

$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }

$beside = Join-Path $scriptDir "Ascent-Steel-Forecast.ico"
if (-not (Test-Path -LiteralPath $beside)) {
  $beside = Join-Path (Get-Location) "Ascent-Steel-Forecast.ico"
}
if (-not (Test-Path -LiteralPath $beside)) {
  throw "Missing Ascent-Steel-Forecast.ico next to this script."
}
Copy-Item -LiteralPath $beside -Destination $IconPath -Force

function Find-BrowserPath {
  $list = @(
    (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"),
    (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe"),
    (Join-Path $env:LOCALAPPDATA "Microsoft\Edge\Application\msedge.exe"),
    (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"),
    (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe")
  )
  foreach ($p in $list) {
    if ($p -and (Test-Path -LiteralPath $p)) { return $p }
  }
  return $null
}

$browser = Find-BrowserPath
$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut($LnkPath)
$sc.Description = "US Steel Cost 2-Year Forecast - Ascent Building Systems"
$sc.WorkingDirectory = $LocalDir
$sc.IconLocation = $IconPath + ",0"

if ($browser) {
  $sc.TargetPath = $browser
  $sc.Arguments = "--app=" + $AppUrl
} else {
  $sc.TargetPath = Join-Path $env:WINDIR "System32\cmd.exe"
  $sc.Arguments = "/c start `"`" `"$AppUrl`""
  $sc.WindowStyle = 7
}
$sc.Save()

Write-Host ""
Write-Host "Created desktop shortcut:"
Write-Host "  $LnkPath"
Write-Host "Icon: steel I-beam"
Write-Host ""
