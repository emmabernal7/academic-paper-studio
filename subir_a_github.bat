@echo off
title Subir Academic Paper Studio a GitHub
cd /d "%~dp0"

echo =======================================================
echo   Subiendo Academic Paper Studio a GitHub
echo   Repositorio: emmabernal7/academic-paper-studio
echo =======================================================
echo.

git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =======================================================
    echo   EXITO: Proyecto subido correctamente a GitHub!
    echo =======================================================
) else (
    echo.
    echo Ocurrio un inconveniente al subir. Revisa tus credenciales.
)

echo.
pause
