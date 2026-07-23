@echo off
chcp 65001 >nul
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo [ApiDog] 正在关闭服务...
call "%ROOT%stop.bat"

echo [ApiDog] 正在启动服务...
call "%ROOT%start.bat"
exit /b %ERRORLEVEL%
