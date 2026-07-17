@echo off
title KriptoSakti Simulator Runner
echo === Memulai KriptoSakti Simulator Backend & Frontend ===

echo Memeriksa port 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    if not "%%a"=="" (
        echo Menghentikan proses dengan PID %%a di port 3000...
        taskkill /F /PID %%a >nul 2>&1
    )
)

call npm run build

set PYTHON_EXE=\\wsl$\Ubuntu\media\sun\DATA\PythonEnv\ComfyUI\venv\bin\python.exe
if not exist %PYTHON_EXE% set PYTHON_EXE=python

echo.
echo ==========================================================
echo  SERVER JALAN! SILAKAN BUKA UI DI URL BERIKUT:
echo  http://localhost:3000
echo ==========================================================
echo.

%PYTHON_EXE% -m backend.main
pause