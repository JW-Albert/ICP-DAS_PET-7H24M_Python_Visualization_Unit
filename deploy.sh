#!/bin/bash
# PET-7H24M Python 可視化系統部署腳本

set -e

echo "============================================================"
echo "PET-7H24M Python 可視化系統部署腳本"
echo "============================================================"

# 取得腳本所在目錄
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 檢查 Python 3
if ! command -v python3 &> /dev/null; then
    echo "[Error] Python 3 未安裝，正在安裝..."
    if [ "$EUID" -ne 0 ]; then
        echo "[Error] 需要 sudo 權限來安裝 Python 3"
        exit 1
    fi
    apt-get update
    apt-get install -y python3 python3-pip python3-venv
fi

# 檢查 pip3
if ! command -v pip3 &> /dev/null; then
    echo "[Error] pip3 未安裝，正在安裝..."
    if [ "$EUID" -ne 0 ]; then
        echo "[Error] 需要 sudo 權限來安裝 pip3"
        exit 1
    fi
    apt-get install -y python3-pip
fi

# 檢查 venv 模組
if ! python3 -c "import venv" 2>/dev/null; then
    echo "[Error] venv 模組未安裝，正在安裝..."
    if [ "$EUID" -ne 0 ]; then
        echo "[Error] 需要 sudo 權限來安裝 venv 模組"
        exit 1
    fi
    apt-get install -y python3-venv
fi

# 建立虛擬環境（如果不存在）
if [ ! -d "venv" ]; then
    echo "[Info] 正在建立虛擬環境..."
    python3 -m venv venv
fi

# 啟動虛擬環境並安裝依賴
echo "[Info] 正在安裝 Python 依賴套件..."
source venv/bin/activate
pip install --upgrade pip
pip install -r src/requirements.txt

# 設定執行權限
echo "[Info] 正在設定執行權限..."
chmod +x src/main.py
chmod +x src/pet7h24m.py
chmod +x src/csv_writer.py

# 檢查 libhsdaq.so 是否存在
HSDAQ_LIB_PATH="docs/ICP-DAS_PET-7H24M-SelfMade/services/daq/include/hsdaq/libhsdaq.so"
if [ -f "$HSDAQ_LIB_PATH" ]; then
    echo "[Info] 找到 HSDAQ 函式庫: $HSDAQ_LIB_PATH"
else
    echo "[Warning] 未找到 HSDAQ 函式庫: $HSDAQ_LIB_PATH"
    echo "[Warning] 請確認函式庫已正確放置，或放置在以下路徑之一："
    echo "  - $HSDAQ_LIB_PATH"
    echo "  - /usr/local/lib/libhsdaq.so"
    echo "  - /usr/lib/libhsdaq.so"
    echo "  - ./libhsdaq.so"
fi

# 建立必要的目錄
echo "[Info] 正在建立必要的目錄..."
mkdir -p output/PET-7H24M
mkdir -p API
mkdir -p src/templates

# 檢查設定檔是否存在
if [ ! -f "API/PET-7H24M.ini" ]; then
    echo "[Warning] API/PET-7H24M.ini 不存在，將建立預設設定檔..."
    cat > API/PET-7H24M.ini << EOF
[PET-7H24M]
ipAddress = 192.168.9.40
channelCount = 2
sampleRate = 12800
gain = 0
triggerMode = 0
targetCount = 0
dataTransMethod = 0
autoRun = 0
EOF
fi

if [ ! -f "API/Master.ini" ]; then
    echo "[Warning] API/Master.ini 不存在，將建立預設設定檔..."
    cat > API/Master.ini << EOF
[SaveUnit]
second = 5
EOF
fi

echo ""
echo "============================================================"
echo "部署完成！"
echo "============================================================"
echo "啟動方式："
echo "  1. 使用 run.sh: ./run.sh"
echo "  2. 手動啟動: source venv/bin/activate && python3 src/main.py"
echo ""
echo "Web 介面將在以下網址可用："
echo "  http://localhost:8080/"
echo "  http://<設備IP>:8080/"
echo "============================================================"

