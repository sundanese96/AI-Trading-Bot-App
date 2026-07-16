#!/bin/bash
# Script to run advanced GPU ML model training
if [ -f "./venv/bin/python" ]; then
    PYTHON_PATH="./venv/bin/python"
else
    PYTHON_PATH="/media/sun/DATA/PythonEnv/ComfyUI/venv/bin/python"
fi

echo "=== KriptoSakti Advanced ML Training Engine ==="
echo "Model Options: xgboost, catboost, lightgbm, pytorch"
read -p "Enter Symbol (default: ETHUSDT): " SYMBOL
SYMBOL=${SYMBOL:-ETHUSDT}

read -p "Enter Model Type (default: xgboost): " MODEL_TYPE
MODEL_TYPE=${MODEL_TYPE:-xgboost}

read -p "Enter Epochs (default: 100): " EPOCHS
EPOCHS=${EPOCHS:-100}

read -p "Enter Learning Rate (default: 0.05): " LR
LR=${LR:-0.05}

JSON_PAYLOAD="{\"symbol\": \"$SYMBOL\", \"model_type\": \"$MODEL_TYPE\", \"learning_rate\": $LR, \"epochs\": $EPOCHS, \"features\": [\"ma10\", \"ma20\", \"rsi\", \"volume\"]}"

echo "Starting GPU/CPU Fallback training for $SYMBOL with $MODEL_TYPE ($EPOCHS epochs)..."
echo $JSON_PAYLOAD | $PYTHON_PATH server/train_gpu_models.py
