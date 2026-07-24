@echo off
REM ============================================================
REM  traer-cambios.bat  -  Git pull (solo lectura, no push)
REM  Trae los ultimos cambios del repositorio remoto.
REM ============================================================
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo [+] Trayendo cambios del repositorio...
echo.

git fetch origin
if errorlevel 1 (
    echo [!] Error al hacer fetch. Revisa tu conexion o las credenciales.
    pause
    exit /b 1
)

git pull origin main
if errorlevel 1 (
    echo [!] Error al hacer pull. Quizas hay cambios locales que conflitan.
    echo     Revisa con: git status
    pause
    exit /b 1
)

echo.
echo [+] Cambios traidos correctamente.
echo.

REM Si hay requirements.txt modificado, avisar que reinstale
git diff HEAD@{1} --quiet -- requirements.txt 2>nul
if errorlevel 1 (
    echo [!] requirements.txt cambio. Ejecuta 'activar.bat' para reinstalar dependencias.
)

pause