' Batch re-save of old Multisim files (.ms8 ... .ms13) as .ms14 via the Multisim Automation API (COM).
' Result: files saved by Multisim 14 itself -> can be scanned by harvest.py.
'
' Run (Windows, Multisim 14 installed; close the Multisim window first). The COM server is 32-bit,
' so use the 32-bit script host:
'   C:\Windows\SysWOW64\cscript.exe //nologo resave.vbs SOURCE_FOLDER [TARGET_FOLDER]
' TARGET_FOLDER defaults to SOURCE_FOLDER_ms14; subfolders are kept. Already converted files are skipped,
' so after a hang (Ctrl+C, close Multisim in Task Manager) just run it again.
' API: MultisimApp.Connect / OpenFile (closes the previous circuit itself) / MultisimCircuit.SaveAs / Disconnect.
Option Explicit
Dim fso, re, app, src, dst, nOk, nBad, nSkip
Set fso = CreateObject("Scripting.FileSystemObject")
Set re = New RegExp: re.Pattern = "^ms(8|9|1[0-3])$": re.IgnoreCase = True
If WScript.Arguments.Count < 1 Then
    WScript.Echo "usage: cscript //nologo resave.vbs SOURCE_FOLDER [TARGET_FOLDER]"
    WScript.Quit 1
End If
src = fso.GetAbsolutePathName(WScript.Arguments(0))
If WScript.Arguments.Count > 1 Then dst = fso.GetAbsolutePathName(WScript.Arguments(1)) Else dst = src & "_ms14"
nOk = 0: nBad = 0: nSkip = 0
If Not fso.FolderExists(src) Then
    WScript.Echo "Source folder not found: " & src
    WScript.Quit 1
End If

On Error Resume Next
Set app = CreateObject("MultisimInterface.MultisimApp")
If Err.Number <> 0 Then
    WScript.Echo "Cannot create MultisimInterface.MultisimApp: " & Err.Description
    WScript.Echo "Use C:\Windows\SysWOW64\cscript.exe (32-bit); check that Multisim 14 is installed."
    WScript.Quit 2
End If
app.Connect
If Err.Number <> 0 Then WScript.Echo "Connect failed: " & Err.Description: WScript.Quit 3
On Error GoTo 0

Walk fso.GetFolder(src), dst
app.Disconnect
WScript.Echo "done: " & nOk & " saved, " & nSkip & " skipped (already there), " & nBad & " failed -> " & dst

Sub Walk(folder, outDir)
    Dim f, sf, target, c, r
    If Not fso.FolderExists(outDir) Then fso.CreateFolder outDir
    For Each f In folder.Files
        If re.Test(fso.GetExtensionName(f.Name)) Then
            target = outDir & "\" & fso.GetBaseName(f.Name) & ".ms14"
            If fso.FileExists(target) Then
                nSkip = nSkip + 1
            Else
                r = ""
                On Error Resume Next
                Set c = app.OpenFile(f.Path)
                If Err.Number = 0 Then r = c.SaveAs(target)
                If Err.Number <> 0 Or r = "" Then
                    WScript.Echo "FAIL " & f.Path & " : " & Err.Description
                    nBad = nBad + 1
                Else
                    WScript.Echo "ok   " & target
                    nOk = nOk + 1
                End If
                Err.Clear
                On Error GoTo 0
            End If
        End If
    Next
    For Each sf In folder.SubFolders
        Walk sf, outDir & "\" & sf.Name
    Next
End Sub
