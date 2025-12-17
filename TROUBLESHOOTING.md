# 故障排除指南

## 函式庫載入錯誤

### 錯誤：`invalid ELF header` 或 `wrong ELF class`

**問題描述**：
```
[Error] 無法載入 HSDAQ 函式庫: invalid ELF header
```

**原因**：
- 函式庫架構不匹配（例如：x86_64 函式庫在 ARM64 系統上）
- 函式庫檔案損壞或格式不正確
- 函式庫是 ar 歸檔檔案而非真正的共享庫

**解決方案**：

#### 方案 1：取得正確架構的函式庫（推薦）

1. **確認系統架構**：
   ```bash
   uname -m
   # 或
   python3 -c "import platform; print(platform.machine())"
   ```

2. **從 ICP-DAS 官方取得對應架構的函式庫**：
   - ARM64 (aarch64) 系統需要 ARM64 版本的 `libhsdaq.so`
   - x86_64 系統需要 x86_64 版本的 `libhsdaq.so`

3. **放置函式庫**：
   將正確版本的 `libhsdaq.so` 放置在以下路徑之一：
   - `src/include/hsdaq/libhsdaq.so`（優先）
   - `docs/ICP-DAS_PET-7H24M-SelfMade/services/daq/include/hsdaq/libhsdaq.so`
   - `/usr/local/lib/libhsdaq.so`
   - `/usr/lib/libhsdaq.so`

#### 方案 2：使用靜態庫重新編譯

如果只有靜態庫（`libhsdaq.a`），需要重新編譯為共享庫：

```bash
# 1. 建立臨時目錄
mkdir -p /tmp/hsdaq_build
cd /tmp/hsdaq_build

# 2. 從 ar 歸檔中提取目標檔案
ar x /path/to/libhsdaq.a

# 3. 使用 gcc 重新編譯為共享庫（ARM64）
gcc -shared -fPIC -o libhsdaq.so *.o -lm

# 4. 複製到專案目錄
cp libhsdaq.so /root/ICP-DAS_PET-7H24M_Python_Visualization_Unit/src/include/hsdaq/
```

**注意**：此方法需要目標檔案與系統架構匹配。如果目標檔案是 x86_64，仍無法在 ARM64 系統上使用。

#### 方案 3：聯繫 ICP-DAS 技術支援

如果無法取得正確版本的函式庫，請聯繫 ICP-DAS 技術支援：
- 提供系統架構資訊（`uname -m`）
- 說明需要 ARM64 版本的 HSDAQ 函式庫
- 提供產品型號：PET-7H24M

### 檢查函式庫格式

**檢查檔案類型**：
```bash
# 檢查是否是 ar 歸檔
head -c 8 /path/to/libhsdaq.so
# 如果是 ar 歸檔，會顯示：!<arch>

# 檢查 ELF 檔案架構
readelf -h /path/to/libhsdaq.so | grep Machine
# 應該顯示：Machine: AArch64 (ARM64) 或 Machine: Advanced Micro Devices X86-64
```

**驗證函式庫**：
```bash
# 嘗試載入函式庫（Python）
python3 -c "from ctypes import CDLL; dll = CDLL('/path/to/libhsdaq.so'); print('成功')"
```

## 其他常見問題

### 無法連接設備

**檢查項目**：
1. IP 位址是否正確（檢查 `API/PET-7H24M.ini`）
2. 網路連線是否正常（`ping <設備IP>`）
3. 防火牆是否允許連接（埠 9999, 10010）
4. 設備是否正常運作

### Web 介面無法開啟

**檢查項目**：
1. 程式是否正在執行
2. 埠 8080 是否被佔用：`netstat -tuln | grep 8080`
3. 防火牆是否允許 8080 埠

### 資料讀取錯誤

**檢查項目**：
1. 設定檔中的通道數和取樣率是否正確
2. 設備是否支援設定的參數
3. 查看終端機的錯誤訊息

