Set shell = CreateObject("WScript.Shell")
root = "F:\ApiDog"
shell.CurrentDirectory = root & "\backend"
shell.Run """" & root & "\backend\.venv\Scripts\python.exe"" main.py", 0, False
