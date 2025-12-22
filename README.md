# PET-7H24M 即時資料可視化系統

**目標平台**：LinuxArm64 (aarch64)

## 系統概述

PET-7H24M 即時資料可視化系統是一個基於 Python 的振動數據採集與可視化平台，用於從 **PET-7H24M**（TCP/IP）設備取得振動數據，並在瀏覽器中即時顯示所有資料點的連續曲線，同時自動進行 CSV 儲存。

本系統針對 **ARM64 架構的 Linux 系統**進行開發與優化，需要 ARM64 版本的 HSDAQ 函式庫。

本系統提供完整的 Web 介面，讓使用者可以透過瀏覽器操作，不需進入終端機，即可：
- 修改設定檔（`PET-7H24M.ini`、`csv.ini`、`sql.ini`）
- 配置通道開關（動態啟用/停用 AI0-AI3 通道）
- 輸入資料標籤（Label）
- 按下「開始讀取」即啟動採集與即時顯示
- 系統同時自動分檔儲存資料（根據 `csv.ini` 的秒數）
- 可選的 SQL 資料庫上傳功能（根據 `sql.ini` 設定）
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
- 多執行緒架構（5 個獨立執行緒：Flask、DAQ Reading、Collection、CSV Writer、SQL Writer）
- Queue 架構進行執行緒間通訊，確保資料採集與 Web 服務不互相干擾
- 降頻處理優化網頁顯示效能（降頻比例 25:1）
- 支援動態通道配置（可啟用/停用 AI0-AI3 通道）
- 高效能 CSV 寫入（128KB 緩衝區、批次寫入、定期刷新）
- 可選的 SQL 資料庫上傳功能（MySQL/MariaDB）

## 系統需求

### 平台需求
- **目標平台**：LinuxArm64 (aarch64)
- 本系統針對 ARM64 架構的 Linux 系統進行優化
- 需要 ARM64 版本的 HSDAQ 函式庫（libhsdaq.so）

### 硬體需求
- PET-7H24M 設備（透過 TCP/IP 連接）
- 網路連線
- ARM64 架構的處理器（例如：Raspberry Pi 4/5、Jetson 系列等）

### 軟體需求
- Python 3.9 或更高版本
- 支援的作業系統（ARM64 架構）：
  - DietPi（建議）
  - Debian-based Linux 發行版（ARM64）
  - Ubuntu（ARM64）
  - Raspberry Pi OS（64-bit）
- HSDAQ 函式庫（libhsdaq.so，ARM64 版本）

### Python 套件依賴
請參考 `src/requirements.txt` 檔案，主要依賴包括：
- `Flask>=3.1.2` - Web 伺服器
- `pymysql>=1.0.2` - SQL 資料庫連線（可選，用於 SQL 上傳功能）

## 安裝說明

### 1. 確認 HSDAQ 函式庫

**重要**：本系統需要 **ARM64 (aarch64)** 版本的 `libhsdaq.so` 函式庫。

確保 `libhsdaq.so` 函式庫已放置在以下路徑之一：
- `src/include/hsdaq/LinuxArm64/libhsdaq.so`（優先檢查）
- `docs/linux_python3_SDK_Demo/python_demo/PET-7H24M/LinuxArm64/ET7H24_AI_Buffer_Continue/libhsdaq.so`
- `docs/linux_python3_SDK_Demo/python_demo/PET-7H24M/LinuxArm64/ET7H24_N_Sample_float/libhsdaq.so`
- `/usr/local/lib/libhsdaq.so`
- `/usr/lib/libhsdaq.so`
- `./libhsdaq.so`

**注意**：如果使用 x86_64 或其他架構的函式庫，系統會顯示錯誤訊息並無法啟動。

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
   - 可以編輯 `PET-7H24M.ini`、`csv.ini` 和 `sql.ini`
   - 可以配置通道開關（啟用/停用 AI0-AI3）
   - 可以設定 SQL 資料庫連線（如果啟用 SQL 上傳）
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
[PET7H24M]
; 基本連線設定
device_ip = 192.168.255.1   # PET-7H24M 設備 IP 位址
device_port = 502           # Modbus 埠號（通常為 502）

