@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title Book It Escuelas - Detener

echo ============================================================
echo  Deteniendo aplicacion...
echo ============================================================
echo.

set "MATADOS=0"

REM Buscar ventanas CMD que esten corriendo activar.bat o app.py y matarlas.
REM Usamos tasklist + taskkill (compatible con Windows 10 y 11).

REM 1) Matar python.exe / pythonw.exe que tengan app.py en su linea de comando.
REM    wmic ya no existe en Win11, usamos powershell como fallback robusto.
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*app.py*' } | Select-Object -ExpandProperty ProcessId" 2^>nul') do (
    echo [+] Deteniendo proceso PID %%i (python app.py)...
    taskkill /pid %%i /f >nul 2>&1
    if !errorlevel! == 0 set "MATADOS=1"
)

REM 2) Tambien matar cualquier cmd.exe lanzando python escuela\app.py
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='cmd.exe'\" | Where-Object { $_.CommandLine -like '*escuela*' -or $_.CommandLine -like '*app.py*' } | Select-Object -ExpandProperty ProcessId" 2^>nul') do (
    echo [+] Deteniendo ventana CMD PID %%i...
    taskkill /pid %%i /f >nul 2>&1
)

if "%MATADOS%"=="0" (
    echo [+] No se encontro la aplicacion en ejecucion.
) else (
    echo [+] Aplicacion detenida.
)
echo.
timeout /t 2 >nul
endlocal