' Probe of the Multisim component database (MSCOMP_S.PRD looks like a Microsoft Access file):
' list of tables, their columns, row counts and the first rows of each table -> dbprobe.txt (UTF-8).
' The database is copied to %TEMP% first; the original is only read.
'
' Run (32-bit script host - it has the Access/Jet driver):
'   C:\Windows\SysWOW64\cscript.exe //nologo dbprobe.vbs [DATABASE_FILE] [OUTPUT_FILE]
' DATABASE_FILE defaults to the Master Database of Multisim 14.3, OUTPUT_FILE to dbprobe.txt in the current folder.
Option Explicit
Const ROWS = 3, MAXLEN = 100
Dim fso, sh, db, outPath, tmp, cn, cs, i, rsT, tables, t, out
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
db = "C:\ProgramData\National Instruments\Circuit Design Suite\14.3\database\MSCOMP_S.PRD"
If WScript.Arguments.Count > 0 Then db = fso.GetAbsolutePathName(WScript.Arguments(0))
outPath = fso.GetAbsolutePathName("dbprobe.txt")
If WScript.Arguments.Count > 1 Then outPath = fso.GetAbsolutePathName(WScript.Arguments(1))
If Not fso.FileExists(db) Then WScript.Echo "Database not found: " & db: WScript.Quit 1

out = "database: " & db & " (" & fso.GetFile(db).Size & " bytes)" & vbCrLf
tmp = sh.ExpandEnvironmentStrings("%TEMP%") & "\msdb_probe_copy.mdb"
On Error Resume Next
fso.CopyFile db, tmp, True
If Err.Number <> 0 Then WScript.Echo "Cannot copy the database (close Multisim and retry): " & Err.Description: WScript.Quit 2
Err.Clear

' Jet 4.0 (32-bit, built into Windows), then ACE 12 / 16 (Access Database Engine)
cs = Array("Provider=Microsoft.Jet.OLEDB.4.0;Data Source=" & tmp & ";Mode=Read;", _
           "Provider=Microsoft.ACE.OLEDB.12.0;Data Source=" & tmp & ";Mode=Read;", _
           "Provider=Microsoft.ACE.OLEDB.16.0;Data Source=" & tmp & ";Mode=Read;")
Set cn = Nothing
For i = 0 To UBound(cs)
    Set cn = CreateObject("ADODB.Connection")
    Err.Clear
    cn.Open cs(i)
    If Err.Number = 0 Then out = out & "opened with: " & Split(cs(i), ";")(0) & vbCrLf: Exit For
    out = out & "failed " & Split(cs(i), ";")(0) & ": " & Err.Description & vbCrLf
    Set cn = Nothing
Next
If cn Is Nothing Then Finish "Could not open the database (see above; maybe a password or another format)."

' tables (adSchemaTables = 20), user tables only
Set rsT = cn.OpenSchema(20)
tables = ""
Do Until rsT.EOF
    If rsT("TABLE_TYPE") = "TABLE" Then tables = tables & rsT("TABLE_NAME") & vbLf
    rsT.MoveNext
Loop
rsT.Close
out = out & vbCrLf & "tables:" & vbCrLf & tables & vbCrLf
For Each t In Split(tables, vbLf)
    If t <> "" Then DumpTable t
Next
Finish "done"

Sub DumpTable(name)
    Dim rs, n, f, row, k, v
    On Error Resume Next
    Err.Clear
    Set rs = cn.Execute("SELECT COUNT(*) FROM [" & name & "]")
    If Err.Number <> 0 Then out = out & "== " & name & ": " & Err.Description & vbCrLf: Err.Clear: Exit Sub
    n = rs(0).Value: rs.Close
    out = out & "== " & name & "  (" & n & " rows)" & vbCrLf
    Set rs = cn.Execute("SELECT TOP " & ROWS & " * FROM [" & name & "]")
    If Err.Number <> 0 Then out = out & "   " & Err.Description & vbCrLf: Err.Clear: Exit Sub
    row = "   columns:"
    For Each f In rs.Fields: row = row & " " & f.Name & "(" & f.Type & ")": Next
    out = out & row & vbCrLf
    k = 0
    Do Until rs.EOF Or k >= ROWS
        row = "   row:"
        For Each f In rs.Fields
            If f.Type = 128 Or f.Type = 204 Or f.Type = 205 Then
                v = "<binary " & f.ActualSize & ">"
            ElseIf IsNull(f.Value) Then
                v = "NULL"
            Else
                v = Replace(Replace(CStr(f.Value), vbCr, " "), vbLf, " ")
                If Len(v) > MAXLEN Then v = Left(v, MAXLEN) & "..."
            End If
            row = row & " | " & v
        Next
        out = out & row & vbCrLf
        rs.MoveNext: k = k + 1
    Loop
    rs.Close
End Sub

Sub Finish(msg)
    Dim st
    On Error Resume Next
    out = out & vbCrLf & msg & vbCrLf
    If Not cn Is Nothing Then cn.Close
    fso.DeleteFile tmp, True
    Set st = CreateObject("ADODB.Stream")
    st.Type = 2: st.Charset = "utf-8": st.Open: st.WriteText out: st.SaveToFile outPath, 2: st.Close
    WScript.Echo msg & " -> " & outPath
    WScript.Quit 0
End Sub
