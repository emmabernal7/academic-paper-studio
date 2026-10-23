@echo off
title Academic Paper Studio - Iniciar Servidor
color 0B
cls
echo ======================================================================
echo           ACADEMIC PAPER STUDIO - DESCARGADOR DE PAPERS & BIBTEX
echo ======================================================================
echo.
echo  Iniciando el servidor local de descargas...
echo  URL: http://localhost:8765
echo.

:: Abrir navegador predeterminado tras 2 segundos
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8765"

:: Ejecutar servidor Python
python web_downloader\app.py

pause
