@echo off
title KriptoSakti Advanced ML Training Engine
echo === KriptoSakti Advanced ML Training Engine ===
set /p SYMBOL="Enter Symbol (default: ETHUSDT): "
if "%SYMBOL%"=="" set SYMBOL=ETHUSDT

set /p MODEL_TYPE="Enter Model Type (xgboost/catboost/lightgbm/pytorch, default: xgboost): "
if "%MODEL_TYPE%"=="" set MODEL_TYPE=xgboost

set /p EPOCHS="Enter Epochs (default: 100): "
if "%EPOCHS%"=="" set EPOCHS=100

set /p LR="Enter Learning Rate (default: 0.05): "
if "%LR%"=="" set LR=0.05

rem Path virtual env
set PYTHON_EXE=\\wsl$\Ubuntu\media\sun\DATA\PythonEnv\ComfyUI\venv\bin\python.exe
if not exist %PYTHON_EXE% set PYTHON_EXE=python

echo Sending payload to Python training script...
(echo {"symbol": "%SYMBOL%", "model_type": "%MODEL_TYPE%", "learning_rate": %LR%, "epochs": %EPOCHS%, "features": ["ma10", "ma20", "rsi", "volume"]}) | %PYTHON_EXE% server/train_gpu_models.py

pause