; 取樣率設定（單位 Hz，建議值: 10000, 20000, 50000, 128000）
sample_rate = 20000

; 通道開關 (1=開啟, 0=關閉)
enable_ai0 = 1              # 啟用 AI0 通道
enable_ai1 = 1              # 啟用 AI1 通道
enable_ai2 = 1              # 啟用 AI2 通道
enable_ai3 = 1              # 啟用 AI3 通道

; 進階掃描參數
gain = 0                    # 增益（0 通常代表 +/- 10V 或 5V）
trigger_mode = 0            # 觸發模式（0 = Software Trigger）
target_count = 0            # 目標計數（0 = 連續採集模式）
data_trans_method = 0       # 資料傳輸方式（0 = Polling）
auto_run = 0                # 自動執行模式（0 = 關閉）
```

**通道配置說明**：
- 系統會根據 `enable_ai0`、`enable_ai1`、`enable_ai2`、`enable_ai3` 動態計算啟用的通道數
- 至少必須啟用一個通道（否則會報錯）
- 通道數會自動計算，例如：啟用 AI0 和 AI1 → 通道數 = 2

#### csv.ini
```ini
[DumpUnit]
second = 60                 # 每個 CSV 檔案的資料時間長度（秒）
```

#### sql.ini
```ini
[SQLServer]
enabled = false             # 是否啟用 SQL 上傳功能
host = localhost            # SQL 伺服器位址
port = 3306                 # SQL 伺服器埠號
user = root                 # SQL 使用者名稱
password =                  # SQL 密碼
database = pet7h24m        # 資料庫名稱

