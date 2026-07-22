#!/bin/bash
echo "=== Memulai KriptoSakti Simulator Backend & Frontend ==="

# Kill any process currently using port 3000
if lsof -t -i:3000 >/dev/null 2>&1; then
    echo "Menghentikan proses yang sedang berjalan di port 3000..."
    kill -9 $(lsof -t -i:3000) 2>/dev/null || true
    
    # Wait until port 3000 is actually free (up to 5 seconds)
    for i in {1..10}; do
        if ! lsof -i:3000 >/dev/null 2>&1; then
            break
        fi
        sleep 0.5
    done
fi

npm run build

echo ""
echo "=========================================================="
echo " SERVER JALAN! SILAKAN BUKA UI DI URL BERIKUT:"
echo " http://localhost:3000"
echo "=========================================================="
echo ""

# Start FastAPI backend which also serves frontend static files from dist/ folder
if [ -f "./venv/bin/python" ]; then
    PYTHON_EXEC="./venv/bin/python"
elif [ -f "/media/sun/DATA/PythonEnv/ComfyUI/venv/bin/python" ]; then
    PYTHON_EXEC="/media/sun/DATA/PythonEnv/ComfyUI/venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_EXEC="python3"
else
    PYTHON_EXEC="python"
fi

PYTHONPATH="" $PYTHON_EXEC -m backend.main