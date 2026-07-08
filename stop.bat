@echo off
chcp 65001 >nul
call :KillPort 19527
call :KillPort 5173
exit /b 0

:KillPort
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":%~1 " ^| findstr LISTENING') do (
  taskkill /F /PID %%p >nul 2>&1
)
exit /b 0
