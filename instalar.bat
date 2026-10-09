@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
title Astronyx Mini Forge Studio V2.0.1 - Instalar
if exist "dist\AstronyxMiniForgeStudio.exe" goto :ready
if exist "AstronyxMiniForgeStudio.exe" goto :ready
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import tkinter; print('Python e Tkinter prontos')"
  if not errorlevel 1 goto :ready
)
where python >nul 2>nul
if not errorlevel 1 (
  python -c "import tkinter; print('Python e Tkinter prontos')"
  if not errorlevel 1 goto :ready
)
echo [ERRO] Python 3.10+ necessario para executar esta versao do CODIGO-FONTE.
echo Para seus amigos, compile o .exe usando tools\build_windows.ps1 no Windows.
echo https://www.python.org/downloads/windows/
pause
exit /b 1
:ready
echo.
echo [OK] Aplicativo pronto para iniciar.
echo [INFO] Para converter miniaturas instale Blender e TaleSpire.
echo [INFO] TaleWeaverCmd vem com o TaleSpire pela Steam.
echo Execute iniciar.bat
pause
