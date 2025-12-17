from __future__ import print_function
import platform
import ipaddress
import sys
from ctypes import *

from sys import platform
if platform == "linux" or platform == "linux2":
    #libc = cdll.LoadLibrary('libc.so.6')
    #dll = CDLL("./libhsdaq.so")
    libc=cdll.LoadLibrary
    dll = libc("./libhsdaq.so")    
elif platform == "win32":
    import msvcrt
    dll = CDLL("HSDAQ.dll")
    #import os
    #import ctypes
    #from ctypes.util import find_library
    #print(os.getcwd())
    #os.add_dll_directory(os.getcwd())
    #name = find_library(".\HSDAQ.dll")
    #dll = ctypes.cdll.LoadLibrary(".\HSDAQ.dll")
    #dll = CDLL(os.path.abspath(os.path.join(os.path.dirname(__file__), "DLLs", "HSDAQ.dll")))
#elif platform == "darwin":
    # OS X
#import platform
#platform.machine()
#AMD64
    
#IP="10.0.8.223"
chcnt=2
Gain=0
triggermode=0
samplerate=1000
targetCnt=0
DatatransMethod=0
AutoRun=0
BufferStatus=0
BufferCnt=0
fdatabuffer = [1.0]

buf = create_string_buffer(128)
    
dll.HS_GetSDKVersion.argtypes=c_char_p,
dll.HS_GetSDKVersion.restype=None 
dll.HS_GetSDKVersion(buf)
print('ver='+buf.value.decode("utf-8"))