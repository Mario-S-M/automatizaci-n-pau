@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title Book It Escuelas - Reiniciar

echo ============================================================
echo  Reiniciando aplicacion...
echo  (detiene + vuelve a abrir automaticamente)
echo ============================================================
echo.

call "%~dp0detener.bat"

echo.
echo [+] Esperando 3 segundos antes de reabrir...
timeout /t 3 >nul
echo.

call "%~dp0activar.bat"