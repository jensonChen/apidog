@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "F:\ApiWorkbench\scripts\start.ps1"
exit /b %ERRORLEVEL%
