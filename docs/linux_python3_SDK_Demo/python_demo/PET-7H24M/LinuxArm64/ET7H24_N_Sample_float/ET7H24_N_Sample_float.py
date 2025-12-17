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
elif platform == "win32"or platform == "win64":
    import os
    import ctypes
    from ctypes.util import find_library
    #print(os.getcwd())
    os.add_dll_directory(os.getcwd())
    #name = find_library(".\HSDAQ.dll")
    dll = ctypes.cdll.LoadLibrary(".\HSDAQ.dll")
#elif platform == "darwin":
    # OS X
#import platform
#platform.machine()
#AMD64

#IP="10.0.8.221"
chcnt=2
Gain=0
triggermode=0
samplerate=1000
targetCnt=1000*2*5 
DatatransMethod=0
AutoRun=0
BufferStatus=0
BufferCnt=0
fdatabuffer = [1.0]

print ("Number of arguments: ", len(sys.argv))

try:
    ips = ipaddress.ip_address(sys.argv[1])
    print('%s is a correct IP%s address.' % (ips, ips.version))

    IP=sys.argv[1]
    #與module連線
    dll.HS_Device_Create.restype=c_void_p
    #先轉成Byte再轉成string(char)
    Hhs = dll.HS_Device_Create(c_char_p(IP.encode('utf-8')))


    #設定採樣參數

    dll.HS_SetAIScanParam.argtypes=c_void_p,c_short,c_short,c_long,c_long,c_short,c_short
    dll.HS_SetAIScanParam.restype=c_bool
    dll.HS_SetAIScanParam(Hhs,chcnt,Gain,triggermode,samplerate,targetCnt,DatatransMethod,AutoRun)
    print('error code: '+hex(dll.HS_GetLastError()))
    chcnt=c_short()
    Gain=c_short()
    triggermode=c_short()
    samplerate=c_long()
    targetCnt=c_long()
    DatatransMethod=c_short()
    AutoRun=c_short()
    
    #HS_GetAIScanParam(HANDLE obj, short *pacerChCnt, short *pacerGain, short *triggerMode, long *sampleRate, unsigned long *targetCnt, short *DataTransMethod, short *AutoRun);
    #取得module目前參數設定
    dll.HS_GetAIScanParam.argtypes=c_void_p,
    dll.HS_GetAIScanParam.restype=c_bool
    dll.HS_GetAIScanParam(Hhs,byref(chcnt),byref(Gain),byref(triggermode),byref(samplerate),byref(targetCnt),byref(DatatransMethod),byref(AutoRun))
    print('CH:'+str(chcnt.value))
    print('Gain:'+str(Gain.value))
    print('Mode:'+str(triggermode.value))
    print('Samplerate:'+str(samplerate.value))
    print('TargetCnt:'+str(targetCnt.value))
    
    
    #開始採樣
    dll.HS_StartAIScan.argtypes=c_void_p,
    dll.HS_StartAIScan(Hhs)
    dll.HS_GetAIBufferStatus.argtypes=c_void_p,
    dll.HS_StopAIScan.argtypes=c_void_p,
    dll.HS_GetAIBuffer.argtypes=c_void_p,
    run=True
    while run :
    
        #HS_GetAIBufferStatus(HANDLE obj,WORD *wBufferStatus, DWORD *dwDataCountOnBuffer);
        BufferCnt=c_ulong()
        BufferStatus=c_short()
        #確認Buffer狀態、已傳回筆數
        dll.HS_GetAIBufferStatus(Hhs,byref(BufferStatus),byref(BufferCnt))
        print("\rCnt:"+str(BufferCnt.value),end='\r')
        if ((BufferStatus.value & 0x02) == 0x02):
            print('error code: '+hex(dll.HS_GetLastError()))
            dll.HS_StopAIScan(Hhs)
        else:
            if BufferCnt.value >= targetCnt.value :
                fdatabuffer = (c_float * BufferCnt.value)()
                dll.HS_GetAIBuffer(Hhs,fdatabuffer,BufferCnt.value)
                run=False
    
    
    #結束採樣
    dll.HS_StopAIScan(Hhs)
    print('')
    #印出前1000筆資料，每個ch的資料為1000/2=500筆
    for i in range(0,1000,2):
        print(str(fdatabuffer[i])+','+str(fdatabuffer[i+1]))
      
    #與module結束連線
    dll.HS_Device_Release.argtypes=c_void_p,
    dll.HS_Device_Release(Hhs)
    print('End')

except ValueError:
    print('address/netmask is invalid: %s' % sys.argv[1])
except:
    print('Usage : %s  ip' % sys.argv[0])