[DumpUnit]
second = 600                # SQL 上傳間隔（秒）
```

**分檔邏輯說明**：
- CSV 分檔：系統會根據 `sample_rate × channels × second` 計算每個檔案應包含的資料點數
- 當累積的資料點數達到目標值時，自動建立新檔案
- 例如：取樣率 20000 Hz，2 通道，60 秒 → 每個檔案約 2,400,000 個資料點
- SQL 上傳：根據 `sql.ini` 中的 `DumpUnit.second` 設定上傳間隔

### 輸出檔案

CSV 檔案會儲存在 `output/PET-7H24M/` 目錄下，檔案命名格式：
```
YYYYMMDDHHMMSS_<Label>_001.csv
YYYYMMDDHHMMSS_<Label>_002.csv
...
```

每個 CSV 檔案包含：
- `Timestamp` - 時間戳記（格式：YYYY-MM-DD HH:MM:SS.ffffff，包含微秒精度）
- `Channel_1` - 通道 1 資料（對應第一個啟用的通道，例如 AI0）
- `Channel_2` - 通道 2 資料（對應第二個啟用的通道，例如 AI1）
- ...（根據啟用的通道數動態調整）

**注意**：通道編號對應啟用的通道順序，例如：
- 如果只啟用 AI0 和 AI2，則 Channel_1 = AI0，Channel_2 = AI2
- 如果啟用 AI0、AI1、AI2、AI3，則 Channel_1 = AI0，Channel_2 = AI1，Channel_3 = AI2，Channel_4 = AI3

## 檔案架構

```
ICP-DAS_PET-7H24M_Python_Visualization_Unit/
│
├── API/
│   ├── PET-7H24M.ini      # PET-7H24M 設備設定檔（連線、通道、取樣率等）
│   ├── csv.ini            # CSV 分檔設定檔
│   └── sql.ini            # SQL 資料庫上傳設定檔（可選）
│
├── output/
│   └── PET-7H24M/         # CSV 輸出目錄
│       └── YYYYMMDDHHMMSS_<Label>/
│           ├── YYYYMMDDHHMMSS_<Label>_001.csv
│           ├── YYYYMMDDHHMMSS_<Label>_002.csv
│           └── .sql_temp/  # SQL 暫存檔案目錄（如果啟用 SQL）
│
├── src/
│   ├── pet7h24m.py        # PET-7H24M 核心模組（TCP/IP 通訊，使用 HSDAQ 函式庫）
│   ├── csv_writer.py      # CSV 寫入器模組（高效能批次寫入）
│   ├── sql_uploader.py    # SQL 上傳器模組（MySQL/MariaDB）
│   ├── logger.py          # 統一日誌系統模組
│   ├── main.py            # 主控制程式（Web 介面，多執行緒架構）
│   ├── requirements.txt   # Python 依賴套件列表
│   └── templates/         # HTML 模板目錄
│       ├── index.html     # 主頁模板（即時圖表）
│       ├── config.html    # 設定檔管理頁面模板
│       └── files.html     # 檔案瀏覽頁面模板
│
├── docs/
│   └── ICP-DAS_PET-7H24M-SelfMade/
│       └── services/
│           └── daq/
│               └── include/
│                   └── hsdaq/
│                       └── libhsdaq.so  # HSDAQ 函式庫
│
├── deploy.sh              # 部署腳本
├── run.sh                 # 啟動腳本
└── README.md              # 本文件
```

## API 路由說明

| 路由 | 方法 | 功能說明 |
|------|------|----------|
| `/` | GET | 主頁，顯示設定表單、Label 輸入、開始/停止按鈕與折線圖 |
| `/data` | GET | 回傳目前最新資料 JSON 給前端（降頻後的資料） |
| `/status` | GET | 檢查資料收集狀態（用於前端狀態恢復） |
| `/sql_config` | GET | 取得 SQL 設定（從 sql.ini 檔案讀取） |
| `/config` | GET | 顯示設定檔編輯頁面（PET-7H24M.ini、csv.ini、sql.ini） |
| `/config` | POST | 儲存修改後的設定檔 |
| `/start` | POST | 啟動 DAQ、CSVWriter、SQLUploader 與即時顯示 |
| `/stop` | POST | 停止所有執行緒、安全關閉，並上傳剩餘資料 |
| `/files_page` | GET | 檔案瀏覽頁面 |
| `/files` | GET | 列出 output 目錄中的檔案和資料夾（查詢參數：path） |
| `/download` | GET | 下載檔案（查詢參數：path） |

**API 回應格式範例**：

`/data` 回應：
```json
{
  "success": true,
  "data": [1.23, 4.56, 7.89, ...],
  "counter": 123456,
  "sample_rate": 20000,
  "is_collecting": true,
  "start_time": "2025-01-15T10:30:00"
}
```

`/start` 請求格式：
```json
{
  "label": "test_001",
  "sql_enabled": false,
  "sql_host": "localhost",
  "sql_port": "3306",
  "sql_user": "root",
  "sql_password": "",
  "sql_database": "pet7h24m"
}
```

## 故障排除

### 常見問題

#### 1. 無法連接設備
**症狀**：啟動後無法讀取資料

**解決方法**：
- 檢查 IP 位址是否正確（`PET-7H24M.ini` 中的 `device_ip`）
- 檢查埠號是否正確（`PET-7H24M.ini` 中的 `device_port`，通常為 502）
- 確認設備已正確連接網路
- 檢查防火牆是否允許連接設備的 IP 和埠
- 使用 `ping` 確認設備是否可達
- 確認至少啟用一個通道（`enable_ai0`、`enable_ai1`、`enable_ai2`、`enable_ai3` 至少一個為 1）

#### 2. 找不到 libhsdaq.so 或架構不匹配
**症狀**：啟動時顯示「無法找到 libhsdaq.so 函式庫」或「函式庫架構不匹配」

**解決方法**：
- 確認函式庫檔案已放置在正確路徑
- 檢查檔案權限（應可讀取）
- **確認函式庫為 ARM64 (aarch64) 版本**（本系統僅支援 ARM64）
- 使用 `file libhsdaq.so` 命令檢查函式庫架構
- 如果顯示 "ELF 64-bit LSB shared object, x86-64"，表示是 x86_64 版本，需要 ARM64 版本
- 從 ICP-DAS 官方取得 ARM64 版本的 libhsdaq.so

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
- 檢查設定檔中的取樣率是否正確（`sample_rate`）
- 確認通道開關設定（`enable_ai0`、`enable_ai1`、`enable_ai2`、`enable_ai3`）
- 確認至少啟用一個通道
- 檢查瀏覽器控制台是否有 JavaScript 錯誤
- 確認通道數與實際啟用的通道數匹配（系統會自動計算）

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
| **DAQ Reading Thread** | TCP/IP 資料讀取迴圈（pet7h24m.py） | daemon=True | `reading` 旗標 |
| **Collection Thread** | 資料處理與分發到各 Queue | daemon=True | `is_collecting` 旗標 |
| **CSV Writer Thread** | CSV 檔案寫入（批次處理） | daemon=True | `is_collecting` 旗標 |
| **SQL Writer Thread** | SQL 暫存檔案寫入與上傳 | daemon=True | `is_collecting` 旗標 |

### 資料流

```
PET-7H24M 設備
    ↓ (TCP/IP, Modbus RTU)
