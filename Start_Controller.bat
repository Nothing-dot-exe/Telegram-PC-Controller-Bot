@echo off
title Telegram PC Controller
cd /d "%~dp0"
start "" pythonw TelegramController.py
exit

""
@echo off
title Telegram PC Controller
cd /d "%~dp0"

if exist "TelegramPCController.exe" (
    start "" "TelegramPCController.exe"
) else (
    start "" pythonw TelegramController.py
)
exit
""
