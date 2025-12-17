/******************************************************************************/
Python 是一種解釋型、面向對象的高級編程語言，具有動態語義，它可用於一系列應用，
包括數據科學、軟件等。使用 NumPy、pandas 和 MatplotLib 包讓您輕鬆分析大數據，
可視化結果以快速提供最佳解決方案
 
  先在Linux平台安裝Python，即可創建python程式並調用libhsdaq 庫式庫
  存取 PET-7H16M/PET-7H24M/PET-AR400 模具。
/******************************************************************************/
將linux_python3_SDK_Demo.tar.bz22檔案copy 至Linux 環境目錄內, 以下命令解壓縮
tar xvfj linux_python3_SDK_Demo.tar.bz2

目錄檔結構
\PYTHON_DEMO
\PET-7H16M
├─LinuxArm32
│  ├─ET7H16_AI_Buffer_Continue
│  ├─ET7H16_N_Sample_float
│  └─sysinfo
├─LinuxArm64
│  ├─ET7H16_AI_Buffer_Continue
│  ├─ET7H16_N_Sample_float
│  └─sysinfo
└─Linuxx64
    ├─ET7H16_AI_Buffer_Continue
    ├─ET7H16_N_Sample_float
    └─sysinfo
\PET-7H24M
├─LinuxArm32
│  ├─ET7H24_AI_Buffer_Continue
│  ├─ET7H24_N_Sample_float
│  └─sysinfo
├─LinuxArm64
│  ├─ET7H24_AI_Buffer_Continue
│  ├─ET7H24_N_Sample_float
│  └─sysinfo
└─Linuxx64
    ├─ET7H24_AI_Buffer_Continue
    ├─ET7H24_N_Sample_float
    └─sysinfo    
\PET-AR400
├─LinuxArm32
│  ├─ARx00_AI_Buffer_Continue
│  ├─ARx00_N_Sample_float
│  └─sysinfo
├─LinuxArm64
│  ├─ARx00_AI_Buffer_Continue
│  ├─ARx00_N_Sample_float
│  └─sysinfo
└─Linuxx64
    ├─ARx00_AI_Buffer_Continue
    ├─ARx00_N_Sample_float
    └─sysinfo  
    
Build Python demo
以LinuxArm64平台 ET7H16_AI_Buffer_Continue demo為例

1.將路徑切換至\python_demo\PET-7H16M\LinuxArm64\ET7H16_AI_Buffer_Continue

將Libhsdaq.so檔案拷貝至 
\python_demo\PET-7H16M\LinuxArm64\ET7H16_AI_Buffer_Continue

執行命令
# python3 ET7H16_AI_Buffer_Continue.py 10.1.107.111
Number of arguments:  2
10.1.107.111 is a correct IP4 address.
error code: 0x0
CH:2
Gain:0
Mode:0
Samplerate:1000
TargetCnt:0
Press 'Q' to stop scan
0.0,0.000305175781255003051757812555
Q
End
#-------------------------------------------------------------------------------
Python 安裝

在 Linux 上安裝官方 Python 發行版有兩種方法：

從包管理器安裝：這是最常見的安裝方法
在大多數 Linux 發行版上。 它涉及從命令行運行命令。

從source code構建：這種方法比使用包管理器更困難。
它涉及從命令行運行一系列命令以及製作
確保安裝了正確的依賴項來編譯 Python 源代碼

Ubuntu 18.04、Ubuntu 20.04 及更高版本：
要安裝 3.8 版，請打開終端應用程序並鍵入以下命令：

$ sudo apt-get 更新
$ sudo apt-get install python3-all

其他平台請參考網絡資源安裝python