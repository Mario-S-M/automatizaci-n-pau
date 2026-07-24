@echo off
REM ============================================================
REM  activar.bat  -  Levanta la app de Book It Escuelas
REM  Crea el venv si no existe, instala dependencias si hace
REM  falta, descarga chromium si falta, y corre la app.
REM ============================================================
chcp 65001 >nul 2>&1
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [+] Creando entorno virtual (venv)...
    python -m venv venv
    if errorlevel 1 (
        echo [!] No se pudo crear el venv. Revisa que Python este instalado.
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat

echo [+] Verificando dependencias...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [!] Error instalando dependencias.
    pause
    exit /b 1
)

echo [+] Verificando navegador Chromium...
python -m playwright install chromium
if errorlevel 1 (
    echo [!] Error descargando Chromium.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Iniciando aplicacion... (login real contra Bookitech)
echo  Presiona Enter en esta ventana cuando termines para cerrar.
echo ============================================================
echo.

python escuela\app.py

pause