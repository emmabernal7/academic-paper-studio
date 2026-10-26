@echo off
cd /d "%~dp0"
title Academic Paper Studio - Servidor Local
color 0B
cls
echo ======================================================================
echo      ACADEMIC PAPER STUDIO - DESCARGADOR DE PAPERS ^& LIBROS
echo ======================================================================
echo.
echo  Iniciando el servidor local y abriendo el navegador...
echo  URL: http://localhost:8765
echo.

:: Detectar interprete de Python (Miniconda, Anaconda o PATH del sistema)
set "PYTHON_EXE=python"
if exist "%USERPROFILE%\Miniconda3\python.exe" (
    set "PYTHON_EXE=%USERPROFILE%\Miniconda3\python.exe"
) else if exist "%USERPROFILE%\anaconda3\python.exe" (
    set "PYTHON_EXE=%USERPROFILE%\anaconda3\python.exe"
) else if exist "C:\Miniconda3\python.exe" (
    set "PYTHON_EXE=C:\Miniconda3\python.exe"
)

:: Ejecutar servidor Python y abrir el navegador automaticamente (--open)
"%PYTHON_EXE%" web_downloader\app.py --open

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] No se pudo iniciar el servidor con %PYTHON_EXE%.
    pause
)
