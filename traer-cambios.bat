@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title Book It Escuelas - Traer cambios

echo ============================================================
echo  Trayendo cambios del repositorio (git pull, solo lectura)
echo ============================================================
echo.

where git >nul 2>&1
if errorlevel 1 (
    echo [!] Git no esta instalado o no esta en el PATH.
    echo     Descargalo de https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

echo [+] Haciendo fetch...
git fetch origin
if errorlevel 1 (
    echo [!] Error al hacer fetch. Revisa tu conexion o credenciales.
    echo.
    pause
    exit /b 1
)

echo.
echo [+] Haciendo pull de origin/main...
git pull origin main
if errorlevel 1 (
    echo.
    echo [!] Error al hacer pull. Quizas hay cambios locales que conflitan.
    echo     Revisa con:  git status
    echo.
    pause
    exit /b 1
)

echo.
echo [+] Cambios traidos correctamente.
echo.

REM Avisar si requirements.txt cambio en el ultimo pull
git diff HEAD~1 HEAD --quiet -- requirements.txt 2>nul
if errorlevel 1 (
    echo [!] requirements.txt cambio en este pull.
    echo     Ejecuta 'activar.bat' (o 'reiniciar.bat') para reinstalar dependencias.
    echo.
)

echo.
pause
endlocal