#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PET-7H24M 即時資料可視化系統 - 主控制程式

此模組整合所有功能模組，提供完整的 Web 介面控制，支援：
- Web 介面控制（使用 Flask 提供瀏覽器操作介面）
- 即時資料可視化（使用 Chart.js 顯示多通道連續曲線圖）
- 資料採集管理（整合 PET-7H24M 設備通訊）
- CSV 自動儲存（根據設定檔自動分檔儲存資料）
- SQL 資料庫上傳（可選的 MySQL/MariaDB 上傳功能）
- 設定檔管理（透過 Web 介面編輯 PET-7H24M.ini、csv.ini、sql.ini）
- 多執行緒架構（5 個獨立執行緒：Flask、DAQ Reading、Collection、CSV Writer、SQL Writer）
- 執行緒安全通訊（使用 queue.Queue 進行執行緒間通訊）
- 降頻佇列架構（web_data_queue 存儲降頻後的資料供前端使用）
"""

import os
import sys
import time
import threading
import queue
import configparser
import argparse
import csv
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from flask import Flask, render_template, request, jsonify, send_from_directory
from pet7h24m import PET7H24M
from csv_writer import CSVWriter
from sql_uploader import SQLUploader

try:
    from logger import info, debug, error, warning
except ImportError:
    def info(msg): print(f"[INFO] {msg}")
    def debug(msg): print(f"[Debug] {msg}")
    def error(msg): print(f"[Error] {msg}")
    def warning(msg): print(f"[Warning] {msg}")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
os.chdir(PROJECT_ROOT)

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

template_dir = os.path.join(SCRIPT_DIR, 'templates')
app = Flask(__name__, template_folder=template_dir)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# ==========================================
# 全域變數與資料結構 (優化核心)
# ==========================================

# 1. 網頁顯示專用佇列 (Web Visualization Queue)
web_data_queue: "queue.Queue[List[float]]" = queue.Queue(maxsize=50000)

# 2. 降頻比例 (Downsampling Ratio)
WEB_DOWNSAMPLE_RATIO = 25

# 3. 資料流佇列 (Raw Data Queues)
csv_data_queue: "queue.Queue[List[float]]" = queue.Queue(maxsize=50000)
sql_data_queue: "queue.Queue[List[float]]" = queue.Queue(maxsize=50000)

# 4. 控制旗標與物件
is_collecting = False
data_lock = threading.Lock()

collection_thread: Optional[threading.Thread] = None
csv_writer_thread: Optional[threading.Thread] = None
sql_writer_thread: Optional[threading.Thread] = None

daq_instance: Optional[PET7H24M] = None
csv_writer_instance: Optional[CSVWriter] = None
sql_uploader_instance: Optional[SQLUploader] = None

data_counter = 0
collection_start_time: Optional[datetime] = None
current_sample_rate: int = 12800

target_size = 0
current_data_size = 0
sql_target_size = 0
sql_current_data_size = 0
sql_enabled = False
sql_config: Dict[str, str] = {}
sql_upload_interval = 0
sql_temp_dir = None
sql_current_temp_file = None
sql_temp_file_lock = threading.Lock()
sql_sample_count = 0
sql_start_time: Optional[datetime] = None
channels = 2  # 預設通道數，會在啟動時從 DAQ 取得


# ==========================================
# 核心邏輯：資料更新與處理
# ==========================================

def update_realtime_data(data: List[float]) -> None:
    """更新即時資料（針對 Web 顯示進行降頻處理）"""
    global web_data_queue, WEB_DOWNSAMPLE_RATIO, data_counter

    if web_data_queue.full():
        try:
            for _ in range(10):
                web_data_queue.get_nowait()
        except queue.Empty:
            pass

    # 根據通道數進行降頻處理
    step = channels * WEB_DOWNSAMPLE_RATIO
    
    downsampled_chunk = []
    
    for i in range(0, len(data), step):
        if i + channels <= len(data):
            downsampled_chunk.extend(data[i : i + channels])

    if downsampled_chunk:
        with data_lock:
            web_data_queue.put(downsampled_chunk)
            
    data_counter += len(data)


# Flask 路由
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/files_page')
def files_page():
    return render_template('files.html')

@app.route('/data')
def get_data():
    """前端輪詢 API"""
    global web_data_queue, current_sample_rate, is_collecting, data_counter, collection_start_time

    new_data = []
    with data_lock:
        while not web_data_queue.empty():
            try:
                chunk = web_data_queue.get_nowait()
                new_data.extend(chunk)
            except queue.Empty:
                break
    
    response_data = {
        "success": True,
        "data": new_data,
        "counter": data_counter,
        "sample_rate": current_sample_rate,
        "is_collecting": is_collecting
    }

    if collection_start_time:
        response_data["start_time"] = collection_start_time.isoformat()

    return jsonify(response_data)


@app.route('/status')
def get_status():
    """檢查資料收集狀態（用於前端狀態恢復）"""
    global is_collecting, data_counter
    return jsonify({
        'success': True,
        'is_collecting': is_collecting,
        'counter': data_counter
    })


@app.route('/sql_config')
def get_sql_config():
    """取得 SQL 設定（從 sql.ini 檔案讀取）"""
    try:
        ini_file_path = "API/sql.ini"
        config = configparser.ConfigParser()
        config.read(ini_file_path, encoding='utf-8')

        sql_config = {
            'enabled': False,
            'host': 'localhost',
            'port': '3306',
            'user': 'root',
            'password': '',
            'database': 'pet7h24m'
        }

        if config.has_section('SQLServer'):
            sql_config['enabled'] = config.getboolean('SQLServer', 'enabled', fallback=False)
            sql_config['host'] = config.get('SQLServer', 'host', fallback='localhost')
            sql_config['port'] = config.get('SQLServer', 'port', fallback='3306')
            sql_config['user'] = config.get('SQLServer', 'user', fallback='root')
            sql_config['password'] = config.get('SQLServer', 'password', fallback='')
            sql_config['database'] = config.get('SQLServer', 'database', fallback='pet7h24m')

        return jsonify({
            'success': True,
            'sql_config': sql_config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'sql_config': {
                'enabled': False,
                'host': 'localhost',
                'port': '3306',
                'user': 'root',
                'password': '',
                'database': 'pet7h24m'
            }
        })


@app.route('/config', methods=['GET', 'POST'])
def config():
    """顯示與修改設定檔（PET-7H24M.ini、csv.ini、sql.ini）"""
    ini_dir = "API"
    pet7h24m_ini = os.path.join(ini_dir, "PET-7H24M.ini")
    csv_ini = os.path.join(ini_dir, "csv.ini")
    sql_ini = os.path.join(ini_dir, "sql.ini")

    if request.method == 'POST':
        try:
            # 讀取 PET-7H24M.ini 設定
            pet7h24m_config = configparser.ConfigParser()
            pet7h24m_config.read(pet7h24m_ini, encoding='utf-8')
            if not pet7h24m_config.has_section('PET7H24M'):
                pet7h24m_config.add_section('PET7H24M')
            
            pet7h24m_config.set('PET7H24M', 'device_ip', request.form.get('pet7h24m_device_ip', '192.168.255.1'))
            pet7h24m_config.set('PET7H24M', 'device_port', request.form.get('pet7h24m_device_port', '502'))
            pet7h24m_config.set('PET7H24M', 'sample_rate', request.form.get('pet7h24m_sample_rate', '20000'))
            # 處理通道 checkbox（前端已處理，未勾選時會傳送 '0'，勾選時傳送 '1'）
            pet7h24m_config.set('PET7H24M', 'enable_ai0', request.form.get('pet7h24m_enable_ai0', '0'))
            pet7h24m_config.set('PET7H24M', 'enable_ai1', request.form.get('pet7h24m_enable_ai1', '0'))
            pet7h24m_config.set('PET7H24M', 'enable_ai2', request.form.get('pet7h24m_enable_ai2', '0'))
            pet7h24m_config.set('PET7H24M', 'enable_ai3', request.form.get('pet7h24m_enable_ai3', '0'))
            pet7h24m_config.set('PET7H24M', 'gain', request.form.get('pet7h24m_gain', '0'))
            pet7h24m_config.set('PET7H24M', 'trigger_mode', request.form.get('pet7h24m_trigger_mode', '0'))
            pet7h24m_config.set('PET7H24M', 'target_count', request.form.get('pet7h24m_target_count', '0'))
            pet7h24m_config.set('PET7H24M', 'data_trans_method', request.form.get('pet7h24m_data_trans_method', '0'))
            pet7h24m_config.set('PET7H24M', 'auto_run', request.form.get('pet7h24m_auto_run', '0'))

            # 讀取 csv.ini 設定
            csv_config = configparser.ConfigParser()
            csv_config.read(csv_ini, encoding='utf-8')
            if not csv_config.has_section('DumpUnit'):
                csv_config.add_section('DumpUnit')
            
            csv_config.set('DumpUnit', 'second', request.form.get('csv_second', '60'))

            # 讀取 sql.ini 設定
            sql_config = configparser.ConfigParser()
            sql_config.read(sql_ini, encoding='utf-8')
            if not sql_config.has_section('SQLServer'):
                sql_config.add_section('SQLServer')
            if not sql_config.has_section('DumpUnit'):
                sql_config.add_section('DumpUnit')
            
            # 處理 SQL enabled checkbox（前端已處理，未勾選時會傳送 'false'，勾選時傳送 'true'）
            sql_config.set('SQLServer', 'enabled', request.form.get('sql_enabled', 'false'))
            sql_config.set('SQLServer', 'host', request.form.get('sql_host', 'localhost'))
            sql_config.set('SQLServer', 'port', request.form.get('sql_port', '3306'))
            sql_config.set('SQLServer', 'user', request.form.get('sql_user', 'root'))
            sql_config.set('SQLServer', 'password', request.form.get('sql_password', ''))
            sql_config.set('SQLServer', 'database', request.form.get('sql_database', 'pet7h24m'))
            sql_config.set('DumpUnit', 'second', request.form.get('sql_second', '60'))

            # 寫入檔案
            with open(pet7h24m_ini, 'w', encoding='utf-8') as f:
                pet7h24m_config.write(f)
            
            with open(csv_ini, 'w', encoding='utf-8') as f:
                csv_config.write(f)
            
            with open(sql_ini, 'w', encoding='utf-8') as f:
                sql_config.write(f)

            return jsonify({'success': True, 'message': '設定檔已儲存'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    # GET 請求：讀取設定檔並顯示編輯頁面
    pet7h24m_config = configparser.ConfigParser()
    try:
        pet7h24m_config.read(pet7h24m_ini, encoding='utf-8')
    except:
        pass
    
    pet7h24m_data = {
        'device_ip': pet7h24m_config.get('PET7H24M', 'device_ip', fallback='192.168.255.1'),
        'device_port': pet7h24m_config.get('PET7H24M', 'device_port', fallback='502'),
        'sample_rate': pet7h24m_config.get('PET7H24M', 'sample_rate', fallback='20000'),
        'enable_ai0': pet7h24m_config.get('PET7H24M', 'enable_ai0', fallback='1'),
        'enable_ai1': pet7h24m_config.get('PET7H24M', 'enable_ai1', fallback='1'),
        'enable_ai2': pet7h24m_config.get('PET7H24M', 'enable_ai2', fallback='0'),
        'enable_ai3': pet7h24m_config.get('PET7H24M', 'enable_ai3', fallback='0'),
        'gain': pet7h24m_config.get('PET7H24M', 'gain', fallback='0'),
        'trigger_mode': pet7h24m_config.get('PET7H24M', 'trigger_mode', fallback='0'),
        'target_count': pet7h24m_config.get('PET7H24M', 'target_count', fallback='0'),
        'data_trans_method': pet7h24m_config.get('PET7H24M', 'data_trans_method', fallback='0'),
        'auto_run': pet7h24m_config.get('PET7H24M', 'auto_run', fallback='0')
    }

    # 讀取 csv.ini
    csv_config_parser = configparser.ConfigParser()
    try:
        csv_config_parser.read(csv_ini, encoding='utf-8')
    except:
        pass
    
    csv_data = {
        'second': csv_config_parser.get('DumpUnit', 'second', fallback='60')
    }

    # 讀取 sql.ini
    sql_config_parser = configparser.ConfigParser()
    try:
        sql_config_parser.read(sql_ini, encoding='utf-8')
    except:
        pass
    
    sql_data = {
        'enabled': sql_config_parser.getboolean('SQLServer', 'enabled', fallback=False),
        'host': sql_config_parser.get('SQLServer', 'host', fallback='localhost'),
        'port': sql_config_parser.get('SQLServer', 'port', fallback='3306'),
        'user': sql_config_parser.get('SQLServer', 'user', fallback='root'),
        'password': sql_config_parser.get('SQLServer', 'password', fallback=''),
        'database': sql_config_parser.get('SQLServer', 'database', fallback='pet7h24m'),
        'second': sql_config_parser.get('DumpUnit', 'second', fallback='60')
    }

    return render_template('config.html',
                           pet7h24m_data=pet7h24m_data,
                           csv_data=csv_data,
                           sql_data=sql_data)


@app.route('/start', methods=['POST'])
def start_collection():
    """啟動資料收集（DAQ、CSVWriter、SQLUploader 與即時顯示）"""
    global is_collecting, collection_thread, daq_instance, csv_writer_instance
    global target_size, current_data_size, realtime_data, data_counter
    global sql_uploader_instance, sql_target_size, sql_current_data_size, sql_enabled, sql_config
    global sql_upload_interval, sql_temp_dir, sql_current_temp_file
    global sql_start_time, sql_sample_count, last_data_request_time

    if is_collecting:
        return jsonify({'success': False, 'message': '資料收集已在執行中'})

    try:
        data = request.get_json()
        label = data.get('label', '') if data else ''
        csv_enabled = data.get('csv_enabled', True) if data else True
        sql_enabled_request = data.get('sql_enabled', False) if data else False

        if not label:
            return jsonify({'success': False, 'message': '請提供資料標籤'})

        # 至少需要啟用一個選項
        if not csv_enabled and not sql_enabled_request:
            return jsonify({'success': False, 'message': '請至少選擇一個儲存選項（CSV 或 SQL）'})

        with data_lock:
            with web_data_queue.mutex:
                web_data_queue.queue.clear()
            with csv_data_queue.mutex:
                csv_data_queue.queue.clear()
            with sql_data_queue.mutex:
                sql_data_queue.queue.clear()
                
            data_counter = 0
            current_data_size = 0
            sql_current_data_size = 0
            collection_start_time = datetime.now()
            sql_sample_count = 0
            sql_start_time = None

        # 讀取 CSV 分檔間隔（從 csv.ini）
        csv_ini_file_path = "API/csv.ini"
        csv_config_parser = configparser.ConfigParser()
        csv_config_parser.read(csv_ini_file_path, encoding='utf-8')
        save_unit = csv_config_parser.getint('DumpUnit', 'second', fallback=60)

        # 讀取 SQL 上傳間隔（從 sql.ini）
        sql_ini_file_path = "API/sql.ini"
        sql_config_parser = configparser.ConfigParser()
        sql_config_parser.read(sql_ini_file_path, encoding='utf-8')
        
        # 讀取 SQL 上傳間隔
        sql_upload_interval = sql_config_parser.getint('DumpUnit', 'second', fallback=60)
        
        sql_enabled_ini = False
        sql_config_ini = {
            'host': 'localhost',
            'port': '3306',
            'user': 'root',
            'password': '',
            'database': 'pet7h24m'
        }
        
        if sql_config_parser.has_section('SQLServer'):
            sql_enabled_ini = sql_config_parser.getboolean('SQLServer', 'enabled', fallback=False)
            sql_config_ini['host'] = sql_config_parser.get('SQLServer', 'host', fallback='localhost')
            sql_config_ini['port'] = sql_config_parser.get('SQLServer', 'port', fallback='3306')
            sql_config_ini['user'] = sql_config_parser.get('SQLServer', 'user', fallback='root')
            sql_config_ini['password'] = sql_config_parser.get('SQLServer', 'password', fallback='')
            sql_config_ini['database'] = sql_config_parser.get('SQLServer', 'database', fallback='pet7h24m')

        # 處理 SQL 設定（優先使用前端請求的設定）
        if sql_enabled_request:
            sql_enabled = True
            sql_config = {
                'host': data.get('sql_host', sql_config_ini['host']) if data else sql_config_ini['host'],
                'port': data.get('sql_port', sql_config_ini['port']) if data else sql_config_ini['port'],
                'user': data.get('sql_user', sql_config_ini['user']) if data else sql_config_ini['user'],
                'password': data.get('sql_password', sql_config_ini['password']) if data else sql_config_ini['password'],
                'database': data.get('sql_database', sql_config_ini['database']) if data else sql_config_ini['database']
            }
        else:
            sql_enabled = False
            sql_config = sql_config_ini.copy()

        # 1. 初始化 DAQ 設備 (讀取 ini)
        try:
            # 確保這裡是使用 PET7H24M 類別
            if daq_instance is None:
                daq_instance = PET7H24M()
            
            # 這一步會讀取 ini 並計算 channel_mask
            daq_instance.init_devices("API/PET-7H24M.ini")
            
            # 2. 動態獲取配置 (關鍵！)
            sample_rate = daq_instance.get_sample_rate()
            current_sample_rate = sample_rate
            global channels
            channels = daq_instance.get_active_channel_count()
            
            info(f"系統啟動參數: 通道數={channels}, 取樣率={sample_rate} Hz")

        except Exception as e:
            error(f"設備初始化失敗: {e}")
            is_collecting = False
            return jsonify({'success': False, 'message': f'設備初始化失敗: {str(e)}'})

        expected_samples_per_second = sample_rate * channels
        target_size = save_unit * expected_samples_per_second
        sql_target_size = sql_upload_interval * expected_samples_per_second

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        folder = f"{timestamp}_{label}"
        output_path = os.path.join(PROJECT_ROOT, "output", "PET-7H24M", folder)
        
        # 只有在啟用 CSV 或 SQL 時才建立資料夾
        if csv_enabled or sql_enabled_request:
            os.makedirs(output_path, exist_ok=True)

        # 3. 根據通道數初始化 CSV Writer（如果啟用）
        csv_writer_instance = None
        if csv_enabled:
            try:
                # 這裡傳入動態計算的 channels
                csv_writer_instance = CSVWriter(
                    channels=channels,  # <--- 動態改變
                    output_dir=output_path,
                    label=label,
                    sample_rate=sample_rate   # <--- 動態改變
                )
            except Exception as e:
                error(f"CSV Writer 初始化失敗: {e}")
                is_collecting = False
                return jsonify({'success': False, 'message': f'CSV Writer 初始化失敗: {str(e)}'})

        # 4. 根據通道數初始化 SQL Uploader (如果啟用)
        sql_uploader_instance = None
        sql_temp_dir = None
        sql_current_temp_file = None
        sql_start_time = datetime.now()
        sql_sample_count = 0
        sql_current_data_size = 0
        
        if sql_enabled:
            try:
                # 使用動態獲取的通道數初始化 SQL Uploader
                sql_uploader_instance = SQLUploader(channels, label, sql_config)
                
                # 建立暫存檔案目錄
                sql_temp_dir = os.path.join(output_path, ".sql_temp")
                os.makedirs(sql_temp_dir, exist_ok=True)
                
                # 建立第一個暫存檔案
                temp_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                temp_filename = f"{temp_timestamp}_sql_temp.csv"
                sql_current_temp_file = os.path.join(sql_temp_dir, temp_filename)
                
                # 建立 CSV 檔案並寫入標題
                with open(sql_current_temp_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    headers = ['Timestamp'] + [f'Channel_{i+1}' for i in range(channels)]
                    writer.writerow(headers)
                
                info(f"SQL 暫存檔案已建立: {temp_filename}")
                
            except Exception as e:
                return jsonify({'success': False, 'message': f'SQL 上傳器初始化失敗: {str(e)}'})

        is_collecting = True

        collection_thread = threading.Thread(target=collection_loop, daemon=True)
        collection_thread.start()

        if csv_writer_instance:
            csv_writer_thread = threading.Thread(target=csv_writer_loop, daemon=True)
            csv_writer_thread.start()

        if sql_uploader_instance and sql_enabled:
            sql_writer_thread = threading.Thread(target=sql_writer_loop, daemon=True)
            sql_writer_thread.start()

        daq_instance.start_reading()

        # 構建狀態訊息
        status_parts = [f'取樣率: {sample_rate} Hz', f'通道數: {channels}']
        if csv_enabled:
            status_parts.append(f'CSV 分檔間隔: {save_unit} 秒')
        if sql_enabled:
            status_parts.append(f'SQL 上傳間隔: {sql_upload_interval} 秒')
        
        return jsonify({
            'success': True,
            'message': f'資料收集已啟動 ({", ".join(status_parts)})'
        })

    except Exception as e:
        is_collecting = False
        return jsonify({'success': False, 'message': f'啟動失敗: {str(e)}'})


@app.route('/stop', methods=['POST'])
def stop_collection():
    """停止資料收集（停止所有執行緒、安全關閉，並上傳剩餘資料）"""
    global is_collecting, daq_instance, csv_writer_instance, sql_uploader_instance
    global current_data_size, sql_current_data_size, sql_enabled
    global sql_temp_dir, sql_current_temp_file

    if not is_collecting:
        return jsonify({'success': False, 'message': '資料收集未在執行中'})

    try:
        is_collecting = False

        if daq_instance:
            daq_instance.stop_reading()

        # 立即返回成功回應，讓前端知道已停止
        # 剩餘的上傳工作在背景執行
        response_message = '資料收集已停止'
        
        # 在背景執行緒中處理剩餘的上傳工作（避免阻塞前端）
        cleanup_thread = threading.Thread(target=finalize_upload, daemon=True)
        cleanup_thread.start()
        
        return jsonify({'success': True, 'message': response_message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'停止失敗: {str(e)}'})


def finalize_upload():
    """停止後的清理與剩餘資料上傳"""
    global collection_thread, csv_writer_thread, sql_writer_thread
    global csv_data_queue, sql_data_queue
    global sql_uploader_instance, sql_enabled, sql_temp_dir, sql_current_temp_file
    global csv_writer_instance

    if collection_thread and collection_thread.is_alive():
        collection_thread.join(timeout=2.0)
    
    if csv_writer_thread and csv_writer_thread.is_alive():
        start_t = time.time()
        while not csv_data_queue.empty() and (time.time() - start_t < 5):
            time.sleep(0.1)
    
    if sql_writer_thread and sql_writer_thread.is_alive():
        start_t = time.time()
        while not sql_data_queue.empty() and (time.time() - start_t < 5):
            time.sleep(0.1)

    time.sleep(0.5)

    if sql_uploader_instance and sql_enabled and sql_temp_dir:
        try:
            with sql_temp_file_lock:
                current_temp = sql_current_temp_file

            if current_temp and os.path.exists(current_temp):
                if csv_writer_instance:
                    csv_filename = csv_writer_instance.get_current_filename()
                    if csv_filename:
                        table_name = csv_filename
                    else:
                        table_name = None
                else:
                    table_name = None

                if sql_uploader_instance.upload_from_csv_file(current_temp, table_name):
                    try:
                        os.remove(current_temp)
                        info(f"停止時已上傳並刪除暫存檔案: {os.path.basename(current_temp)}")
                    except Exception as e:
                        warning(f"刪除暫存檔案失敗: {e}")
                else:
                    error(f"停止時上傳暫存檔案失敗: {os.path.basename(current_temp)}")

            if os.path.exists(sql_temp_dir):
                temp_files = [
                    f for f in os.listdir(sql_temp_dir)
                    if f.endswith("_sql_temp.csv")
                ]
                for temp_file in temp_files:
                    temp_file_path = os.path.join(sql_temp_dir, temp_file)
                    if os.path.exists(temp_file_path):
                        if csv_writer_instance:
                            csv_filename = csv_writer_instance.get_current_filename()
                            if csv_filename:
                                table_name = csv_filename
                            else:
                                table_name = None
                        else:
                            table_name = None

                        if sql_uploader_instance.upload_from_csv_file(temp_file_path, table_name):
                            try:
                                os.remove(temp_file_path)
                                info(f"停止時已上傳並刪除暫存檔案: {temp_file}")
                            except Exception as e:
                                warning(f"刪除暫存檔案失敗: {e}")
                        else:
                            error(f"停止時上傳暫存檔案失敗: {temp_file}")

                try:
                    if not os.listdir(sql_temp_dir):
                        os.rmdir(sql_temp_dir)
                except:
                    pass

        except Exception as e:
            warning(f"清理 SQL 暫存檔案時發生錯誤: {e}")

    if csv_writer_instance:
        csv_writer_instance.close()

    if sql_uploader_instance:
        sql_uploader_instance.close()

    info("所有資源已安全關閉")


@app.route('/files')
def list_files():
    """列出 output 目錄中的檔案和資料夾"""
    try:
        path = request.args.get('path', '')
        base_path = os.path.join(PROJECT_ROOT, "output", "PET-7H24M")
        
        if path:
            full_path = os.path.join(base_path, path)
            full_path = os.path.normpath(full_path)
            base_path_norm = os.path.normpath(os.path.abspath(base_path))
            full_path_abs = os.path.abspath(full_path)
            
            if not full_path_abs.startswith(base_path_norm):
                return jsonify({'success': False, 'message': '無效的路徑'})
        else:
            full_path = base_path
        
        if not os.path.exists(full_path):
            return jsonify({'success': False, 'message': '路徑不存在'})
        
        items = []
        try:
            for item in sorted(os.listdir(full_path)):
                item_path = os.path.join(full_path, item)
                relative_path = os.path.join(path, item) if path else item
                relative_path = relative_path.replace('\\', '/')
                
                if os.path.isdir(item_path):
                    items.append({
                        'name': item,
                        'type': 'directory',
                        'path': relative_path
                    })
                else:
                    size = os.path.getsize(item_path)
                    items.append({
                        'name': item,
                        'type': 'file',
                        'path': relative_path,
                        'size': size
                    })
        except PermissionError:
            return jsonify({'success': False, 'message': '沒有權限讀取此目錄'})
        
        return jsonify({
            'success': True,
            'items': items,
            'current_path': path
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/download')
def download_file():
    """下載檔案"""
    try:
        path = request.args.get('path', '')
        if not path:
            return jsonify({'success': False, 'message': '請提供檔案路徑'})
        
        base_path = os.path.join(PROJECT_ROOT, "output", "PET-7H24M")
        full_path = os.path.join(base_path, path)
        
        full_path = os.path.normpath(full_path)
        base_path_norm = os.path.normpath(os.path.abspath(base_path))
        full_path_abs = os.path.abspath(full_path)
        
        if not full_path_abs.startswith(base_path_norm):
            return jsonify({'success': False, 'message': '無效的路徑'})
        
        if not os.path.exists(full_path):
            return jsonify({'success': False, 'message': '檔案不存在'})
        
        if os.path.isdir(full_path):
            return jsonify({'success': False, 'message': '無法下載資料夾'})
        
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        
        return send_from_directory(directory, filename, as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


def _create_new_temp_file() -> Optional[str]:
    """建立新的 SQL 暫存檔案"""
    global sql_temp_dir, sql_current_temp_file, channels

    if not sql_temp_dir:
        return None

    try:
        temp_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        temp_filename = f"{temp_timestamp}_sql_temp.csv"
        new_temp_file = os.path.join(sql_temp_dir, temp_filename)

        with open(new_temp_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            headers = ['Timestamp'] + [f'Channel_{i+1}' for i in range(channels)]
            writer.writerow(headers)

        with sql_temp_file_lock:
            sql_current_temp_file = new_temp_file

        info(f"新的 SQL 暫存檔案已建立: {temp_filename}")
        return new_temp_file
    except Exception as e:
        error(f"建立新暫存檔案失敗: {e}")
        return None


def _write_to_temp_file(
    data: List[float], sample_rate: int, start_time: datetime, sample_count: int
) -> int:
    """將資料寫入 SQL 暫存檔案"""
    global sql_current_temp_file
    
    if not sql_current_temp_file or not os.path.exists(sql_current_temp_file):
        return sample_count
    
    try:
        with sql_temp_file_lock:
            current_file = sql_current_temp_file
            if not current_file or not os.path.exists(current_file):
                return sample_count
            
            with open(current_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                sample_interval = 1.0 / sample_rate
                current_count = sample_count
                
                for i in range(0, len(data), channels):
                    elapsed_time = current_count * sample_interval
                    timestamp = start_time + timedelta(seconds=elapsed_time)
                    
                    row = [timestamp.isoformat()]
                    for j in range(channels):
                        if i + j < len(data):
                            row.append(data[i + j])
                        else:
                            row.append(0.0)
                    
                    writer.writerow(row)
                    current_count += 1
        
        return current_count
    except Exception as e:
        error(f"寫入暫存檔案失敗: {e}")
        return sample_count


def _upload_temp_file_if_needed():
    """檢查並上傳 SQL 暫存檔案（如果資料量達到門檻）"""
    global sql_uploader_instance, sql_current_temp_file, sql_temp_dir, csv_writer_instance
    global sql_current_data_size, sql_target_size, channels
    
    if not sql_uploader_instance or not sql_current_temp_file:
        return False
    
    # 檢查資料量是否達到門檻
    if sql_current_data_size < sql_target_size:
        return False
    
    # 資料量達到門檻，準備上傳
    with sql_temp_file_lock:
        temp_file_to_upload = sql_current_temp_file
    
    if not temp_file_to_upload or not os.path.exists(temp_file_to_upload):
        return False
    
    try:
        # 記錄當前資料量（用於日誌）
        current_data_size_before_upload = sql_current_data_size
        
        # 從檔名推斷表名（使用對應的 CSV 檔名）
        if csv_writer_instance:
            csv_filename = csv_writer_instance.get_current_filename()
            if csv_filename:
                table_name = csv_filename
            else:
                table_name = None
        else:
            table_name = None
        
        # 上傳檔案
        if sql_uploader_instance.upload_from_csv_file(temp_file_to_upload, table_name):
            # 計算筆數（資料點數 / 通道數）
            rows_count = current_data_size_before_upload // channels
            target_rows = sql_target_size // channels
            
            # 上傳成功，刪除暫存檔
            try:
                os.remove(temp_file_to_upload)
                info(f"暫存檔案已上傳並刪除: {os.path.basename(temp_file_to_upload)} (筆數: {rows_count} 筆, 目標: {target_rows} 筆)")
            except Exception as e:
                warning(f"刪除暫存檔案失敗: {e}")
            
            # 建立新的暫存檔案
            _create_new_temp_file()
            
            # 計算超出部分的資料量（用於下一個暫存檔案）
            excess_data_size = current_data_size_before_upload - sql_target_size
            
            # 重置資料量計數器，保留超出部分的資料量
            sql_current_data_size = excess_data_size
            
            if excess_data_size > 0:
                excess_rows = excess_data_size // channels
                debug(f"保留超出部分的資料量: {excess_rows} 筆 ({excess_data_size} 個資料點) 到新暫存檔案")
            
            return True
        else:
            error(f"上傳暫存檔案失敗: {os.path.basename(temp_file_to_upload)}")
            # 上傳失敗，保留檔案等待下次重試
            return False
            
    except Exception as e:
        error(f"上傳暫存檔案時發生錯誤: {e}")
        return False


def collection_loop():
    """資料收集主迴圈（在獨立執行緒中執行）"""
    global is_collecting, daq_instance, csv_data_queue, sql_data_queue
    global csv_writer_instance, sql_uploader_instance, sql_enabled

    while is_collecting:
        try:
            data = daq_instance.get_data()

            while data and len(data) > 0:
                update_realtime_data(data)

                if csv_writer_instance:
                    try:
                        csv_data_queue.put(data.copy(), block=False)
                    except queue.Full:
                        warning("CSV Queue Full")

                if sql_uploader_instance and sql_enabled:
                    try:
                        sql_data_queue.put(data.copy(), block=False)
                    except queue.Full:
                        warning("SQL Queue Full")

                data = daq_instance.get_data()

            time.sleep(0.01)

        except Exception as e:
            error(f"Collection loop error: {e}")
            time.sleep(0.1)

def csv_writer_loop():
    """CSV 寫入迴圈（在獨立執行緒中執行）"""
    global is_collecting, csv_writer_instance, sql_uploader_instance, sql_enabled
    global target_size, current_data_size, csv_data_queue

    while is_collecting or not csv_data_queue.empty():
        try:
            try:
                data = csv_data_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            data_size = len(data)
            current_data_size += data_size

            if current_data_size < target_size:
                csv_writer_instance.add_data_block(data)
            else:
                data_actual_size = data_size
                empty_space = target_size - (current_data_size - data_actual_size)
                empty_space = (empty_space // channels) * channels

                while current_data_size >= target_size:
                    batch = data[:empty_space]
                    csv_writer_instance.add_data_block(batch)
                    csv_writer_instance.update_filename()

                    if sql_uploader_instance and sql_enabled:
                        csv_filename = (
                            csv_writer_instance.get_current_filename()
                            if csv_writer_instance
                            else None
                        )
                        if csv_filename:
                            if sql_uploader_instance.create_table(csv_filename):
                                info(f"SQL 表已建立，對應 CSV: {csv_filename}")
                            else:
                                warning(f"SQL 表建立失敗，對應 CSV: {csv_filename}")

                    current_data_size -= target_size

                    if empty_space < data_actual_size:
                        data = data[empty_space:]
                        data_actual_size = len(data)
                        empty_space = target_size
                        empty_space = (empty_space // channels) * channels
                    else:
                        break

                pending = data_actual_size
                if pending:
                    csv_writer_instance.add_data_block(data)
                    current_data_size = pending
                else:
                    current_data_size = 0

            csv_data_queue.task_done()

        except Exception as e:
            error(f"CSV writer loop error: {e}")
            time.sleep(0.1)

def sql_writer_loop():
    """SQL 寫入迴圈（在獨立執行緒中執行）"""
    global is_collecting, sql_uploader_instance, sql_enabled, sql_current_temp_file
    global sql_target_size, sql_current_data_size, sql_sample_count, sql_start_time
    global sql_data_queue, csv_writer_instance, daq_instance

    sample_rate = 12800
    if csv_writer_instance:
        sample_rate = csv_writer_instance.sample_rate
    elif daq_instance:
        try:
            sample_rate = daq_instance.get_sample_rate()
        except:
            pass

    if sql_start_time is None:
        sql_start_time = datetime.now()
        sql_sample_count = 0
        sql_current_data_size = 0

    while is_collecting or not sql_data_queue.empty():
        try:
            try:
                sql_data = sql_data_queue.get(timeout=1.0)
            except queue.Empty:
                if sql_current_data_size > 0:
                    _upload_temp_file_if_needed()
                continue

            if not sql_current_temp_file:
                continue

            remaining_data = sql_data

            while len(remaining_data) > 0:
                remaining_space = sql_target_size - sql_current_data_size

                if remaining_space <= 0:
                    if not _upload_temp_file_if_needed():
                        sql_sample_count = _write_to_temp_file(
                            remaining_data,
                            sample_rate,
                            sql_start_time,
                            sql_sample_count,
                        )
                        sql_current_data_size += len(remaining_data)
                        break
                    remaining_space = sql_target_size - sql_current_data_size

                write_size = min(len(remaining_data), remaining_space)
                write_size = (write_size // channels) * channels

                if write_size > 0:
                    data_to_write = remaining_data[:write_size]
                    sql_sample_count = _write_to_temp_file(
                        data_to_write, sample_rate, sql_start_time, sql_sample_count
                    )
                    sql_current_data_size += write_size

                    remaining_data = remaining_data[write_size:]

                    if sql_current_data_size >= sql_target_size:
                        if not _upload_temp_file_if_needed():
                            break
                else:
                    if not _upload_temp_file_if_needed():
                        sql_sample_count = _write_to_temp_file(
                            remaining_data,
                            sample_rate,
                            sql_start_time,
                            sql_sample_count,
                        )
                        sql_current_data_size += len(remaining_data)
                        break

            sql_data_queue.task_done()

        except Exception as e:
            error(f"SQL writer loop error: {e}")
            time.sleep(0.1)


def run_flask_server(port: int = 8080):
    """在獨立執行緒中執行 Flask 伺服器"""
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


def main():
    """主函數（程式入口點）"""
    parser = argparse.ArgumentParser(
        description='PET-7H24M Real-time Data Visualization System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  python src/main.py              # 使用預設 port 8080
  python src/main.py --port 3000  # 使用自訂 port 3000
  python src/main.py -p 9000      # 使用自訂 port 9000
        """
    )
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=8080,
        help='Flask 伺服器監聽的埠號（預設: 8080）'
    )
    
    args = parser.parse_args()
    port = args.port
    
    if not (1 <= port <= 65535):
        error(f"無效的埠號: {port}，請使用 1-65535 之間的數字")
        sys.exit(1)
    
    info("=" * 60)
    info("PET-7H24M Real-time Data Visualization System")
    info("=" * 60)
    info(f"Web interface will be available at http://0.0.0.0:{port}/")
    info("Press Ctrl+C to stop the server")
    info("=" * 60)

    flask_thread = threading.Thread(target=run_flask_server, args=(port,), daemon=True)
    flask_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        info("\nShutting down server...")
        global is_collecting, daq_instance, csv_writer_instance, sql_uploader_instance
        if is_collecting:
            is_collecting = False
            if daq_instance:
                daq_instance.stop_reading()
            if csv_writer_instance:
                csv_writer_instance.close()
            if sql_uploader_instance:
                sql_uploader_instance.close()
        info("Server has been shut down")


if __name__ == "__main__":
    main()
