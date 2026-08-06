# Ascent US Steel Forecast - desktop shortcut (ASCII-only, downloads icon if needed)
$ErrorActionPreference = "Stop"

$AppName  = "Ascent US Steel Forecast"
$AppUrl   = "https://ascent-steel-forecast-cnz5m3zmygunxam6xrnubz.streamlit.app/"
$IconUrl  = "https://raw.githubusercontent.com/SpiderForce-Star/ascent-steel-forecast/main/desktop/Ascent-Steel-Forecast.ico"
$LocalDir = Join-Path $env:LOCALAPPDATA "AscentSteelForecast"
$IconPath = Join-Path $LocalDir "Ascent-Steel-Forecast.ico"
$Desktop  = [Environment]::GetFolderPath("Desktop")
$LnkPath  = Join-Path $Desktop ($AppName + ".lnk")

New-Item -ItemType Directory -Force -Path $LocalDir | Out-Null

$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }

$found = $null
$tryPaths = @(
  (Join-Path $scriptDir "Ascent-Steel-Forecast.ico"),
  (Join-Path (Get-Location) "Ascent-Steel-Forecast.ico"),
  (Join-Path $Desktop "Ascent-Steel-Desktop-Installer\Ascent-Steel-Forecast.ico"),
  (Join-Path $Desktop "Ascent-Steel-Desktop-Installer (1)\Ascent-Steel-Forecast.ico"),
  (Join-Path $env:USERPROFILE "Downloads\Ascent-Steel-Desktop-Installer\Ascent-Steel-Forecast.ico"),
  (Join-Path $env:USERPROFILE "Downloads\Ascent-Steel-Desktop-Installer (1)\Ascent-Steel-Forecast.ico")
)
foreach ($p in $tryPaths) {
  if ($p -and (Test-Path -LiteralPath $p)) { $found = $p; break }
}

if ($found) {
  Copy-Item -LiteralPath $found -Destination $IconPath -Force
} else {
  Write-Host "Downloading steel I-beam icon..."
  Invoke-WebRequest -Uri $IconUrl -OutFile $IconPath -UseBasicParsing
}

if (-not (Test-Path -LiteralPath $IconPath)) {
  throw "Could not obtain Ascent-Steel-Forecast.ico"
}

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

Write-Host "Created: $LnkPath"
Write-Host "Icon: steel I-beam"
if ($browser) {
  Start-Process -FilePath $browser -ArgumentList ("--app=" + $AppUrl)
} else {
  Start-Process $AppUrl
}
