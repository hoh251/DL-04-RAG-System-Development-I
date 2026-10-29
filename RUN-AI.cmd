@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Gemini.ps1" -Mode Chat
set taskExit=%errorlevel%
:end
pause
exit /b %taskExit%
