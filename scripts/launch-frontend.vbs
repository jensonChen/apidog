Set shell = CreateObject("WScript.Shell")
root = "F:\ApiDog"
shell.CurrentDirectory = root & "\frontend"
shell.Run "cmd /c npm run dev", 0, False
