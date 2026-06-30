Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "C:\Users\Admin\System Apps\Razor"
shell.Run """C:\Program Files\Python313\pythonw.exe"" ""C:\Users\Admin\System Apps\Razor\main.py"" --tray", 0, False
