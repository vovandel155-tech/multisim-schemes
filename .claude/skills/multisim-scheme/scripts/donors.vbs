' Donor files for harvest.py made by Multisim itself: for every line of the list the template is opened,
' one placeholder part is replaced by a part from the Multisim database (Automation API ReplaceComponent)
' and the result is saved as <OUT_FOLDER>\<part>.ms14.
'
' Run (Windows, Multisim 14; close the Multisim window first) - usually through get_parts.bat:
'   C:\Windows\SysWOW64\cscript.exe //nologo donors.vbs LIST_FILE [OUT_FOLDER] [TEMPLATE] [DATABASE]
' LIST_FILE: one part per line   placeholder;group;family;part   (# - comment). Family and part may list variants
' separated by | (the first one found in the database is used), e.g.
'   Q1;Transistors;DARLINGTON_NPN;TIP121|TIP121G
' Placeholders of the template (samples\template_replace.ms14, made by scripts\donor_template.py):
'   see the comment in donor_template.py (Q1 npn, Q2 pnp, D1 diode, R1, C1, U1/U2 opamps, ...)
' (replace a placeholder by a part of the same kind - so NI recommends).
' DATABASE: 0 = Master Database (default); -1 = try 0..3.
Option Explicit
Dim fso, app, here, list, outDir, tpl, dbn, ts, line, f, nOk, nBad
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
If WScript.Arguments.Count < 1 Then
    WScript.Echo "usage: cscript //nologo donors.vbs LIST_FILE [OUT_FOLDER] [TEMPLATE] [DATABASE]"
    WScript.Quit 1
End If
list = fso.GetAbsolutePathName(WScript.Arguments(0))
outDir = fso.GetAbsolutePathName("donors_new")
If WScript.Arguments.Count > 1 Then outDir = fso.GetAbsolutePathName(WScript.Arguments(1))
tpl = ""
If WScript.Arguments.Count > 2 Then
    If WScript.Arguments(2) <> "" Then tpl = fso.GetAbsolutePathName(WScript.Arguments(2))
End If
If tpl = "" Then tpl = fso.BuildPath(fso.BuildPath(fso.GetParentFolderName(here), "samples"), "template_replace.ms14")
dbn = 0
If WScript.Arguments.Count > 3 Then dbn = CInt(WScript.Arguments(3))
If Not fso.FileExists(list) Then WScript.Echo "List not found: " & list: WScript.Quit 1
If tpl = "" Then WScript.Echo "Template not found": WScript.Quit 1
If Not fso.FileExists(tpl) Then WScript.Echo "Template not found: " & tpl: WScript.Quit 1
If Not fso.FolderExists(outDir) Then fso.CreateFolder outDir

On Error Resume Next
Set app = CreateObject("MultisimInterface.MultisimApp")
If Err.Number <> 0 Then WScript.Echo "Cannot create MultisimInterface.MultisimApp: " & Err.Description: WScript.Quit 2
app.Connect
If Err.Number <> 0 Then WScript.Echo "Connect failed: " & Err.Description: WScript.Quit 3
On Error GoTo 0
WScript.Echo "template: " & tpl
nOk = 0: nBad = 0
Set ts = fso.OpenTextFile(list, 1)
Do Until ts.AtEndOfStream
    line = Trim(ts.ReadLine)
    If line <> "" And Left(line, 1) <> "#" Then
        f = Split(line, ";")
        If UBound(f) <> 3 Then
            WScript.Echo "BAD LINE (need placeholder;group;family;part): " & line: nBad = nBad + 1
        ElseIf TryLine(Trim(f(0)), Trim(f(1)), Split(f(2), "|"), Split(f(3), "|")) Then
            nOk = nOk + 1
        Else
            WScript.Echo "FAIL " & line
            nBad = nBad + 1
        End If
    End If
Loop
ts.Close
On Error Resume Next
app.Disconnect
WScript.Echo "done: " & nOk & " saved, " & nBad & " failed -> " & outDir

' every family variant x every part variant x database(s): the first successful replacement is saved
Function TryLine(ph, grp, fams, names)
    Dim fam, nm, k, k0, k1
    TryLine = False
    If dbn < 0 Then
        k0 = 0: k1 = 3
    Else
        k0 = dbn: k1 = dbn
    End If
    For Each fam In fams
        For Each nm In names
            For k = k0 To k1
                If TryOne(ph, grp, Trim(fam), Trim(nm), k) Then
                    TryLine = True
                    Exit Function
                End If
            Next
        Next
    Next
End Function

Function TryOne(ph, grp, fam, nm, k)
    Dim c, en, ed, r, target
    On Error Resume Next
    TryOne = False
    Set c = app.OpenFile(tpl)
    If Err.Number <> 0 Then
        en = Err.Number
        WScript.Echo "     open template: " & Err.Description
        If en = 462 Or en = -2147023174 Then Reconnect   ' Multisim crashed
        Exit Function
    End If
    c.ReplaceComponent ph, "", k, grp, fam, nm, ""
    en = Err.Number: ed = Err.Description: Err.Clear
    If en <> 0 And InStr(LastError(c), "multi-section") > 0 Then   ' e.g. LM358: needs a section name - take A
        Set c = app.OpenFile(tpl)
        c.ReplaceComponent ph, "A", k, grp, fam, nm, ""
        en = Err.Number: ed = Err.Description: Err.Clear
        If en = 0 Then WScript.Echo "     " & nm & ": multi-section, section A"
    End If
    If en <> 0 Then
        WScript.Echo "     " & fam & "/" & nm & " (database " & k & "): " & ed & " " & LastError(c)
        If en = 462 Or en = -2147023174 Then Reconnect
        Exit Function
    End If
    target = outDir & "\" & SafeName(nm) & ".ms14"
    r = ""
    r = c.SaveAs(target)
    If Err.Number <> 0 Or r = "" Then
        WScript.Echo "     save " & target & ": " & Err.Description & " " & LastError(c)
        Exit Function
    End If
    WScript.Echo "ok   " & grp & "/" & fam & "/" & nm & " -> " & target
    TryOne = True
End Function

Sub Reconnect()
    On Error Resume Next
    Set app = CreateObject("MultisimInterface.MultisimApp")
    app.Connect
End Sub

Function SafeName(s)
    Dim ch
    SafeName = s
    For Each ch In Array("\", "/", ":", "*", "?", """", "<", ">", "|")
        SafeName = Replace(SafeName, ch, "_")
    Next
End Function

Function LastError(c)
    On Error Resume Next
    LastError = ""
    LastError = "(" & c.LastErrorMessage & ")"
End Function
