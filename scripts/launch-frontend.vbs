Set shell = CreateObject("WScript.Shell")
root = "F:\ApiWorkbench"
shell.CurrentDirectory = root & "\frontend"
shell.Run "cmd /c npm run dev", 0, False
