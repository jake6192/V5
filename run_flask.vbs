Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.Run Chr(34) & folder & "\run_flask.cmd" & Chr(34), 0
Set WshShell = Nothing
