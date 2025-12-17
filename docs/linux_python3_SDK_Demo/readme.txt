/******************************************************************************/
Python is an interpreted, object-oriented high-level programming language with
Dynamic semantics, it can be used in a range of applications, including
Data science, software, etc.
Use NumPy, pandas and MatplotLib packages to allow you to easily analyze big data,
Visualize the results to quickly provide the best solution
 
 Install Python on Linux platform first, and you can create python program 
 calling  libhsdaq library to access  PET-7H16M/PET-7H24M/PET-AR400 module.
/******************************************************************************/
Copy the linux_python3_SDK_Demo.tar.bz22 file to the Linux environment 
directory, and unzip it with the following command 
tar xvfj linux_python3_SDK_Demo.tar.bz2

Directory file structure
\PYTHON_DEMO
\PET-7H16M
¢u¢wLinuxArm32
¢x  ¢u¢wET7H16_AI_Buffer_Continue
¢x  ¢u¢wET7H16_N_Sample_float
¢x  ¢|¢wsysinfo
¢u¢wLinuxArm64
¢x  ¢u¢wET7H16_AI_Buffer_Continue
¢x  ¢u¢wET7H16_N_Sample_float
¢x  ¢|¢wsysinfo
¢|¢wLinuxx64
    ¢u¢wET7H16_AI_Buffer_Continue
    ¢u¢wET7H16_N_Sample_float
    ¢|¢wsysinfo
\PET-7H24M
¢u¢wLinuxArm32
¢x  ¢u¢wET7H24_AI_Buffer_Continue
¢x  ¢u¢wET7H24_N_Sample_float
¢x  ¢|¢wsysinfo
¢u¢wLinuxArm64
¢x  ¢u¢wET7H24_AI_Buffer_Continue
¢x  ¢u¢wET7H24_N_Sample_float
¢x  ¢|¢wsysinfo
¢|¢wLinuxx64
    ¢u¢wET7H24_AI_Buffer_Continue
    ¢u¢wET7H24_N_Sample_float
    ¢|¢wsysinfo    
\PET-AR400
¢u¢wLinuxArm32
¢x  ¢u¢wARx00_AI_Buffer_Continue
¢x  ¢u¢wARx00_N_Sample_float
¢x  ¢|¢wsysinfo
¢u¢wLinuxArm64
¢x  ¢u¢wARx00_AI_Buffer_Continue
¢x  ¢u¢wARx00_N_Sample_float
¢x  ¢|¢wsysinfo
¢|¢wLinuxx64
    ¢u¢wARx00_AI_Buffer_Continue
    ¢u¢wARx00_N_Sample_float
    ¢|¢wsysinfo  

Build Python demo
Take the LinuxArm64 platform / ET7H16_AI_Buffer_Continue demo as an example

1.Change the path to \python_demo\PET-7H16M\LinuxArm64\ET7H16_AI_Buffer_Continue

copy Libhsdaq.so to 
\python_demo\PET-7H16M\LinuxArm64\ET7H16_AI_Buffer_Continue

Execute the command 
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
Python Installation

There are two ways to install the official Python distribution on Linux:

Install from a package manager: This is the most common installation method 
on most Linux distributions. It involves running a command from the command line.

Build from source code: This method is more difficult than using a package manager. 
It involves running a series of commands from the command line as well as making 
sure you have the correct dependencies installed to compile the Python source code

Ubuntu 18.04, Ubuntu 20.04 and above: 
To install version 3.8, open a terminal application and type the following commands:

$ sudo apt-get update
$ sudo apt-get install python3-all

For other platforms, please refer to network resources to install python
