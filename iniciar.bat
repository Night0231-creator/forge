@echo off
setlocal
cd /d "%~dp0"
title Astronyx Mini Forge Studio V2.1.0
if exist "AstronyxMiniForgeStudio.exe" (
  start "" "%~dp0AstronyxMiniForgeStudio.exe"
  exit /b 0
)
if exist "dist\AstronyxMiniForgeStudio.exe" (
  start "" "%~dp0dist\AstronyxMiniForgeStudio.exe"
  exit /b 0
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0studio.py"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo [ERRO] Python nao encontrado e ainda nao existe .exe.
    echo Execute instalar.bat, ou compile em tools\build_windows.ps1
    pause
    exit /b 1
  )
  python "%~dp0studio.py"
)
if errorlevel 1 (
  echo [ERRO] Nao foi possivel iniciar. Verifique a instalacao.
  pause
)
