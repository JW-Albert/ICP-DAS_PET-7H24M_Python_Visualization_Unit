# 版本更新記錄

本文檔記錄 PET-7H24M 即時資料可視化系統的所有版本更新歷史。

**目標平台**：LinuxArm64 (aarch64)

---

## Version 5.0.0 (2025-12)

### 新增功能
- **前端選項控制**：使用者可在前端選擇是否啟用 CSV 儲存或 SQL 上傳
  - 新增「儲存 CSV 檔案」checkbox（預設啟用）
  - 新增「上傳 SQL 資料庫」checkbox（預設停用）
  - 至少需選擇一個儲存選項
- **動態通道配置**：支援透過設定檔動態配置啟用的通道
  - 使用通道遮罩（Channel Bitmask）控制 AI0-AI3 通道
  - 系統自動計算啟用的通道數
  - 支援任意通道組合（例如：只啟用 AI0 和 AI2）

### 改進
- **設定檔結構優化**：
  - PET-7H24M.ini 區段名稱從 `PET-7H24M` 改為 `PET7H24M`
  - 參數命名從 camelCase 改為 snake_case
  - 新增 `device_ip` 和 `device_port` 參數
  - 新增 `enable_ai0`、`enable_ai1`、`enable_ai2`、`enable_ai3` 通道開關
- **CSV 和 SQL 分離**：
  - 將 Master.ini 拆分為 csv.ini 和 sql.ini
  - CSV 分檔間隔從 csv.ini 讀取
  - SQL 上傳間隔從 sql.ini 讀取
- **條件初始化**：
  - 僅在啟用 CSV 時初始化 CSV Writer
  - 僅在啟用 SQL 時初始化 SQL Uploader
  - 優化資源使用，避免不必要的初始化

### 技術改進
- 改進錯誤處理和驗證邏輯
- 優化狀態訊息顯示（根據啟用的功能顯示對應資訊）
- 改進目錄建立邏輯（僅在需要時建立輸出目錄）

---

## Version 4.0.0 (2025-01)

### 重大更新
- **Queue 架構**：採用 Queue 架構進行執行緒間通訊
  - `web_data_queue`：網頁顯示專用佇列（降頻後資料，maxsize=50000）
  - `csv_data_queue`：CSV 寫入佇列（原始資料，maxsize=50000）
  - `sql_data_queue`：SQL 上傳佇列（原始資料，maxsize=50000）

### 效能優化
- **降頻處理**：網頁顯示使用降頻比例 25:1，減少前端資料量
- **CSV 寫入優化**：
  - 128KB 緩衝區（buffering=131072）
  - 定期刷新機制（每 1 秒刷新一次，而非每次寫入都刷新）
  - 使用 `writerows` 批次寫入
  - 使用 `os.fsync()` 確保資料寫入物理硬碟
  - 時間戳記包含微秒精度

### 多執行緒架構
- 5 個獨立執行緒：
  - Flask Thread：處理 HTTP 請求
  - DAQ Reading Thread：TCP/IP 資料讀取迴圈
  - Collection Thread：資料處理與分發到各 Queue
  - CSV Writer Thread：CSV 檔案寫入（批次處理）
  - SQL Writer Thread：SQL 暫存檔案寫入與上傳

### 新增功能
- **SQL 資料庫上傳**：可選的 MySQL/MariaDB 上傳功能
  - 動態建立資料表（表名與 CSV 檔名對應）
  - 批次插入資料
  - 自動重連機制
  - 重試機制和資料保護（失敗時保留資料）

### 設定檔更新
- 設定檔結構更新（PET7H24M.ini、csv.ini、sql.ini）
- 參數命名從 camelCase 改為 snake_case

---

## 版本說明

- **主版本號（Major）**：重大架構變更或不相容的 API 變更
- **次版本號（Minor）**：新增功能，向後兼容
- **修訂版本號（Patch）**：錯誤修復和小幅改進

---

**最後更新**：2025年12月