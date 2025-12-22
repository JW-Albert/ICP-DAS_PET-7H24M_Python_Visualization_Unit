#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PET-7H24M 設備通訊模組

此模組負責與 PET-7H24M 設備進行 TCP/IP 通訊，支援：
- TCP/IP 通訊（使用 HSDAQ 函式庫）
- 多通道配置（支援 AI0-AI3，可選通道）
- 動態通道遮罩（位元遮罩配置）
- 兩種讀取模式（AI Buffer Continue、N Sample）
- 高效能讀取（使用資料佇列緩衝）
- 執行緒安全（使用 queue.Queue 進行資料傳遞）
"""

import os
import time
import threading
import configparser
from typing import List, Optional
import sys
import queue
from ctypes import *

try:
    from logger import info, debug, warning, error
except ImportError:
    def info(m): print(f"[INFO] {m}")
    def debug(m): print(f"[DEBUG] {m}")
    def warning(m): print(f"[WARN] {m}")
    def error(m): print(f"[ERROR] {m}")

# 嘗試載入 HSDAQ 函式庫（Linux 版本）
# 參考官方範例：docs/linux_python3_SDK_Demo/python_demo/PET-7H24M/LinuxArm64/
HSDAQ_LIB_PATH = os.path.join(os.path.dirname(__file__), 'include', 'hsdaq', 'LinuxArm64', 'libhsdaq.so')

try:
    dll = CDLL(HSDAQ_LIB_PATH)
    info(f"成功載入 HSDAQ 函式庫: {HSDAQ_LIB_PATH}")
except Exception as e:
    error_msg = str(e)
    error(f"無法載入 HSDAQ 函式庫: {error_msg}")
    
    # 檢查是否是架構不匹配的問題
    if "invalid ELF header" in error_msg or "wrong ELF class" in error_msg:
        error("\n函式庫架構不匹配！")
        import platform
        error(f"系統架構：{platform.machine()}")
        error("請確認函式庫是 ARM64 (aarch64) 版本")
        error("當前找到的函式庫可能是 x86_64 或其他架構版本")
        info("\n可能的解決方案：")
        info("  1. 從 ICP-DAS 官方取得 ARM64 版本的 libhsdaq.so")
        info("  2. 或使用靜態庫 libhsdaq.a 重新編譯")
        info("  3. 或聯繫 ICP-DAS 技術支援取得正確版本的函式庫")
    
    sys.exit(1)


class PET7H24M:
    """PET-7H24M 設備通訊類別"""

    def __init__(self):
        """初始化 PET-7H24M 物件"""
        self.device_handle = None
        self.device_ip = "192.168.255.1"
        self.device_port = 502
        self.sample_rate = 20000
        self.channel_mask = 0
        self.active_channels = []  # 紀錄哪幾個通道被開啟，例如 [0, 2, 3]
        self.channels_count = 0
        # 保留舊的變數名稱以向後兼容
        self.ip_address = None  # 將在 init_devices 中設定
        self.channel_count = 0  # 將在 init_devices 中設定
        self.gain = 0
        self.trigger_mode = 0
        self.target_count = 0
        self.data_trans_method = 0
        self.auto_run = 0
        self.counter = 0
        self.reading = False
        self.reading_thread: Optional[threading.Thread] = None
        self.data_queue = queue.Queue(maxsize=1000)
        
        # 設定函式庫函數簽名
        self._setup_function_signatures()

    def _setup_function_signatures(self):
        """設定 ctypes 函數簽名"""
        # HS_Device_Create
        dll.HS_Device_Create.restype = c_void_p
        dll.HS_Device_Create.argtypes = [c_char_p]
        
        # HS_Device_Release
        dll.HS_Device_Release.restype = c_bool
        dll.HS_Device_Release.argtypes = [c_void_p]
        
        # HS_SetAIScanParam
        dll.HS_SetAIScanParam.restype = c_bool
        dll.HS_SetAIScanParam.argtypes = [c_void_p, c_short, c_short, c_short, c_long, c_ulong, c_short, c_short]
        
        # HS_GetAIScanParam（用於驗證參數設定）
        dll.HS_GetAIScanParam.restype = c_bool
        dll.HS_GetAIScanParam.argtypes = [c_void_p, POINTER(c_short), POINTER(c_short), POINTER(c_short), 
                                          POINTER(c_long), POINTER(c_ulong), POINTER(c_short), POINTER(c_short)]
        
        # HS_StartAIScan
        dll.HS_StartAIScan.restype = c_bool
        dll.HS_StartAIScan.argtypes = [c_void_p]
        
        # HS_StopAIScan
        dll.HS_StopAIScan.restype = c_bool
        dll.HS_StopAIScan.argtypes = [c_void_p]
        
        # HS_GetAIBufferStatus
        dll.HS_GetAIBufferStatus.restype = c_bool
        dll.HS_GetAIBufferStatus.argtypes = [c_void_p, POINTER(c_ushort), POINTER(c_ulong)]
        
        # HS_GetAIBuffer
        dll.HS_GetAIBuffer.restype = c_ulong
        dll.HS_GetAIBuffer.argtypes = [c_void_p, POINTER(c_float), c_ulong]
        
        # HS_GetLastError
        dll.HS_GetLastError.restype = c_ulong
        dll.HS_GetLastError.argtypes = []

    def init_devices(self, ini_path: str) -> None:
        """從設定檔讀取參數並初始化設備"""
        try:
            cfg = configparser.ConfigParser()
            cfg.read(ini_path, encoding="utf-8")

            # 1. 讀取連線資訊
            self.device_ip = cfg.get("PET7H24M", "device_ip", fallback="192.168.255.1")
            self.device_port = cfg.getint("PET7H24M", "device_port", fallback=502)
            
            # 向後兼容：保留 ip_address
            self.ip_address = self.device_ip
            
            # 2. 讀取取樣率 (PET-7H24M 必須是特定數值，如 10k, 20k...)
            self.sample_rate = cfg.getint("PET7H24M", "sample_rate", fallback=20000)

            # 3. 計算通道遮罩 (Channel Bitmask)
            # AI0=1, AI1=2, AI2=4, AI3=8
            self.channel_mask = 0
            self.active_channels = []  # 紀錄哪幾個通道被開啟，例如 [0, 2, 3]
            
            if cfg.getint("PET7H24M", "enable_ai0", fallback=1):
                self.channel_mask |= 1
                self.active_channels.append(0)
            if cfg.getint("PET7H24M", "enable_ai1", fallback=1):
                self.channel_mask |= 2
                self.active_channels.append(1)
            if cfg.getint("PET7H24M", "enable_ai2", fallback=1):
                self.channel_mask |= 4
                self.active_channels.append(2)
            if cfg.getint("PET7H24M", "enable_ai3", fallback=1):
                self.channel_mask |= 8
                self.active_channels.append(3)

            self.channels_count = len(self.active_channels)
            
            # 向後兼容：保留 channel_count
            self.channel_count = self.channels_count
            
            if self.channels_count == 0:
                raise ValueError("錯誤：至少必須啟用一個通道！")

            info(f"PET-7H24M 初始化完成: IP={self.device_ip}, Port={self.device_port}, Rate={self.sample_rate}Hz, Channels={self.active_channels} (Mask=0x{self.channel_mask:x})")

            # 4. 連線與設定 (呼叫 C 函式庫)
            # 步驟1：建立TCP/IP連線（參考官方範例）
            debug("正在建立 TCP/IP 連線...")
            try:
                # 連接字串格式：僅 IP 位址（參考官方範例）
                # 官方範例使用 IP 位址字串，不需要指定埠號
                self.device_handle = dll.HS_Device_Create(c_char_p(self.device_ip.encode('utf-8')))
                
                if self.device_handle is None:
                    error_code = dll.HS_GetLastError()
                    error(f"無法建立設備連線！錯誤碼: 0x{error_code:x}")
                    raise RuntimeError(f"無法建立設備連線，錯誤碼: 0x{error_code:x}")
                
                debug("TCP/IP 連線建立成功。")

            except Exception as e:
                error(f"建立 TCP/IP 連線時發生錯誤: {e}")
                raise

            # 步驟2：設定類比輸入掃描參數
            # 注意：HS_SetAIScanParam 的第一個參數是通道數，我們使用啟用的通道數
            debug("正在設定類比輸入掃描參數...")
            try:
                # 保留舊的參數（如果設定檔中有）
                self.gain = cfg.getint("PET7H24M", "gain", fallback=0)
                self.trigger_mode = cfg.getint("PET7H24M", "trigger_mode", fallback=0)
                self.target_count = cfg.getint("PET7H24M", "target_count", fallback=0)
                self.data_trans_method = cfg.getint("PET7H24M", "data_trans_method", fallback=0)
                self.auto_run = cfg.getint("PET7H24M", "auto_run", fallback=0)
                
                ret = dll.HS_SetAIScanParam(
                    self.device_handle,
                    c_short(self.channels_count),  # 使用啟用的通道數
                    c_short(self.gain),
                    c_short(self.trigger_mode),
                    c_long(self.sample_rate),
                    c_ulong(self.target_count),
                    c_short(self.data_trans_method),
                    c_short(self.auto_run)
                )
                
                if not ret:
                    error_code = dll.HS_GetLastError()
                    error(f"設定掃描參數失敗！錯誤碼: 0x{error_code:x}")
                    raise RuntimeError(f"設定掃描參數失敗，錯誤碼: 0x{error_code:x}")
                
                # 驗證參數設定（參考官方範例）
                chcnt = c_short()
                gain = c_short()
                triggermode = c_short()
                samplerate = c_long()
                targetcnt = c_ulong()
                datatransmethod = c_short()
                autorun = c_short()
                
                if dll.HS_GetAIScanParam(self.device_handle, byref(chcnt), byref(gain), byref(triggermode),
                                         byref(samplerate), byref(targetcnt), byref(datatransmethod), byref(autorun)):
                    debug(f"掃描參數設定成功並驗證:")
                    debug(f"  通道數: {chcnt.value}")
                    debug(f"  增益: {gain.value}")
                    debug(f"  觸發模式: {triggermode.value}")
                    debug(f"  取樣率: {samplerate.value} Hz")
                    debug(f"  目標計數: {targetcnt.value}")
                    debug(f"  資料傳輸方法: {datatransmethod.value}")
                    debug(f"  自動執行: {autorun.value}")
                else:
                    warning("無法驗證參數設定，但繼續執行")

            except Exception as e:
                error(f"設定掃描參數時發生錯誤: {e}")
                raise

        except Exception as e:
            error(f"初始化設備時發生錯誤: {e}")
            raise

    def start_reading(self) -> None:
        """開始讀取振動數據"""
        if self.reading:
            error("讀取已在進行中！")
            return

        if self.device_handle is None:
            error("設備未初始化！")
            return

        # 啟動掃描
        debug("正在啟動類比輸入掃描...")
        ret = dll.HS_StartAIScan(self.device_handle)
        if not ret:
            error_code = dll.HS_GetLastError()
            error(f"啟動掃描失敗！錯誤碼: 0x{error_code:x}")
            return

        self.reading = True
        self.reading_thread = threading.Thread(target=self._read_loop)
        self.reading_thread.daemon = True
        self.reading_thread.start()
        debug("讀取執行緒已啟動。")

    def stop_reading(self) -> None:
        """停止讀取振動數據並清理資源"""
        if self.reading:
            self.reading = False
            if self.reading_thread and self.reading_thread.is_alive():
                self.reading_thread.join()

        # 停止掃描
        if self.device_handle:
            try:
                dll.HS_StopAIScan(self.device_handle)
                debug("掃描已停止。")
            except Exception as e:
                error(f"停止掃描時發生錯誤: {e}")

        # 重置計數器和清空佇列
        self.counter = 0
        while not self.data_queue.empty():
            try:
                self.data_queue.get_nowait()
            except queue.Empty:
                break

        # 釋放設備連線
        if self.device_handle:
            try:
                dll.HS_Device_Release(self.device_handle)
                self.device_handle = None
                debug("設備連線已釋放。")
            except Exception as e:
                error(f"釋放設備連線時發生錯誤: {e}")

    def _read_loop(self) -> None:
        """讀取振動數據（主要讀取迴圈，在獨立執行緒中執行）"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        total_samples_read = 0  # 累計讀取的樣本數（用於 N Sample 模式）

        try:
            debug("讀取迴圈已啟動...")
            if self.target_count > 0:
                debug(f"N Sample 模式：目標樣本數 = {self.target_count}")
            else:
                debug("AI Buffer Continue 模式：持續讀取")
            
            while self.reading:
                try:
                    # 取得緩衝區狀態（參考官方範例）
                    buffer_status = c_ushort()
                    buffer_cnt = c_ulong()
                    
                    ret = dll.HS_GetAIBufferStatus(
                        self.device_handle,
                        byref(buffer_status),
                        byref(buffer_cnt)
                    )
                    
                    if not ret:
                        error_code = dll.HS_GetLastError()
                        error(f"取得緩衝區狀態失敗！錯誤碼: 0x{error_code:x}")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            error(f"連續 {max_consecutive_errors} 次錯誤，停止讀取")
                            break
                        time.sleep(0.1)
                        continue

                    # 檢查緩衝區狀態錯誤（參考官方範例）
                    status_value = buffer_status.value
                    if (status_value & 0x02) == 0x02:
                        error_code = dll.HS_GetLastError()
                        error(f"AI 緩衝區溢位！錯誤碼: 0x{error_code:x}")
                        dll.HS_StopAIScan(self.device_handle)
                        break
                    elif (status_value & 0x04) == 0x04:
                        error("AI 掃描已停止")
                        break
                    elif (status_value & 0x08) == 0x08:
                        error("其他錯誤")
                        break

                    # 決定是否讀取資料
                    should_read = False
                    
                    if self.target_count > 0:
                        # N Sample 模式：等待達到目標數量
                        if buffer_cnt.value >= self.target_count:
                            should_read = True
                            debug(f"達到目標樣本數 {self.target_count}，開始讀取")
                    else:
                        # AI Buffer Continue 模式：有資料就讀取
                        if buffer_cnt.value > 0:
                            should_read = True

                    if should_read:
                        # 計算實際讀取大小（確保是通道數的倍數）
                        # 在 N Sample 模式下，讀取目標數量；在 Continue 模式下，讀取所有可用資料
                        if self.target_count > 0:
                            read_count = min(buffer_cnt.value, self.target_count)
                        else:
                            read_count = buffer_cnt.value
                        
                        # 確保讀取數量是通道數的倍數
                        read_count = read_count - (read_count % self.channels_count)
                        
                        if read_count > 0:
                            # 建立浮點數陣列緩衝區（參考官方範例）
                            fdata_buffer = (c_float * read_count)()
                            
                            # 讀取資料
                            read_size = dll.HS_GetAIBuffer(
                                self.device_handle,
                                fdata_buffer,
                                read_count
                            )
                            
                            if read_size > 0:
                                # 轉換為 Python 列表
                                processed_data = [float(fdata_buffer[i]) for i in range(read_size)]
                                
                                # 將處理後的數據放入佇列
                                try:
                                    self.data_queue.put_nowait(processed_data)
                                except queue.Full:
                                    # 佇列滿了，移除最舊的數據
                                    try:
                                        self.data_queue.get_nowait()
                                        self.data_queue.put_nowait(processed_data)
                                    except queue.Empty:
                                        pass
                                
                                self.counter += 1
                                total_samples_read += read_size
                                consecutive_errors = 0
                                
                                # N Sample 模式：達到目標後停止
                                if self.target_count > 0 and total_samples_read >= self.target_count:
                                    debug(f"已讀取 {total_samples_read} 個樣本，達到目標 {self.target_count}，停止讀取")
                                    self.reading = False
                                    break
                            else:
                                warning("未讀取到資料")
                        else:
                            # 資料不足一個完整通道組，等待更多資料
                            time.sleep(0.001)  # 1ms
                    else:
                        # 尚未達到讀取條件，短暫休息
                        if self.target_count > 0:
                            # N Sample 模式：顯示進度（每 10% 更新一次，減少日誌輸出）
                            if buffer_cnt.value > 0:
                                progress = (buffer_cnt.value / self.target_count) * 100
                                # 只在進度達到 10% 的倍數時輸出，避免產生過多日誌
                                if int(progress) % 10 == 0:
                                    debug(f"等待資料中... 緩衝區: {buffer_cnt.value}/{self.target_count} ({progress:.1f}%)")
                        time.sleep(0.001)  # 1ms

                except Exception as e:
                    consecutive_errors += 1
                    error(f"讀取資料時發生錯誤: {e}")
                    if consecutive_errors >= max_consecutive_errors:
                        error(f"連續 {max_consecutive_errors} 次錯誤，停止讀取")
                        break
                    time.sleep(0.1)

        except Exception as e:
            error(f"讀取迴圈發生嚴重錯誤: {e}")
        finally:
            debug("讀取迴圈已結束。")

    def get_data(self) -> List[float]:
        """取得最新的振動數據（非阻塞式，從佇列中取出）"""
        try:
            return self.data_queue.get_nowait()
        except queue.Empty:
            return []

    def get_counter(self) -> int:
        """取得數據讀取次數"""
        return self.counter

    def reset_counter(self) -> None:
        """重置計數器"""
        self.counter = 0

    def get_sample_rate(self) -> int:
        """取得取樣率"""
        return self.sample_rate

    def get_channel_count(self) -> int:
        """取得通道數（向後兼容方法）"""
        return self.channels_count
    
    def get_active_channel_count(self) -> int:
        """取得目前啟用的通道總數"""
        return self.channels_count

    def __del__(self):
        """解構函數"""
        self.stop_reading()