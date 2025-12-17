# PET-7H24M 即時資料可視化系統

## 系統概述

PET-7H24M 即時資料可視化系統是一個基於 Python 的振動數據採集與可視化平台，用於從 **PET-7H24M**（TCP/IP）設備取得振動數據，並在瀏覽器中即時顯示所有資料點的連續曲線，同時自動進行 CSV 儲存。

本系統提供完整的 Web 介面，讓使用者可以透過瀏覽器操作，不需進入終端機，即可：
- 修改設定檔（`PET-7H24M.ini`、`Master.ini`）
- 輸入資料標籤（Label）
- 按下「開始讀取」即啟動採集與即時顯示
- 系統同時自動分檔儲存資料（根據 `Master.ini` 的秒數）
- 按下「停止」即可安全結束

## 功能特性

### 核心功能
- **即時資料採集**：透過 TCP/IP 協議從 PET-7H24M 設備讀取振動數據
- **即時資料可視化**：使用 Chart.js 在瀏覽器中顯示多通道連續曲線圖
- **自動 CSV 儲存**：根據設定檔自動分檔儲存資料
- **Web 介面控制**：完整的瀏覽器操作介面，無需終端機
- **設定檔管理**：透過 Web 介面直接編輯 INI 設定檔

### 技術特性
- 使用 Flask 提供 Web 服務
- 使用 Chart.js 實現即時圖表（每 200ms 更新）
- 多執行緒架構，確保資料採集與 Web 服務不互相干擾
- 記憶體中資料傳遞，高效能即時處理
- 支援可配置的多通道資料顯示（預設 2 通道）

## 系統需求

### 硬體需求
- PET-7H24M 設備（透過 TCP/IP 連接）
- 網路連線
- 支援 Python 3.9+ 的系統（建議 DietPi 或其他 Debian-based 系統）

### 軟體需求
- Python 3.9 或更高版本
- 支援的作業系統：
  - DietPi（建議）
  - Debian-based Linux 發行版
  - Ubuntu
  - Raspberry Pi OS
- HSDAQ 函式庫（libhsdaq.so）

### Python 套件依賴
請參考 `src/requirements.txt` 檔案，主要依賴包括：
- `Flask>=3.1.2` - Web 伺服器

## 安裝說明

### 1. 確認 HSDAQ 函式庫

確保 `libhsdaq.so` 函式庫已放置在以下路徑之一：
- `docs/ICP-DAS_PET-7H24M-SelfMade/services/daq/include/hsdaq/libhsdaq.so`
- `/usr/local/lib/libhsdaq.so`
- `/usr/lib/libhsdaq.so`
- `./libhsdaq.so`

### 2. 簡易安裝指令

```bash
./deploy.sh
```

**注意**：`deploy.sh` 腳本在以下情況需要 `sudo` 權限：
- 系統未安裝 Python 3、pip3 或 venv 模組時（需要安裝系統套件）

如果系統已安裝 Python 環境，則不需要 `sudo`。

若需要 `sudo`，請執行：
```bash
sudo ./deploy.sh
```

### 3. 手動安裝

```bash
# 建立虛擬環境
python3 -m venv venv

# 啟動虛擬環境
source venv/bin/activate

# 安裝依賴套件
pip install -r src/requirements.txt
```

## 使用說明

### 啟動系統

執行主程式：
```bash
./run.sh
```

或手動啟動：
```bash
source venv/bin/activate
python3 src/main.py
```

啟動成功後，您會看到類似以下的訊息：
```
============================================================
PET-7H24M Real-time Data Visualization System
============================================================
Web interface will be available at http://0.0.0.0:8080/
Press Ctrl+C to stop the server
============================================================
```

### 使用 Web 介面

1. **開啟瀏覽器**
   - 在本地機器：開啟 `http://localhost:8080/`
   - 在遠端機器：開啟 `http://<設備IP>:8080/`

2. **輸入資料標籤**
   - 在「資料標籤 (Label)」欄位輸入本次測量的標籤名稱
   - 例如：`test_001`、`vibration_20240101` 等

3. **開始資料收集**
   - 點擊「開始讀取」按鈕
   - 系統會自動：
     - 連接 PET-7H24M 設備
     - 開始讀取資料
     - 即時顯示資料曲線
     - 自動儲存 CSV 檔案

