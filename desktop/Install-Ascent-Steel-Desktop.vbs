' Ascent US Steel Forecast — one-click desktop shortcut (steel I-beam icon)
' Works after Extract All, or even if the .ico is missing (downloads it).

Option Explicit

Dim sh, fso, desktop, localDir, iconDst, lnkPath
Dim edge, chrome, browser, appUrl, appName, iconSrc, scriptDir
Dim http, stream, ok

appName = "Ascent US Steel Forecast"
appUrl  = "https://ascent-steel-forecast-cnz5m3zmygunxam6xrnubz.streamlit.app/"

Const IconDownloadUrl = "https://raw.githubusercontent.com/SpiderForce-Star/ascent-steel-forecast/main/desktop/Ascent-Steel-Forecast.ico"

Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

desktop  = sh.SpecialFolders("Desktop")
localDir = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\AscentSteelForecast"
iconDst  = localDir & "\Ascent-Steel-Forecast.ico"
lnkPath  = desktop & "\" & appName & ".lnk"

If Not fso.FolderExists(localDir) Then fso.CreateFolder localDir

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
ok = False

' 1) Same folder as this script
iconSrc = scriptDir & "\Ascent-Steel-Forecast.ico"
If fso.FileExists(iconSrc) Then
  fso.CopyFile iconSrc, iconDst, True
  ok = True
End If

' 2) Current working directory
If Not ok Then
  iconSrc = fso.GetAbsolutePathName(".\Ascent-Steel-Forecast.ico")
  If fso.FileExists(iconSrc) Then
    fso.CopyFile iconSrc, iconDst, True
    ok = True
  End If
End If

' 3) Desktop unzip folders (common names)
If Not ok Then
  Dim candidates, c
  candidates = Array( _
    desktop & "\Ascent-Steel-Desktop-Installer\Ascent-Steel-Forecast.ico", _
    desktop & "\Ascent-Steel-Desktop-Installer (1)\Ascent-Steel-Forecast.ico", _
    desktop & "\Ascent-Steel-Desktop-Installer (2)\Ascent-Steel-Forecast.ico", _
    sh.ExpandEnvironmentStrings("%USERPROFILE%") & "\Downloads\Ascent-Steel-Desktop-Installer\Ascent-Steel-Forecast.ico", _
    sh.ExpandEnvironmentStrings("%USERPROFILE%") & "\Downloads\Ascent-Steel-Desktop-Installer (1)\Ascent-Steel-Forecast.ico", _
    sh.ExpandEnvironmentStrings("%USERPROFILE%") & "\Downloads\Ascent-Steel-Desktop-Installer (2)\Ascent-Steel-Forecast.ico" _
  )
  For Each c In candidates
    If fso.FileExists(c) Then
      fso.CopyFile c, iconDst, True
      ok = True
      Exit For
    End If
  Next
End If

' 4) Download from GitHub (works when run from inside a zip / temp)
If Not ok Then
  On Error Resume Next
  Set http = CreateObject("MSXML2.XMLHTTP")
  If http Is Nothing Then Set http = CreateObject("Microsoft.XMLHTTP")
  http.Open "GET", IconDownloadUrl, False
  http.Send
  If Err.Number = 0 And http.Status = 200 Then
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 1 ' binary
    stream.Open
    stream.Write http.ResponseBody
    stream.SaveToFile iconDst, 2 ' overwrite
    stream.Close
    If fso.FileExists(iconDst) Then ok = True
  End If
  Err.Clear
  On Error GoTo 0
End If

If Not ok Or Not fso.FileExists(iconDst) Then
  MsgBox "Could not get the steel I-beam icon." & vbCrLf & vbCrLf & _
         "Please right-click the zip -> Extract All, then double-click" & vbCrLf & _
         "Install-Ascent-Steel-Desktop.vbs in the extracted folder." & vbCrLf & vbCrLf & _
         "Or download the icon:" & vbCrLf & IconDownloadUrl, _
         vbCritical, appName
  WScript.Quit 1
End If

' Find Edge or Chrome
edge = sh.ExpandEnvironmentStrings("%ProgramFiles(x86)%") & "\Microsoft\Edge\Application\msedge.exe"
If Not fso.FileExists(edge) Then edge = sh.ExpandEnvironmentStrings("%ProgramFiles%") & "\Microsoft\Edge\Application\msedge.exe"
If Not fso.FileExists(edge) Then edge = sh.ExpandEnvironmentStrings("%LocalAppData%") & "\Microsoft\Edge\Application\msedge.exe"

chrome = sh.ExpandEnvironmentStrings("%ProgramFiles%") & "\Google\Chrome\Application\chrome.exe"
If Not fso.FileExists(chrome) Then chrome = sh.ExpandEnvironmentStrings("%ProgramFiles(x86)%") & "\Google\Chrome\Application\chrome.exe"
If Not fso.FileExists(chrome) Then chrome = sh.ExpandEnvironmentStrings("%LocalAppData%") & "\Google\Chrome\Application\chrome.exe"

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
  sc.TargetPath = sh.ExpandEnvironmentStrings("%WINDIR%") & "\System32\cmd.exe"
  sc.Arguments = "/c start """" """ & appUrl & """"
  sc.WindowStyle = 7
End If
sc.Save

' Open the app immediately so it feels instant
On Error Resume Next
If browser <> "" Then
  sh.Run """" & browser & """ --app=" & appUrl, 1, False
Else
  sh.Run appUrl, 1, False
End If
On Error GoTo 0

MsgBox "Done!" & vbCrLf & vbCrLf & _
       "Desktop shortcut:" & vbCrLf & lnkPath & vbCrLf & vbCrLf & _
       "Icon: steel I-beam" & vbCrLf & _
       "The forecast is opening now.", _
       vbInformation, appName
