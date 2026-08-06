' Ascent US Steel Forecast — desktop shortcut with steel I-beam icon
' Double-click this file. No prompts. Creates shortcut on Desktop.

Option Explicit

Dim sh, fso, desktop, localDir, iconSrc, iconDst, lnkPath
Dim edge, chrome, browser, appUrl, appName

appName = "Ascent US Steel Forecast"
appUrl  = "https://ascent-steel-forecast-cnz5m3zmygunxam6xrnubz.streamlit.app/"

Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

desktop  = sh.SpecialFolders("Desktop")
localDir = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\AscentSteelForecast"
iconDst  = localDir & "\Ascent-Steel-Forecast.ico"
lnkPath  = desktop & "\" & appName & ".lnk"

If Not fso.FolderExists(localDir) Then
  fso.CreateFolder localDir
End If

' Prefer icon next to this script
iconSrc = fso.GetParentFolderName(WScript.ScriptFullName) & "\Ascent-Steel-Forecast.ico"
If fso.FileExists(iconSrc) Then
  fso.CopyFile iconSrc, iconDst, True
Else
  ' Fallback: try common unzip folder name on Desktop
  iconSrc = desktop & "\Ascent-Steel-Desktop-Installer\Ascent-Steel-Forecast.ico"
  If fso.FileExists(iconSrc) Then
    fso.CopyFile iconSrc, iconDst, True
  End If
End If

If Not fso.FileExists(iconDst) Then
  MsgBox "Could not find Ascent-Steel-Forecast.ico next to this installer." & vbCrLf & _
         "Keep the .ico in the same folder as this .vbs and try again.", _
         vbCritical, appName
  WScript.Quit 1
End If

' Find Edge or Chrome for app-mode window
edge = sh.ExpandEnvironmentStrings("%ProgramFiles(x86)%") & "\Microsoft\Edge\Application\msedge.exe"
If Not fso.FileExists(edge) Then
  edge = sh.ExpandEnvironmentStrings("%ProgramFiles%") & "\Microsoft\Edge\Application\msedge.exe"
End If
If Not fso.FileExists(edge) Then
  edge = sh.ExpandEnvironmentStrings("%LocalAppData%") & "\Microsoft\Edge\Application\msedge.exe"
End If

chrome = sh.ExpandEnvironmentStrings("%ProgramFiles%") & "\Google\Chrome\Application\chrome.exe"
If Not fso.FileExists(chrome) Then
  chrome = sh.ExpandEnvironmentStrings("%ProgramFiles(x86)%") & "\Google\Chrome\Application\chrome.exe"
End If
If Not fso.FileExists(chrome) Then
  chrome = sh.ExpandEnvironmentStrings("%LocalAppData%") & "\Google\Chrome\Application\chrome.exe"
End If

If fso.FileExists(edge) Then
  browser = edge
ElseIf fso.FileExists(chrome) Then
  browser = chrome
Else
  browser = ""
End If

Dim sc
Set sc = sh.CreateShortcut(lnkPath)
sc.Description = "US Steel Cost 2-Year Forecast - Ascent Building Systems"
sc.WorkingDirectory = localDir
sc.IconLocation = iconDst & ",0"

If browser <> "" Then
  sc.TargetPath = browser
  sc.Arguments = "--app=" & appUrl
Else
  ' Open with default browser via cmd start
  sc.TargetPath = sh.ExpandEnvironmentStrings("%WINDIR%") & "\System32\cmd.exe"
  sc.Arguments = "/c start """" """ & appUrl & """"
  sc.WindowStyle = 7
End If

sc.Save

MsgBox "Desktop shortcut created:" & vbCrLf & vbCrLf & _
       lnkPath & vbCrLf & vbCrLf & _
       "Icon: steel I-beam (not the Edge logo)." & vbCrLf & _
       "Double-click it anytime to open the forecast.", _
       vbInformation, appName
