#!/bin/bash
# Script untuk menjalankan aplikasi di background VPS agar tidak mati saat SSH terputus

LOG_FILE="vps_app.log"

echo "=== Memulai AI Trading Bot di Background (VPS Mode) ==="

# Offload ke nohup
nohup ./run_project.sh > "$LOG_FILE" 2>&1 &
PID=$!

echo "✅ Aplikasi berhasil dijalankan di background dengan PID: $PID"
echo "📄 Log aplikasi ditulis ke: $LOG_FILE"
echo ""
echo "🔹 Untuk memantau log secara realtime, jalankan:"
echo "   tail -f $LOG_FILE"
echo ""
echo "🔹 Untuk menghentikan aplikasi, jalankan:"
echo "   kill -9 $PID  (atau: pkill -f 'backend.main')"
echo "========================================================"
