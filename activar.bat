@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  activar.bat  -  Levanta la app de Book It Escuelas en Windows
REM  Crea el venv si no existe, instala dependencias, descarga
REM  chromium, y corre la app. Robusto: nunca se cierra solo.
REM ============================================================
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title Book It Escuelas - Activar

echo ============================================================
echo  Book It Escuelas - Activando aplicacion
echo ============================================================
echo.

REM --- 1) Detectar Python (probar python, py, python3) ---
set "PYCMD="
for %%c in (python py python3) do (
    where %%c >nul 2>&1
    if !errorlevel! == 0 (
        if not defined PYCMD set "PYCMD=%%c"
    )
)
if not defined PYCMD (
    echo [!] No se encontro Python. Instala Python 3.9+ desde https://www.python.org/downloads/
    echo     Asegurate de marcar "Add Python to PATH" al instalar.
    echo.
    pause
    exit /b 1
)
echo [+] Python encontrado: !PYCMD!
!PYCMD! --version
echo.

REM --- 2) Crear venv si no existe ---
if not exist "venv\Scripts\activate.bat" (
    echo [+] Creando entorno virtual (venv)...
    !PYCMD! -m venv venv
    if errorlevel 1 (
        echo [!] No se pudo crear el venv.
        echo     Prueba manualmente: !PYCMD! -m venv venv
        echo.
        pause
        exit /b 1
    )
    echo [+] venv creado.
    echo.
) else (
    echo [+] venv ya existe.
    echo.
)

REM --- 3) Activar venv ---
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [!] No se pudo activar el venv.
    pause
    exit /b 1
)

REM --- 4) Instalar dependencias ---
echo [+] Verificando/instalando dependencias...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [!] Error instalando dependencias. Revisa el mensaje arriba.
    echo.
    pause
    exit /b 1
)
echo [+] Dependencias OK.
echo.

REM --- 5) Descargar Chromium si falta ---
echo [+] Verificando navegador Chromium...
python -m playwright install chromium
if errorlevel 1 (
    echo [!] Error descargando Chromium. Reintenta o corre manualmente:
    echo     python -m playwright install chromium
    echo.
    pause
    exit /b 1
)
echo [+] Chromium OK.
echo.

REM --- 6) Verificar config.py ---
if not exist "config.py" (
    echo [!] FALTA config.py con tus credenciales (EMAIL, PASSWORD).
    echo     Copia config.example.py a config.py y completa los valores.
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo  Iniciando aplicacion... (login real contra Bookitech)
echo  Cuando termines, presiona Enter aqui para cerrar todo.
echo ============================================================
echo.

python escuela\app.py

echo.
echo [+] La aplicacion cerro. Presiona cualquier tecla para salir.
pause >nul
endlocal