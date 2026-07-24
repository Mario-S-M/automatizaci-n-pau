@echo off
REM ============================================================
REM  reiniciar.bat  -  Detiene la app y la vuelve a levantar
REM ============================================================
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo [+] Reiniciando aplicacion...
echo.

REM --- Detener primero ---
call "%~dp0detener.bat"

echo.
echo [+] Esperando 2 segundos antes de reabrir...
timeout /t 2 >nul

echo.
REM --- Levantar de nuevo ---
call "%~dp0activar.bat"