@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Gemini.ps1" -Mode Evaluate
set taskExit=%errorlevel%
pause
exit /b %taskExit%