4. **查看即時資料**
   - 即時曲線圖會自動更新（每 200ms）
   - 可以同時查看多個通道的資料
   - 資料點數會即時顯示

5. **停止資料收集**
   - 點擊「停止讀取」按鈕
   - 系統會安全地停止採集並關閉連線

6. **管理設定檔**
   - 點擊「設定檔管理」連結
   - 可以編輯 `PET-7H24M.ini` 和 `Master.ini`
   - 修改後點擊「儲存設定檔」

7. **瀏覽和下載檔案**
   - 點擊「檔案瀏覽」連結
   - 可以瀏覽 `output/PET-7H24M/` 目錄中的所有資料夾和檔案
   - 點擊資料夾名稱或「進入」按鈕可以進入資料夾
   - 點擊「下載」按鈕可以下載 CSV 檔案
   - 使用麵包屑導航可以返回上層目錄

### 設定檔說明

#### PET-7H24M.ini
```ini
[PET-7H24M]
ipAddress = 192.168.9.40    # PET-7H24M 設備 IP 位址
channelCount = 2            # 通道數
sampleRate = 12800          # 取樣率（Hz）
gain = 0                    # 增益
triggerMode = 0             # 觸發模式
targetCount = 0             # 目標計數（0 = 連續採集）
dataTransMethod = 0         # 資料傳輸方式
autoRun = 0                 # 自動執行模式
```

#### Master.ini
```ini
[SaveUnit]
second = 5                   # 每個 CSV 檔案的資料時間長度（秒）
```

**分檔邏輯說明**：
- 系統會根據 `sampleRate × channels × second` 計算每個檔案應包含的資料點數
- 當累積的資料點數達到目標值時，自動建立新檔案
- 例如：取樣率 12800 Hz，2 通道，5 秒 → 每個檔案約 128,000 個資料點

### 輸出檔案

CSV 檔案會儲存在 `output/PET-7H24M/` 目錄下，檔案命名格式：
```
YYYYMMDDHHMMSS_<Label>_001.csv
YYYYMMDDHHMMSS_<Label>_002.csv
...
```

每個 CSV 檔案包含：
- `Timestamp` - 時間戳記
- `Channel_1` - 通道 1 資料
- `Channel_2` - 通道 2 資料
- ...（根據通道數動態調整）

## 檔案架構

```
ICP-DAS_PET-7H24M_Python_Visualization_Unit/
│
├── API/
│   ├── PET-7H24M.ini      # PET-7H24M 設備設定檔
│   └── Master.ini          # 儲存設定檔
│
├── output/
│   └── PET-7H24M/         # CSV 輸出目錄
│       └── YYYYMMDDHHMMSS_<Label>_*.csv
│
├── src/
│   ├── pet7h24m.py         # PET-7H24M 核心模組（TCP/IP 通訊）
│   ├── csv_writer.py       # CSV 寫入器模組
│   ├── main.py             # 主控制程式（Web 介面）
│   ├── requirements.txt    # Python 依賴套件列表
│   └── templates/          # HTML 模板目錄
│       ├── index.html      # 主頁模板
│       ├── config.html     # 設定檔管理頁面模板
│       └── files.html      # 檔案瀏覽頁面模板
│
├── docs/
│   └── ICP-DAS_PET-7H24M-SelfMade/
│       └── services/
│           └── daq/
│               └── include/
│                   └── hsdaq/
│                       └── libhsdaq.so  # HSDAQ 函式庫
│
├── deploy.sh               # 部署腳本
├── run.sh                  # 啟動腳本
└── README.md               # 本文件
```

## API 路由說明

| 路由 | 方法 | 功能說明 |
|------|------|----------|
| `/` | GET | 主頁，顯示設定表單、Label 輸入、開始/停止按鈕與折線圖 |
| `/data` | GET | 回傳目前最新資料 JSON 給前端 |
| `/status` | GET | 檢查資料收集狀態 |
| `/config` | GET | 顯示設定檔編輯頁面 |
| `/config` | POST | 儲存修改後的設定檔 |
| `/start` | POST | 啟動 DAQ、CSVWriter 與即時顯示 |
| `/stop` | POST | 停止所有執行緒、安全關閉 |
| `/files_page` | GET | 檔案瀏覽頁面 |
| `/files` | GET | 列出 output 目錄中的檔案和資料夾（查詢參數：path） |
| `/download` | GET | 下載檔案（查詢參數：path） |