PET7H24M 類別 (pet7h24m.py)
    ↓ (data_queue)
Collection Thread (main.py)
    ├──→ update_realtime_data() → web_data_queue (降頻處理)
    │       ↓
    │   Flask /data API
    │       ↓
    │   前端 Chart.js (templates/index.html)
    │
    ├──→ csv_data_queue
    │       ↓
    │   CSV Writer Thread (csv_writer_loop)
    │       ↓
    │   CSV 檔案（高效能批次寫入，128KB 緩衝區）
    │
    └──→ sql_data_queue (如果啟用 SQL)
            ↓
        SQL Writer Thread (sql_writer_loop)
            ↓
        SQL 暫存檔案 → SQL 資料庫上傳
```

### Queue 架構

系統使用 Queue 架構進行執行緒間通訊，確保資料不遺失：

- **web_data_queue**：網頁顯示專用佇列（降頻後資料，maxsize=50000）
- **csv_data_queue**：CSV 寫入佇列（原始資料，maxsize=50000）
- **sql_data_queue**：SQL 上傳佇列（原始資料，maxsize=50000）

**降頻處理**：
- 網頁顯示使用降頻比例 25:1，減少前端資料量
- 例如：取樣率 20000 Hz，降頻後約 800 點/秒供前端顯示

## 開發說明

### 擴展功能

如需擴展系統功能，可以：

1. **修改前端介面**：編輯 `src/templates/index.html` 和 `src/templates/config.html` 模板
2. **調整圖表設定**：在 `src/templates/index.html` 中修改 Chart.js 的配置選項
3. **新增 API 路由**：在 `src/main.py` 中新增路由處理函數
4. **自訂 CSV 格式**：修改 `src/csv_writer.py` 中的寫入邏輯

### 程式碼結構

- `pet7h24m.py`：負責 TCP/IP 通訊與資料讀取（使用 HSDAQ 函式庫）
  - 支援動態通道配置（通道遮罩）
  - 使用 Queue 進行資料傳遞
- `csv_writer.py`：負責 CSV 檔案的建立與寫入
  - 高效能批次寫入（128KB 緩衝區）
  - 定期刷新機制（每 1 秒）
  - 精確時間戳記（包含微秒精度）
- `sql_uploader.py`：負責 SQL 資料庫上傳（MySQL/MariaDB）
  - 動態建立資料表
  - 批次插入資料
  - 自動重連機制
- `logger.py`：統一日誌系統
  - 統一的日誌格式
  - 可關閉 Debug 訊息
- `main.py`：整合所有功能，提供 Web 介面（使用 Flask + templates）
  - 多執行緒架構（5 個執行緒）
  - Queue 架構進行執行緒間通訊
  - 降頻處理優化網頁顯示
- `templates/index.html`：主頁 HTML 模板（包含 Chart.js 圖表）
- `templates/config.html`：設定檔管理頁面模板
- `templates/files.html`：檔案瀏覽頁面模板

## 授權資訊

本專案為內部使用專案，請遵循相關使用規範。

## 聯絡資訊

如有問題或建議，請聯絡專案維護者。

---

**最後更新**：2025年12月
**版本**：5.0.0
**作者**：基於 ProWaveDAQ 系統改編

## 版本資訊

詳細的版本更新記錄請參考 [CHANGELOG.md](CHANGELOG.md)