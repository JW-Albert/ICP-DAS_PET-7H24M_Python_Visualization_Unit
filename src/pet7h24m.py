#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PET-7H24M Python版本
振動數據採集系統 - 使用TCP/IP通訊協議（HSDAQ函式庫）
"""

import os
import time
import threading
import configparser
from typing import List, Optional
import sys
import queue
from ctypes import *

# 嘗試載入 HSDAQ 函式庫（Linux 版本）
# 參考官方範例：docs/linux_python3_SDK_Demo/python_demo/PET-7H24M/LinuxArm64/
HSDAQ_LIB_PATH = None
# 可能的函式庫路徑
possible_paths = [
    os.path.join(os.path.dirname(__file__), 'include', 'hsdaq', 'libhsdaq.so'),  # 優先檢查 src/include/hsdaq/
    os.path.join(os.path.dirname(__file__), '..', 'docs', 'linux_python3_SDK_Demo', 'python_demo', 'PET-7H24M', 'LinuxArm64', 'ET7H24_AI_Buffer_Continue', 'libhsdaq.so'),  # 官方範例路徑
    os.path.join(os.path.dirname(__file__), '..', 'docs', 'linux_python3_SDK_Demo', 'python_demo', 'PET-7H24M', 'LinuxArm64', 'ET7H24_N_Sample_float', 'libhsdaq.so'),  # 官方範例路徑
    os.path.join(os.path.dirname(__file__), '..', 'docs', 'ICP-DAS_PET-7H24M-SelfMade', 'services', 'daq', 'include', 'hsdaq', 'libhsdaq.so'),
    '/usr/local/lib/libhsdaq.so',
    '/usr/lib/libhsdaq.so',
    './libhsdaq.so',  # 官方範例使用的相對路徑
    'libhsdaq.so',
    'include/hsdaq/libhsdaq.so'
]

for path in possible_paths:
    abs_path = os.path.abspath(path)
    if os.path.exists(abs_path):
        HSDAQ_LIB_PATH = abs_path
        break

if HSDAQ_LIB_PATH is None:
    print("[Error] 無法找到 libhsdaq.so 函式庫")
    print("[Error] 請確認函式庫已正確安裝或放置在以下路徑之一：")
    for path in possible_paths:
        print(f"  - {os.path.abspath(path)}")
    sys.exit(1)

try:
    dll = CDLL(HSDAQ_LIB_PATH)
    print(f"[Info] 成功載入 HSDAQ 函式庫: {HSDAQ_LIB_PATH}")
except Exception as e:
    error_msg = str(e)
    print(f"[Error] 無法載入 HSDAQ 函式庫: {error_msg}")
    
    # 檢查是否是架構不匹配的問題
    if "invalid ELF header" in error_msg or "wrong ELF class" in error_msg:
        print("\n[Error] 函式庫架構不匹配！")
        print("[Error] 系統架構：", end="")
        import platform
        print(platform.machine())
        print("[Error] 請確認函式庫是 ARM64 (aarch64) 版本")
        print("[Error] 當前找到的函式庫可能是 x86_64 或其他架構版本")
        print("\n[提示] 可能的解決方案：")
        print("  1. 從 ICP-DAS 官方取得 ARM64 版本的 libhsdaq.so")
        print("  2. 或使用靜態庫 libhsdaq.a 重新編譯")
        print("  3. 或聯繫 ICP-DAS 技術支援取得正確版本的函式庫")
    
    sys.exit(1)


class PET7H24M:
    """PET-7H24M振動數據採集類別"""

    def __init__(self):
        """初始化PET-7H24M物件"""
        self.device_handle = None
        self.ip_address = "192.168.9.40"
        self.channel_count = 2
        self.sample_rate = 12800
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
        """設定 ctypes 函數簽名（參考官方範例）"""
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

    def init_devices(self, filename: str) -> None:
        """從INI檔案初始化設備"""
        print("[Debug] 正在從 INI 檔案載入設定...")

        try:
            config = configparser.ConfigParser()
            config.read(filename, encoding='utf-8')

            # 讀取設定值
            self.ip_address = config.get('PET-7H24M', 'ipAddress', fallback='192.168.9.40')
            self.channel_count = config.getint('PET-7H24M', 'channelCount', fallback=2)
            self.sample_rate = config.getint('PET-7H24M', 'sampleRate', fallback=12800)
            self.gain = config.getint('PET-7H24M', 'gain', fallback=0)
            self.trigger_mode = config.getint('PET-7H24M', 'triggerMode', fallback=0)
            self.target_count = config.getint('PET-7H24M', 'targetCount', fallback=0)
            self.data_trans_method = config.getint('PET-7H24M', 'dataTransMethod', fallback=0)
            self.auto_run = config.getint('PET-7H24M', 'autoRun', fallback=0)

            print(f"[Debug] 從 INI 檔案載入的設定:\n"
                  f"IP 位址: {self.ip_address}\n"
                  f"通道數: {self.channel_count}\n"
                  f"取樣率: {self.sample_rate} Hz\n"
                  f"增益: {self.gain}\n"
                  f"觸發模式: {self.trigger_mode}\n"
                  f"目標計數: {self.target_count}")

        except Exception as e:
            print(f"[Error] 解析 INI 檔案時發生錯誤: {e}")
            return

        # 步驟1：建立TCP/IP連線（參考官方範例）
        print("[Debug] 正在建立 TCP/IP 連線...")
        try:
            # 連接字串格式：僅 IP 位址（參考官方範例）
            # 官方範例使用 IP 位址字串，不需要指定埠號
            self.device_handle = dll.HS_Device_Create(c_char_p(self.ip_address.encode('utf-8')))
            
            if self.device_handle is None:
                error_code = dll.HS_GetLastError()
                print(f"[Error] 無法建立設備連線！錯誤碼: 0x{error_code:x}")
                return
            
            print("[Debug] TCP/IP 連線建立成功。")

        except Exception as e:
            print(f"[Error] 建立 TCP/IP 連線時發生錯誤: {e}")
            return

        # 步驟2：設定類比輸入掃描參數
        print("[Debug] 正在設定類比輸入掃描參數...")
        try:
            ret = dll.HS_SetAIScanParam(
                self.device_handle,
                c_short(self.channel_count),
                c_short(self.gain),
                c_short(self.trigger_mode),
                c_long(self.sample_rate),
                c_ulong(self.target_count),
                c_short(self.data_trans_method),
                c_short(self.auto_run)
            )
            
            if not ret:
                error_code = dll.HS_GetLastError()
                print(f"[Error] 設定掃描參數失敗！錯誤碼: 0x{error_code:x}")
                return
            
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
                print(f"[Debug] 掃描參數設定成功並驗證:")
                print(f"  通道數: {chcnt.value}")
                print(f"  增益: {gain.value}")
                print(f"  觸發模式: {triggermode.value}")
                print(f"  取樣率: {samplerate.value} Hz")
                print(f"  目標計數: {targetcnt.value}")
                print(f"  資料傳輸方法: {datatransmethod.value}")
                print(f"  自動執行: {autorun.value}")
            else:
                print("[Warning] 無法驗證參數設定，但繼續執行")

        except Exception as e:
            print(f"[Error] 設定掃描參數時發生錯誤: {e}")

    def start_reading(self) -> None:
        """開始讀取振動數據（在背景執行緒中執行）"""
        if self.reading:
            print("[Error] 讀取已在進行中！")
            return

        if self.device_handle is None:
            print("[Error] 設備未初始化！")
            return

        # 啟動掃描
        print("[Debug] 正在啟動類比輸入掃描...")
        ret = dll.HS_StartAIScan(self.device_handle)
        if not ret:
            error_code = dll.HS_GetLastError()
            print(f"[Error] 啟動掃描失敗！錯誤碼: 0x{error_code:x}")
            return

        self.reading = True
        self.reading_thread = threading.Thread(target=self._read_loop)
        self.reading_thread.daemon = True
        self.reading_thread.start()
        print("[Debug] 讀取執行緒已啟動。")

    def stop_reading(self) -> None:
        """停止讀取振動數據"""
        if self.reading:
            self.reading = False
            if self.reading_thread and self.reading_thread.is_alive():
                self.reading_thread.join()

        # 停止掃描
        if self.device_handle:
            try:
                dll.HS_StopAIScan(self.device_handle)
                print("[Debug] 掃描已停止。")
            except Exception as e:
                print(f"[Error] 停止掃描時發生錯誤: {e}")

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
                print("[Debug] 設備連線已釋放。")
            except Exception as e:
                print(f"[Error] 釋放設備連線時發生錯誤: {e}")

    def _read_loop(self) -> None:
        """
        讀取振動數據（主要讀取迴圈）
        
        支援兩種模式：
        1. AI Buffer Continue 模式（targetCount = 0）：持續讀取所有可用資料
        2. N Sample 模式（targetCount > 0）：等待達到目標數量後讀取
        
        參考官方範例：
        - ET7H24_AI_Buffer_Continue.py：持續讀取模式
        - ET7H24_N_Sample_float.py：N 樣本讀取模式
        """
        consecutive_errors = 0
        max_consecutive_errors = 5
        total_samples_read = 0  # 累計讀取的樣本數（用於 N Sample 模式）

        try:
            print("[Debug] 讀取迴圈已啟動...")
            if self.target_count > 0:
                print(f"[Debug] N Sample 模式：目標樣本數 = {self.target_count}")
            else:
                print("[Debug] AI Buffer Continue 模式：持續讀取")
            
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
                        print(f"[Error] 取得緩衝區狀態失敗！錯誤碼: 0x{error_code:x}")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            print(f"[Error] 連續 {max_consecutive_errors} 次錯誤，停止讀取")
                            break
                        time.sleep(0.1)
                        continue

                    # 檢查緩衝區狀態錯誤（參考官方範例）
                    status_value = buffer_status.value
                    if (status_value & 0x02) == 0x02:
                        error_code = dll.HS_GetLastError()
                        print(f"[Error] AI 緩衝區溢位！錯誤碼: 0x{error_code:x}")
                        dll.HS_StopAIScan(self.device_handle)
                        break
                    elif (status_value & 0x04) == 0x04:
                        print("[Error] AI 掃描已停止")
                        break
                    elif (status_value & 0x08) == 0x08:
                        print("[Error] 其他錯誤")
                        break

                    # 決定是否讀取資料
                    should_read = False
                    
                    if self.target_count > 0:
                        # N Sample 模式：等待達到目標數量
                        if buffer_cnt.value >= self.target_count:
                            should_read = True
                            print(f"[Debug] 達到目標樣本數 {self.target_count}，開始讀取")
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
                        read_count = read_count - (read_count % self.channel_count)
                        
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
                                    print(f"[Debug] 已讀取 {total_samples_read} 個樣本，達到目標 {self.target_count}，停止讀取")
                                    self.reading = False
                                    break
                            else:
                                print("[Warning] 未讀取到資料")
                        else:
                            # 資料不足一個完整通道組，等待更多資料
                            time.sleep(0.001)  # 1ms
                    else:
                        # 尚未達到讀取條件，短暫休息
                        if self.target_count > 0:
                            # N Sample 模式：顯示進度
                            if buffer_cnt.value > 0:
                                progress = (buffer_cnt.value / self.target_count) * 100
                                print(f"\r[Debug] 等待資料中... 緩衝區: {buffer_cnt.value}/{self.target_count} ({progress:.1f}%)", end='', flush=True)
                        time.sleep(0.001)  # 1ms

                except Exception as e:
                    consecutive_errors += 1
                    print(f"\n[Error] 讀取資料時發生錯誤: {e}")
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"[Error] 連續 {max_consecutive_errors} 次錯誤，停止讀取")
                        break
                    time.sleep(0.1)

        except Exception as e:
            print(f"\n[Error] 讀取迴圈發生嚴重錯誤: {e}")
        finally:
            print("\n[Debug] 讀取迴圈已結束。")

    def get_data(self) -> List[float]:
        """取得最新的振動數據（從佇列中取出）"""
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
        """取得通道數"""
        return self.channel_count

    def __del__(self):
        """解構函數"""
        self.stop_reading()

