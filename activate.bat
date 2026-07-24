@echo off
REM ============================================================
REM  activate.bat  -  alias de activar.bat (sin acento)
REM  Mismo comportamiento que activar.bat (corre la app). Existe
REM  para evitar confusion con venv\Scripts\activate.bat del
REM  Python venv, que solo parpadea si lo abres con doble-click.
REM  Siempre abre con activate.bat / activar.bat de la RAIZ.
REM ============================================================
call "%~dp0activar.bat"