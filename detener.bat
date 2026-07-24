@echo off
REM ============================================================
REM  detener.bat  -  Detiene la app de Book It Escuelas
REM  Busca y mata los procesos de python que corren app.py
REM ============================================================
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo [+] Buscando la aplicacion en ejecucion...

REM Buscar python corriendo escuela\app.py y matarlo
set "ENCONTRADO=0"
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" /fo list 2^>nul ^| findstr /i "PID"') do (
    set "ENCONTRADO=1"
)

REM Usar wmic para encontrar el proceso por linea de comando
for /f "tokens=*" %%i in ('wmic process where "name='python.exe' or name='python3.exe'" get processid^,commandline 2^>nul ^| findstr /i "app.py"') do (
    for /f "tokens=2" %%p in ("%%i") do (
        echo [+] Deteniendo proceso PID %%p...
        taskkill /pid %%p /f >nul 2>&1
        if errorlevel 1 (
            echo [!] No se pudo detener el proceso %%p.
        ) else (
            echo [+] Proceso %%p detenido.
        )
    )
)

REM Tambien buscar pythonw.exe (sin consola)
for /f "tokens=*" %%i in ('wmic process where "name='pythonw.exe'" get processid^,commandline 2^>nul ^| findstr /i "app.py"') do (
    for /f "tokens=2" %%p in ("%%i") do (
        echo [+] Deteniendo proceso PID %%p...
        taskkill /pid %%p /f >nul 2>&1
    )
)

echo [+] Listo. Aplicacion detenida.
timeout /t 2 >nul