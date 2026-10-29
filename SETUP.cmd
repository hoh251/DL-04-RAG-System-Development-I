@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup.ps1"
set setupExit=%errorlevel%
pause
exit /b %setupExit%