## 故障排除

### 常見問題

#### 1. 無法連接設備
**症狀**：啟動後無法讀取資料

**解決方法**：
- 檢查 IP 位址是否正確（`PET-7H24M.ini` 中的 `ipAddress`）
- 確認設備已正確連接網路
- 檢查防火牆是否允許連接設備的 IP 和埠（9999, 10010）
- 使用 `ping` 確認設備是否可達

#### 2. 找不到 libhsdaq.so
**症狀**：啟動時顯示「無法找到 libhsdaq.so 函式庫」

**解決方法**：
- 確認函式庫檔案已放置在正確路徑
- 檢查檔案權限（應可讀取）
- 確認函式庫版本與系統架構相容

#### 3. Web 介面無法開啟
**症狀**：無法在瀏覽器中開啟網頁

**解決方法**：
- 確認防火牆允許 8080 埠
- 檢查是否有其他程式佔用 8080 埠
- 確認 Python 程式正在執行
- 檢查系統日誌是否有錯誤訊息

#### 4. 資料顯示不正確
**症狀**：圖表顯示異常或資料點不正確

**解決方法**：
- 檢查設定檔中的取樣率和通道數是否正確
- 確認通道數設定與設備匹配
- 檢查瀏覽器控制台是否有 JavaScript 錯誤

#### 5. CSV 檔案未產生
**症狀**：資料收集正常但沒有 CSV 檔案

**解決方法**：
- 檢查 `output/PET-7H24M/` 目錄是否有寫入權限
- 確認 Label 已正確輸入
- 檢查磁碟空間是否充足

## 技術架構

### 執行緒設計

| 執行緒 | 功能 | 類型 | 狀態管理 |
|--------|------|------|----------|
| **主執行緒** | 控制流程、等待中斷 | 主執行緒 | - |
| **Flask Thread** | 處理 HTTP 請求 | daemon=True | 主程式結束時自動終止 |
| **Reading Thread** (PETAR400) | TCP/IP 資料讀取迴圈 | daemon=True | `reading` 旗標 |
| **Collection Thread** (main.py) | 資料處理與分發 | daemon=True | `is_collecting` 旗標 |

### 資料流

```
PET-7H24M 設備
    ↓ (TCP/IP)
PETAR400 類別 (pet7h24m.py)
    ↓ (資料佇列)
主程式 (main.py)
    ├──→ 即時顯示 (記憶體變數)
    │       ↓
    │   Flask /data API
    │       ↓
    │   前端 Chart.js (templates/index.html)
    │
    └──→ CSV 儲存 (csv_writer.py)
            ↓
        CSV 檔案
```

## 開發說明

### 擴展功能

如需擴展系統功能，可以：

1. **修改前端介面**：編輯 `src/templates/index.html` 和 `src/templates/config.html` 模板
2. **調整圖表設定**：在 `src/templates/index.html` 中修改 Chart.js 的配置選項
3. **新增 API 路由**：在 `src/main.py` 中新增路由處理函數
4. **自訂 CSV 格式**：修改 `src/csv_writer.py` 中的寫入邏輯

### 程式碼結構

- `pet7h24m.py`：負責 TCP/IP 通訊與資料讀取（使用 HSDAQ 函式庫）
- `csv_writer.py`：負責 CSV 檔案的建立與寫入
- `main.py`：整合所有功能，提供 Web 介面（使用 Flask + templates）
- `templates/index.html`：主頁 HTML 模板（包含 Chart.js 圖表）
- `templates/config.html`：設定檔管理頁面模板
- `templates/files.html`：檔案瀏覽頁面模板

## 授權資訊

本專案為內部使用專案，請遵循相關使用規範。

## 聯絡資訊

如有問題或建議，請聯絡專案維護者。

---

**最後更新**：2025年1月
**作者**：基於 ProWaveDAQ 系統改編
