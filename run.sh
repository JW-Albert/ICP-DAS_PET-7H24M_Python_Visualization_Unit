#!/bin/bash
# PET-7H24M Python 可視化系統啟動腳本

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 檢查虛擬環境是否存在
if [ ! -d "venv" ]; then
    echo "[Error] 虛擬環境不存在，請先執行 ./deploy.sh"
    exit 1
fi

# 啟動虛擬環境並執行主程式
source venv/bin/activate
python3 src/main.py

