import pyvisa
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
import configparser
import os
from decimal import Decimal
import re
import time
import sys
import numpy as np
from PIL import Image
import random
import string
import ctypes
from tkinter import font


window_name= '[Keysight] MXR/EXR-Series Controller Pro_v1.0.0'

def enable_dpi_awareness_windows():
    """Try to enable DPI awareness on Windows. Call BEFORE creating Tk()."""
    if sys.platform != "win32":
        return False
    try:
        user32 = ctypes.windll.user32
        if hasattr(user32, "SetProcessDpiAwarenessContext"):
            user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            return True
    except Exception:
        pass
    try:
        shcore = ctypes.windll.shcore
        shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        return True
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        return True
    except Exception:
        pass
    return False

# DEVMODE for EnumDisplaySettings
class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", ctypes.c_wchar * 32),
        ("dmSpecVersion", ctypes.c_ushort),
        ("dmDriverVersion", ctypes.c_ushort),
        ("dmSize", ctypes.c_ushort),
        ("dmDriverExtra", ctypes.c_ushort),
        ("dmFields", ctypes.c_uint),
        ("dmOrientation", ctypes.c_short),
        ("dmPaperSize", ctypes.c_short),
        ("dmPaperLength", ctypes.c_short),
        ("dmPaperWidth", ctypes.c_short),
        ("dmScale", ctypes.c_short),
        ("dmCopies", ctypes.c_short),
        ("dmDefaultSource", ctypes.c_short),
        ("dmPrintQuality", ctypes.c_short),
        ("dmColor", ctypes.c_short),
        ("dmDuplex", ctypes.c_short),
        ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short),
        ("dmCollate", ctypes.c_short),
        ("dmFormName", ctypes.c_wchar * 32),
        ("dmLogPixels", ctypes.c_ushort),
        ("dmBitsPerPel", ctypes.c_uint),
        ("dmPelsWidth", ctypes.c_uint),
        ("dmPelsHeight", ctypes.c_uint),
        ("dmDisplayFlags", ctypes.c_uint),
        ("dmDisplayFrequency", ctypes.c_uint),
        ("dmICMMethod", ctypes.c_uint),
        ("dmICMIntent", ctypes.c_uint),
        ("dmMediaType", ctypes.c_uint),
        ("dmDitherType", ctypes.c_uint),
        ("dmReserved1", ctypes.c_uint),
        ("dmReserved2", ctypes.c_uint),
        ("dmPanningWidth", ctypes.c_uint),
        ("dmPanningHeight", ctypes.c_uint),
    ]

def get_primary_physical_resolution_enumdisplay():
    """Return (width, height) of primary display using EnumDisplaySettings (fallback to GetSystemMetrics)."""
    try:
        user32 = ctypes.windll.user32
        enum = user32.EnumDisplaySettingsW
        enum.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.POINTER(DEVMODEW)]
        ENUM_CURRENT_SETTINGS = -1
        dm = DEVMODEW()
        dm.dmSize = ctypes.sizeof(DEVMODEW)
        ok = enum(None, ENUM_CURRENT_SETTINGS, ctypes.byref(dm))
        if ok:
            return int(dm.dmPelsWidth), int(dm.dmPelsHeight)
    except Exception:
        pass
    try:
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return (800, 600)

# ---------- reference list & helper ----------
REFERENCE_RESO = [
    (2560, 1600),  # primary requested reference
    (1920, 1200),
    (1920, 1080),
    (1366, 768),
    (3840, 2160),
    (1280, 800),
]

def pick_reference_by_aspect(mw, mh, refs=REFERENCE_RESO):
    target_ar = mw / mh
    best = None
    best_diff = 1e9
    for (rw, rh) in refs:
        ar = rw / rh
        diff = abs(ar - target_ar)
        if diff < best_diff:
            best_diff = diff
            best = (rw, rh)
    return best


def choose_available_font(root, preferred_list, fallback="TkDefaultFont"):
    avail = set(font.families(root))
    for fam in preferred_list:
        if fam in avail:
            return fam
    return fallback

# 第一個視窗取得scope id並開啟主視窗
def show_main_window(old_scope_ips):
    # 取得scope id
    selected_value = str_scope_ip.get()

    # 新增scope id
    if selected_value and selected_value not in old_scope_ips:
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(os.path.join(os.path.dirname(__file__), 'InitConfig_setup_new.ini'), encoding='utf-8',)
        config.set('Scope_IPs', f'IP_{len(old_scope_ips)-1}', selected_value)

        # 寫回ini
        with open(os.path.join(os.path.dirname(__file__), 'InitConfig_setup_new.ini'), 'w') as configfile:
            config.write(configfile)
        
    # 關閉第一個視窗
    id_window.destroy()
    
    # 創建主視窗
    main_window(scope_ip= selected_value)
    

# =====================================================================================================================================================
def main_window(scope_ip):

    def initialize():
        config_initial = configparser.ConfigParser()
        config_initial.optionxform = str
        config_initial.read(os.path.join(os.path.dirname(__file__), 'InitConfig_setup_new.ini'), encoding='UTF-8',)

        select_VoltScale = config_initial['Scale_Offset_Selected_Values']['VoltScale']
        select_VoltOffset = config_initial['Scale_Offset_Selected_Values']['VoltOffset']
        TimebaseScale = config_initial['Scale_Offset_Config']['TimebaseScale']
        TimebaseOffset = config_initial['Scale_Offset_Config']['TimebaseOffset']
        select_TriggerLevel = config_initial['Scale_Offset_Selected_Values']['TriggerLevel']
        TriggerChan = config_initial['Scale_Offset_Config']['TriggerChan']
        WfmIntensity = config_initial['Scale_Offset_Config']['WfmIntensity']

        DeltaStartEdge = config_initial['Delta_Setup_Config']['DeltaStartEdge']
        DeltaStartNum = config_initial['Delta_Setup_Config']['DeltaStartNum']
        DeltaStartPosition = config_initial['Delta_Setup_Config']['DeltaStartPosition']
        DeltaStopEdge = config_initial['Delta_Setup_Config']['DeltaStopEdge']
        DeltaStopNum = config_initial['Delta_Setup_Config']['DeltaStopNum']
        DeltaStopPosition = config_initial['Delta_Setup_Config']['DeltaStopPosition']

        select_GeneralTopPercent = config_initial['Threshold_Selected_Values']['GeneralTopPercent']
        select_GeneralMiddlePercent = config_initial['Threshold_Selected_Values']['GeneralMiddlePercent']
        select_GeneralBasePercent = config_initial['Threshold_Selected_Values']['GeneralBasePercent']
        select_GeneralTopValue = config_initial['Threshold_Selected_Values']['GeneralTopValue']
        select_GeneralMiddleValue = config_initial['Threshold_Selected_Values']['GeneralMiddleValue']
        select_GeneralBaseValue = config_initial['Threshold_Selected_Values']['GeneralBaseValue']
        select_RFTopPercent = config_initial['Threshold_Selected_Values']['RFTopPercent']
        select_RFBasePercent = config_initial['Threshold_Selected_Values']['RFBasePercent']
        select_RFTopValue = config_initial['Threshold_Selected_Values']['RFTopValue']
        select_RFBaseValue = config_initial['Threshold_Selected_Values']['RFBaseValue']
        SamplingRate = config_initial['Acquisition']['SamplingRate']
        MemoryDepth = config_initial['Acquisition']['MemoryDepth']

        ChanLabel1 = config_initial['Lable_Setup_Config']['ChanLabel1']
        ChanLabel2 = config_initial['Lable_Setup_Config']['ChanLabel2']
        ChanLabel3 = config_initial['Lable_Setup_Config']['ChanLabel3']
        ChanLabel4 = config_initial['Lable_Setup_Config']['ChanLabel4']
        WMeLabel1 = config_initial['Lable_Setup_Config']['WMeLabel1']
        WMeLabel2 = config_initial['Lable_Setup_Config']['WMeLabel2']
        WMeLabel3 = config_initial['Lable_Setup_Config']['WMeLabel3']
        WMeLabel4 = config_initial['Lable_Setup_Config']['WMeLabel4']

        ChanSingle = config_initial['Chan_Delta']['ChanSingle']
        ChanStart = config_initial['Chan_Delta']['ChanStart']
        ChanStop = config_initial['Chan_Delta']['ChanStop']

        # SaveImgFolder = config_initial['Save_Setup_Config']['SaveImgFolder']
        # SaveImgLocation = config_initial['Save_Setup_Config']['SaveImgLocation']
        SaveImgPCFolder = config_initial['Save_Setup_Config']['SaveImgPCFolder']
        SaveImgName = config_initial['Save_Setup_Config']['SaveImgName']
        SaveWMeFolder = config_initial['Save_Setup_Config']['SaveWMeFolder']
        SaveWMeLocation = config_initial['Save_Setup_Config']['SaveWMeLocation']
        SaveWMePCFolder = config_initial['Save_Setup_Config']['SaveWMePCFolder']
        SaveWMeName = config_initial['Save_Setup_Config']['SaveWMeName']

        LoadWMe1 = config_initial['Load_WMemory_Setup_Config']['LoadWMe1']
        LoadWMe2 = config_initial['Load_WMemory_Setup_Config']['LoadWMe2']
        LoadWMe3 = config_initial['Load_WMemory_Setup_Config']['LoadWMe3']
        LoadWMe4 = config_initial['Load_WMemory_Setup_Config']['LoadWMe4']

        setupfile_interface_list = []
        for i in range(len(config_initial['Setupfile_Interface'])):
            setupfile_interface_list.append(config_initial['Setupfile_Interface'][f'Interface_{i}'])
        setupfile_interface_list.append('')

        SetupFileInterface = config_initial['Load_WMemory_Setup_Config']['SetupFileInterface']
        SetupFileClass = config_initial['Load_WMemory_Setup_Config']['SetupFileClass']
        LoadSetup = config_initial['Load_WMemory_Setup_Config']['LoadSetup']

        # ScopeSegment = config_initial['Scope_Server_Segment']['ScopeSegment']
        # PCSegment = config_initial['Scope_Server_Segment']['PCSegment']
        # Segment= [ScopeSegment, PCSegment]

        # strvar_voltage_scale.set(value= select_VoltScale)
        # strvar_voltage_offset.set(value= select_VoltOffset)
        # strvar_timebase_scale.set(value= TimebaseScale)
        # strvar_timebase_offset.set(value= TimebaseOffset)
        # strvar_trigger_level.set(value= select_TriggerLevel)
        # strvar_trigger_channel.set(value= TriggerChan)
        # strvar_waveform_intensity.set(value= WfmIntensity)

        # strvar_start_risefall.set(value= DeltaStartEdge)
        # strvar_start_N_edge.set(value= DeltaStartNum)
        # strvar_start_position.set(value= DeltaStartPosition)
        # strvar_stop_risefall.set(value= DeltaStopEdge)
        # strvar_stop_N_edge.set(value= DeltaStopNum)
        # strvar_stop_position.set(value= DeltaStopPosition)

        # strvar_general_percent_top.set(value= select_GeneralTopPercent)
        # strvar_general_percent_middle.set(value= select_GeneralMiddlePercent)
        # strvar_general_percent_base.set(value= select_GeneralBasePercent)
        # strvar_general_value_top.set(value= select_GeneralTop)
        # strvar_general_value_middle.set(value= select_GeneralMiddle)
        # strvar_general_value_base.set(value= select_GeneralBase)
        # strvar_risefall_percent_top.set(value= select_RFTopPercent)
        # strvar_risefall_percent_base.set(value= select_RFBasePercent)
        # strvar_risefall_value_top.set(value= select_RFTop)
        # strvar_risefall_value_base.set(value= select_RFBase)
        # strvar_sampling_rate.set(value= SamplingRate)
        # strvar_memory_depth.set(value= MemoryDepth)

        # strvar_label_1.set(value= ChanLabel1)
        # strvar_label_2.set(value= ChanLabel2)
        # strvar_label_3.set(value= ChanLabel3)
        # strvar_label_4.set(value= ChanLabel4)
        # strvar_label_5.set(value= WMeLabel1)
        # strvar_label_6.set(value= WMeLabel2)
        # strvar_label_7.set(value= WMeLabel3)
        # strvar_label_8.set(value= WMeLabel4)

        # intvar_channel_single.set(value= int(ChanSingle))
        # intvar_channel_delta_start.set(value= int(ChanStart))
        # intvar_channel_delta_stop.set(value= int(ChanStop))

        # # str_image_folder.set(value= SaveImgFolder)
        # # int_img_path_choice.set(value= SaveImgLocation)
        # strvar_image_pc_folder.set(value= SaveImgPCFolder)
        # strvar_image.set(value= SaveImgName)
        # strvar_wmemory_folder.set(value= SaveWMeFolder)
        # intvar_wmemory_path_choice.set(value= SaveWMeLocation)
        # strvar_wmemory_pc_folder.set(value= SaveWMePCFolder)
        # strvar_other_file.set(value= SaveWMeName)

        # strvar_wmemory_1.set(value= LoadWMe1)
        # strvar_wmemory_2.set(value= LoadWMe2)
        # strvar_wmemory_3.set(value= LoadWMe3)
        # strvar_wmemory_4.set(value= LoadWMe4)
        # strvar_setupfile_interface.set(value= SetupFileInterface)
        # strvar_setupfile_class.set(value= SetupFileClass)
        # strvar_setup.set(value= LoadSetup)
        # # if SetupFileInterface == '' or SetupFileInterface == 'User':
        # #     cbb_setupfile_class.config(state= 'disabled')
        #     # cbb_setup.config(state= 'disabled')
        # combobox_setupfile_interface.config(values= setupfile_interface_list)
        # select_setupfile_interface(event= combobox_setupfile_interface.bind("<<ComboboxSelected>>"), segment_list= Segment)
        # select_setupfile_class(event= combobox_setupfile_class.bind("<<ComboboxSelected>>"), segment_list= Segment)

        # move_mouse_entry_end(entry= entry_wmemory_folder)
        # move_mouse_entry_end(entry= entry_wmemory_pc_folder)
    
        # return Segment


    class MXR:
        pass

    #     # def __init__(self, scope_ip, visa_lib= r'C:\Windows\System32\visa64.dll'):
    #     #     rm = pyvisa.ResourceManager(visa_lib)
    #     #     # self.inst = rm.open_resource(f'TCPIP0::KEYSIGH-{scope_id}::inst0::INSTR')
    #     #     try:
    #     #         self.inst = rm.open_resource(f'TCPIP0::{scope_ip}::inst0::INSTR')
    #     #         self.inst.timeout = 6000
    #     #         idn = self.inst.query('*IDN?').strip()
    #     #         print(f'Connect successfully! / {idn}')
    #     #         time.sleep(0.1)
    #     #         self.inst.write(f':ANALyze:AEDGes 0')
    #     #         time.sleep(0.05)
    #     #     except:
    #     #         warning_root = tk.Tk()
    #     #         warning_root.withdraw()  # 隱藏主視窗
    #     #         connection_fail = messagebox.showinfo("Error", f"Connection Failed.")
    #     #         close_window()
    #     #         # sys.exit()

    #     def acquire_sampling_rate(self, rate): # 科學記號
    #         self.inst.write(f':ACQuire:SRATe:ANALog {rate}')
    #         time.sleep(0.05)

    #     def acquire_memory_depth(self, points_value: int):
    #         self.inst.write(f':ACQuire:POINts:ANALog {points_value}')
    #         time.sleep(0.05)

    #     def add_bookmark(self, choose_type, bookmark, chan):
    #         if choose_type == 1:
    #             self.inst.write(f':DISPlay:BOOKmark:DELete:ALL')
    #             time.sleep(0.05)
    #             self.add_label(chan= chan, label= bookmark)
    #             return
    #         else:
    #             self.inst.write(f':DISPlay:LABel OFF')
    #             time.sleep(0.05)
    #             if bookmark == '':
    #                 self.inst.write(f':DISPlay:BOOKmark{chan}:DELete')

    #             else:
    #                 display_dict= self.judge_channal_wmemory()    
    #                 try:
    #                     is_meas_area= self.inst.query(':MEASure:NAME? MEAS1') 
    #                     time.sleep(0.05)
    #                 except:
    #                     is_meas_area= 0
    #                 is_marker_area= self.inst.query(':MARKer1:ENABle?') 
    #                 time.sleep(0.05)
    #                 if not is_meas_area == '"no meas"\n' or is_marker_area == '1\n':
    #                     interval= 5
    #                 else:
    #                     interval= 3.5
                        
    #                 bookmark_display_list= []
    #                 count= 0
    #                 for cha in display_dict['CHANnel']:
    #                     if cha == chan:
    #                         self.inst.write(f':DISPlay:BOOKmark{chan}:DELete')
    #                         time.sleep(0.05)
    #                         self.inst.write(f':DISPlay:BOOKmark{chan}:SET NONE,"{bookmark}",CHANnel{chan},"",1')
    #                         time.sleep(0.05)
    #                         self.inst.write(f':DISPlay:BOOKmark{chan}:XPOSition {0.01}')
    #                         time.sleep(0.05)
    #                         bookmark_display_list.append(count)
    #                         self.inst.write(f':DISPlay:BOOKmark{chan}:YPOSition {2+interval*count}E-02')
    #                         time.sleep(0.05)
    #                     count+=1
    #                 for wme in display_dict['WMEMory']:
    #                     if wme == chan-4:
    #                         self.inst.write(f':DISPlay:BOOKmark{chan}:DELete')
    #                         time.sleep(0.05)
    #                         self.inst.write(f':DISPlay:BOOKmark{chan}:SET NONE,"{bookmark}",WMEMory{chan-4},"",1')
    #                         time.sleep(0.05)
    #                         self.inst.write(f':DISPlay:BOOKmark{chan}:XPOSition {0.01}')
    #                         time.sleep(0.05)
    #                         bookmark_display_list.append(count)
    #                         self.inst.write(f':DISPlay:BOOKmark{chan}:YPOSition {2+interval*count}E-02')
    #                         time.sleep(0.05)
    #                     count+=1

    #     def add_label(self, chan, label):
    #         display_dict= self.judge_channal_wmemory()
    #         if label == '':
    #             self.inst.write(f':DISPlay:LABel OFF')
    #             time.sleep(0.05)
    #         else:
    #             self.inst.write(f':DISPlay:LABel ON')
    #             time.sleep(0.05)
    #             for cha in display_dict['CHANnel']:
    #                 if cha == chan:
    #                     self.inst.write(f':CHANnel{chan}:LABel "{label}"')
    #                     time.sleep(0.05)
    #             for wme in display_dict['WMEMory']:
    #                 if wme == chan-4:
    #                     self.inst.write(f':WMEMory{chan-4}:LABel "{label}"')
    #                     time.sleep(0.05)

    #     def add_marker(self):
    #         tuple_marker = (boolvar_marker_1, boolvar_marker_2, boolvar_marker_3, boolvar_marker_4, boolvar_marker_5, boolvar_marker_6, 
    #                         boolvar_marker_7, boolvar_marker_8, boolvar_marker_9, boolvar_marker_10, boolvar_marker_11, boolvar_marker_12, 
    #                         )
            
    #         # ans= self.inst.query(':MARKer2:COLor?')
    #         # print(ans)
            
    #         multe_color_list= [
    #             '#FFFF8A00',  # 橘
    #             '#FFFFE4C4',  # 膚
    #             '#FFFFA8BD',  # 粉
    #             '#FF99DAE8',  # 淡藍
    #             '#FFC0C0C0',  # 灰
    #             '#FF8FBC8F'  # 灰綠

    #             '#FFFF8A00',  # 橘
    #             '#FFFDF5E6',  # 淡膚
    #             '#FFFF00FF',  # 亮粉
    #             '#FF00FFFF',  # 水藍
    #             '#FFE6E6FA',  # 灰
    #             '#FFB8FFBA',  # 淡綠
    #         ]
    #         single_color_list= [
    #             '#FFFF8A00',  # 橘
    #             '#FFFF8A00',  # 橘
    #             '#FFFF8A00',  # 橘
    #             '#FFFF8A00',  # 橘
    #             '#FFFF8A00',  # 橘
    #             '#FFFF8A00'  # 橘

    #             '#FFFF8A00',  # 橘
    #             '#FFFF8A00',  # 橘
    #             '#FFFF8A00',  # 橘
    #             "#FFFF8A00",  # 橘
    #             '#FFFF8A00',  # 橘
    #             '#FFFF8A00',  # 橘
    #         ]

    #         if boolvar_marker_color.get() == True:
    #             color_list= multe_color_list
    #         else:
    #             color_list= single_color_list

    #         for i, boolvar in enumerate(tuple_marker):
    #             self.inst.write(f':MARKer:MEASurement:MEASurement MEAS{i+1},OFF')
    #             time.sleep(0.05)

    #         c=0
    #         for i, boolvar in enumerate(tuple_marker):
    #             if boolvar.get():
    #                 self.inst.write(f"SYSTem:CONTrol 'MeasSetupSrc1EdgeByRef -{i+1} on'")
    #                 time.sleep(0.05)
    #                 self.inst.write(f"SYSTem:CONTrol 'DoMeas -{i+1}'")
    #                 time.sleep(0.05)
    #                 self.inst.write(f':MARKer:MEASurement:MEASurement MEAS{i+1},ON')
    #                 time.sleep(0.05)
    #                 self.inst.write(f':MARKer{2*c+1}:COLor "{color_list[c]}"')
    #                 time.sleep(0.05)
    #                 self.inst.write(f':MARKer{2*c+2}:COLor "{color_list[c]}"')
    #                 time.sleep(0.05)
    #                 c+=1

    #     def autoscale(self):
    #         self.inst.write(':AUToscale')
    #         time.sleep(0.05)

    #     def call_measurement_delta_time(self, edge_1, num_1, pos_1, edge_2, num_2, pos_2, chan, chan_start, chan_stop, modify_name, timing_name):
    #         displayed_dict= self.judge_channal_wmemory()
    #         for format in displayed_dict:
    #             for channel in displayed_dict[format]:
    #                 if chan_start == channel:
    #                     res_start= f'{format}'
    #                 if chan_stop == channel:
    #                     res_stop= f'{format}'

    #         if chan == 2:
    #             self.inst.write(f':MEASure:DELTatime:DEFine {edge_1},{num_1},{pos_1},{edge_2},{num_2},{pos_2}')
    #             time.sleep(0.05)
    #             self.inst.write(f':MEASure:DELTatime {res_start}{chan_start}, {res_stop}{chan_stop}')
    #             time.sleep(0.05)
                
    #             if modify_name:
    #                 if 'CHAN' in res_start and 'CHAN' in res_stop:
    #                     self.inst.write(f':MEASure:NAME MEAS1,"{timing_name}({chan_start}-{chan_stop})"')
    #                     time.sleep(0.05)
    #                 elif 'CHAN' in res_start and 'WMEM' in res_stop:
    #                     self.inst.write(f':MEASure:NAME MEAS1,"{timing_name}({chan_start}-m{chan_stop})"')
    #                     time.sleep(0.05)
    #                 elif 'WMEM' in res_start and 'CHAN' in res_stop:
    #                     self.inst.write(f':MEASure:NAME MEAS1,"{timing_name}(m{chan_start}-{chan_stop})"')
    #                     time.sleep(0.05)
    #                 else:
    #                     self.inst.write(f':MEASure:NAME MEAS1,"{timing_name}(m{chan_start}-m{chan_stop})"')
    #                     time.sleep(0.05)
                
    #         else:
    #             pass

    #     def call_measurement_dutycycle(self, chan):
    #         command_templates = {
    #             'CHANnel': ':MEASure:DUTYcycle CHANnel{}',
    #             'WMEMory': ':MEASure:DUTYcycle WMEMory{}'
    #         }            
    #         self.call_measurement_function(chan= chan, command_templates= command_templates)

    #     def call_measurement_frequency(self, chan):
    #         command_templates = {
    #             'CHANnel': ':MEASure:FREQuency CHANnel{}',
    #             'WMEMory': ':MEASure:FREQuency WMEMory{}'
    #         }            
    #         self.call_measurement_function(chan= chan, command_templates= command_templates)

    #     def call_measurement_function(self, chan, command_templates: dict):
    #         display_dict= self.judge_channal_wmemory()
    #         for key in command_templates:
    #             if chan in display_dict[key]:
    #                 self.inst.write(command_templates[key].format(chan))
    #                 time.sleep(0.05)            
        
    #     def call_measurement_NCJitter(self, chan, direction):
    #         display_dict= self.judge_channal_wmemory()
    #         for cha in display_dict['CHANnel']:
    #             if cha == chan:
    #                 self.inst.write(f':MEASure:NCJitter CHANnel{cha},{direction},1,1')
    #                 time.sleep(0.05)
    #         for wme in display_dict['WMEMory']:
    #             if wme == chan:
    #                 self.inst.write(f':MEASure:NCJitter WMEMory{cha},{direction},1,1')
    #                 time.sleep(0.05)

    #     def call_measurement_period(self, chan):
    #         command_templates = {
    #             'CHANnel': ':MEASure:PERiod CHANnel{}',
    #             'WMEMory': ':MEASure:PERiod WMEMory{}'
    #         }            
    #         self.call_measurement_function(chan= chan, command_templates= command_templates)
    
    #     def call_measurement_slewrate(self, chan, direction):
    #         display_dict= self.judge_channal_wmemory()
    #         for cha in display_dict['CHANnel']:
    #             if cha == chan:
    #                 self.inst.write(f':MEASure:SLEWrate CHANnel{cha},{direction}')
    #                 time.sleep(0.05)
    #                 self.inst.write(f':MEASure:NAME MEAS1,"{direction} Slew Rate({cha})"')
    #                 time.sleep(0.05)
    #         for wme in display_dict['WMEMory']:
    #             if wme == chan:
    #                 self.inst.write(f':MEASure:SLEWrate WMEMory{wme},{direction}')
    #                 time.sleep(0.05)
    #                 self.inst.write(f':MEASure:NAME MEAS1,"{direction} Slew Rate(m{wme})"')
    #                 time.sleep(0.05)

    #     def call_measurement_tH(self, chan):
    #         command_templates = {
    #             'CHANnel': ':MEASure:PWIDth CHANnel{}',
    #             'WMEMory': ':MEASure:PWIDth WMEMory{}'
    #         }            
    #         self.call_measurement_function(chan= chan, command_templates= command_templates)  

    #     def call_measurement_tL(self, chan):
    #         command_templates = {
    #             'CHANnel': ':MEASure:NWIDth CHANnel{}',
    #             'WMEMory': ':MEASure:NWIDth WMEMory{}'
    #         }            
    #         self.call_measurement_function(chan= chan, command_templates= command_templates)  

    #     def call_measurement_tR(self, chan):
    #         command_templates = {
    #             'CHANnel': ':MEASure:RISetime CHANnel{}',
    #             'WMEMory': ':MEASure:RISetime WMEMory{}'
    #         }            
    #         self.call_measurement_function(chan= chan, command_templates= command_templates)              

    #     def call_measurement_tF(self, chan):
    #         command_templates = {
    #             'CHANnel': ':MEASure:FALLtime CHANnel{}',
    #             'WMEMory': ':MEASure:FALLtime WMEMory{}'
    #         }            
    #         self.call_measurement_function(chan= chan, command_templates= command_templates)              

    #     def call_measurement_VIH(self, chan):
    #         command_templates = {
    #             'CHANnel': ':MEASure:VTOP CHANnel{}',
    #             'WMEMory': ':MEASure:VTOP WMEMory{}'
    #         }            
    #         self.call_measurement_function(chan= chan, command_templates= command_templates)              

    #     def call_measurement_VIL(self, chan):
    #         command_templates = {
    #             'CHANnel': ':MEASure:VBASe CHANnel{}',
    #             'WMEMory': ':MEASure:VBASe WMEMory{}'
    #         }            
    #         self.call_measurement_function(chan= chan, command_templates= command_templates)              

    #     def call_measurement_VPP(self, chan):
    #         command_templates = {
    #             'CHANnel': ':MEASure:VPP CHANnel{}',
    #             'WMEMory': ':MEASure:VPP WMEMory{}'
    #         }            
    #         self.call_measurement_function(chan= chan, command_templates= command_templates)   

    #     def call_measurement_VMAX(self, chan):
    #         command_templates = {
    #             'CHANnel': ':MEASure:VMAX CHANnel{}',
    #             'WMEMory': ':MEASure:VMAX WMEMory{}'
    #         }            
    #         self.call_measurement_function(chan= chan, command_templates= command_templates)   
            
    #     def call_measurement_VMIN(self, chan):
    #         command_templates = {
    #             'CHANnel': ':MEASure:VMIN CHANnel{}',
    #             'WMEMory': ':MEASure:VMIN WMEMory{}'
    #         }            
    #         self.call_measurement_function(chan= chan, command_templates= command_templates)   
            
    #     def check_intensity_setting(self, intensity_value):
    #         self.inst.write(f'SYSTem:CONTrol "WaveformBrt -1 {intensity_value}"')
    #         time.sleep(0.05)

    #     def check_timebase_offset(self, position): # 科學記號
    #         self.inst.write(f':TIMebase:POSition {position}')
    #         time.sleep(0.05)

    #     def check_timebase_scale(self, scale): # 科學記號
    #         self.inst.write(f':TIMebase:SCALe {scale}')
    #         time.sleep(0.05)

    #     def check_trigger_setting(self, chan, level):
    #         res= self.inst.query(f':CHANnel{chan}:DISPlay?')
    #         time.sleep(0.05)
    #         if not res == '1\n':
    #             self.inst.write(f':CHANnel{chan}:DISPlay ON')
    #             time.sleep(0.05)
    #         self.inst.write(f':TRIGger:EDGE:SOURce CHANnel{chan}')
    #         time.sleep(0.05)
    #         self.inst.write(f':TRIGger:LEVel CHANnel{chan},{level}')
    #         time.sleep(0.05)
    #         if not res == '1\n':
    #             self.inst.write(f':CHANnel{chan}:DISPlay OFF')
    #             time.sleep(0.05)

    #     def check_voltage(self, scale, offset): # 科學記號
    #         display_dict= self.judge_channal_wmemory()
    #         for chan in display_dict['CHANnel']:
    #             self.inst.write(f':CHANnel{chan}:SCALe {scale}')
    #             time.sleep(0.05)
    #             self.inst.write(f':CHANnel{chan}:OFFSet {offset}')
    #             time.sleep(0.05)
    #         for wme in display_dict['WMEMory']:
    #             self.inst.write(f':WMEMory{wme}:YRANge {float(scale)*8}')
    #             time.sleep(0.05)
    #             self.inst.write(f':WMEMory{wme}:YOFFset {offset}')
    #             time.sleep(0.05)

    #     def clear_diaplay(self):
    #         self.inst.write(':CDISplay')
    #         time.sleep(0.05)

    #     def clear_wmemory(self, chan, string):
    #         self.inst.write(f':WMEMory{chan}:CLEar')
    #         time.sleep(0.05)
    #         string.set('')

    #     def default(self):
    #         self.inst.write(':SYSTem:PRESet DEFault')
    #         time.sleep(0.05)

    #     def delete_bookmark(self, chan, choose_type):
    #         if choose_type == 1:
    #             self.inst.write(f':DISPlay:LABel OFF')
    #             time.sleep(0.05)
    #         else:
    #             self.inst.write(f':DISPlay:BOOKmark{chan}:DELete')
    #             time.sleep(0.05)

    #     def display_channel(self, chan, bookmark, choose_type):
    #         res= self.inst.query(f':CHANnel{chan}:DISPlay?')
    #         time.sleep(0.05)
    #         if res == '1\n':
    #             self.inst.write(f':CHANnel{chan}:DISPlay OFF')
    #             time.sleep(0.05)
    #             try:
    #                 self.inst.write(f':DISPlay:BOOKmark{chan}:DELete')
    #                 time.sleep(0.05)
    #             except:
    #                 pass
    #         else:
    #             self.inst.write(f':CHANnel{chan}:DISPlay ON')
    #             time.sleep(0.05)
    #             self.add_bookmark(choose_type= choose_type,bookmark= bookmark, chan= chan)

    #     def delete_marker(self):
    #         tuple_marker = (boolvar_marker_1, boolvar_marker_2, boolvar_marker_3, boolvar_marker_4, boolvar_marker_5, boolvar_marker_6, 
    #                         boolvar_marker_7, boolvar_marker_8, boolvar_marker_9, boolvar_marker_10, boolvar_marker_11, boolvar_marker_12, 
    #                         )
        
    #         for i, boolvar in enumerate(tuple_marker):
    #             if boolvar.get():
    #                 self.inst.write(f':MARKer:MEASurement:MEASurement MEASurement{i+1},OFF')
    #                 time.sleep(0.05)

    #     def delete_measurement(self):
    #         tuple_marker = (boolvar_marker_1, boolvar_marker_2, boolvar_marker_3, boolvar_marker_4, boolvar_marker_5, boolvar_marker_6, 
    #                         boolvar_marker_7, boolvar_marker_8, boolvar_marker_9, boolvar_marker_10, boolvar_marker_11, boolvar_marker_12, 
    #                         )
    #         for i, boolvar in enumerate(tuple_marker):
    #             if boolvar.get():
    #                 self.inst.write(f'MEASurement{i+1}:CLEar')
    #                 time.sleep(0.05)

    #     def display_wmemory(self, chan, bookmark, choose_type):
    #         res= self.inst.query(f':WMEMory{chan}:DISPlay?')
    #         time.sleep(0.05)
    #         if res == '1\n':
    #             self.inst.write(f':WMEMory{chan}:DISPlay OFF')
    #             time.sleep(0.05)
    #             try:
    #                 self.inst.write(f':DISPlay:BOOKmark{chan+4}:DELete')
    #                 time.sleep(0.05)
    #             except:
    #                 pass
    #         else:
    #             self.inst.write(f':WMEMory{chan}:DISPlay ON')
    #             time.sleep(0.05)
    #             self.add_bookmark(choose_type= choose_type, bookmark= bookmark, chan= chan+4)
        
    #     def extract_result(self):
    #         meas_name= ['', '', '', '', '', '', '', '', '', '', '', '']
    #         result1= ['', '', '', '', '', '', '', '', '', '', '', '']
    #         result2= ['', '', '', '', '', '', '', '', '', '', '', '']
    #         all_results= self.inst.query(f':MEASure:RESults?')
    #         time.sleep(0.05)
    #         for index, value in enumerate(all_results.split(',')):
    #             if divmod(index, 7)[1] == 0:
    #                 try:
    #                     meas_name[divmod(index, 7)[0]]= value
    #                 except:
    #                     # l_meas_name_1.config(text=f'484超過3個??')
    #                     continue
    #                 if value[0] == 'V':  # 0: Voltage, 1: Time, 2: Slew Rate, 3: Frequency, 4: Duty cycle
    #                     measurement_type = 0 
    #                 elif 'Slew Rate' in value:
    #                     measurement_type = 2
    #                 elif 'Freq' in value:
    #                     measurement_type = 3
    #                 elif 'Duty cycle' in value:
    #                     measurement_type = 4
    #                 elif value == '\n':
    #                     meas_name[divmod(index, 7)[0]] = ''
    #                     continue
    #                 else:
    #                     measurement_type = 1
                
    #             if intvar_result_type.get() == 1:  # 選擇Mean Value
    #                 if divmod(index, 7)[1] == 4:
    #                     if measurement_type == 0:
    #                         final_result_1= self.judge_unit_voltage(value= value)
    #                         final_result_2= ''
    #                     elif measurement_type == 1:
    #                         slew= False
    #                         final_result_1= self.judge_unit_time(value= value, slew= slew)
    #                         final_result_2= ''
    #                     elif measurement_type == 2:
    #                         slew= True
    #                         final_result_1= self.judge_unit_time(value= value, slew= slew)
    #                         final_result_2= ''
    #                     elif measurement_type == 3:
    #                         final_result_1= self.judge_unit_frequency(value= value)
    #                         final_result_2= ''
    #                     elif measurement_type == 4:
    #                         final_result_1 = f"{float(value):.3f}"+' %'
    #                         final_result_2= ''

    #                     try:
    #                         result1[divmod(index, 7)[0]]= final_result_1
    #                         result2[divmod(index, 7)[0]]= final_result_2
    #                     except:
    #                         continue

    #             elif intvar_result_type.get() == 2:  # 選擇Min & Max Value
    #                 if divmod(index, 7)[1] == 2:
    #                     if measurement_type == 0:
    #                         final_result_1= self.judge_unit_voltage(value= value)
    #                     elif measurement_type == 1:
    #                         slew= False
    #                         final_result_1= self.judge_unit_time(value= value, slew= slew)
    #                     elif measurement_type == 2:
    #                         slew= True
    #                         final_result_1= self.judge_unit_time(value= value, slew= slew)
    #                     elif measurement_type == 3:
    #                         final_result_1= self.judge_unit_frequency(value= value)
    #                     elif measurement_type == 4:
    #                         final_result_1 = f"{float(value):.3f}"+' %'

    #                     try:
    #                         result1[divmod(index, 7)[0]]= final_result_1
    #                     except:
    #                         continue

    #                 if divmod(index, 7)[1] == 3:
    #                     if measurement_type == 0:
    #                         final_result_2= self.judge_unit_voltage(value= value)
    #                     elif measurement_type == 1:
    #                         slew= False
    #                         final_result_2= self.judge_unit_time(value= value, slew= slew)
    #                     elif measurement_type == 2:
    #                         slew= True
    #                         final_result_2= self.judge_unit_time(value= value, slew= slew)
    #                     elif measurement_type == 3:
    #                         final_result_2= self.judge_unit_frequency(value= value)
    #                     elif measurement_type == 4:
    #                         final_result_2 = f"{float(value):.3f}"+' %'

    #                     try:
    #                         result2[divmod(index, 7)[0]]= final_result_2
    #                     except:
    #                         continue

    #         label_measurement_name_1.config(text=f'{meas_name[0]}')
    #         text_result_mean_1.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_mean_1.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_mean_1.insert(tk.END, f"{result1[0]}")
    #         text_result_mean_1.config(state=tk.DISABLED)  # 設置為只讀狀態
    #         text_result_minmax_1.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_minmax_1.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_minmax_1.insert(tk.END, f"{result2[0]}")
    #         text_result_minmax_1.config(state=tk.DISABLED)  # 設置為只讀狀態

    #         label_measurement_name_2.config(text=f'{meas_name[1]}')
    #         text_result_mean_2.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_mean_2.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_mean_2.insert(tk.END, f"{result1[1]}")
    #         text_result_mean_2.config(state=tk.DISABLED)  # 設置為只讀狀態
    #         text_result_minmax_2.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_minmax_2.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_minmax_2.insert(tk.END, f"{result2[1]}")
    #         text_result_minmax_2.config(state=tk.DISABLED)  # 設置為只讀狀態
            
    #         label_measurement_name_3.config(text=f'{meas_name[2]}')
    #         text_result_mean_3.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_mean_3.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_mean_3.insert(tk.END, f"{result1[2]}")
    #         text_result_mean_3.config(state=tk.DISABLED)  # 設置為只讀狀態
    #         text_result_minmax_3.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_minmax_3.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_minmax_3.insert(tk.END, f"{result2[2]}")
    #         text_result_minmax_3.config(state=tk.DISABLED)  # 設置為只讀狀態
            
    #         label_measurement_name_4.config(text=f'{meas_name[3]}')
    #         text_result_mean_4.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_mean_4.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_mean_4.insert(tk.END, f"{result1[3]}")
    #         text_result_mean_4.config(state=tk.DISABLED)  # 設置為只讀狀態
    #         text_result_minmax_4.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_minmax_4.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_minmax_4.insert(tk.END, f"{result2[3]}")
    #         text_result_minmax_4.config(state=tk.DISABLED)  # 設置為只讀狀態
            
    #         label_measurement_name_5.config(text=f'{meas_name[4]}')
    #         text_result_mean_5.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_mean_5.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_mean_5.insert(tk.END, f"{result1[4]}")
    #         text_result_mean_5.config(state=tk.DISABLED)  # 設置為只讀狀態
    #         text_result_minmax_5.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_minmax_5.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_minmax_5.insert(tk.END, f"{result2[4]}")
    #         text_result_minmax_5.config(state=tk.DISABLED)  # 設置為只讀狀態
            
    #         label_measurement_name_6.config(text=f'{meas_name[5]}')
    #         text_result_mean_6.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_mean_6.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_mean_6.insert(tk.END, f"{result1[5]}")
    #         text_result_mean_6.config(state=tk.DISABLED)  # 設置為只讀狀態
    #         text_result_minmax_6.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_minmax_6.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_minmax_6.insert(tk.END, f"{result2[5]}")
    #         text_result_minmax_6.config(state=tk.DISABLED)  # 設置為只讀狀態
            
    #         label_measurement_name_7.config(text=f'{meas_name[6]}')
    #         text_result_mean_7.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_mean_7.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_mean_7.insert(tk.END, f"{result1[6]}")
    #         text_result_mean_7.config(state=tk.DISABLED)  # 設置為只讀狀態
    #         text_result_minmax_7.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_minmax_7.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_minmax_7.insert(tk.END, f"{result2[6]}")
    #         text_result_minmax_7.config(state=tk.DISABLED)  # 設置為只讀狀態
            
    #         label_measurement_name_8.config(text=f'{meas_name[7]}')
    #         text_result_mean_8.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_mean_8.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_mean_8.insert(tk.END, f"{result1[7]}")
    #         text_result_mean_8.config(state=tk.DISABLED)  # 設置為只讀狀態
    #         text_result_minmax_8.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_minmax_8.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_minmax_8.insert(tk.END, f"{result2[7]}")
    #         text_result_minmax_8.config(state=tk.DISABLED)  # 設置為只讀狀態
            
    #         label_measurement_name_9.config(text=f'{meas_name[8]}')
    #         text_result_mean_9.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_mean_9.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_mean_9.insert(tk.END, f"{result1[8]}")
    #         text_result_mean_9.config(state=tk.DISABLED)  # 設置為只讀狀態
    #         text_result_minmax_9.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_minmax_9.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_minmax_9.insert(tk.END, f"{result2[8]}")
    #         text_result_minmax_9.config(state=tk.DISABLED)  # 設置為只讀狀態
            
    #         label_measurement_name_10.config(text=f'{meas_name[9]}')
    #         text_result_mean_10.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_mean_10.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_mean_10.insert(tk.END, f"{result1[9]}")
    #         text_result_mean_10.config(state=tk.DISABLED)  # 設置為只讀狀態
    #         text_result_minmax_10.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_minmax_10.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_minmax_10.insert(tk.END, f"{result2[9]}")
    #         text_result_minmax_10.config(state=tk.DISABLED)  # 設置為只讀狀態
            
    #         label_measurement_name_11.config(text=f'{meas_name[10]}')
    #         text_result_mean_11.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_mean_11.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_mean_11.insert(tk.END, f"{result1[10]}")
    #         text_result_mean_11.config(state=tk.DISABLED)  # 設置為只讀狀態
    #         text_result_minmax_11.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_minmax_11.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_minmax_11.insert(tk.END, f"{result2[10]}")
    #         text_result_minmax_11.config(state=tk.DISABLED)  # 設置為只讀狀態
            
    #         label_measurement_name_12.config(text=f'{meas_name[11]}')
    #         text_result_mean_12.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_mean_12.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_mean_12.insert(tk.END, f"{result1[11]}")
    #         text_result_mean_12.config(state=tk.DISABLED)  # 設置為只讀狀態
    #         text_result_minmax_12.config(state=tk.NORMAL)  # 先啟用Text小部件的編輯狀態
    #         text_result_minmax_12.delete(1.0, tk.END)  # 清空當前內容
    #         text_result_minmax_12.insert(tk.END, f"{result2[11]}")
    #         text_result_minmax_12.config(state=tk.DISABLED)  # 設置為只讀狀態
            
    #     def judge_channal_wmemory(self):
    #         display_dict= {'CHANnel': [],'WMEMory': []}
    #         for i in range(1, 5):
    #             chan_res= self.inst.query(f':CHANnel{i}:DISPlay?')
    #             time.sleep(0.05)
    #             wme_res= self.inst.query(f':WMEMory{i}:DISPlay?')
    #             time.sleep(0.05)

    #             if chan_res == '1\n' and not wme_res == '1\n':
    #                 display_dict['CHANnel'].append(i)
    #                 # return 'CHANnel'
    #             if not chan_res == '1\n' and wme_res == '1\n':
    #                 display_dict['WMEMory'].append(i)
    #                 # return 'WMEMory'
    #             if chan_res == '1\n' and wme_res == '1\n':
    #                 display_dict['CHANnel'].append(i)
    #                 display_dict['WMEMory'].append(i)

    #         return display_dict

    #     def judge_unit_frequency(self, value):
    #         pattern = r'([+-]?\d*\.?\d+)E([+-]?\d+)'
    #         match = re.search(pattern, value)
    #         # 提取基數和指數
    #         base = float(match.group(1))
    #         exponent = int(match.group(2))
    #         # 基于不同的指数值进行不同的转换
    #         if exponent == 9:
    #             return f"{base} GHz"
    #         elif exponent == 8:
    #             return f"{base * 100} MHz"
    #         elif exponent == 7:
    #             return f"{base * 10} MHz"
    #         elif exponent == 6:
    #             return f"{base} MHz"
    #         elif exponent == 5:
    #             return f"{base * 100} kHz"
    #         elif exponent == 4:
    #             return f"{base * 10} kHz"
    #         elif exponent == 3:
    #             return f"{base} kHz"
    #         elif exponent == 2:
    #             return f"{base * 100} Hz"
    #         elif exponent == 1:
    #             return f"{base * 10} Hz"
    #         else:
    #             # 如果指数不在指定的范围内，返回原始文本
    #             return f"{base} Hz"

    #     def judge_unit_time(self, value, slew):
    #         pattern = r'([+-]?\d*\.?\d+)E([+-]?\d+)'
    #         match = re.search(pattern, value)
    #         # 提取基數和指數
    #         base = float(match.group(1))
    #         exponent = int(match.group(2))
    #         if slew:
    #             if exponent == 3:
    #                 return f"{base} V/ms"
    #             elif exponent == 4:
    #                 return f"{base * 10} V/ms"
    #             elif exponent == 5:
    #                 return f"{base * 100} V/ms"
    #             elif exponent == 6:
    #                 return f"{base} V/us"
    #             elif exponent == 7:
    #                 return f"{base * 10} V/us"
    #             elif exponent == 8:
    #                 return f"{base * 100} V/us"
    #             elif exponent == 9:
    #                 return f"{base} V/ns"
    #             elif exponent == 10:
    #                 return f"{base * 10} V/ns"
    #             elif exponent == 11:
    #                 return f"{base * 100} V/ns"
    #             elif exponent == 12:
    #                 return f"{base} V/ps"
    #             elif exponent == 13:
    #                 return f"{base * 10} V/ps"
    #             elif exponent == 14:
    #                 return f"{base * 100} V/ps"
    #             elif exponent == 15:
    #                 return f"{base} V/fs"
    #             elif exponent == 16:
    #                 return f"{base * 10} V/fs"
    #             elif exponent == 17:
    #                 return f"{base * 100} V/fs"
    #             else:
    #                 # 如果指數不在指定的範圍内，返回原始字串
    #                 return f"{base} V/s"
    #         else:
    #             if exponent == -9:
    #                 return f"{base} ns"
    #             elif exponent == -8:
    #                 return f"{base * 10} ns"
    #             elif exponent == -7:
    #                 return f"{base * 100} ns"
    #             elif exponent == -6:
    #                 return f"{base} us"
    #             elif exponent == -5:
    #                 return f"{base * 10} us"
    #             elif exponent == -4:
    #                 return f"{base * 100} us"
    #             elif exponent == -3:
    #                 return f"{base} ms"
    #             elif exponent == -2:
    #                 return f"{base * 10} ms"
    #             elif exponent == -1:
    #                 return f"{base * 100} ms"
    #             elif exponent == -12:
    #                 return f"{base} ps"
    #             elif exponent == -11:
    #                 return f"{base * 10} ps"
    #             elif exponent == -10:
    #                 return f"{base * 100} ps"
    #             elif exponent == -15:
    #                 return f"{base} fs"
    #             elif exponent == -14:
    #                 return f"{base * 10} fs"
    #             elif exponent == -13:
    #                 return f"{base * 100} fs"
    #             else:
    #                 # 如果指數不在指定的範圍内，返回原始字串
    #                 return f'{base} s'
                
    #     def judge_unit_voltage(self, value):
    #         pattern = r'([+-]?\d*\.?\d+)E([+-]?\d+)'
    #         match = re.search(pattern, value)
    #         # 提取基數和指數
    #         base = float(match.group(1))
    #         exponent = int(match.group(2))
    #         # 基于不同的指数值进行不同的转换
    #         if exponent == -3:
    #             return f"{base} mV"
    #         elif exponent == -2:
    #             return f"{base * 10} mV"
    #         elif exponent == -1:
    #             return f"{base * 100} mV"
    #         else:
    #             # 如果指数不在指定的范围内，返回原始文本
    #             return f"{base} V"

    #     def load_setup(self, folder, scope_segment, setup_name, choose_type, file_path_choice, g_top, g_middle, g_base, g_top_percent, g_middle_percent, g_base_percent, rf_top, rf_base, rf_top_percent, rf_base_percent):
            
    #         if file_path_choice == 2: # Server
                
    #             if strvar_setupfile_interface.get() == 'User':
    #                 total_folder_path = folder
    #             elif strvar_setupfile_interface.get() == '':
    #                 total_folder_path = folder
    #             else: 
    #                 total_folder_path = f'{scope_segment}:/#_Eric Team/02_Penny/Setup_Files_Collection/{strvar_setupfile_interface.get()}/{strvar_setupfile_class.get()}'

    #         else: # Desktop
    #             total_folder_path = f"C:/Users/Administrator/Desktop/{folder}"

    #         # 記錄示波器timebase設定
    #         time_position= self.inst.query(':TIMebase:POSition?').rstrip('\n')
    #         time.sleep(0.05)
    #         time_scale= self.inst.query(':TIMebase:SCALe?').rstrip('\n')
    #         time.sleep(0.05)

    #         # 記錄示波器voltage設定
    #         temp_voltscale_dict= {}
    #         temp_voltoffset_dict= {}
    #         display_dict= self.judge_channal_wmemory()
    #         for chan in display_dict['CHANnel']:
    #             volt_scale= self.inst.query(f':CHANnel{chan}:SCALe?')
    #             time.sleep(0.05)
    #             temp_voltscale_dict[chan]= volt_scale
    #             volt_offset= self.inst.query(f':CHANnel{chan}:OFFSet?')
    #             time.sleep(0.05)
    #             temp_voltoffset_dict[chan]= volt_offset
    #         for wme in display_dict['WMEMory']:
    #             volt_scale= self.inst.query(f':WMEMory{wme}:YRANge?').rstrip('\n')
    #             time.sleep(0.05)
    #             temp_voltscale_dict[wme]= float(volt_scale)/8
    #             volt_offset= self.inst.query(f':WMEMory{wme}:YOFFset?').rstrip('\n')
    #             time.sleep(0.05)
    #             temp_voltoffset_dict[wme]= volt_offset

    #         # 記錄示波器trigger設定
    #         trig_chan= self.inst.query(f':TRIGger:EDGE:SOURce?').rstrip('\n')
    #         time.sleep(0.05)
    #         trig_chan= trig_chan.lstrip("CHAN")
    #         trig_level= self.inst.query(f':TRIGger:LEVel? CHANnel{trig_chan}').rstrip('\n')
    #         time.sleep(0.05)

    #         # 呼叫設定檔
    #         self.inst.write(f':DISK:LOAD "{total_folder_path}/{setup_name}.set"')
    #         time.sleep(0.05)

    #         # 依據勾選狀態修改數值
    #         if boolvar_setup_timebase.get() == True:
    #             # 依照示波器畫面的timebase
    #             self.check_timebase_scale(scale= time_scale)
    #             self.check_timebase_offset(position= time_position)
    #         if boolvar_setup_volt.get() == True:
    #             display_dict= self.judge_channal_wmemory()
    #             # 依照示波器畫面的Voltage
    #             for chan in display_dict['CHANnel']:
    #                 self.inst.write(f':CHANnel{chan}:SCALe {temp_voltscale_dict[chan]}')
    #                 time.sleep(0.05)
    #                 self.inst.write(f':CHANnel{chan}:OFFSet {temp_voltoffset_dict[chan]}')
    #                 time.sleep(0.05)
    #             for wme in display_dict['WMEMory']:
    #                 self.inst.write(f':WMEMory{wme}:YRANge {float(temp_voltscale_dict[wme])*8}')
    #                 time.sleep(0.05)
    #                 self.inst.write(f':WMEMory{wme}:YOFFset {temp_voltoffset_dict[wme]}')
    #                 time.sleep(0.05)

    #             # 依照示波器畫面的trigger
    #             res= self.inst.query(f':CHANnel{trig_chan}:DISPlay?')
    #             time.sleep(0.05)
    #             if not res == '1\n':
    #                 self.inst.write(f':CHANnel{trig_chan}:DISPlay ON')
    #                 time.sleep(0.05)
    #             self.inst.write(f':TRIGger:EDGE:SOURce CHANnel{trig_chan}')
    #             time.sleep(0.05)
    #             self.inst.write(f':TRIGger:LEVel CHANnel{trig_chan},{trig_level}')
    #             time.sleep(0.05)
    #             if not res == '1\n':
    #                 self.inst.write(f':CHANnel{trig_chan}:DISPlay OFF')
    #                 time.sleep(0.05)
 
    #             # self.volt_check(scale= volt_scale, offset= volt_offset)
    #             # self.trig_check(chan= trig_chan, level= trig_level)
                
    #             # 依照GUI的threshold
    #             self.set_general_threshold(g_top= g_top, g_middle= g_middle, g_base= g_base, g_top_percent= g_top_percent, g_middle_percent= g_middle_percent, g_base_percent= g_base_percent)
    #             self.set_risefall_threshold(rf_top= rf_top, rf_base= rf_base, rf_top_percent= rf_top_percent, rf_base_percent= rf_base_percent)

    #         if boolvar_setup_label.get() == True:
    #             # 依照GUI的label
    #             label_content = [
    #                 strvar_label_1, strvar_label_2, strvar_label_3, strvar_label_4, 
    #                 strvar_label_5, strvar_label_6, strvar_label_7, strvar_label_8, 
    #                 ]
    #             for i in range(8):
    #                 self.add_bookmark(choose_type= choose_type, bookmark= label_content[i].get().rstrip('\n'), chan= i+1)

    #     def load_wmemory(self, chan, folder, wme_name, file_path_choice):
    #         self.inst.write(f':WMEMory:TIETimebase 1')
    #         time.sleep(0.05)
    #         self.inst.write(f':DISPlay:SCOLor WMEMory1,17,100,100')
    #         time.sleep(0.05)
    #         self.inst.write(f':DISPlay:SCOLor WMEMory2,38,100,84')
    #         time.sleep(0.05)
    #         self.inst.write(f':DISPlay:SCOLor WMEMory3,60,80,100')
    #         time.sleep(0.05)
    #         self.inst.write(f':DISPlay:SCOLor WMEMory4,94,100,100')
    #         time.sleep(0.05)
            
    #         if file_path_choice == 2:
    #             total_folder_path = folder
    #         else:
    #             total_folder_path = f"C:/Users/Administrator/Desktop/{folder}"

    #         self.inst.write(f':DISK:LOAD "{total_folder_path}/{wme_name}.h5",WMEMory{chan},OFF')
    #         time.sleep(0.05)

    #     def measure_all_edge(self):
    #         ans= self.inst.query(':ANALyze:AEDGes?')
    #         time.sleep(0.05)
    #         if ans == '0\n':
    #             button_measure_all_edge['text'] = "Meas All Edge: ON"
    #             self.inst.write(f':ANALyze:AEDGes 1')
    #             time.sleep(0.05)
    #         else:
    #             button_measure_all_edge['text'] = "Meas All Edge: OFF"
    #             self.inst.write(f':ANALyze:AEDGes 0')
    #             time.sleep(0.05)
        
    #     def run(self):
    #         self.inst.write(':RUN')
    #         time.sleep(0.05)

    #     def save_pc_image(self, pc_folder, file_name):
    #         screen_data = np.array(self.inst.query_binary_values(":DISPlay:DATA? PNG", datatype = 's', container = bytes))
    #         time.sleep(0.05)

    #         if not os.path.exists(pc_folder):
    #             ask_root = tk.Tk()
    #             ask_root.withdraw()  # 隱藏主視窗
    #             ask_result = messagebox.askyesno("Warning", f"資料夾不存在，是否新增？")
    #             ask_root.destroy()
                
    #             if not ask_result:
    #                 ask_root = tk.Tk()
    #                 ask_root.withdraw()  # 隱藏主視窗
    #                 messagebox.showinfo("Warning", f'檔案未儲存')
    #                 # print("檔案未保存。")
    #                 return     
    #             os.mkdir(pc_folder) 

    #         if os.path.exists(f"{pc_folder}/{file_name}.png"):
    #             ask_root = tk.Tk()
    #             ask_root.withdraw()  # 隱藏主視窗
    #             ask_result = messagebox.askyesno("Warning", f"檔案已經存在，是否覆蓋？")
    #             ask_root.destroy()
                
    #             if not ask_result:
    #                 # print("檔案未保存。")
    #                 ask_root = tk.Tk()
    #                 ask_root.withdraw()  # 隱藏主視窗
    #                 messagebox.showinfo("Warning", f'檔案未儲存')
    #                 return     
    #         temp_img_name= ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    #         temp_folder= fr'{os.path.dirname(__file__)}/Temp'
    #         if not os.path.exists(temp_folder):
    #             os.mkdir(temp_folder) 
                
    #         f_img = open(f"{temp_folder}/{temp_img_name}.png", "wb")
    #         f_img.write(bytearray(screen_data))
    #         f_img.close()

    #         rgba_to_rgb_composite(f"{temp_folder}/{temp_img_name}.png", f"{pc_folder}/{file_name}.png", background=(0,0,0))

    #     def save_pc_waveform(self, folder, pc_folder, file_name):            

    #         full_path = rf"C:/Users/Administrator/Desktop/{folder}/{file_name}.png"
    #         full_path = full_path.replace('\\', '/')
    #         # print(full_path)
    #         data = b''
    #         message = f':DISK:GETFILE? "{full_path}"'
    #         data = self.inst.query_binary_values(message=message, datatype='B', header_fmt='ieee', container=bytes)
    #         time.sleep(0.05)

    #         if not os.path.exists(pc_folder):
    #             ask_root = tk.Tk()
    #             ask_root.withdraw()  # 隱藏主視窗
    #             ask_result = messagebox.askyesno("Warning", f"資料夾不存在，是否新增？")
    #             ask_root.destroy()
                
    #             if not ask_result:
    #                 ask_root = tk.Tk()
    #                 ask_root.withdraw()  # 隱藏主視窗
    #                 messagebox.showinfo("Warning", f'檔案未儲存')
    #                 # print("檔案未保存。")
    #                 return     
    #             os.mkdir(pc_folder) 

    #         if os.path.exists(f"{pc_folder}/{file_name}.png"):
    #             ask_root = tk.Tk()
    #             ask_root.withdraw()  # 隱藏主視窗
    #             ask_result = messagebox.askyesno("Warning", f"檔案已經存在，是否覆蓋？")
    #             ask_root.destroy()
                
    #             if not ask_result:
    #                 # print("檔案未保存。")
    #                 ask_root = tk.Tk()
    #                 ask_root.withdraw()  # 隱藏主視窗
    #                 messagebox.showinfo("Warning", f'檔案未儲存')
    #                 return     
           
    #         with open(f"{pc_folder}/{file_name}.png", 'wb') as f:
    #             f.write(data)

    #     def save_pc_wmemory(self, folder, pc_folder, file_name, ext_type):
    #         if ext_type == 1:
    #             ext = 'h5'
    #         else:
    #             ext = 'set'

    #         full_path = f"C:/Users/Administrator/Desktop/{folder}/{file_name}.{ext}"
    #         data = b''
    #         message = ':DISK:GETFILE? "' + full_path + '"'
    #         data = self.inst.query_binary_values(message= message, datatype= 'B', header_fmt= 'ieee', container= bytes)
    #         time.sleep(0.05)
            
    #         if not os.path.exists(pc_folder):
    #             ask_root = tk.Tk()
    #             ask_root.withdraw()  # 隱藏主視窗
    #             ask_result = messagebox.askyesno("Warning", f"資料夾不存在，是否新增？")
    #             ask_root.destroy()
                
    #             if not ask_result:
    #                 ask_root = tk.Tk()
    #                 ask_root.withdraw()  # 隱藏主視窗
    #                 messagebox.showinfo("Warning", f'檔案未儲存')
    #                 # print("檔案未保存。")
    #                 return     
    #             os.mkdir(pc_folder) 

    #         if os.path.exists(f"{pc_folder}/{file_name}.{ext}"):
    #             ask_root = tk.Tk()
    #             ask_root.withdraw()  # 隱藏主視窗
    #             ask_result = messagebox.askyesno("Warning", f"檔案已經存在，是否覆蓋？")
    #             ask_root.destroy()
                
    #             if not ask_result:
    #                 # print("檔案未保存。")
    #                 ask_root = tk.Tk()
    #                 ask_root.withdraw()  # 隱藏主視窗
    #                 messagebox.showinfo("Warning", f'檔案未儲存')
    #                 return     
           
    #         with open(f"{pc_folder}/{file_name}.{ext}", 'wb') as f:
    #             f.write(data)

    #     def save_scope_file(self, chan, folder, current_file_name, ext_type, path_choice):
    #         # 清空狀態
    #         self.inst.write('*CLS')
    #         time.sleep(0.05)
    #         # error messenge
    #             # 113 This directory is not valid.
    #             # -256 File name not found
    #             # -257 File name error
    #             # -410 Query INTERRUPTED
    #             # -420 Query UNTERMINATED
    #             # 0 No error

    #         if path_choice == 2:
    #             folder_total_path = folder
    #         else:
    #             folder_total_path = f"C:/Users/Administrator/Desktop/{folder}"

    #         # 資料夾是否存在
    #         self.inst.query(f':DISK:DIRectory? "{folder_total_path}"')
    #         time.sleep(0.05)
    #         error_messenge=self.inst.query(f':SYSTem:ERRor?')
    #         time.sleep(0.05)
    #         # print(error_messenge)
    #         if error_messenge == '-256\n' or error_messenge == '113\n' or error_messenge == '-257\n':
    #             ask_scp_root = tk.Tk()
    #             ask_scp_root.withdraw()  # 隱藏主視窗
    #             ask_scp_result = messagebox.askyesno("Warning", f"資料夾不存在，是否新增？")
    #             ask_scp_root.destroy()
                
    #             if not ask_scp_result:
    #                 ask_scp_root = tk.Tk()
    #                 ask_scp_root.withdraw()  # 隱藏主視窗
    #                 messagebox.showinfo("Warning", f'檔案未儲存')
    #                 # print("檔案未保存。")
    #                 return     
    #             # 新建資料夾
    #             folder_total_path= folder_total_path.replace("/", "\\")
    #             # print(folder_total_path)
    #             split_folder_list= folder_total_path.split('\\')

    #             folder= split_folder_list[0]
    #             for split in split_folder_list[1:]:
    #                 folder= f'{folder}\\{split}'
    #                 self.inst.query(f':DISK:DIRectory? "{folder}"')
    #                 time.sleep(0.05)
    #                 response= self.inst.query(f':SYSTem:ERRor?')
    #                 time.sleep(0.05)
    #                 # print(response)
    #                 if response == '-256\n' or response == '113\n' or response == '-257\n':
    #                     self.inst.write(f':DISK:MDIRectory "{folder}"')
    #                     time.sleep(0.05)

    #         # 資料夾全部內容
    #         folder_content= self.inst.query(f':DISK:DIRectory? "{folder_total_path}"')
    #         time.sleep(0.05)

    #         # 判斷存.h5或.set
    #         if ext_type == 1:
    #             # 使用正則表達式來匹配所有 .h5 檔案名稱
    #             files = re.findall(r'\b[\w-]+\.(?:h5)\b', folder_content)
    #             ext= 'h5'
    #             command= f':DISK:SAVE:WAVeform CHANnel{chan},"{folder_total_path}/{current_file_name}",H5,OFF'
    #         else:
    #             # 使用正則表達式來匹配所有 .set 檔案名稱
    #             files = re.findall(r'\b[\w-]+\.(?:set)\b', folder_content)
    #             ext= 'set'
    #             command= f':DISK:SAVE:SETup "{folder_total_path}/{current_file_name}"'

    #         for file_name in files:
    #             if f'{current_file_name}.{ext}' == file_name:
    #                 ask_scp_root = tk.Tk()
    #                 ask_scp_root.withdraw()  # 隱藏主視窗
    #                 ask_scp_result = messagebox.askyesno("Warning", f"檔案已經存在，是否覆蓋？")
    #                 ask_scp_root.destroy()
                    
    #                 if not ask_scp_result:
    #                     # print("檔案未保存。")
    #                     ask_scp_root = tk.Tk()
    #                     ask_scp_root.withdraw()  # 隱藏主視窗
    #                     messagebox.showinfo("Warning", f'檔案未儲存')
    #                     return     

    #         self.inst.write(command)
    #         time.sleep(0.05)

    #     def save_scope_image(self, folder, image_name, path_choice):
    #         # 清空狀態
    #         self.inst.write('*CLS')
    #         time.sleep(0.05)

    #         # error messenge
    #             # 113 This directory is not valid.
    #             # -256 File name not found
    #             # -257 File name error
    #             # -410 Query INTERRUPTED
    #             # -420 Query UNTERMINATED
    #             # 0 No error

    #         # CDIRectory會害存圖卡死 orz

    #         if path_choice == 2:
    #             folder_total_path = folder
    #         else:
    #             folder_total_path = f"C:/Users/Administrator/Desktop/{folder}"

    #         # 資料夾是否存在
    #         self.inst.query(f':DISK:DIRectory? "{folder_total_path}"')
    #         time.sleep(0.05)
    #         error_messenge=self.inst.query(f':SYSTem:ERRor?')
    #         time.sleep(0.05)
    #         # print(error_messenge)
    #         if error_messenge == '-256\n' or error_messenge == '113\n' or error_messenge == '-257\n':
    #             ask_scp_root = tk.Tk()
    #             ask_scp_root.withdraw()  # 隱藏主視窗
    #             ask_scp_result = messagebox.askyesno("Warning", f"資料夾不存在，是否新增？")
    #             ask_scp_root.destroy()
                
    #             if not ask_scp_result:
    #                 ask_scp_root = tk.Tk()
    #                 ask_scp_root.withdraw()  # 隱藏主視窗
    #                 messagebox.showinfo("Warning", f'檔案未儲存')
    #                 # print("檔案未保存。")
    #                 return     
    #             # 新建資料夾
    #             folder_total_path= folder_total_path.replace("/", "\\")
    #             # print(folder_total_path)

    #             split_folder_list= folder_total_path.split('\\')

    #             folder= split_folder_list[0]
    #             for split in split_folder_list[1:]:
    #                 folder= f'{folder}\\{split}'
    #                 self.inst.query(f':DISK:DIRectory? "{folder}"')
    #                 time.sleep(0.05)
    #                 response= self.inst.query(f':SYSTem:ERRor?')
    #                 time.sleep(0.05)
    #                 # print(response)
    #                 if response == '-256\n' or response == '113\n' or response == '-257\n':
    #                     self.inst.write(f':DISK:MDIRectory "{folder}"')
    #                     time.sleep(0.05)

    #         # 資料夾全部內容
    #         folder_content= self.inst.query(f':DISK:DIRectory? "{folder_total_path}"')
    #         time.sleep(0.05)
    #         # 使用正則表達式來匹配所有 .png 檔案名稱
    #         png_files = re.findall(r'\b[\w-]+\.(?:png)\b', folder_content)

    #         for file_name in png_files:
    #             if f'{image_name}.png' == file_name:
    #                 ask_scp_root = tk.Tk()
    #                 ask_scp_root.withdraw()  # 隱藏主視窗
    #                 ask_scp_result = messagebox.askyesno("Warning", f"檔案已經存在，是否覆蓋？")
    #                 ask_scp_root.destroy()
                    
    #                 if not ask_scp_result:
    #                     # print("檔案未保存。")
    #                     ask_scp_root = tk.Tk()
    #                     ask_scp_root.withdraw()  # 隱藏主視窗
    #                     messagebox.showinfo("Warning", f'檔案未儲存')
    #                     return     

    #         self.inst.write(f':DISK:SAVE:IMAGe "{folder_total_path}/{image_name}",PNG,SCReen,OFF,NORMal,OFF')
    #         time.sleep(0.05)

    #     def set_general_threshold(self, g_top, g_middle, g_base, g_top_percent, g_middle_percent, g_base_percent):
    #         if intvar_general_threshold.get() == 1:
    #             do_the_judge= False
    #             if float(g_top_percent) <= float(g_middle_percent):
    #                 g_top_percent= Decimal(g_middle_percent) + Decimal('0.1')
    #                 combobox_general_percent_top.config(foreground= 'red')
    #                 combobox_general_percent_middle.config(foreground= 'red')
    #                 do_the_judge= True
    #             if float(g_middle_percent) <= float(g_base_percent):
    #                 g_base_percent= Decimal(g_middle_percent) - Decimal('0.1')
    #                 combobox_general_percent_base.config(foreground= 'red')
    #                 combobox_general_percent_middle.config(foreground= 'red')
    #                 do_the_judge= True
    #             if not do_the_judge:
    #                 combobox_general_percent_top.config(foreground= 'black')
    #                 combobox_general_percent_middle.config(foreground= 'black')
    #                 combobox_general_percent_base.config(foreground= 'black')

    #             self.inst.write(f':MEASure:THResholds:GENeral:METHod ALL,PERCent')
    #             time.sleep(0.05)
    #             self.inst.write(f':MEASure:THResholds:GENeral:PERCent ALL,{g_top_percent},{g_middle_percent},{g_base_percent}')
    #             time.sleep(0.05)
    #         elif intvar_general_threshold.get() == 2:
    #             do_the_judge= False
    #             if float(g_top) <= float(g_middle):
    #                 g_top= Decimal(g_middle) + Decimal('0.01')
    #                 combobox_general_value_top.config(foreground= 'red')
    #                 combobox_general_value_middle.config(foreground= 'red')
    #                 do_the_judge= True
    #             if float(g_middle) <= float(g_base):
    #                 g_base= Decimal(g_middle) - Decimal('0.01')
    #                 combobox_general_value_base.config(foreground= 'red')
    #                 combobox_general_value_middle.config(foreground= 'red')
    #                 do_the_judge= True
    #             if not do_the_judge:
    #                 combobox_general_value_top.config(foreground= 'black')
    #                 combobox_general_value_middle.config(foreground= 'black')
    #                 combobox_general_value_base.config(foreground= 'black')

    #             self.inst.write(f':MEASure:THResholds:GENeral:METHod ALL,ABSolute')
    #             time.sleep(0.05)
    #             self.inst.write(f':MEASure:THResholds:GENeral:ABSolute ALL,{g_top},{g_middle},{g_base}')
    #             time.sleep(0.05)

    #     def set_risefall_threshold(self, rf_top, rf_base, rf_top_percent, rf_base_percent):
    #         if intvar_risefall_threshold.get() == 1:
    #             self.inst.write(f':MEASure:THResholds:RFALl:METHod ALL,PERCent')
    #             time.sleep(0.05)
    #             self.inst.write(f':MEASure:THResholds:RFALl:PERCent ALL,{rf_top_percent},{(float(rf_top_percent)+float(rf_base_percent))/2},{rf_base_percent}')
    #             time.sleep(0.05)
    #         elif intvar_risefall_threshold.get() == 2:
    #             self.inst.write(f':MEASure:THResholds:RFALl:METHod ALL,ABSolute')
    #             time.sleep(0.05)
    #             self.inst.write(f':MEASure:THResholds:RFALl:ABSolute ALL,{rf_top},{(float(rf_top)+float(rf_base))/2},{rf_base}')
    #             time.sleep(0.05)

    #     def set_trigger_type(self):
    #         res= self.inst.query(f':TRIGger:SWEep?')
    #         time.sleep(0.05)
    #         if res == 'AUTO\n':
    #             self.inst.write(':TRIGger:SWEep TRIGgered')
    #             time.sleep(0.05)
    #         else:
    #             self.inst.write(':TRIGger:SWEep AUTO')
    #             time.sleep(0.05)

    #     def set_trigger_slope(self):
    #         res= self.inst.query(f':TRIGger:EDGE:SLOPe?')
    #         time.sleep(0.05)
    #         if res == 'POS\n':
    #             self.inst.write(':TRIGger:EDGE:SLOPe NEGative')
    #             time.sleep(0.05)
    #         else:
    #             self.inst.write(':TRIGger:EDGE:SLOPe POSitive')
    #             time.sleep(0.05)
        
    #     def single(self):
    #         self.inst.write(':SINGLE')
    #         time.sleep(0.05)

    #     def stop(self):
    #         self.inst.write(':STOP')
    #         time.sleep(0.05)


    ### Others ###
    def add_combobox_option(combobox, combobox_value, options, config_file, section, key, selected_section):
        new_option = combobox_value.get().strip()
        if new_option and new_option not in options:
            options.append(new_option)
            combobox['values'] = options
            save_option_to_ini(config_file, section, key, options, selected_section, combobox.get())

    # def change_label_text_mean_result():
    #     label_result_tag_1.config(text= "Mean")
    #     label_result_tag_2.config(text= "--")
    #     text_result_mean_1.config(width= 22)
    #     text_result_minmax_1.config(width= 0)
    #     text_result_mean_2.config(width= 22)
    #     text_result_minmax_2.config(width= 0)
    #     text_result_mean_3.config(width= 22)
    #     text_result_minmax_3.config(width= 0)
    #     text_result_mean_4.config(width= 22)
    #     text_result_minmax_4.config(width= 0)
    #     text_result_mean_5.config(width= 22)
    #     text_result_minmax_5.config(width= 0)
    #     text_result_mean_6.config(width= 22)
    #     text_result_minmax_6.config(width= 0)
    #     text_result_mean_7.config(width= 22)
    #     text_result_minmax_7.config(width= 0)
    #     text_result_mean_8.config(width= 22)
    #     text_result_minmax_8.config(width= 0)
    #     text_result_mean_9.config(width= 22)
    #     text_result_minmax_9.config(width= 0)
    #     text_result_mean_10.config(width= 22)
    #     text_result_minmax_10.config(width= 0)
    #     text_result_mean_11.config(width= 22)
    #     text_result_minmax_11.config(width= 0)
    #     text_result_mean_12.config(width= 22)
    #     text_result_minmax_12.config(width= 0)

    # def change_label_text_minmax_result():
    #     label_result_tag_1.config(text= "Min")
    #     label_result_tag_2.config(text= "Max")   
    #     text_result_mean_1.config(width= 22)
    #     text_result_minmax_1.config(width= 22)
    #     text_result_mean_2.config(width= 22)
    #     text_result_minmax_2.config(width= 22)
    #     text_result_mean_3.config(width= 22)
    #     text_result_minmax_3.config(width= 22)
    #     text_result_mean_4.config(width= 22)
    #     text_result_minmax_4.config(width= 22)
    #     text_result_mean_5.config(width= 22)
    #     text_result_minmax_5.config(width= 22)
    #     text_result_mean_6.config(width= 22)
    #     text_result_minmax_6.config(width= 22)
    #     text_result_mean_7.config(width= 22)
    #     text_result_minmax_7.config(width= 22)
    #     text_result_mean_8.config(width= 22)
    #     text_result_minmax_8.config(width= 22)
    #     text_result_mean_9.config(width= 22)
    #     text_result_minmax_9.config(width= 22)
    #     text_result_mean_10.config(width= 22)
    #     text_result_minmax_10.config(width= 22)
    #     text_result_mean_11.config(width= 22)
    #     text_result_minmax_11.config(width= 22)
    #     text_result_mean_12.config(width= 22)
    #     text_result_minmax_12.config(width= 22)

    def clear(string):
        string.set('')

    def close_window():
        if messagebox.askyesno('Message', 'Exit?'):
            config = configparser.ConfigParser()
            config.optionxform = str
            config.read( os.path.join(os.path.dirname(__file__), 'InitConfig_setup_new.ini'), encoding='utf-8',)
            
            # config.set('Scale_Offset_Selected_Values', 'VoltScale', strvar_voltage_scale.get())
            # config.set('Scale_Offset_Selected_Values', 'VoltOffset', strvar_voltage_offset.get())
            # config.set('Scale_Offset_Config', 'TimebaseScale', strvar_timebase_scale.get())
            # config.set('Scale_Offset_Config', 'TimebaseOffset', strvar_timebase_offset.get())
            # config.set('Scale_Offset_Selected_Values', 'TriggerLevel', strvar_trigger_level.get())
            # config.set('Scale_Offset_Config', 'TriggerChan', strvar_trigger_channel.get())
            # config.set('Scale_Offset_Config', 'WfmIntensity', strvar_waveform_intensity.get())
            
            # config.set('Delta_Setup_Config', 'DeltaStartEdge', strvar_start_risefall.get())
            # config.set('Delta_Setup_Config', 'DeltaStartNum', strvar_start_N_edge.get())
            # config.set('Delta_Setup_Config', 'DeltaStartPosition', strvar_start_position.get())
            # config.set('Delta_Setup_Config', 'DeltaStopEdge', strvar_stop_risefall.get())
            # config.set('Delta_Setup_Config', 'DeltaStopNum', strvar_stop_N_edge.get())
            # config.set('Delta_Setup_Config', 'DeltaStopPosition', strvar_stop_position.get())

            # config.set('Threshold_Selected_Values', 'GeneralTopPercent', strvar_general_percent_top.get())
            # config.set('Threshold_Selected_Values', 'GeneralMiddlePercent', strvar_general_percent_middle.get())
            # config.set('Threshold_Selected_Values', 'GeneralBasePercent', strvar_general_percent_base.get())
            # config.set('Threshold_Selected_Values', 'GeneralTop', strvar_general_value_top.get())
            # config.set('Threshold_Selected_Values', 'GeneralMiddle', strvar_general_value_middle.get())
            # config.set('Threshold_Selected_Values', 'GeneralBase', strvar_general_value_base.get())
            # config.set('Threshold_Selected_Values', 'RFTopPercent', strvar_risefall_percent_top.get())
            # config.set('Threshold_Selected_Values', 'RFBasePercent', strvar_risefall_percent_base.get())
            # config.set('Threshold_Selected_Values', 'RFTop', strvar_risefall_value_top.get())
            # config.set('Threshold_Selected_Values', 'RFBase', strvar_risefall_value_base.get())
            # config.set('Acquisition', 'SamplingRate', strvar_sampling_rate.get())
            # config.set('Acquisition', 'MemoryDepth', strvar_memory_depth.get())

            # config.set('Lable_Setup_Config', 'ChanLabel1', strvar_label_1.get())
            # config.set('Lable_Setup_Config', 'ChanLabel2', strvar_label_2.get())
            # config.set('Lable_Setup_Config', 'ChanLabel3', strvar_label_3.get())
            # config.set('Lable_Setup_Config', 'ChanLabel4', strvar_label_4.get())
            # config.set('Lable_Setup_Config', 'WMeLabel1', strvar_label_5.get())
            # config.set('Lable_Setup_Config', 'WMeLabel2', strvar_label_6.get())
            # config.set('Lable_Setup_Config', 'WMeLabel3', strvar_label_7.get())
            # config.set('Lable_Setup_Config', 'WMeLabel4', strvar_label_8.get())

            # config.set('Chan_Delta', 'ChanSingle', str(intvar_channel_single.get()))
            # config.set('Chan_Delta', 'ChanStart', str(intvar_channel_delta_start.get()))
            # config.set('Chan_Delta', 'ChanStop', str(intvar_channel_delta_stop.get()))

            # # config.set('Save_Setup_Config', 'SaveImgFolder', str_image_folder.get())
            # # config.set('Save_Setup_Config', 'SaveImgLocation', str(int_img_path_choice.get()))
            # config.set('Save_Setup_Config', 'SaveImgPCFolder', strvar_image_pc_folder.get())
            # config.set('Save_Setup_Config', 'SaveImgName', strvar_image.get())
            # config.set('Save_Setup_Config', 'SaveWMeFolder', strvar_wmemory_folder.get())
            # config.set('Save_Setup_Config', 'SaveWMeLocation', str(intvar_wmemory_path_choice.get()))
            # config.set('Save_Setup_Config', 'SaveWMePCFolder', strvar_wmemory_pc_folder.get())
            # config.set('Save_Setup_Config', 'SaveWMeName', strvar_other_file.get())

            # config.set('Load_WMemory_Setup_Config', 'LoadWMe1', strvar_wmemory_1.get())
            # config.set('Load_WMemory_Setup_Config', 'LoadWMe2', strvar_wmemory_2.get())
            # config.set('Load_WMemory_Setup_Config', 'LoadWMe3', strvar_wmemory_3.get())
            # config.set('Load_WMemory_Setup_Config', 'LoadWMe4', strvar_wmemory_4.get())
            # config.set('Load_WMemory_Setup_Config', 'SetupFileInterface', strvar_setupfile_interface.get())
            # config.set('Load_WMemory_Setup_Config', 'SetupFileClass', strvar_setupfile_class.get())
            # config.set('Load_WMemory_Setup_Config', 'LoadSetup', strvar_setup.get())

            config.write(open(os.path.join(os.path.dirname(__file__), 'InitConfig_setup_new.ini'), 'w'))

            # formatted_time= self.current_time()
            # print(f'\n{formatted_time} [GUI Message] Window Closed.')
            window.destroy()
            sys.exit()

    def delete_combobox_option(combobox, combobox_value, options, config_file, section, key, selected_section):
        selected_option = combobox_value.get().strip()
        if selected_option in options:
            options.remove(selected_option)
            combobox['values'] = options
            combobox_value.set('')  # 清空當前選擇
            save_option_to_ini(config_file, section, key, options, selected_section, combobox.get())

    def move_mouse_entry_end(entry):
        """將 Entry 的內容視圖滾動到最後，並設置游標到最後一位"""
        entry.focus()           # 設置 Entry 欄位獲取焦點
        entry.icursor(tk.END)   # 將游標移動到文本的最後一位
        entry.xview_moveto(1)   # 滾動視圖到最後一部分，1 表比例最右邊

    def on_mouse_wheel(event):
        try:
            value = int(entry_waveform_intensity.get())
        except ValueError:
            value = 0

        if event.delta > 0:
            value += waveform_intensity_step
        else:
            value -= waveform_intensity_step

        value = max(waveform_intensity_min_value, min(waveform_intensity_max_value, value))
        entry_waveform_intensity.delete(0, tk.END)
        entry_waveform_intensity.insert(0, str(value))
        update_intensity_color(value)

    def recall_combobox_option_from_inifile():
        config_initial = configparser.ConfigParser()
        config_initial.optionxform = str
        config_file = os.path.join(os.path.dirname(__file__), 'InitConfig_setup_new.ini')
        config_initial.read(config_file, encoding='UTF-8')
        
        # Scale
        VoltScale_options = config_initial['Scale_Offset_Config'].get('VoltScale', '').split(',')
        VoltOffset_options = config_initial['Scale_Offset_Config'].get('VoltOffset', '').split(',')
        TriggerLevel_options = config_initial['Scale_Offset_Config'].get('TriggerLevel', '').split(',')

        # Threshold
        GeneralTopPercent_options = config_initial['Threshold_Setup_Config'].get('GeneralTopPercent', '').split(',')
        GeneralMiddlePercent_options = config_initial['Threshold_Setup_Config'].get('GeneralMiddlePercent', '').split(',')
        GeneralBasePercent_options = config_initial['Threshold_Setup_Config'].get('GeneralBasePercent', '').split(',')
        GeneralTopValue_options = config_initial['Threshold_Setup_Config'].get('GeneralTopValue', '').split(',')
        GeneralMiddleValue_options = config_initial['Threshold_Setup_Config'].get('GeneralMiddleValue', '').split(',')
        GeneralBaseValue_options = config_initial['Threshold_Setup_Config'].get('GeneralBaseValue', '').split(',')
        RFTopPercent_options = config_initial['Threshold_Setup_Config'].get('RFTopPercent', '').split(',')
        RFBasePercent_options = config_initial['Threshold_Setup_Config'].get('RFBasePercent', '').split(',')
        RFTopValue_options = config_initial['Threshold_Setup_Config'].get('RFTopValue', '').split(',')
        RFBaseValue_options = config_initial['Threshold_Setup_Config'].get('RFBaseValue', '').split(',')

        # Scope Segment
        SaveOthersScopeSegment_options = config_initial['Scope_Server_Segment'].get('SaveOthersScopeSegment', '').split(',')
        LoadWmemoryScopeSegment_options = config_initial['Scope_Server_Segment'].get('LoadWmemoryScopeSegment', '').split(',')
        LoadSetupScopeSegment_options = config_initial['Scope_Server_Segment'].get('LoadSetupScopeSegment', '').split(',')

        # 從這裡返回值供其他部分調用
        return {
            'VoltScale': VoltScale_options, 
            'VoltOffset': VoltOffset_options, 
            'TriggerLevel': TriggerLevel_options, 
            'GeneralTopPercent': GeneralTopPercent_options,
            'GeneralMiddlePercent': GeneralMiddlePercent_options, 
            'GeneralBasePercent': GeneralBasePercent_options, 
            'GeneralTopValue': GeneralTopValue_options, 
            'GeneralMiddleValue': GeneralMiddleValue_options, 
            'GeneralBaseValue': GeneralBaseValue_options, 
            'RFTopPercent': RFTopPercent_options, 
            'RFBasePercent': RFBasePercent_options, 
            'RFTopValue': RFTopValue_options, 
            'RFBaseValue': RFBaseValue_options, 
            'SaveOthersScopeSegment': SaveOthersScopeSegment_options,
            'LoadWmemoryScopeSegment': LoadWmemoryScopeSegment_options,
            'LoadSetupScopeSegment': LoadSetupScopeSegment_options,
            
            'config_file': config_file,  # 儲存config文件路徑以便後續使用

            'selected_values': {
                'VoltScale': config_initial['Scale_Offset_Selected_Values'].get('VoltScale', ''),
                'VoltOffset': config_initial['Scale_Offset_Selected_Values'].get('VoltOffset', ''),
                'TriggerLevel': config_initial['Scale_Offset_Selected_Values'].get('TriggerLevel', ''),
                'GeneralTopPercent': config_initial['Threshold_Selected_Values'].get('GeneralTopPercent', ''),
                'GeneralMiddlePercent': config_initial['Threshold_Selected_Values'].get('GeneralMiddlePercent', ''),
                'GeneralBasePercent': config_initial['Threshold_Selected_Values'].get('GeneralBasePercent', ''),
                'GeneralTopValue': config_initial['Threshold_Selected_Values'].get('GeneralTopValue', ''),
                'GeneralMiddleValue': config_initial['Threshold_Selected_Values'].get('GeneralMiddleValue', ''),
                'GeneralBaseValue': config_initial['Threshold_Selected_Values'].get('GeneralBaseValue', ''),
                'RFTopPercent': config_initial['Threshold_Selected_Values'].get('RFTopPercent', ''),
                'RFBasePercent': config_initial['Threshold_Selected_Values'].get('RFBasePercent', ''),
                'RFTopValue': config_initial['Threshold_Selected_Values'].get('RFTopValue', ''),
                'RFBaseValue': config_initial['Threshold_Selected_Values'].get('RFBaseValue', ''),
                'SaveOthersScopeSegment': config_initial['Scope_Server_Segment_Selected_Values'].get('SaveOthersScopeSegment', ''),
                'LoadWmemoryScopeSegment': config_initial['Scope_Server_Segment_Selected_Values'].get('LoadWmemoryScopeSegment', ''),
                'LoadSetupScopeSegment': config_initial['Scope_Server_Segment_Selected_Values'].get('LoadSetupScopeSegment', ''),
                }        
        }

    def rgba_to_rgb_composite(in_path, out_path, background=(0, 0, 0)):
        img = Image.open(in_path)
        # 確保有 alpha 通道用 RGBA
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        # 建一個同尺寸的背景（含不透明 alpha）
        bg = Image.new('RGBA', img.size, background + (255,))
        # 將原圖疊在背景上，並去掉 alpha
        composed = Image.alpha_composite(bg, img).convert('RGB')
        composed.save(out_path, format='PNG')

    def save_option_to_ini(config_file, section, key, updated_options, selected_section, selected_value):
        config = configparser.ConfigParser()
        config.optionxform = str  # 保持大小寫
        config.read(config_file)
        if section not in config:
            config.add_section(section)
        
        # 更新指定的選項值
        config[section][key] = ','.join(updated_options)

        if selected_section not in config:
            config.add_section(selected_section)
        
        config[selected_section][key] = selected_value
        
        # 寫回INI文件
        with open(config_file, 'w') as configfile:
            config.write(configfile)

    def select_folder(entry_var, target_entry):
        # 打開檔案瀏覽器以選擇資料夾
        folder_selected = filedialog.askdirectory()
        # 將選擇的資料夾路徑填入 Entry
        entry_var.set(folder_selected)

        move_mouse_entry_end(entry= target_entry)

    # def select_setupfile_class(event, segment_list):

    #     target_class_files= []

    #     strvar_setup.set(value= '')

    #     # 示波器folder路徑
    #     setupfile_class_folderpath = fr'{segment_list[0]}:\#_Eric Team\02_Penny\Setup_Files_Collection\{strvar_setupfile_interface.get()}\{strvar_setupfile_class.get()}'
    #     # str_WMe_folder.set(value= setupfile_class_folderpath)

    #     # PC folder路徑
    #     pc_setupfile_class_folderpath = fr'{segment_list[1]}:\#_Eric Team\02_Penny\Setup_Files_Collection\{strvar_setupfile_interface.get()}\{strvar_setupfile_class.get()}'

    #     # os.walk 會回傳 root (目前路徑), dirs (子資料夾名稱列表), files (檔案名稱列表)
    #     for root, dirs, files in os.walk(pc_setupfile_class_folderpath):
    #         for file in files:
    #             # 篩選.set
    #             if file.endswith('.set'):
    #                 # 取得設定檔的絕對路徑
    #                 file_path = os.path.join(root, file)
    #                 target_class_files.append((os.path.basename(file_path)).rstrip('.set'))

    #     combobox_setup.config(values= target_class_files)
    #     # adjust_entry(entry= e_WMe_folder)

    # def select_setupfile_interface(event, segment_list):
        
    #     target_interface_subfolder= []

    #     strvar_setupfile_class.set(value= '')

    #     if strvar_setupfile_interface.get() == 'User':
    #         strvar_setupfile_class.set(value= '')
    #         combobox_setupfile_class.config(state= 'disabled')
    #     elif strvar_setupfile_interface.get() == '':
    #         strvar_setupfile_class.set(value= '')
    #         combobox_setupfile_class.config(state= 'disabled')
    #     else: 
    #         combobox_setupfile_class.config(state= 'readonly')

    #         # 示波器folder路徑
    #         setupfile_interface_folderpath = fr'{segment_list[0]}:\#_Eric Team\02_Penny\Setup_Files_Collection\{strvar_setupfile_interface.get()}'
    #         # str_WMe_folder.set(value= setupfile_interface_folderpath)

    #         # PC folder路徑
    #         pc_setupfile_interface_folderpath = fr'{segment_list[1]}:\#_Eric Team\02_Penny\Setup_Files_Collection\{strvar_setupfile_interface.get()}'

    #         # os.walk 會回傳 root (目前路徑), dirs (子資料夾名稱列表), files (檔案名稱列表)
    #         for root, dirs, files in os.walk(pc_setupfile_interface_folderpath):
    #             for dir_name in dirs:
    #                 # 取得子資料夾的絕對路徑
    #                 dir_path = os.path.join(root, dir_name)
    #                 target_interface_subfolder.append(os.path.basename(dir_path))

    #         combobox_setupfile_class.config(values= target_interface_subfolder)
    #         # adjust_entry(entry= e_WMe_folder)
    
    def set_to_fixty():
        value = 50
        entry_waveform_intensity.delete(0, tk.END)
        entry_waveform_intensity.insert(0, str(value))
        update_intensity_color(value)
        # mxr.check_intensity_setting(intensity_value= 50)

    def switch_string(var_1, var_2):
        string_1= var_1.get()
        string_2= var_2.get()
        var_1.set(string_2)
        var_2.set(string_1)

    def update_intensity_color(value):
        """根據數值改變文字顏色"""
        if value == 50:
            entry_waveform_intensity.config(foreground= colors['entry'][1])
        else:
            entry_waveform_intensity.config(foreground= "red")

    def validate_number(new_value):
        """限制只能輸入數字 (允許空白)"""
        if new_value == "":  # 空白允許
            entry_waveform_intensity.config(foreground= "red")
            return True
        if new_value.isdigit():
            num = int(new_value)
            # 限制範圍
            if waveform_intensity_min_value <= num <= waveform_intensity_max_value:
                update_intensity_color(num)
            else:
                entry_waveform_intensity.config(foreground= "red")
            return True
        return False  # 阻擋非數字字元



    class ToolTip:
        def __init__(self, widget, text):
            self.widget = widget
            self.text = text
            self.tip_window = None
            self.widget.bind("<Enter>", self.show_tip)
            self.widget.bind("<Leave>", self.hide_tip)

        def show_tip(self, event= None):
            "Display text in tooltip window"
            if self.tip_window or not self.text:
                return
            x, y, cx, cy = self.widget.bbox("insert")
            if not x == None:
                x += self.widget.winfo_rootx() + 57
                y += self.widget.winfo_rooty() + 21
                self.tip_window = tw = tk.Toplevel(self.widget)
                tw.wm_overrideredirect(True)
                tw.wm_geometry("+%d+%d" % (x, y))
                label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                                background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                                font=("tahoma", "8", "normal"))
                label.pack(ipadx=1)
            else:
                return

        def hide_tip(self, event=None):
            if self.tip_window:
                self.tip_window.destroy()
                self.tip_window = None


    # 獲取ini數據
    config_data = recall_combobox_option_from_inifile()
    # general_top_percent_options = config_data['GeneralTopPercent']
    config_file_path = config_data['config_file']


    def execute_commbobox_function(combobox, combobox_var, ini_dict_key, ini_option_section, ini_option_key, ini_selected_section):
        combobox['values'] = config_data[ini_dict_key]  # 設置初始選項
        combobox.bind('<Return>', lambda event: add_combobox_option(combobox, combobox_var, config_data[ini_dict_key], config_file_path, ini_option_section, ini_option_key, ini_selected_section))
        combobox.bind('<Delete>', lambda event: delete_combobox_option(combobox, combobox_var, config_data[ini_dict_key], config_file_path, ini_option_section, ini_option_key, ini_selected_section))




    # Get physical resolution (prefer EnumDisplaySettings)
    if sys.platform == "win32":
        phys_w, phys_h = get_primary_physical_resolution_enumdisplay()
    else:
        # non-windows: fallback to tkinter reported screen size later
        phys_w, phys_h = None, None
    print("physical resolution (fallback) ->", phys_w, phys_h)


    window = tk.Tk()
    window.title(window_name)

    # If physical resolution not available (non-windows), use Tk reported screen
    # 取得螢幕解析度（像素）
    tk_screen_w = window.winfo_screenwidth()
    tk_screen_h = window.winfo_screenheight()
    print("Tk reported screen ->", tk_screen_w, tk_screen_h)

    if not phys_w or not phys_h:
        screen_w, screen_h = tk_screen_w, tk_screen_h
    else:
        screen_w, screen_h = phys_w, phys_h

    # pick reference by aspect and compute scale (resolution-primary)
    ref_w, ref_h = pick_reference_by_aspect(screen_w, screen_h)
    res_scale = min(screen_w / ref_w, screen_h / ref_h)
    if res_scale <= 0:
        res_scale = 1.0

    print("selected ref:", (ref_w, ref_h), "res_scale:", round(res_scale, 3))

    
    # 設定style ========================================================================================================================================================================
    style = ttk.Style(window)
    # style.theme_use('alt')

    # 顏色表 (name -> (bg, fg, select))
    colors = {
        'window': ('#084F6A', '#000000', '#000000'), 
        'labelframe': ("#011E25", '#9DB5B2', '#000000'), 
        'label': ('#011E25', '#DAF0EE', '#000000'), 
        'button': ('#8CC6D0', '#0B3041', '#000000'), 
        'special_button': ('#61CBF4', '#FFFFFF', '#000000'), 
        'entry': ('#EAF4F6', '#0B3041', '#000000'), 
        'combobox': ('#F2F2F2', '#0B3041', '#000000'), 
        'radiobutton_1': ('#011E25', '#F6C6AD', '#8CC6D0'), 
        'radiobutton_2': ('#011E25', '#F2CFEE', '#8CC6D0'), 
        'radiobutton_3': ('#011E25', '#E59EDD', '#8CC6D0'), 
        'checkbutton_1': ('#011E25', '#FFFFB3', '#EAF4F6'), 
        'checkbutton_2': ('#011E25', '#83CBEB', '#EAF4F6')       
    }

    base_font_size= 10
    
    # 設定label style
    label_style= {
        'calibri_bold': ('Calibri', 'bold'), 
        'calibri_normal': ('Candara', 'normal'), 
        'candara_bold': ('Calibri', 'bold'), 
        'candara_normal': ('Candara', 'normal'), 
    }
    for name, (font_name, weight) in label_style.items():
        ui_label_font= font.Font(root= window, family= font_name, size= max(8, int(round(base_font_size * res_scale))), weight= weight)
        style_name = f"label_{name}.TLabel"
        # configure the style; some themes ignore background for TLabel
        style.configure(style_name, background= colors['label'][0], foreground= colors['label'][1], font= ui_label_font, padding= 1)

    # 設定button style
    ui_button_font= font.Font(root= window, family= f'Calibri', size= max(8, int(round(base_font_size * res_scale))))
    style.configure('normal_height.TButton', background= colors['button'][0], foreground= colors['button'][1], font= ui_button_font, padding= 1)
    style.map('normal_height.TButton', background=[('active',colors['button'][0])])
    style.configure('double_height.TButton', background= colors['button'][0], foreground= colors['button'][1], font= ui_button_font, padding= 2)
    style.configure('special.TButton', background= colors['special_button'][0], foreground= colors['special_button'][1], font= ui_button_font, padding= 2)

    # 設定entry style
    ui_entry_font= font.Font(root= window, family= f'Calibri', size= max(10, int(round((base_font_size-1) * res_scale))))
    style.configure('TEntry', background= colors['entry'][0], foreground= colors['entry'][1], font= ui_entry_font, padding= 1)

    # 設定combobox style
    ui_combobox_font= font.Font(root= window, family= f'Calibri', size= max(10, int(round((base_font_size-1) * res_scale))))
    style.configure('TCombobox', background= colors['combobox'][0], foreground= colors['combobox'][1], font= ui_combobox_font, padding= 1)

    # 設定radiobutton style
    ui_radiobutton_font= font.Font(root= window, family= f'Calibri', size= max(8, int(round(base_font_size * res_scale))))
    for i in range(1, 4):
        style.configure(f'radiobutton_{i}.TRadiobutton', background= colors[f'radiobutton_{i}'][0], foreground= colors[f'radiobutton_{i}'][1], font= ui_radiobutton_font, padding= 1)

    # 設定checkbutton style
    ui_checkbutton_font= font.Font(root= window, family= f'Calibri', size= max(8, int(round(base_font_size * res_scale))))
    for i in range(1, 3):
        style.configure(f'checkbutton_{i}.TCheckbutton', background= colors[f'checkbutton_{i}'][0], foreground= colors[f'checkbutton_{i}'][1], font= ui_checkbutton_font, padding= 1)


    # 設定按鈕大小, 初始按鈕尺寸以 dpi_scale 調整（width/height 為字元/行數）
    def set_button_size(base_btn_w, base_btn_h):
        btn_w = max(4, int(round(base_btn_w * res_scale)))
        btn_h = max(1, int(round(base_btn_h * res_scale)))

        return btn_w, btn_h
    
    def set_entry_width(base_entry_width):
        entry_w = max(10, int(round(base_entry_width * res_scale)))
        return entry_w
    
    # =============================================================================================================================================================================

    # initial window size (occupy a ratio of monitor)
    win_w = int(screen_w * 0.9)
    win_h = int(screen_h * 0.7)
    window.geometry(f"{win_w}x{win_h}")
    window.minsize(360, 240)

    # # window.geometry('1500x760+2+2')
    window.geometry('+2+2')
    window.configure(bg= colors['window'][0])
    # window.resizable(True, True)

    # 設定waveform intensity參數
    waveform_intensity_step = 1
    waveform_intensity_min_value = 0
    waveform_intensity_max_value = 100



    # base_font_size= 7

    # candara_family = choose_available_font(window, ["Candara", "Calibri"], fallback="Segoe UI")
    # calibri_family = choose_available_font(window, ["Calibri", "Candara"], fallback="Segoe UI")

    # # base fonts (pure tk)
    # # family = "Segoe UI" if sys.platform == "win32" else "Helvetica"
    # candara_base_font = font.Font(root= window, family= candara_family, size= max(10, int(round(base_font_size * res_scale))))
    # calibri_base_font = font.Font(root= window, family= calibri_family, size= max(10, int(round(base_font_size * res_scale))))

    # candara_bold_font = font.Font(root= window, family= candara_family, size=max(10, int(round(base_font_size * res_scale))), weight="bold")
    # calibri_bold_font = font.Font(root= window, family= calibri_family, size=max(10, int(round(base_font_size * res_scale))), weight="bold")
    
    # entry_font = font.Font(root= window, family= calibri_family, size=max(10, int(round((base_font_size-1) * res_scale))))
    
    # # safe font retrieval and base UI font (shared)
    # try:
    #     ui_font = font.nametofont("TkDefaultFont").copy()
    # except Exception:
    #     ui_font = font.Font(root= window, family="Helvetica", size=10)
    # ui_font.configure(size=max(8, int(round(base_font_size * res_scale))))

    # # # apply font to ttk widgets via style
    # # style = ttk.Style(window)
    # # try:
    # #     # style.configure("TLabel", font=ui_font)
    # #     style.configure("TButton", font= ui_font)
    # #     # style.configure("TEntry", font=ui_font)
    # #     # style.configure("TCheckbutton", font=ui_font)
    # #     # style.configure("TRadiobutton", font=ui_font)
    # #     style.configure("TCombobox", font= ui_font)
    # # except Exception:
    # #     # some Tk versions/ttk themes may ignore some styles; continue anyway
    # #     pass


    window.rowconfigure(0 , weight= 1, uniform= 'row')
    window.columnconfigure(0 , weight= 1, uniform= 'col')
    window.columnconfigure(1 , weight= 2, uniform= 'col')

    frame_left= tk.Frame(master= window, background= colors['window'][0])
    frame_right= tk.Frame(master= window, background= colors['window'][0])

    frame_left.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    frame_right.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw')

    # Left Area  ==============================================================================================================================================
    
    # Scale/Offset/Trigger  ===================================================================================================================================
    labelframe_scale_offset_trigger= tk.LabelFrame(master= frame_left, text= 'Scale/Offset/Trigger', background= colors['labelframe'][0], fg= colors['labelframe'][1], font= ('Candara', 10, 'bold'),)

    entry_width_scale_area= set_entry_width(base_entry_width= 20)
    button_width_scale_area, button_height_scale_area= set_button_size(base_btn_w= 20, base_btn_h= 1)

    frame_scalearea_top= tk.Frame(master= labelframe_scale_offset_trigger, background= colors['labelframe'][0])
    # voltage_scale
    button_voltage_scale = ttk.Button(
        master= frame_scalearea_top, text= 'Voltage Scale (V)', width= button_width_scale_area,  padding= 1, 
        style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    
    strvar_voltage_scale= tk.StringVar()
    combobox_voltage_scale = ttk.Combobox(
        frame_scalearea_top, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_voltage_scale, style= 'TCombobox', justify= 'center')
    execute_commbobox_function(combobox= combobox_voltage_scale, combobox_var= strvar_voltage_scale, ini_dict_key= 'VoltScale', ini_option_section= 'Scale_Offset_Config', ini_option_key= 'VoltScale', ini_selected_section= 'Scale_Offset_Selected_Values')
    
    # voltage_offset
    button_voltage_offset = ttk.Button(
        master= frame_scalearea_top, text= 'Voltage Offset (V)', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    
    strvar_voltage_offset= tk.StringVar()
    combobox_voltage_offset = ttk.Combobox(
        frame_scalearea_top, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_voltage_offset, style= 'TCombobox', justify= 'center')
    execute_commbobox_function(combobox= combobox_voltage_offset, combobox_var= strvar_voltage_offset, ini_dict_key= 'VoltOffset', ini_option_section= 'Scale_Offset_Config', ini_option_key= 'VoltOffset', ini_selected_section= 'Scale_Offset_Selected_Values')
    
    # timebase scale
    button_timebase_scale = ttk.Button(
        master= frame_scalearea_top, text= 'Timebase Scale (sec)', width= button_width_scale_area, padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    
    strvar_timebase_scale= tk.StringVar()
    entry_timebase_scale = ttk.Entry(master= frame_scalearea_top, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_timebase_scale, style= 'TEntry', justify= 'center')
   
    # timebase offset
    button_timebase_offset= ttk.Button(
        master= frame_scalearea_top, text= 'Timebase Offset (sec)', width= button_width_scale_area, padding= 1, 
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    
    strvar_timebase_offset= tk.StringVar()
    entry_timebase_offset = ttk.Entry(master= frame_scalearea_top, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_timebase_offset, style= 'TEntry', justify= 'center')
   
    # trigger channel
    button_trigger_channel = ttk.Button(
        master= frame_scalearea_top, text= 'Trigger Channel', width= button_width_scale_area, padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    
    strvar_trigger_channel= tk.StringVar()
    combobox_trigger_channel = ttk.Combobox(
        frame_scalearea_top, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_trigger_channel, style= 'TCombobox', justify= 'center', values= ['1', '2', '3', '4'])
   
    # trigger level
    button_trigger_level = ttk.Button(
        master= frame_scalearea_top, text= 'Trigger Level (V)', width= button_width_scale_area, padding= 1, 
        # style= 'normal_height.TButton', 
        # command= lambda: mxr.
        )
    
    strvar_trigger_level= tk.StringVar()
    combobox_trigger_level = ttk.Combobox(
        frame_scalearea_top, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_trigger_level, style= 'TCombobox', justify= 'center')
    execute_commbobox_function(combobox= combobox_trigger_level, combobox_var= strvar_trigger_level, ini_dict_key= 'TriggerLevel', ini_option_section= 'Scale_Offset_Config', ini_option_key= 'TriggerLevel', ini_selected_section= 'Scale_Offset_Selected_Values')

    frame_scalearea_bottom= tk.Frame(master= labelframe_scale_offset_trigger, background= colors['labelframe'][0])
    # buttons
    button_trigger_mode = ttk.Button(
        master= frame_scalearea_bottom, text= 'Trigger Mode', width= button_width_scale_area, padding= 2, 
        # style= 'double_height.TButton', 
        # command= lambda: mxr.
        )
    button_trigger_slope = ttk.Button(
        master= frame_scalearea_bottom, text= 'Trigger Slope', width= button_width_scale_area, padding= 2, 
        # style= 'double_height.TButton', 
        # command= lambda: mxr.
        )
    button_set_all = ttk.Button(
        master= frame_scalearea_bottom, text= 'All Set', width= button_width_scale_area, padding= 2, 
        # style= 'special.TButton', 
        # command= lambda: mxr.
        )
    
    ################################################
    # Threshold  ===================================================================================================================================
    labelframe_threshold= tk.LabelFrame(master= frame_left, text= 'Threshold', background= colors['labelframe'][0], fg= colors['labelframe'][1], font= ('Candara', 10, 'bold'),)

    # general threshold - value ######
    button_general_threshold_value = ttk.Button(
        master= labelframe_threshold, text= 'General - Value (V)', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    
    ## general threshold - value Top
    label_general_threshold_value_top= tk.Label(
        master= labelframe_threshold, text= 'Top (V)', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        )
    strvar_general_threshold_value_top= tk.StringVar()
    combobox_general_threshold_value_top = ttk.Combobox(
        master= labelframe_threshold, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_general_threshold_value_top, style= 'TCombobox', justify= 'center')
    execute_commbobox_function(
        combobox= combobox_general_threshold_value_top, combobox_var= strvar_general_threshold_value_top, ini_dict_key= 'GeneralTopValue', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'GeneralTopValue', ini_selected_section= 'Threshold_Selected_Values')
    
    ## general threshold - value Middle
    label_general_threshold_value_middle= tk.Label(
        master= labelframe_threshold, text= 'Middle (V)', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        )
    strvar_general_threshold_value_middle= tk.StringVar()
    combobox_general_threshold_value_middle = ttk.Combobox(
        master= labelframe_threshold, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_general_threshold_value_middle, style= 'TCombobox', justify= 'center')
    execute_commbobox_function(
        combobox= combobox_general_threshold_value_middle, combobox_var= strvar_general_threshold_value_middle, ini_dict_key= 'GeneralMiddleValue', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'GeneralMiddleValue', ini_selected_section= 'Threshold_Selected_Values')
    
    ## general threshold - value Base
    label_general_threshold_value_base= tk.Label(
        master= labelframe_threshold, text= 'Base (V)', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        )
    strvar_general_threshold_value_base= tk.StringVar()
    combobox_general_threshold_value_base = ttk.Combobox(
        master= labelframe_threshold, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_general_threshold_value_base, style= 'TCombobox', justify= 'center')
    execute_commbobox_function(
        combobox= combobox_general_threshold_value_base, combobox_var= strvar_general_threshold_value_base, ini_dict_key= 'GeneralBaseValue', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'GeneralBaseValue', ini_selected_section= 'Threshold_Selected_Values')

    # general threshold - percent ######
    button_general_threshold_percent = ttk.Button(
        master= labelframe_threshold, text= 'General - Percentage (%)', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    
    ## general threshold - percent Top
    label_general_threshold_percent_top= tk.Label(
        master= labelframe_threshold, text= 'Top (%)', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        )
    strvar_general_threshold_percent_top= tk.StringVar()
    combobox_general_threshold_percent_top = ttk.Combobox(
        master= labelframe_threshold, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_general_threshold_percent_top, style= 'TCombobox', justify= 'center')
    execute_commbobox_function(
        combobox= combobox_general_threshold_percent_top, combobox_var= strvar_general_threshold_percent_top, ini_dict_key= 'GeneralTopPercent', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'GeneralTopPercent', ini_selected_section= 'Threshold_Selected_Values')
    
    ## general threshold - percent Middle
    label_general_threshold_percent_middle= tk.Label(
        master= labelframe_threshold, text= 'Middle (%)', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        )
    strvar_general_threshold_percent_middle= tk.StringVar()
    combobox_general_threshold_percent_middle = ttk.Combobox(
        master= labelframe_threshold, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_general_threshold_percent_middle, style= 'TCombobox', justify= 'center')
    execute_commbobox_function(
        combobox= combobox_general_threshold_percent_middle, combobox_var= strvar_general_threshold_percent_middle, ini_dict_key= 'GeneralMiddlePercent', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'GeneralMiddlePercent', ini_selected_section= 'Threshold_Selected_Values')
    
    ## general threshold - percent Base
    label_general_threshold_percent_base= tk.Label(
        master= labelframe_threshold, text= 'Base (%)', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        )
    strvar_general_threshold_percent_base= tk.StringVar()
    combobox_general_threshold_percent_base = ttk.Combobox(
        master= labelframe_threshold, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_general_threshold_percent_base, style= 'TCombobox', justify= 'center')
    execute_commbobox_function(
        combobox= combobox_general_threshold_percent_base, combobox_var= strvar_general_threshold_percent_base, ini_dict_key= 'GeneralBasePercent', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'GeneralBasePercent', ini_selected_section= 'Threshold_Selected_Values')
    
    # Rise/Fall threshold - value ######
    button_RF_threshold_value = ttk.Button(
        master= labelframe_threshold, text= 'Ries/Fall - Value (V)', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    
    ## Rise/Fall threshold - value Top
    label_RF_threshold_value_top= tk.Label(
        master= labelframe_threshold, text= 'Top (V)', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        )
    strvar_RF_threshold_value_top= tk.StringVar()
    combobox_RF_threshold_value_top = ttk.Combobox(
        master= labelframe_threshold, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_RF_threshold_value_top, style= 'TCombobox', justify= 'center')
    execute_commbobox_function(
        combobox= combobox_RF_threshold_value_top, combobox_var= strvar_RF_threshold_value_top, ini_dict_key= 'RFTopValue', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'RFTopValue', ini_selected_section= 'Threshold_Selected_Values')
    
    ## Rise/Fall threshold - value Base
    label_RF_threshold_value_base= tk.Label(
        master= labelframe_threshold, text= 'Base (V)', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        )
    strvar_RF_threshold_value_base= tk.StringVar()
    combobox_RF_threshold_value_base = ttk.Combobox(
        master= labelframe_threshold, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_RF_threshold_value_base, style= 'TCombobox', justify= 'center')
    execute_commbobox_function(
        combobox= combobox_RF_threshold_value_base, combobox_var= strvar_RF_threshold_value_base, ini_dict_key= 'RFBaseValue', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'RFBaseValue', ini_selected_section= 'Threshold_Selected_Values')

    # Rise/Fall threshold - percent ######
    button_RF_threshold_percent = ttk.Button(
        master= labelframe_threshold, text= 'Ries/Fall - Percentage (%)', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    
    ## Rise/Fall threshold - percent Top
    label_RF_threshold_percent_top= tk.Label(
        master= labelframe_threshold, text= 'Top (%)', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        )
    strvar_RF_threshold_percent_top= tk.StringVar()
    combobox_RF_threshold_percent_top = ttk.Combobox(
        master= labelframe_threshold, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_RF_threshold_percent_top, style= 'TCombobox', justify= 'center')
    execute_commbobox_function(
        combobox= combobox_RF_threshold_percent_top, combobox_var= strvar_RF_threshold_percent_top, ini_dict_key= 'RFTopPercent', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'RFTopPercent', ini_selected_section= 'Threshold_Selected_Values')
    
    ## Rise/Fall threshold - percent Base
    label_RF_threshold_percent_base= tk.Label(
        master= labelframe_threshold, text= 'Base (%)', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        )
    strvar_RF_threshold_percent_base= tk.StringVar()
    combobox_RF_threshold_percent_base = ttk.Combobox(
        master= labelframe_threshold, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_RF_threshold_percent_base, style= 'TCombobox', justify= 'center')
    execute_commbobox_function(
        combobox= combobox_RF_threshold_percent_base, combobox_var= strvar_RF_threshold_percent_base, ini_dict_key= 'RFBasePercent', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'RFBasePercent', ini_selected_section= 'Threshold_Selected_Values')

    ################################################
    # Channel  ===================================================================================================================================
    labelframe_channel= tk.LabelFrame(master= frame_left, text= 'Channel', background= colors['labelframe'][0], fg= colors['labelframe'][1], font= ('Candara', 10, 'bold'),)

    button_channel_1 = ttk.Button(
        master= labelframe_channel, text= 'Channel 1', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    button_channel_2 = ttk.Button(
        master= labelframe_channel, text= 'Channel 2', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    button_channel_3 = ttk.Button(
        master= labelframe_channel, text= 'Channel 3', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    button_channel_4 = ttk.Button(
        master= labelframe_channel, text= 'Channel 4', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    button_wememory_1 = ttk.Button(
        master= labelframe_channel, text= 'Wememory 1', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    button_wememory_2 = ttk.Button(
        master= labelframe_channel, text= 'Wememory 2', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    button_wememory_3 = ttk.Button(
        master= labelframe_channel, text= 'Wememory 3', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    button_wememory_4 = ttk.Button(
        master= labelframe_channel, text= 'Wememory 4', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    
    ################################################
    # Control  ===================================================================================================================================
    labelframe_control= tk.LabelFrame(master= frame_left, text= 'Control', background= colors['labelframe'][0], fg= colors['labelframe'][1], font= ('Candara', 10, 'bold'),)

    button_control_run = ttk.Button(
        master= labelframe_control, text= 'RUN', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    button_control_stop = ttk.Button(
        master= labelframe_control, text= 'STOP', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    button_control_single = ttk.Button(
        master= labelframe_control, text= 'Single', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    button_control_autoscale = ttk.Button(
        master= labelframe_control, text= 'Auto Scale', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    button_control_default = ttk.Button(
        master= labelframe_control, text= 'Default', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    button_control_clearwaveform = ttk.Button(
        master= labelframe_control, text= 'Clear', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    button_disable_button = ttk.Button(
        master= labelframe_control, text= 'Disable', width= button_width_scale_area,  padding= 2, 
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    ################################################
    # Acquisition  ===================================================================================================================================
    labelframe_acquisition= tk.LabelFrame(master= frame_left, text= 'Acquisition', background= colors['labelframe'][0], fg= colors['labelframe'][1], font= ('Candara', 10, 'bold'),)

    # sampling rate
    button_smapling_rate = ttk.Button(
        master= labelframe_acquisition, text= 'Sampling Rate (Sa/s)', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )

    strvar_smapling_rate= tk.StringVar()
    combobox_smapling_rate = ttk.Combobox(
        master= labelframe_acquisition, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_smapling_rate, style= 'TCombobox', justify= 'center', 
        values= ['16E+9', '8E+9', '4E+9', '2E+9']
        )
    button_smapling_rate_auto = ttk.Button(
        master= labelframe_acquisition, text= 'Auto Mode', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    
    # memory depth
    button_memory_depth = ttk.Button(
        master= labelframe_acquisition, text= 'Memory Depth (pts)', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )

    strvar_memory_depth= tk.StringVar()
    entry_memory_depth = ttk.Entry(
        master= labelframe_acquisition, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_memory_depth, justify= 'center')
    button_memory_depth_auto = ttk.Button(
        master= labelframe_acquisition, text= 'Auto Mode', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    
    # waveform intensity
    button_waveform_intensity = ttk.Button(
        master= labelframe_acquisition, text= 'Waveform Intensity (%)', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.check_intensity_setting(intensity_value= strvar_waveform_intensity.get())
        )

    vcmd = (window.register(validate_number), "%P") # %P = 輸入後字串
    strvar_waveform_intensity= tk.StringVar()
    entry_waveform_intensity = ttk.Entry(
        master= labelframe_acquisition, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_waveform_intensity, justify= 'center', validate="key", validatecommand= vcmd)
    update_intensity_color(value= strvar_waveform_intensity.get())
    button_set_to_fixty = ttk.Button(
        master= labelframe_acquisition, text= 'Set 50%', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        command= set_to_fixty
        )
    entry_waveform_intensity.bind("<MouseWheel>", on_mouse_wheel)
    entry_waveform_intensity.bind("<Button-4>", lambda e: on_mouse_wheel(type("Event", (), {"delta": 120})))
    entry_waveform_intensity.bind("<Button-5>", lambda e: on_mouse_wheel(type("Event", (), {"delta": -120})))

    ################################################
    # Right Area  ==============================================================================================================================================
    frame_right_top= tk.Frame(master= frame_right, background= colors['window'][0])
    frame_right_bottom_left= tk.Frame(master= frame_right, background= colors['window'][0])
    frame_right_bottom_right= tk.Frame(master= frame_right, background= colors['window'][0])

    # Measurement  ===================================================================================================================================
    labelframe_measurement= tk.LabelFrame(master= frame_right_top, text= 'Measurement', background= colors['labelframe'][0], fg= colors['labelframe'][1], font= ('Candara', 10, 'bold'),)
    
    frame_measurement_top= tk.Frame(master= labelframe_measurement, background= colors['labelframe'][0])
    frame_measurement_middle= tk.Frame(master= labelframe_measurement, background= colors['labelframe'][0])
    frame_measurement_base= tk.Frame(master= labelframe_measurement, background= colors['labelframe'][0])

    frame_measurement_top_left= tk.Frame(master= frame_measurement_top, background= colors['labelframe'][0])
    frame_measurement_top_right= tk.Frame(master= frame_measurement_top, background= colors['labelframe'][0])

    frame_measurement_base_left= tk.Frame(master= frame_measurement_base, background= colors['labelframe'][0])
    frame_measurement_base_middle= tk.Frame(master= frame_measurement_base, background= colors['labelframe'][0])
    frame_measurement_base_right= tk.Frame(master= frame_measurement_base, background= colors['labelframe'][0])
    
    button_show_result_table= ttk.Button(
        master= frame_measurement_top_left, text= 'Show Results Table', width= button_width_scale_area,  padding= 2,
        # style= 'special.TButton',
        # command= lambda: mxr.
        )

    intvar_measurement_channel= tk.IntVar()
    radiobutton_single_channel= ttk.Radiobutton(
        master= frame_measurement_top_left, text= 'Single Channel', value= 1, variable= intvar_measurement_channel
    )
    radiobutton_double_channels= ttk.Radiobutton(
        master= frame_measurement_base_left, text= 'Double Channels', value= 2, variable= intvar_measurement_channel
    )

    strvar_measurement_single_channel= tk.StringVar()
    combobox_measurement_single_channel= ttk.Combobox(
        master= frame_measurement_top_left, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_measurement_single_channel, style= 'TCombobox', justify= 'center', 
        values= ['1', '2', '3', '4']
        )
    
    button_measurement_frequency= ttk.Button(
        master= frame_measurement_top_right, text= 'Frequency', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_measurement_period= ttk.Button(
        master= frame_measurement_top_right, text= 'Period', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_measurement_dutycycle= ttk.Button(
        master= frame_measurement_top_right, text= 'Duty Cycle', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_measurement_tH= ttk.Button(
        master= frame_measurement_top_right, text= 'High time', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_measurement_tL= ttk.Button(
        master= frame_measurement_top_right, text= 'Low time', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_measurement_tR= ttk.Button(
        master= frame_measurement_top_right, text= 'Rising time', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_measurement_tF= ttk.Button(
        master= frame_measurement_top_right, text= 'Falling time', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_measurement_slewR= ttk.Button(
        master= frame_measurement_top_right, text= 'Slew Rate-Falling', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_measurement_slewF= ttk.Button(
        master= frame_measurement_top_right, text= 'Slew Rate-Rising', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_measurement_perper= ttk.Button(
        master= frame_measurement_top_right, text= '1 per-per', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_measurement_VIH= ttk.Button(
        master= frame_measurement_top_right, text= 'VIH', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_measurement_VIL= ttk.Button(
        master= frame_measurement_top_right, text= 'VIL', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_measurement_VPP= ttk.Button(
        master= frame_measurement_top_right, text= 'VPP', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_measurement_Vmax= ttk.Button(
        master= frame_measurement_top_right, text= 'Vmax', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_measurement_Vmin= ttk.Button(
        master= frame_measurement_top_right, text= 'Vmin', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    label_delta_setting= tk.Label(
        master= frame_measurement_middle, text= f'{100*"-"} Delta Setting {100*"-"}', 
        background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 

    boolvar_modify_delta_name= tk.BooleanVar()
    checkbutton_modify_delta_name= ttk.Checkbutton(
        master= frame_measurement_base_left, text= 'Modify Name', variable= boolvar_modify_delta_name, 
    )
    strvar_modify_delta_name= tk.StringVar()
    combobox_modify_delta_name= ttk.Combobox(
        master= frame_measurement_base_left, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_modify_delta_name, style= 'TCombobox', justify= 'center', 
        values= ['Setup time', 'Hold time']
        )

    label_delta_start= tk.Label(
        master= frame_measurement_base_middle, text= 'Start', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    label_delta_arrow= tk.Label(
        master= frame_measurement_base_middle, text= '↓', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    label_delta_stop= tk.Label(
        master= frame_measurement_base_middle, text= 'Stop', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    
    label_delta_channel= tk.Label(
        master= frame_measurement_base_middle, text= 'Channel', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    strvar_delta_channel_start= tk.StringVar()
    combobox_delta_channel_start= ttk.Combobox(
        master= frame_measurement_base_middle, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_delta_channel_start, style= 'TCombobox', justify= 'center', 
        values= ['1', '2', '3', '4']
        )
    label_delta_channel_arrow= tk.Label(
        master= frame_measurement_base_middle, text= '↓', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    strvar_delta_channel_stop= tk.StringVar()
    combobox_delta_channel_stop= ttk.Combobox(
        master= frame_measurement_base_middle, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_delta_channel_stop, style= 'TCombobox', justify= 'center', 
        values= ['1', '2', '3', '4']
        )
    button_deita_channel_switch= ttk.Button(
        master= frame_measurement_base_middle, text= 'Switch', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        command= lambda: switch_string(var_1= strvar_delta_channel_start, var_2= strvar_delta_channel_stop)
        )
    
    label_delta_transition= tk.Label(
        master= frame_measurement_base_middle, text= 'Transition', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    strvar_delta_transition_start= tk.StringVar()
    combobox_delta_transition_start= ttk.Combobox(
        master= frame_measurement_base_middle, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_delta_transition_start, style= 'TCombobox', justify= 'center', 
        values= ['Rising', 'Falling']
        )
    label_delta_transition_arrow= tk.Label(
        master= frame_measurement_base_middle, text= '↓', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    strvar_delta_transition_stop= tk.StringVar()
    combobox_delta_transition_stop= ttk.Combobox(
        master= frame_measurement_base_middle, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_delta_transition_stop, style= 'TCombobox', justify= 'center', 
        values= ['Rising', 'Falling']
        )
    button_deita_transition_switch= ttk.Button(
        master= frame_measurement_base_middle, text= 'Switch', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        command= lambda: switch_string(var_1= strvar_delta_transition_start, var_2= strvar_delta_transition_stop)
        )
    
    label_delta_edge= tk.Label(
        master= frame_measurement_base_middle, text= 'Edge No.', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    intvar_delta_edge_start= tk.IntVar()
    entry_delta_edge_start = ttk.Entry(
        master= frame_measurement_base_middle, width= max(10, int(entry_width_scale_area*0.4)), textvariable= intvar_delta_edge_start, justify= 'center')
    label_delta_edge_arrow= tk.Label(
        master= frame_measurement_base_middle, text= '↓', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    intvar_delta_edge_stop= tk.IntVar()
    entry_delta_edge_stop = ttk.Entry(
        master= frame_measurement_base_middle, width= max(10, int(entry_width_scale_area*0.4)), textvariable= intvar_delta_edge_stop, justify= 'center')
    button_deita_edge_switch= ttk.Button(
        master= frame_measurement_base_middle, text= 'Switch', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        command= lambda: switch_string(var_1= intvar_delta_edge_start, var_2= intvar_delta_edge_stop)
        )
    
    label_delta_position= tk.Label(
        master= frame_measurement_base_middle, text= 'Position', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    strvar_delta_position_start= tk.StringVar()
    combobox_delta_position_start= ttk.Combobox(
        master= frame_measurement_base_middle, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_delta_position_start, style= 'TCombobox', justify= 'center', 
        values= ['Upper', 'Middle', 'Lower']
        )
    label_delta_position_arrow= tk.Label(
        master= frame_measurement_base_middle, text= '↓', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    strvar_delta_position_stop= tk.StringVar()
    combobox_delta_position_stop= ttk.Combobox(
        master= frame_measurement_base_middle, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_delta_position_stop, style= 'TCombobox', justify= 'center', 
        values= ['Upper', 'Middle', 'Lower']
        )
    button_deita_position_switch= ttk.Button(
        master= frame_measurement_base_middle, text= 'Switch', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        command= lambda: switch_string(var_1= strvar_delta_position_start, var_2= strvar_delta_position_stop)
        )

    button_measurement_deltatime= ttk.Button(
        master= frame_measurement_base_right, text= 'Delta time', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )

    ################################################
    # Marker  ===================================================================================================================================
    labelframe_marker= tk.LabelFrame(master= frame_right_bottom_left, text= 'Marker', background= colors['labelframe'][0], fg= colors['labelframe'][1], font= ('Candara', 10, 'bold'),)

    frame_marker_left= tk.Frame(master= labelframe_marker, background= colors['labelframe'][0])
    frame_marker_right= tk.Frame(master= labelframe_marker, background= colors['labelframe'][0])

    button_delete_measurement= ttk.Button(
        master= frame_marker_left, text= 'Delete Measurement', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_add_marker= ttk.Button(
        master= frame_marker_left, text= 'Add Marker', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    button_delete_marker= ttk.Button(
        master= frame_marker_left, text= 'Delete Marker', width= button_width_scale_area,  padding= 2,
        # style= 'double_height.TButton',
        # command= lambda: mxr.
        )
    
    boolvar_multi_color_marker= tk.BooleanVar()
    checkbutton_multi_color_marker= ttk.Checkbutton(
        master= frame_marker_right, text= 'Multi-Color Marker', variable= boolvar_multi_color_marker, 
    )
    
    boolvar_measurement_1= tk.BooleanVar()
    checkbutton_marker_1= ttk.Checkbutton(
        master= frame_marker_right, text= 'Measurement 1', variable= boolvar_measurement_1, 
    )
    boolvar_measurement_2= tk.BooleanVar()
    checkbutton_marker_2= ttk.Checkbutton(
        master= frame_marker_right, text= 'Measurement 2', variable= boolvar_measurement_2, 
    )
    boolvar_measurement_3= tk.BooleanVar()
    checkbutton_marker_3= ttk.Checkbutton(
        master= frame_marker_right, text= 'Measurement 3', variable= boolvar_measurement_3, 
    )
    boolvar_measurement_4= tk.BooleanVar()
    checkbutton_marker_4= ttk.Checkbutton(
        master= frame_marker_right, text= 'Measurement 4', variable= boolvar_measurement_4, 
    )
    boolvar_measurement_5= tk.BooleanVar()
    checkbutton_marker_5= ttk.Checkbutton(
        master= frame_marker_right, text= 'Measurement 5', variable= boolvar_measurement_5, 
    )
    boolvar_measurement_6= tk.BooleanVar()
    checkbutton_marker_6= ttk.Checkbutton(
        master= frame_marker_right, text= 'Measurement 6', variable= boolvar_measurement_6, 
    )
    boolvar_measurement_7= tk.BooleanVar()
    checkbutton_marker_7= ttk.Checkbutton(
        master= frame_marker_right, text= 'Measurement 7', variable= boolvar_measurement_7, 
    )
    boolvar_measurement_8= tk.BooleanVar()
    checkbutton_marker_8= ttk.Checkbutton(
        master= frame_marker_right, text= 'Measurement 8', variable= boolvar_measurement_8, 
    )
    boolvar_measurement_9= tk.BooleanVar()
    checkbutton_marker_9= ttk.Checkbutton(
        master= frame_marker_right, text= 'Measurement 9', variable= boolvar_measurement_9, 
    )
    boolvar_measurement_10= tk.BooleanVar()
    checkbutton_marker_10= ttk.Checkbutton(
        master= frame_marker_right, text= 'Measurement 10', variable= boolvar_measurement_10, 
    )
    boolvar_measurement_11= tk.BooleanVar()
    checkbutton_marker_11= ttk.Checkbutton(
        master= frame_marker_right, text= 'Measurement 11', variable= boolvar_measurement_11, 
    )
    boolvar_measurement_12= tk.BooleanVar()
    checkbutton_marker_12= ttk.Checkbutton(
        master= frame_marker_right, text= 'Measurement 12', variable= boolvar_measurement_12, 
    )

    ################################################
    # Label/Bookmark  ===================================================================================================================================
    labelframe_label_bookmark= tk.LabelFrame(master= frame_right_bottom_left, text= 'Label/Bookmark', background= colors['labelframe'][0], fg= colors['labelframe'][1], font= ('Candara', 10, 'bold'),)

    frame_label_bookmark_top= tk.Frame(master= labelframe_label_bookmark, background= colors['labelframe'][0])
    frame_label_bookmark_base= tk.Frame(master= labelframe_label_bookmark, background= colors['labelframe'][0])
    
    intvar_label_type= tk.IntVar()
    radiobutton_label= ttk.Radiobutton(
        master= frame_label_bookmark_top, text= 'Label', value= 0, variable= intvar_label_type, style= 'radiobutton_3.TRadiobutton')
    radiobutton_bookmark= ttk.Radiobutton(
        master= frame_label_bookmark_top, text= 'Bookmark', value= 1, variable= intvar_label_type, style= 'radiobutton_3.TRadiobutton')
    
    button_label_channel_1_ckeck= ttk.Button(
        master= frame_label_bookmark_base, text= 'Channel 1', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        command= lambda: switch_string(var_1= strvar_delta_position_start, var_2= strvar_delta_position_stop)
        )
    strvar_label_channel_1= tk.StringVar()
    entry_label_channel_1= ttk.Entry(
        master= frame_label_bookmark_base, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_label_channel_1, justify= 'center')
    button_label_channel_1_delete= ttk.Button(
        master= frame_label_bookmark_base, text= 'Delete', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    
    button_label_channel_2_ckeck= ttk.Button(
        master= frame_label_bookmark_base, text= 'Channel 2', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    strvar_label_channel_2= tk.StringVar()
    entry_label_channel_2= ttk.Entry(
        master= frame_label_bookmark_base, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_label_channel_2, justify= 'center')
    button_label_channel_2_delete= ttk.Button(
        master= frame_label_bookmark_base, text= 'Delete', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    
    button_label_channel_3_ckeck= ttk.Button(
        master= frame_label_bookmark_base, text= 'Channel 3', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    strvar_label_channel_3= tk.StringVar()
    entry_label_channel_3= ttk.Entry(
        master= frame_label_bookmark_base, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_label_channel_3, justify= 'center')
    button_label_channel_3_delete= ttk.Button(
        master= frame_label_bookmark_base, text= 'Delete', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    
    button_label_channel_4_ckeck= ttk.Button(
        master= frame_label_bookmark_base, text= 'Channel 4', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    strvar_label_channel_4= tk.StringVar()
    entry_label_channel_4= ttk.Entry(
        master= frame_label_bookmark_base, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_label_channel_4, justify= 'center')
    button_label_channel_4_delete= ttk.Button(
        master= frame_label_bookmark_base, text= 'Delete', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    
    button_label_wmemory_1_ckeck= ttk.Button(
        master= frame_label_bookmark_base, text= 'Wmemory 1', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    strvar_label_wmemory_1= tk.StringVar()
    entry_label_wmemory_1= ttk.Entry(
        master= frame_label_bookmark_base, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_label_wmemory_1, justify= 'center')
    button_label_wmemory_1_delete= ttk.Button(
        master= frame_label_bookmark_base, text= 'Delete', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    
    button_label_wmemory_2_ckeck= ttk.Button(
        master= frame_label_bookmark_base, text= 'Wmemory 2', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    strvar_label_wmemory_2= tk.StringVar()
    entry_label_wmemory_2= ttk.Entry(
        master= frame_label_bookmark_base, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_label_wmemory_2, justify= 'center')
    button_label_wmemory_2_delete= ttk.Button(
        master= frame_label_bookmark_base, text= 'Delete', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    
    button_label_wmemory_3_ckeck= ttk.Button(
        master= frame_label_bookmark_base, text= 'Wmemory 3', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    strvar_label_wmemory_3= tk.StringVar()
    entry_label_wmemory_3= ttk.Entry(
        master= frame_label_bookmark_base, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_label_wmemory_3, justify= 'center')
    button_label_wmemory_3_delete= ttk.Button(
        master= frame_label_bookmark_base, text= 'Delete', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    
    button_label_wmemory_4_ckeck= ttk.Button(
        master= frame_label_bookmark_base, text= 'Wmemory 4', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    strvar_label_wememory_4= tk.StringVar()
    entry_label_wmemory_4= ttk.Entry(
        master= frame_label_bookmark_base, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_label_wememory_4, justify= 'center')
    button_label_wmemory_4_delete= ttk.Button(
        master= frame_label_bookmark_base, text= 'Delete', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    
    ################################################
    # Save Image – in PC  =====button_label_wememory_4_delete==============================================================================================================================
    labelframe_save_image= tk.LabelFrame(master= frame_right_bottom_left, text= 'Save Image in PC', background= colors['labelframe'][0], fg= colors['labelframe'][1], font= ('Candara', 10, 'bold'),)

    label_save_img_pcfolder= tk.Label(
        master= labelframe_save_image, text= 'PC Folder', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    strvar_save_img_pcfolder= tk.StringVar()
    entry_save_img_pcfolder= ttk.Entry(
        master= labelframe_save_image, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_save_img_pcfolder)
    button_browse_img_pcfolder= ttk.Button(
        master= labelframe_save_image, text= 'Browse', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )

    label_save_img_name= tk.Label(
        master= labelframe_save_image, text= 'File Name', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    strvar_save_img_name= tk.StringVar()
    entry_save_img_name= ttk.Entry(
        master= labelframe_save_image, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_save_img_name)
    button_save_img_name= ttk.Button(
        master= labelframe_save_image, text= 'Save', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )

    ################################################
    # Save Others – in Scope  ===================================================================================================================================
    labelframe_save_others= tk.LabelFrame(master= frame_right_bottom_right, text= 'Save Others in Scope', background= colors['labelframe'][0], fg= colors['labelframe'][1], font= ('Candara', 10, 'bold'),)

    frame_save_others_top= tk.Frame(master= labelframe_save_others, background= colors['labelframe'][0])
    frame_save_others_base= tk.Frame(master= labelframe_save_others, background= colors['labelframe'][0])
    
    intvar_save_others_savelocation= tk.IntVar()
    radiobutton_save_others_scopedesktop= ttk.Radiobutton(
        master= frame_save_others_top, text= 'Scope Desktop', value= 0, variable= intvar_save_others_savelocation, style= 'radiobutton_2.TRadiobutton')
    radiobutton_save_others_server= ttk.Radiobutton(
        master= frame_save_others_top, text= 'Server', value= 1, variable= intvar_save_others_savelocation, style= 'radiobutton_2.TRadiobutton')
    
    strvar_save_others_server_segment= tk.StringVar()
    combobox_save_others_server_segment= ttk.Combobox(
        master= frame_save_others_top, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_save_others_server_segment, style= 'TCombobox', justify= 'center')
    execute_commbobox_function(
        combobox= combobox_save_others_server_segment, combobox_var= strvar_save_others_server_segment, ini_dict_key= 'SaveOthersScopeSegment', ini_option_section= 'Scope_Server_Segment', ini_option_key= 'SaveOthersScopeSegment', ini_selected_section= 'Scope_Server_Segment_Selected_Values')
    
    intvar_save_others_filetype= tk.IntVar()
    radiobutton_save_others_wfmfile= ttk.Radiobutton(
        master= frame_save_others_top, text= 'Waveform File', value= 0, variable= intvar_save_others_filetype, style= 'radiobutton_3.TRadiobutton')
    radiobutton_save_others_setupfile= ttk.Radiobutton(
        master= frame_save_others_top, text= 'Setup File', value= 1, variable= intvar_save_others_filetype, style= 'radiobutton_3.TRadiobutton')

    label_save_others_scopefolder= tk.Label(
        master= frame_save_others_base, text= 'Folder', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    strvar_save_others_scopefolder= tk.StringVar()
    entry_save_others_scopefolder= ttk.Entry(
        master= frame_save_others_base, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_save_others_scopefolder)
    button_save_others_browse_scopefolder= ttk.Button(
        master= frame_save_others_base, text= 'Browse', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )

    label_save_others_channel= tk.Label(
        master= frame_save_others_base, text= 'Channel', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    strvar_save_others_channel= tk.StringVar()
    combobox_save_others_channel= ttk.Combobox(
        master= frame_save_others_base, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_save_others_channel, style= 'TCombobox', justify= 'center', 
        values= ['1', '2', '3', '4']
        )

    label_save_others_filename= tk.Label(
        master= frame_save_others_base, text= 'File Name', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    strvar_save_others_filename= tk.StringVar()
    entry_save_others_filename= ttk.Entry(
        master= frame_save_others_base, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_save_others_filename)
    button_save_others_filename_save= ttk.Button(
        master= frame_save_others_base, text= 'Save', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )

    ################################################
    # Load Wmemoey  ===================================================================================================================================
    labelframe_load_waveform= tk.LabelFrame(master= frame_right_bottom_right, text= 'Load Wmemory', background= colors['labelframe'][0], fg= colors['labelframe'][1], font= ('Candara', 10, 'bold'),)

    frame_load_waveform_top= tk.Frame(master= labelframe_load_waveform, background= colors['labelframe'][0])
    frame_load_waveform_base= tk.Frame(master= labelframe_load_waveform, background= colors['labelframe'][0])

    intvar_load_waveform_savelocation= tk.IntVar()
    radiobutton_load_waveform_scopedesktop= ttk.Radiobutton(
        master= frame_load_waveform_top, text= 'Scope Desktop', value= 0, variable= intvar_load_waveform_savelocation, style= 'radiobutton_2.TRadiobutton')
    radiobutton_load_waveform_server= ttk.Radiobutton(
        master= frame_load_waveform_top, text= 'Server', value= 1, variable= intvar_load_waveform_savelocation, style= 'radiobutton_2.TRadiobutton')
    
    strvar_load_waveform_server_segment= tk.StringVar()
    combobox_load_waveform_server_segment= ttk.Combobox(
        master= frame_load_waveform_top, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_load_waveform_server_segment, style= 'TCombobox', justify= 'center')
    execute_commbobox_function(
        combobox= combobox_load_waveform_server_segment, combobox_var= strvar_load_waveform_server_segment, ini_dict_key= 'LoadWmemoryScopeSegment', ini_option_section= 'Scope_Server_Segment', ini_option_key= 'LoadWmemoryScopeSegment', ini_selected_section= 'Scope_Server_Segment_Selected_Values')

    label_load_waveform_scopefolder= tk.Label(
        master= frame_load_waveform_base, text= 'Folder', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    strvar_load_waveform_scopefolder= tk.StringVar()
    entry_load_waveform_scopefolder= ttk.Entry(
        master= frame_load_waveform_base, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_load_waveform_scopefolder)
    button_load_waveform_browse_scopefolder= ttk.Button(
        master= frame_load_waveform_base, text= 'Browse', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )

    label_load_waveform_wmemory= tk.Label(
        master= frame_load_waveform_base, text= 'Wmemory', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    strvar_load_waveform_wmemory= tk.StringVar()
    combobox_load_waveform_wmemory= ttk.Combobox(
        master= frame_load_waveform_base, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_load_waveform_wmemory, style= 'TCombobox', justify= 'center', 
        values= ['1', '2', '3', '4']
        )

    label_load_waveform_filename= tk.Label(
        master= frame_load_waveform_base, text= 'File Name', background= colors['label'][0], fg= colors['label'][1], font= ('Candara', 11,),
        ) 
    strvar_load_waveform_filename= tk.StringVar()
    entry_load_waveform_filename= ttk.Entry(
        master= frame_load_waveform_base, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_load_waveform_filename)
    button_load_waveform_filename_load= ttk.Button(
        master= frame_load_waveform_base, text= 'Load', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )
    button_load_waveform_filename_clear= ttk.Button(
        master= frame_load_waveform_base, text= 'Clear', width= button_width_scale_area,  padding= 1,
        # style= 'normal_height.TButton',
        # command= lambda: mxr.
        )

    ################################################
    # Load Setup File ===================================================================================================================================
    labelframe_load_setup= tk.LabelFrame(master= frame_right_bottom_right, text= 'Load Setup', background= colors['labelframe'][0], fg= colors['labelframe'][1], font= ('Candara', 10, 'bold'),)

    frame_load_setup_1= tk.Frame(master= labelframe_load_setup, background= colors['labelframe'][0])
    frame_load_setup_2= tk.Frame(master= labelframe_load_setup, background= colors['labelframe'][0])
    frame_load_setup_3= tk.Frame(master= labelframe_load_setup, background= colors['labelframe'][0])
    frame_load_setup_4= tk.Frame(master= labelframe_load_setup, background= colors['labelframe'][0])

    intvar_load_setup_call_file_type= tk.IntVar()
    radiobutton_load_setup_user_defined= ttk.Radiobutton(
        master= frame_load_setup_1, text= 'User-defined', value= 0, variable= intvar_load_setup_call_file_type, style= 'radiobutton_1.TRadiobutton')
    radiobutton_load_setup_standard= ttk.Radiobutton(
        master= frame_load_setup_1, text= 'Standard', value= 1, variable= intvar_load_setup_call_file_type, style= 'radiobutton_1.TRadiobutton')

    intvar_load_setup_loadlocation= tk.IntVar()
    radiobutton_load_setup_loacation_scope= ttk.Radiobutton(
        master= frame_load_setup_2, text= 'Scope Desktop', value= 0, variable= intvar_load_setup_loadlocation, style= 'radiobutton_2.TRadiobutton')
    radiobutton_load_setup_loacation_server= ttk.Radiobutton(
        master= frame_load_setup_2, text= 'Server', value= 1, variable= intvar_load_setup_loadlocation, style= 'radiobutton_2.TRadiobutton')

    combobox_load_setup_loacation_server= ttk.Combobox()

    label_load_setup_user_defined_folder= tk.Label(

    )
    strvar_load_setup_user_defined_folder= tk.StringVar()
    entry_load_setup_user_defined_folder= ttk.Entry(
        master= frame_load_setup_2, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_load_setup_user_defined_folder)
    button_load_setup_user_defined_browse= ttk.Button(
        master= frame_load_setup_2, text= 'Browse', width= button_width_scale_area,  padding= 1,)

    label_load_setup_user_defined_filename= tk.Label(

    )
    strvar_load_setup_user_defined_filename= tk.StringVar()
    entry_load_setup_user_defined_filename= ttk.Entry(
        master= frame_load_setup_2, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_load_setup_user_defined_filename)
    button_load_setup_user_defined_load= ttk.Button(
        master= frame_load_setup_2, text= 'Load', width= button_width_scale_area,  padding= 1,)

    boolvar_modify_label= tk.BooleanVar()
    checkbutton_modify_label= ttk.Checkbutton(
        master= frame_load_setup_3, text= 'Label', variable= boolvar_modify_label)
    boolvar_modify_timebase= tk.BooleanVar()
    checkbutton_modify_timebase= ttk.Checkbutton(
        master= frame_load_setup_3, text= 'Time', variable= boolvar_modify_timebase)
    boolvar_modify_voltage= tk.BooleanVar()
    checkbutton_modify_voltage= ttk.Checkbutton(
        master= frame_load_setup_3, text= 'Voltage', variable= boolvar_modify_voltage)

    strvar_load_setup_standard_interface= tk.StringVar()
    combobox_load_setup_standard_interface= ttk.Combobox(
        master= frame_load_setup_4, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_load_setup_standard_interface, style= 'TCombobox', justify= 'center')
    strvar_load_setup_standard_subfolder= tk.StringVar()
    combobox_load_setup_standard_subfolder= ttk.Combobox(
        master= frame_load_setup_4, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_load_setup_standard_subfolder, style= 'TCombobox', justify= 'center')

    strvar_load_setup_standard_files= tk.StringVar()
    combobox_load_setup_standard_files= ttk.Combobox(
        master= frame_load_setup_4, width= max(10, int(entry_width_scale_area*0.4)), textvariable= strvar_load_setup_standard_files, style= 'TCombobox', justify= 'center')

    button_load_setup_standard_load= ttk.Button(
        master= frame_load_setup_4, text= 'Load', width= button_width_scale_area,  padding= 1,)


    # Weight  ==============================================================================================================================================
    frame_left.rowconfigure(0, weight= 3, uniform= 'row')  # scale/offset/trigger
    frame_left.rowconfigure(1, weight= 5, uniform= 'row')  # threshold
    frame_left.rowconfigure(2, weight= 2, uniform= 'row')  # channel
    frame_left.rowconfigure(3, weight= 2, uniform= 'row')  # control
    frame_left.rowconfigure(4, weight= 2, uniform= 'row')  # acquisition

    frame_left.columnconfigure(0, weight= 1, uniform= 'col')

    frame_right.rowconfigure(0, weight= 2, uniform= 'row')  # right top
    frame_right.rowconfigure(1, weight= 3, uniform= 'row')  # right bottom

    frame_right.columnconfigure(0, weight= 1, uniform= 'col')  # right bottom left
    frame_right.columnconfigure(1, weight= 1, uniform= 'col')  # right bottom right

    frame_right_top.rowconfigure(0, weight= 1, uniform= 'row')  # measurement
    frame_right_top.columnconfigure(0, weight= 1, uniform= 'col')

    frame_right_bottom_left.rowconfigure(0, weight= 3, uniform= 'row')  # marker
    frame_right_bottom_left.rowconfigure(1, weight= 2, uniform= 'row')  # label/bookmark
    frame_right_bottom_left.rowconfigure(2, weight= 1, uniform= 'row')  # save image
    frame_right_bottom_left.columnconfigure(0, weight= 1, uniform= 'col')

    frame_right_bottom_right.rowconfigure(0, weight= 1, uniform= 'row')  # save others
    frame_right_bottom_right.rowconfigure(1, weight= 1, uniform= 'row')  # load waveform
    frame_right_bottom_right.rowconfigure(2, weight= 2, uniform= 'row')  # load setup
    frame_right_bottom_right.columnconfigure(0, weight= 1, uniform= 'col')

    ### scale/offset/trigger
    labelframe_scale_offset_trigger.rowconfigure(0, weight= 3, uniform= 'row')
    labelframe_scale_offset_trigger.rowconfigure(1, weight= 1, uniform= 'row')
    labelframe_scale_offset_trigger.columnconfigure(0, weight= 1, uniform= 'col')

    for i in range(4):
        frame_scalearea_top.rowconfigure(i, weight= 1, uniform= 'row')
    for j in range(4):
        if j % 2 == 0:
            frame_scalearea_top.columnconfigure(j, weight= 2, uniform= 'col')
        else:
            frame_scalearea_top.columnconfigure(j, weight= 1, uniform= 'col')
    
    frame_scalearea_bottom.rowconfigure(0, weight= 1, uniform= 'row')
    frame_scalearea_bottom.columnconfigure(0, weight= 1, uniform= 'col')
    frame_scalearea_bottom.columnconfigure(1, weight= 1, uniform= 'col')
    frame_scalearea_bottom.columnconfigure(2, weight= 1, uniform= 'col')
    ###########################
    ### threshold
    for i in range(7):
        labelframe_threshold.rowconfigure(i, weight= 1, uniform= 'row')
    for j in range(4):
        labelframe_threshold.columnconfigure(j, weight= 1, uniform= 'col')    
    ###########################
    ### channel
    for i in range(2):
        labelframe_channel.rowconfigure(i, weight= 1, uniform= 'row')
    for j in range(4):
        labelframe_channel.columnconfigure(j, weight= 1, uniform= 'col')    
    ###########################
    ### control
    for i in range(2):
        labelframe_control.rowconfigure(i, weight= 1, uniform= 'row')
    for j in range(4):
        labelframe_control.columnconfigure(j, weight= 1, uniform= 'col')    
    ###########################
    ### acquisition
    labelframe_acquisition.rowconfigure(0, weight= 1, uniform= 'row')
    labelframe_acquisition.rowconfigure(1, weight= 1, uniform= 'row')
    labelframe_acquisition.rowconfigure(2, weight= 1, uniform= 'row')
    labelframe_acquisition.columnconfigure(0, weight= 4, uniform= 'col')
    labelframe_acquisition.columnconfigure(1, weight= 2, uniform= 'col')
    labelframe_acquisition.columnconfigure(2, weight= 3, uniform= 'col')
    ###########################
    ### measurement
    labelframe_measurement.rowconfigure(0, weight= 4, uniform= 'row')
    labelframe_measurement.rowconfigure(1, weight= 1, uniform= 'row')
    labelframe_measurement.rowconfigure(2, weight= 5, uniform= 'row')
    labelframe_measurement.columnconfigure(0, weight= 4, uniform= 'col')

    frame_measurement_top.rowconfigure(0, weight= 1, uniform= 'row')
    frame_measurement_top.columnconfigure(0, weight= 1, uniform= 'col')
    frame_measurement_top.columnconfigure(1, weight= 3, uniform= 'col')

    frame_measurement_middle.rowconfigure(0, weight= 1, uniform= 'row')
    frame_measurement_middle.columnconfigure(0, weight= 1, uniform= 'col')

    frame_measurement_base.rowconfigure(0, weight= 1, uniform= 'row')
    frame_measurement_base.columnconfigure(0, weight= 2, uniform= 'col')
    frame_measurement_base.columnconfigure(1, weight= 4, uniform= 'col')
    frame_measurement_base.columnconfigure(2, weight= 1, uniform= 'col')

    frame_measurement_top_left.rowconfigure(0, weight= 3, uniform= 'row')
    frame_measurement_top_left.rowconfigure(1, weight= 1, uniform= 'row')
    frame_measurement_top_left.columnconfigure(0, weight= 1, uniform= 'col')
    frame_measurement_top_left.columnconfigure(1, weight= 1, uniform= 'col')

    for i in range(3):
        frame_measurement_top_right.rowconfigure(i, weight= 1, uniform= 'row')
    for j in range(5):
        frame_measurement_top_right.columnconfigure(j, weight= 1, uniform= 'col')
    
    for i in range(5):
        frame_measurement_base_left.rowconfigure(i, weight= 1, uniform= 'row')
    frame_measurement_base_left.columnconfigure(0, weight= 1, uniform= 'col')
    frame_measurement_base_left.columnconfigure(1, weight= 1, uniform= 'col')

    for i in range(5):
        frame_measurement_base_middle.rowconfigure(i, weight= 1, uniform= 'row')
    for j in range(5):
        frame_measurement_base_middle.columnconfigure(j, weight= 1, uniform= 'col')

    frame_measurement_base_right.rowconfigure(0, weight= 1, uniform= 'row')
    frame_measurement_base_right.columnconfigure(0, weight= 1, uniform= 'col')
    ###########################
    ### marker
    labelframe_marker.rowconfigure(0, weight= 1, uniform= 'row')
    labelframe_marker.columnconfigure(0, weight= 1, uniform= 'col')
    labelframe_marker.columnconfigure(1, weight= 2, uniform= 'col')

    for i in range(3):
        frame_marker_left.rowconfigure(i, weight= 1, uniform= 'row')
    frame_marker_left.columnconfigure(0, weight= 1, uniform= 'col')
    for i in range(7):
        frame_marker_right.rowconfigure(i, weight= 1, uniform= 'row')
    frame_marker_right.columnconfigure(0, weight= 1, uniform= 'col')
    frame_marker_right.columnconfigure(1, weight= 1, uniform= 'col')
    ###########################
    ### label/bookmark
    labelframe_label_bookmark.rowconfigure(0, weight= 1, uniform= 'row')
    labelframe_label_bookmark.rowconfigure(1, weight= 4, uniform= 'row')
    labelframe_label_bookmark.columnconfigure(0, weight= 1, uniform= 'col')

    frame_label_bookmark_top.rowconfigure(0, weight= 1, uniform= 'row')
    frame_label_bookmark_top.columnconfigure(0, weight= 1, uniform= 'col')
    frame_label_bookmark_top.columnconfigure(1, weight= 5, uniform= 'col')

    for i in range(4):
        frame_label_bookmark_base.rowconfigure(i, weight= 1, uniform= 'row')
    for j in range(6):
        if j%3 == 0:
            frame_label_bookmark_base.columnconfigure(j, weight= 2, uniform= 'col')
        elif j%3 == 1:
            frame_label_bookmark_base.columnconfigure(j, weight= 5, uniform= 'col')
        else:
            frame_label_bookmark_base.columnconfigure(j, weight= 1, uniform= 'col')
    ###########################
    ### save Image – in PC
    labelframe_save_image.rowconfigure(0, weight= 1, uniform= 'row')
    labelframe_save_image.rowconfigure(1, weight= 1, uniform= 'row')
    labelframe_save_image.columnconfigure(0, weight= 1, uniform= 'col')
    labelframe_save_image.columnconfigure(1, weight= 5, uniform= 'col')
    labelframe_save_image.columnconfigure(2, weight= 1, uniform= 'col')
    ###########################
    ### save Others – in Scope
    labelframe_save_others.rowconfigure(0, weight= 1, uniform= 'row')
    labelframe_save_others.rowconfigure(1, weight= 1, uniform= 'row')
    labelframe_save_others.columnconfigure(0, weight= 1, uniform= 'col')

    frame_save_others_top.rowconfigure(0, weight= 1, uniform= 'row')
    frame_save_others_top.rowconfigure(1, weight= 1, uniform= 'row')
    frame_save_others_top.columnconfigure(0, weight= 1, uniform= 'col')
    frame_save_others_top.columnconfigure(1, weight= 1, uniform= 'col')
    frame_save_others_top.columnconfigure(2, weight= 2, uniform= 'col')

    frame_save_others_base.rowconfigure(0, weight= 1, uniform= 'row')
    frame_save_others_base.rowconfigure(1, weight= 1, uniform= 'row')
    frame_save_others_base.columnconfigure(0, weight= 1, uniform= 'col')
    frame_save_others_base.columnconfigure(1, weight= 1, uniform= 'col')
    frame_save_others_base.columnconfigure(2, weight= 1, uniform= 'col')
    frame_save_others_base.columnconfigure(3, weight= 3, uniform= 'col')
    frame_save_others_base.columnconfigure(4, weight= 1, uniform= 'col')
    ###########################
    ### load wmemory
    labelframe_load_waveform.rowconfigure(0, weight= 1, uniform= 'row')
    labelframe_load_waveform.rowconfigure(1, weight= 2, uniform= 'row')
    labelframe_load_waveform.columnconfigure(0, weight= 1, uniform= 'col')

    frame_load_waveform_top.rowconfigure(0, weight= 1, uniform= 'row')
    frame_load_waveform_top.columnconfigure(0, weight= 1, uniform= 'col')
    frame_load_waveform_top.columnconfigure(1, weight= 1, uniform= 'col')
    frame_load_waveform_top.columnconfigure(2, weight= 2, uniform= 'col')

    frame_load_waveform_base.rowconfigure(0, weight= 1, uniform= 'row')
    frame_load_waveform_base.rowconfigure(1, weight= 1, uniform= 'row')
    frame_load_waveform_base.columnconfigure(0, weight= 2, uniform= 'col')
    frame_load_waveform_base.columnconfigure(1, weight= 2, uniform= 'col')
    frame_load_waveform_base.columnconfigure(2, weight= 2, uniform= 'col')
    frame_load_waveform_base.columnconfigure(3, weight= 4, uniform= 'col')
    frame_load_waveform_base.columnconfigure(4, weight= 1, uniform= 'col')
    frame_load_waveform_base.columnconfigure(5, weight= 1, uniform= 'col')
    ###########################
    ### load setup
    labelframe_load_setup.rowconfigure(0, weight= 2, uniform= 'row')
    labelframe_load_setup.rowconfigure(1, weight= 2, uniform= 'row')
    labelframe_load_setup.rowconfigure(2, weight= 1, uniform= 'row')
    labelframe_load_setup.rowconfigure(3, weight= 1, uniform= 'row')
    labelframe_load_setup.columnconfigure(0, weight= 1, uniform= 'col')

    frame_load_setup_1.rowconfigure(0, weight= 1, uniform= 'row')
    frame_load_setup_1.rowconfigure(1, weight= 1, uniform= 'row')
    frame_load_setup_1.columnconfigure(0, weight= 1, uniform= 'col')
    frame_load_setup_1.columnconfigure(1, weight= 1, uniform= 'col')
    frame_load_setup_1.columnconfigure(2, weight= 1, uniform= 'col')

    frame_load_setup_2.rowconfigure(0, weight= 1, uniform= 'row')
    frame_load_setup_2.rowconfigure(1, weight= 1, uniform= 'row')
    frame_load_setup_2.columnconfigure(0, weight= 1, uniform= 'col')
    frame_load_setup_2.columnconfigure(1, weight= 6, uniform= 'col')
    frame_load_setup_2.columnconfigure(2, weight= 1, uniform= 'col')

    frame_load_setup_3.rowconfigure(0, weight= 1, uniform= 'row')
    frame_load_setup_3.columnconfigure(0, weight= 1, uniform= 'col')
    frame_load_setup_3.columnconfigure(1, weight= 1, uniform= 'col')
    frame_load_setup_3.columnconfigure(2, weight= 1, uniform= 'col')

    frame_load_setup_4.rowconfigure(0, weight= 1, uniform= 'row')
    frame_load_setup_4.columnconfigure(0, weight= 1, uniform= 'col')
    frame_load_setup_4.columnconfigure(1, weight= 4, uniform= 'col')
    frame_load_setup_4.columnconfigure(2, weight= 2, uniform= 'col')
    frame_load_setup_4.columnconfigure(3, weight= 1, uniform= 'col')
    ###########################
    ###########################

    
    # Left Grid  ==============================================================================================================================================
    labelframe_scale_offset_trigger.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    labelframe_threshold.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    labelframe_channel.grid(row= 2, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    labelframe_control.grid(row= 3, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    labelframe_acquisition.grid(row= 4, column= 0, padx= 2, pady= 2, sticky= 'nesw')

    ## Scale/Offset/Trigger  ==============================================================================================================================================
    frame_scalearea_top.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    frame_scalearea_bottom.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    ### top area
    button_voltage_scale.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'ew')
    combobox_voltage_scale.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'ew')
    button_timebase_scale.grid(row= 0, column= 2, padx= 2, pady= 2, sticky= 'ew')
    entry_timebase_scale.grid(row= 0, column= 3, padx= 2, pady= 2, sticky= 'ew')
    button_voltage_offset.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'ew')
    combobox_voltage_offset.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'ew')
    button_timebase_offset.grid(row= 1, column= 2, padx= 2, pady= 2, sticky= 'ew')
    entry_timebase_offset.grid(row= 1, column= 3, padx= 2, pady= 2, sticky= 'ew')
    button_trigger_channel.grid(row= 2, column= 0, padx= 2, pady= 2, sticky= 'ew')
    combobox_trigger_channel.grid(row= 2, column= 1, padx= 2, pady= 2, sticky= 'ew')
    button_trigger_level.grid(row= 3, column= 0, padx= 2, pady= 2, sticky= 'ew')
    combobox_trigger_level.grid(row= 3, column= 1, padx= 2, pady= 2, sticky= 'ew')
    ### bottom area
    button_trigger_mode.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'w')
    button_trigger_slope.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'w')
    button_set_all.grid(row= 0, column= 2, padx= 2, pady= 2, sticky= 'w')
    ###########################
    ## Threshold  ==============================================================================================================================================
    button_general_threshold_value.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw', columnspan= 2)
    label_general_threshold_value_top.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    combobox_general_threshold_value_top.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    label_general_threshold_value_middle.grid(row= 2, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    combobox_general_threshold_value_middle.grid(row= 2, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    label_general_threshold_value_base.grid(row= 3, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    combobox_general_threshold_value_base.grid(row= 3, column= 1, padx= 2, pady= 2, sticky= 'nesw')

    button_general_threshold_percent.grid(row= 0, column= 2, padx= 2, pady= 2, sticky= 'nesw', columnspan= 2)
    label_general_threshold_percent_top.grid(row= 1, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    combobox_general_threshold_percent_top.grid(row= 1, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    label_general_threshold_percent_middle.grid(row= 2, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    combobox_general_threshold_percent_middle.grid(row= 2, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    label_general_threshold_percent_base.grid(row= 3, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    combobox_general_threshold_percent_base.grid(row= 3, column= 3, padx= 2, pady= 2, sticky= 'nesw')

    button_RF_threshold_value.grid(row= 4, column= 0, padx= 2, pady= 2, sticky= 'nesw', columnspan= 2)
    label_RF_threshold_value_top.grid(row= 5, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    combobox_RF_threshold_value_top.grid(row= 5, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    label_RF_threshold_value_base.grid(row= 6, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    combobox_RF_threshold_value_base.grid(row= 6, column= 1, padx= 2, pady= 2, sticky= 'nesw')

    button_RF_threshold_percent.grid(row= 4, column= 2, padx= 2, pady= 2, sticky= 'nesw', columnspan= 2)
    label_RF_threshold_percent_top.grid(row= 5, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    combobox_RF_threshold_percent_top.grid(row= 5, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    label_RF_threshold_percent_base.grid(row= 6, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    combobox_RF_threshold_percent_base.grid(row= 6, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    ###########################
    ## Channel  ==============================================================================================================================================
    button_channel_1.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    button_channel_2.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_channel_3.grid(row= 0, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    button_channel_4.grid(row= 0, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    button_wememory_1.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    button_wememory_2.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_wememory_3.grid(row= 1, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    button_wememory_4.grid(row= 1, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    ###########################
    ## Control  ==============================================================================================================================================
    button_control_run.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    button_control_stop.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_control_single.grid(row= 0, column= 2, padx= 2, pady= 2, sticky= 'nes')

    button_control_autoscale.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    button_control_default.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_control_clearwaveform.grid(row= 1, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    button_disable_button.grid(row= 1, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    ###########################
    ### Acquisition ==============================================================================================================================================
    button_smapling_rate.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    combobox_smapling_rate.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_smapling_rate_auto.grid(row= 0, column= 2, padx= 2, pady= 2, sticky= 'nesw')

    button_memory_depth.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    entry_memory_depth.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_memory_depth_auto.grid(row= 1, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    
    button_waveform_intensity.grid(row= 2, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    entry_waveform_intensity.grid(row= 2, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_set_to_fixty.grid(row= 2, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    ###########################


    # Right Grid  ==============================================================================================================================================
    frame_right_top.grid(row= 0, column= 0, padx= 2, pady= 2, columnspan= 2, sticky= 'nesw')
    frame_right_bottom_left.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    frame_right_bottom_right.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'nesw')

    ## Right top Grid  ==============================================================================================================================================
    labelframe_measurement.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    
    ## Right bottom left Grid  ==============================================================================================================================================
    labelframe_marker.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    labelframe_label_bookmark.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    labelframe_save_image.grid(row= 2, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    
    ## Right bottom right Grid  ==============================================================================================================================================
    labelframe_save_others.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    labelframe_load_waveform.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    labelframe_load_setup.grid(row= 2, column= 0, padx= 2, pady= 2, sticky= 'nesw')

    ### Measurement ==============================================================================================================================================
    frame_measurement_top.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    frame_measurement_middle.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    frame_measurement_base.grid(row= 2, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    
    frame_measurement_top_left.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    frame_measurement_top_right.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw')

    frame_measurement_base_left.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    frame_measurement_base_middle.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    frame_measurement_base_right.grid(row= 0, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    
    button_show_result_table.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw', columnspan= 2)
    radiobutton_single_channel.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    combobox_measurement_single_channel.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'nesw')

    button_measurement_frequency.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    button_measurement_period.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_measurement_dutycycle.grid(row= 0, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    button_measurement_tH.grid(row= 0, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    button_measurement_tL.grid(row= 0, column= 4, padx= 2, pady= 2, sticky= 'nesw')
    button_measurement_tR.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    button_measurement_tF.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_measurement_slewR.grid(row= 1, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    button_measurement_slewF.grid(row= 1, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    button_measurement_perper.grid(row= 1, column= 4, padx= 2, pady= 2, sticky= 'nesw')
    button_measurement_VIH.grid(row= 2, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    button_measurement_VIL.grid(row= 2, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_measurement_VPP.grid(row= 2, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    button_measurement_Vmax.grid(row= 2, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    button_measurement_Vmin.grid(row= 2, column= 4, padx= 2, pady= 2, sticky= 'nesw')
    
    label_delta_setting.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')

    radiobutton_double_channels.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    checkbutton_modify_delta_name.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    combobox_modify_delta_name.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'nesw')

    label_delta_start.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    label_delta_arrow.grid(row= 2, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    label_delta_stop.grid(row= 3, column= 0, padx= 2, pady= 2, sticky= 'nesw')

    label_delta_channel.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    combobox_delta_channel_start.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    label_delta_channel_arrow.grid(row= 2, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    combobox_delta_channel_stop.grid(row= 3, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_deita_channel_switch.grid(row= 4, column= 1, padx= 2, pady= 2, sticky= 'nesw')

    label_delta_transition.grid(row= 0, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    combobox_delta_transition_start.grid(row= 1, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    label_delta_transition_arrow.grid(row= 2, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    combobox_delta_transition_stop.grid(row= 3, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    button_deita_transition_switch.grid(row= 4, column= 2, padx= 2, pady= 2, sticky= 'nesw')

    label_delta_edge.grid(row= 0, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    entry_delta_edge_start.grid(row= 1, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    label_delta_edge_arrow.grid(row= 2, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    entry_delta_edge_stop.grid(row= 3, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    button_deita_edge_switch.grid(row= 4, column= 3, padx= 2, pady= 2, sticky= 'nesw')

    label_delta_position.grid(row= 0, column= 4, padx= 2, pady= 2, sticky= 'nesw')
    combobox_delta_position_start.grid(row= 1, column= 4, padx= 2, pady= 2, sticky= 'nesw')
    label_delta_position_arrow.grid(row= 2, column= 4, padx= 2, pady= 2, sticky= 'nesw')
    combobox_delta_position_stop.grid(row= 3, column= 4, padx= 2, pady= 2, sticky= 'nesw')
    button_deita_position_switch.grid(row= 4, column= 4, padx= 2, pady= 2, sticky= 'nesw')

    button_measurement_deltatime.grid(row= 0, column= 0, padx= 30, pady= 30, sticky= 'nesw')
    
    ###########################
    ### Marker ==============================================================================================================================================
    frame_marker_left.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    frame_marker_right.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw')

    button_delete_measurement.grid(row= 0, column= 0, padx= 5, pady= 5, sticky= 'nesw')
    button_add_marker.grid(row= 1, column= 0, padx= 5, pady= 5, sticky= 'nesw')
    button_delete_marker.grid(row= 2, column= 0, padx= 5, pady= 5, sticky= 'nesw')

    checkbutton_multi_color_marker.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw', columnspan= 2)

    checkbutton_marker_1.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    checkbutton_marker_2.grid(row= 2, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    checkbutton_marker_3.grid(row= 3, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    checkbutton_marker_4.grid(row= 4, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    checkbutton_marker_5.grid(row= 5, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    checkbutton_marker_6.grid(row= 6, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    checkbutton_marker_7.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    checkbutton_marker_8.grid(row= 2, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    checkbutton_marker_9.grid(row= 3, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    checkbutton_marker_10.grid(row= 4, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    checkbutton_marker_11.grid(row= 5, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    checkbutton_marker_12.grid(row= 6, column= 1, padx= 2, pady= 2, sticky= 'nesw')

    ###########################
    ### Label/Bookmark ==============================================================================================================================================
    frame_label_bookmark_top.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    frame_label_bookmark_base.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')

    radiobutton_label.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    radiobutton_bookmark.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw')

    button_label_channel_1_ckeck.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    entry_label_channel_1.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_label_channel_1_delete.grid(row= 0, column= 2, padx= 2, pady= 2, sticky= 'nesw')

    button_label_channel_2_ckeck.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    entry_label_channel_2.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_label_channel_2_delete.grid(row= 1, column= 2, padx= 2, pady= 2, sticky= 'nesw')

    button_label_channel_3_ckeck.grid(row= 2, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    entry_label_channel_3.grid(row= 2, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_label_channel_3_delete.grid(row= 2, column= 2, padx= 2, pady= 2, sticky= 'nesw')

    button_label_channel_4_ckeck.grid(row= 3, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    entry_label_channel_4.grid(row= 3, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_label_channel_4_delete.grid(row= 3, column= 2, padx= 2, pady= 2, sticky= 'nesw')

    button_label_wmemory_1_ckeck.grid(row= 0, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    entry_label_wmemory_1.grid(row= 0, column= 4, padx= 2, pady= 2, sticky= 'nesw')
    button_label_wmemory_1_delete.grid(row= 0, column= 5, padx= 2, pady= 2, sticky= 'nesw')

    button_label_wmemory_2_ckeck.grid(row= 1, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    entry_label_wmemory_2.grid(row= 1, column= 4, padx= 2, pady= 2, sticky= 'nesw')
    button_label_wmemory_2_delete.grid(row= 1, column= 5, padx= 2, pady= 2, sticky= 'nesw')

    button_label_wmemory_3_ckeck.grid(row= 2, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    entry_label_wmemory_3.grid(row= 2, column= 4, padx= 2, pady= 2, sticky= 'nesw')
    button_label_wmemory_3_delete.grid(row= 2, column= 5, padx= 2, pady= 2, sticky= 'nesw')

    button_label_wmemory_4_ckeck.grid(row= 3, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    entry_label_wmemory_4.grid(row= 3, column= 4, padx= 2, pady= 2, sticky= 'nesw')
    button_label_wmemory_4_delete.grid(row= 3, column= 5, padx= 2, pady= 2, sticky= 'nesw')

    ###########################
    ### Save Image – in PC ==============================================================================================================================================
    label_save_img_pcfolder.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    entry_save_img_pcfolder.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_browse_img_pcfolder.grid(row= 0, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    
    label_save_img_name.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    entry_save_img_name.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    button_save_img_name.grid(row= 1, column= 2, padx= 2, pady= 2, sticky= 'nesw')

    ###########################
    ### Save Others – in Scope ==============================================================================================================================================
    frame_save_others_top.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    frame_save_others_base.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')

    radiobutton_save_others_scopedesktop.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    radiobutton_save_others_server.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    combobox_save_others_server_segment.grid(row= 0, column= 2, padx= 2, pady= 2, sticky= 'nsw')

    radiobutton_save_others_wfmfile.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    radiobutton_save_others_setupfile.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'nesw')

    label_save_others_scopefolder.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    entry_save_others_scopefolder.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw', columnspan= 3)
    button_save_others_browse_scopefolder.grid(row= 0, column= 4, padx= 2, pady= 2, sticky= 'nesw')

    label_save_others_channel.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    combobox_save_others_channel.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    
    label_save_others_filename.grid(row= 1, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    entry_save_others_filename.grid(row= 1, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    button_save_others_filename_save.grid(row= 1, column= 4, padx= 2, pady= 2, sticky= 'nesw')

    ###########################
    ### Load Wmemory ==============================================================================================================================================
    frame_load_waveform_top.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    frame_load_waveform_base.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')

    radiobutton_load_waveform_scopedesktop.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    radiobutton_load_waveform_server.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    combobox_load_waveform_server_segment.grid(row= 0, column= 2, padx= 2, pady= 2, sticky= 'nsw')

    label_load_waveform_scopefolder.grid(row= 0, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    entry_load_waveform_scopefolder.grid(row= 0, column= 1, padx= 2, pady= 2, sticky= 'nesw', columnspan= 3)
    button_load_waveform_browse_scopefolder.grid(row= 0, column= 4, padx= 2, pady= 2, sticky= 'nesw', columnspan= 2)

    label_load_waveform_wmemory.grid(row= 1, column= 0, padx= 2, pady= 2, sticky= 'nesw')
    combobox_load_waveform_wmemory.grid(row= 1, column= 1, padx= 2, pady= 2, sticky= 'nesw')
    
    label_load_waveform_filename.grid(row= 1, column= 2, padx= 2, pady= 2, sticky= 'nesw')
    entry_load_waveform_filename.grid(row= 1, column= 3, padx= 2, pady= 2, sticky= 'nesw')
    button_load_waveform_filename_load.grid(row= 1, column= 4, padx= 2, pady= 2, sticky= 'nesw')
    button_load_waveform_filename_clear.grid(row= 1, column= 5, padx= 2, pady= 2, sticky= 'nesw')

    ###########################
    ### Load Setup ==============================================================================================================================================
    frame_load_setup_1
    frame_load_setup_2
    frame_load_setup_3
    frame_load_setup_4

    radiobutton_load_setup_user_defined
    radiobutton_load_setup_standard

    radiobutton_load_setup_loacation_scope
    radiobutton_load_setup_loacation_server
    combobox_load_setup_loacation_server

    label_load_setup_user_defined_folder
    entry_load_setup_user_defined_folder
    button_load_setup_user_defined_browse

    label_load_setup_user_defined_filename
    entry_load_setup_user_defined_filename
    button_load_setup_user_defined_load

    checkbutton_modify_label
    checkbutton_modify_timebase
    checkbutton_modify_voltage

    combobox_load_setup_standard_interface
    combobox_load_setup_standard_subfolder
    combobox_load_setup_standard_files
    button_load_setup_standard_load



























    # button_width, button_height= set_button_size(base_btn_w= 20, base_btn_h= 2)

    # ## ttk.Button沒有-height 
    # button_frequency = ttk.Button(label_frame_measurement_item, text='Frequency', width= button_width, command= lambda: mxr.call_measurement_frequency(chan= intvar_channel_single.get()))
    # button_period = ttk.Button(label_frame_measurement_item, text='Period', width= button_width, command= lambda: mxr.call_measurement_period(chan= intvar_channel_single.get()))
    # button_dutycycle = ttk.Button(label_frame_measurement_item, text='Duty Cycle', width= button_width, command= lambda: mxr.call_measurement_dutycycle(chan= intvar_channel_single.get()))
    # button_delta_time = ttk.Button(label_frame_measurement_item, text='Delta Time', width= button_width, command= lambda: mxr.call_measurement_delta_time(
    #     edge_1= strvar_start_risefall.get(), 
    #     num_1= strvar_start_N_edge.get(), 
    #     pos_1= strvar_start_position.get(), 
    #     edge_2= strvar_stop_risefall.get(), 
    #     num_2= strvar_stop_N_edge.get(), 
    #     pos_2= strvar_stop_position.get(), 
    #     chan= intvar_channel.get(), 
    #     chan_start= intvar_channel_delta_start.get(), 
    #     chan_stop= intvar_channel_delta_stop.get(), 
    #     modify_name= boolvar_delta_name.get(),
    #     timing_name= strvar_delta_name.get()
    #     ))
    # button_tH = ttk.Button(label_frame_measurement_item, text='tH', width= button_width, command= lambda: mxr.call_measurement_tH(chan= intvar_channel_single.get()))
    # button_tL = ttk.Button(label_frame_measurement_item, text='tL', width= button_width, command= lambda: mxr.call_measurement_tL(chan= intvar_channel_single.get()))
    # button_tR = ttk.Button(label_frame_measurement_item, text='tR', width= button_width, command= lambda: mxr.call_measurement_tR(chan= intvar_channel_single.get()))
    # button_tF = ttk.Button(label_frame_measurement_item, text='tF', width= button_width, command= lambda: mxr.call_measurement_tF(chan= intvar_channel_single.get()))
    # button_VIH = ttk.Button(label_frame_measurement_item, text='VIH', width= button_width, command= lambda: mxr.call_measurement_VIH(chan= intvar_channel_single.get()))
    # button_VIL= ttk.Button(label_frame_measurement_item, text='VIL', width= button_width, command= lambda: mxr.call_measurement_VIL(chan= intvar_channel_single.get()))
    # button_slewrate_tR = ttk.Button(label_frame_measurement_item, text='Slew Rate tR', width= button_width, command= lambda: mxr.call_measurement_slewrate(chan= intvar_channel_single.get(), direction= 'RISing'))
    # button_slewrate_tF = ttk.Button(label_frame_measurement_item, text='Slew Rate tF', width= button_width, command= lambda: mxr.call_measurement_slewrate(chan= intvar_channel_single.get(), direction= 'FALLing'))
    # button_VPP = ttk.Button(label_frame_measurement_item, text='VPP', width= button_width, command= lambda: mxr.call_measurement_VPP(chan= intvar_channel_single.get()))
    # button_VMAX = ttk.Button(label_frame_measurement_item, text='VMAX', width= button_width, command= lambda: mxr.call_measurement_VMAX(chan= intvar_channel_single.get()))
    # button_VMIN = ttk.Button(label_frame_measurement_item, text='VMIN', width= button_width, command= lambda: mxr.call_measurement_VMIN(chan= intvar_channel_single.get()))
    # button_PeriodtoPeriod =  ttk.Button(label_frame_measurement_item, text='1Per-Per', width= button_width, command= lambda: mxr.call_measurement_NCJitter(chan= intvar_channel_single.get(), direction= 'RISing'))

    # # Scale / Offset Frame ===================================================================================================================================

    # label_frame_scale= tk.LabelFrame(window, text= 'Scale / Offset', background= background_color_1, fg= '#506376', font= ('Candara', 10, 'bold'),)


    # entry_width= set_entry_width(base_entry_width= 7)


    # label_volt_scale = tk.Label(label_frame_scale, text= 'Voltage Scale (V)', background= background_color_1, fg= '#0D325C', font= candara_base_font,)

    # strvar_voltage_scale = tk.StringVar()
    # combobox_voltage_scale = ttk.Combobox(label_frame_scale, width= max(4, int(entry_width*0.4)), textvariable= strvar_voltage_scale, font= entry_font)
    # execute_commbobox_function(combobox= combobox_voltage_scale, combobox_var= strvar_voltage_scale, ini_dict_key= 'VoltScale', ini_option_section= 'Scale_Offset_Config', ini_option_key= 'VoltScale', ini_selected_section= 'Scale_Offset_Selected_Values')

    # label_voltage_offset = tk.Label(label_frame_scale, text= 'Voltage Offset (V)', background= background_color_1, fg= '#0D325C', font= candara_base_font,)

    # strvar_voltage_offset = tk.StringVar()
    # combobox_voltage_offset = ttk.Combobox(label_frame_scale, width= max(4, int(entry_width*0.4)), textvariable= strvar_voltage_offset, font= entry_font)
    # execute_commbobox_function(combobox= combobox_voltage_offset, combobox_var= strvar_voltage_offset, ini_dict_key= 'VoltOffset', ini_option_section= 'Scale_Offset_Config', ini_option_key= 'VoltOffset', ini_selected_section= 'Scale_Offset_Selected_Values')

    # button_voltage_scale = ttk.Button(label_frame_scale, text= 'Volt Check', width= button_width, command= lambda: mxr.check_voltage(scale= strvar_voltage_scale.get(), offset= strvar_voltage_offset.get()))

    # label_trigger_level = tk.Label(label_frame_scale, text= 'Trigger level (V)', background= background_color_1, fg= '#0D325C', font= candara_base_font,)

    # strvar_trigger_level = tk.StringVar()
    # combobox_trigger_level = ttk.Combobox(label_frame_scale, width= max(4, int(entry_width*0.4)), textvariable= strvar_trigger_level, font= entry_font)
    # execute_commbobox_function(combobox= combobox_trigger_level, combobox_var= strvar_trigger_level, ini_dict_key= 'TriggerLevel', ini_option_section= 'Scale_Offset_Config', ini_option_key= 'TriggerLevel', ini_selected_section= 'Scale_Offset_Selected_Values')

    # label_trigger_channel = tk.Label(label_frame_scale, text= 'Trigger Channel', background= background_color_1, fg= '#0D325C', font= candara_base_font,)

    # strvar_trigger_channel = tk.StringVar()
    # combobox_trigger_channel = ttk.Combobox(label_frame_scale, width= max(4, int(entry_width*0.4)), textvariable= strvar_trigger_channel, values= [1, 2, 3, 4], font= entry_font)

    # button_trigger_check = ttk.Button(label_frame_scale, text= 'Trig Check', width= button_width, command= lambda: mxr.check_trigger_setting(chan= strvar_trigger_channel.get(), level= strvar_trigger_level.get()))

    # label_timebase_scale = tk.Label(label_frame_scale, text= 'Timebase Scale (sec)', background= background_color_1, fg= '#0D325C', font= candara_base_font,)

    # strvar_timebase_scale = tk.StringVar()
    # entry_timebase_scale = tk.Entry(label_frame_scale, width= max(4, int(entry_width*0.4)), textvariable= strvar_timebase_scale, font= entry_font)

    # label_timebase_offset = tk.Label(label_frame_scale, text= 'Timebase Offset (sec)', background= background_color_1, fg= '#0D325C', font= candara_base_font,)

    # strvar_timebase_offset = tk.StringVar()
    # entry_timebase_offset = tk.Entry(label_frame_scale, width= max(4, int(entry_width*0.4)), textvariable= strvar_timebase_offset, font= entry_font)

    # button_timebase_scale_check = ttk.Button(label_frame_scale, text= 'Time scale Check', width= button_width, command= lambda: mxr.check_timebase_scale(scale= strvar_timebase_scale.get()))
    # button_timebase_offset_check = ttk.Button(label_frame_scale, text= 'Time posi Check', width= button_width, command= lambda: mxr.check_timebase_offset(position= strvar_timebase_offset.get()))

    # label_waveform_intensity = tk.Label(label_frame_scale, text= 'Waveform Intensity (%)', background= background_color_1, fg= '#0D325C', font= candara_base_font,)

    # vcmd = (window.register(validate_number), "%P") # %P = 輸入後字串
    # strvar_waveform_intensity = tk.StringVar()
    # entry_waveform_intensity = tk.Entry(label_frame_scale, width= max(4, int(entry_width*0.4)), justify="center", textvariable= strvar_waveform_intensity, validate="key", validatecommand=vcmd, font= entry_font)
    # update_intensity_color(value= strvar_waveform_intensity.get())
    # button_waveform_intensity = ttk.Button(label_frame_scale, text= 'Intensity Check', width= button_width, command= lambda: mxr.check_intensity_setting(intensity_value= strvar_waveform_intensity.get()))
    
    # button_set_intensity_50 = ttk.Button(label_frame_scale, text="Set Intensity 50", width= button_width, command=set_to_fixty)

    # entry_waveform_intensity.bind("<MouseWheel>", on_mouse_wheel)
    # entry_waveform_intensity.bind("<Button-4>", lambda e: on_mouse_wheel(type("Event", (), {"delta": 120})))
    # entry_waveform_intensity.bind("<Button-5>", lambda e: on_mouse_wheel(type("Event", (), {"delta": -120})))

    # button_measure_all_edge = ttk.Button(label_frame_scale, text= 'Meas All Edge: OFF', width= button_width, command= lambda: mxr.measure_all_edge(), 
    #                             state= 'disabled')

    # # Delta Setup Frame ===================================================================================================================================

    # label_frame_delta= tk.LabelFrame(window, text= 'Delta Setup', background= backgroung_color_2, fg= '#506376', font= ('Candara', 10, 'bold'),)


    # entry_width= set_entry_width(base_entry_width= 11)


    # label_start = tk.Label(label_frame_delta, text= 'Delta Start', background= 'yellow', fg= '#0D325C', font= candara_base_font,)

    # strvar_start_risefall = tk.StringVar()
    # combobox_start_risefall = ttk.Combobox(label_frame_delta, width= 11, textvariable= strvar_start_risefall, values= ['RISING', 'FALLING'], font= entry_font)

    # strvar_start_N_edge = tk.StringVar()
    # combobox_start_N = tk.Entry(label_frame_delta, width= max(11, int(entry_width*0.4)), textvariable= strvar_start_N_edge, font= entry_font)
    
    # strvar_start_position = tk.StringVar()
    # combobox_start_position = ttk.Combobox(label_frame_delta, width= 11, textvariable= strvar_start_position, values= ['UPPER', 'MIDDLE', 'LOWER'], font= entry_font)
    
    # label_stop = tk.Label(label_frame_delta, text= 'Delta Stop', background= 'yellow', fg= '#0D325C', font= candara_base_font,)

    # strvar_stop_risefall = tk.StringVar()
    # combobox_stop_risefall = ttk.Combobox(label_frame_delta, width= 11, textvariable= strvar_stop_risefall, values= ['RISING', 'FALLING'], font= entry_font)
    
    # strvar_stop_N_edge = tk.StringVar()
    # combobox_stop_N = tk.Entry(label_frame_delta, width= max(11, int(entry_width*0.4)), textvariable= strvar_stop_N_edge, font= entry_font)
    
    # strvar_stop_position = tk.StringVar()
    # combobox_stop_position = ttk.Combobox(label_frame_delta, width= 11, textvariable= strvar_stop_position, values= ['UPPER', 'MIDDLE', 'LOWER'], font= entry_font)
    
    # button_edge_switch = ttk.Button(label_frame_delta, text= 'Edge Switch', width= button_width, command= lambda: switch_string(var_1= strvar_start_risefall, var_2= strvar_stop_risefall))
    # button_position_switch = ttk.Button(label_frame_delta, text= 'Position Switch', width= button_width, command= lambda: switch_string(var_1= strvar_start_position, var_2= strvar_stop_position))

    # # Threshold Frame ===================================================================================================================================

    # label_frame_threshold= tk.LabelFrame(window, text= 'Threshold', background= background_color_1, fg= '#506376', font= ('Candara', 10, 'bold'),)


    # entry_width= set_entry_width(base_entry_width= 10)


    # intvar_general_threshold = tk.IntVar()    
    # radiobutton_general_percent_top= tk.Radiobutton(label_frame_threshold, text= 'Gen Thres Top (%)', variable= intvar_general_threshold, value= 1, background= background_color_1, fg= '#0D325C', font= candara_bold_font,)

    # strvar_general_percent_top = tk.StringVar()
    # combobox_general_percent_top = ttk.Combobox(label_frame_threshold, width= 8, textvariable= strvar_general_percent_top, font= entry_font)
    # execute_commbobox_function(combobox= combobox_general_percent_top, combobox_var= strvar_general_percent_top, ini_dict_key= 'GeneralTopPercent', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'GeneralTopPercent', ini_selected_section= 'Threshold_Selected_Values')
    
    # label_general_percent_middle= tk.Label(label_frame_threshold, text= '            Gen Thres Middle (%)', background= background_color_1, fg= '#0D325C', font= candara_base_font,)

    # strvar_general_percent_middle = tk.StringVar()
    # combobox_general_percent_middle = ttk.Combobox(label_frame_threshold, width= 8, textvariable= strvar_general_percent_middle, font= entry_font)
    # execute_commbobox_function(combobox= combobox_general_percent_middle, combobox_var= strvar_general_percent_middle, ini_dict_key= 'GeneralMiddlePercent', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'GeneralMiddlePercent', ini_selected_section= 'Threshold_Selected_Values')

    # label_general_percent_base= tk.Label(label_frame_threshold, text= '        Gen Thres Base (%)', background= background_color_1, fg= '#0D325C', font= candara_base_font,)

    # strvar_general_percent_base = tk.StringVar()
    # combobox_general_percent_base = ttk.Combobox(label_frame_threshold, width= 8, textvariable= strvar_general_percent_base, font= entry_font)
    # execute_commbobox_function(combobox= combobox_general_percent_base, combobox_var= strvar_general_percent_base, ini_dict_key= 'GeneralBasePercent', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'GeneralBasePercent', ini_selected_section= 'Threshold_Selected_Values')

    # radiobutton_general_value_top= tk.Radiobutton(label_frame_threshold, text= 'Gen Thres Top (V)', variable= intvar_general_threshold, value= 2, background= background_color_1, fg= '#0D325C', font= candara_bold_font,)
    # radiobutton_general_value_top.select()

    # strvar_general_value_top = tk.StringVar()
    # combobox_general_value_top = ttk.Combobox(label_frame_threshold, width= 8, textvariable= strvar_general_value_top, font= entry_font)
    # execute_commbobox_function(combobox= combobox_general_value_top, combobox_var= strvar_general_value_top, ini_dict_key= 'GeneralTop', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'GeneralTop', ini_selected_section= 'Threshold_Selected_Values')

    # label_general_value_middle= tk.Label(label_frame_threshold, text= '            Gen Thres Middle (V)', background= background_color_1, fg= '#0D325C', font= candara_base_font,)

    # strvar_general_value_middle = tk.StringVar()
    # combobox_general_value_middle = ttk.Combobox(label_frame_threshold, width= 8, textvariable= strvar_general_value_middle, font= entry_font)
    # execute_commbobox_function(combobox= combobox_general_value_middle, combobox_var= strvar_general_value_middle, ini_dict_key= 'GeneralMiddle', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'GeneralMiddle', ini_selected_section= 'Threshold_Selected_Values')

    # label_general_value_base= tk.Label(label_frame_threshold, text= '        Gen Thres Base (V)', background= background_color_1, fg= '#0D325C', font= candara_base_font,)

    # strvar_general_value_base = tk.StringVar()
    # combobox_general_value_base = ttk.Combobox(label_frame_threshold, width= 8, textvariable= strvar_general_value_base, font= entry_font)
    # execute_commbobox_function(combobox= combobox_general_value_base, combobox_var= strvar_general_value_base, ini_dict_key= 'GeneralBase', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'GeneralBase', ini_selected_section= 'Threshold_Selected_Values')
    # button_general_threshold_check = ttk.Button(
    #     label_frame_threshold, text= 'Gen Thres Check', width= button_width, command= lambda: mxr.set_general_threshold(
    #         g_top= combobox_general_value_top.get(), g_middle= combobox_general_value_middle.get(), g_base= combobox_general_value_base.get(), g_top_percent= combobox_general_percent_top.get(), g_middle_percent= combobox_general_percent_middle.get(), g_base_percent= combobox_general_percent_base.get(), 
    #         )
    #     )

    # intvar_risefall_threshold = tk.IntVar()    
    # radiobutton_risefall_percent_top= tk.Radiobutton(label_frame_threshold, text= 'tRtF Thres Top (%)', variable= intvar_risefall_threshold, value= 1, background= background_color_1, fg= '#0D325C', font= candara_bold_font,)

    # label_risefall_percent_base= tk.Label(label_frame_threshold, text= '       tRtF Thres Base (%)', background= background_color_1, fg= '#0D325C', font= candara_base_font,)

    # strvar_risefall_percent_top = tk.StringVar()
    # combobox_risefall_percent_top = ttk.Combobox(label_frame_threshold, width= 8, textvariable= strvar_risefall_percent_top, font= entry_font)
    # execute_commbobox_function(combobox= combobox_risefall_percent_top, combobox_var= strvar_risefall_percent_top, ini_dict_key= 'RFTopPercent', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'RFTopPercent', ini_selected_section= 'Threshold_Selected_Values')

    # strvar_risefall_percent_base = tk.StringVar()
    # combobox_risefall_percent_base = ttk.Combobox(label_frame_threshold, width= 8, textvariable= strvar_risefall_percent_base, font= entry_font)
    # execute_commbobox_function(combobox= combobox_risefall_percent_base, combobox_var= strvar_risefall_percent_base, ini_dict_key= 'RFBasePercent', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'RFBasePercent', ini_selected_section= 'Threshold_Selected_Values')

    # radiobutton_risefall_value_top= tk.Radiobutton(label_frame_threshold, text= 'tRtF Thres Top (V)', variable= intvar_risefall_threshold, value= 2, background= background_color_1, fg= '#0D325C', font= candara_bold_font,)
    # radiobutton_risefall_value_top.select()

    # label_risefall_value_base= tk.Label(label_frame_threshold, text= '       tRtF Thres Base (V)', background= background_color_1, fg= '#0D325C', font= candara_base_font,)

    # strvar_risefall_value_top = tk.StringVar()
    # combobox_risefall_value_top = ttk.Combobox(label_frame_threshold, width= 8, textvariable= strvar_risefall_value_top, font= entry_font)
    # execute_commbobox_function(combobox= combobox_risefall_value_top, combobox_var= strvar_risefall_value_top, ini_dict_key= 'RFTop', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'RFTop', ini_selected_section= 'Threshold_Selected_Values')

    # strvar_risefall_value_base = tk.StringVar()
    # combobox_risefall_value_base = ttk.Combobox(label_frame_threshold, width= 8, textvariable= strvar_risefall_value_base, font= entry_font)
    # execute_commbobox_function(combobox= combobox_risefall_value_base, combobox_var= strvar_risefall_value_base, ini_dict_key= 'RFBase', ini_option_section= 'Threshold_Setup_Config', ini_option_key= 'RFBase', ini_selected_section= 'Threshold_Selected_Values')

    # button_risefall_threshold_check = ttk.Button(
    #     label_frame_threshold, text= 'RF Thres Check', width= button_width, command= lambda: mxr.set_risefall_threshold(
    #         rf_top= combobox_risefall_value_top.get(), rf_base= combobox_risefall_value_base.get(), rf_top_percent= combobox_risefall_percent_top.get(), rf_base_percent= combobox_risefall_percent_base.get(),
    #         )
    #     )

    # label_sampling_rate = tk.Label(label_frame_threshold, text= '※ Sampling Rate', background= background_color_1, fg= '#0D325C', font= candara_bold_font,)
    # strvar_sampling_rate = tk.StringVar()
    # entry_sampling_rate = tk.Entry(label_frame_threshold, width= max(10, int(entry_width*0.4)), textvariable= strvar_sampling_rate, font= entry_font)
    # button_sampling_rate_check = ttk.Button(label_frame_threshold, text= 'Check', width= button_width, command= lambda: mxr.acquire_sampling_rate(rate= strvar_sampling_rate.get()))
    # button_sampling_rate_automode = ttk.Button(label_frame_threshold, text= 'Auto', width= button_width, command= lambda: mxr.acquire_sampling_rate(rate= 'AUTO'))

    # label_memory_depth = tk.Label(label_frame_threshold, text= '※ Memory Depth', background= background_color_1, fg= '#0D325C', font= candara_base_font,)
    # strvar_memory_depth = tk.StringVar()
    # entry_memory_depth = tk.Entry(label_frame_threshold, width= max(10, int(entry_width*0.4)), textvariable= strvar_memory_depth, font= entry_font)
    # button_memory_depth_check = ttk.Button(label_frame_threshold, text= 'Check', width= button_width, command= lambda: mxr.acquire_memory_depth(points_value= strvar_memory_depth.get()))
    # button_memory_depth_automode = ttk.Button(label_frame_threshold, text= 'Auto', width= button_width, command= lambda: mxr.acquire_memory_depth(points_value= 'AUTO'))


    # # Label Frame ===================================================================================================================================

    # label_frame_label= tk.LabelFrame(window, text= 'Label', background= backgroung_color_2, fg= '#506376', font= ('Candara', 10, 'bold'),)


    # entry_width= set_entry_width(base_entry_width= 25)


    # intvar_label_type = tk.IntVar()    
    # radiobutton_label= tk.Radiobutton(label_frame_label, text= 'Label', variable= intvar_label_type, value= 1, background= backgroung_color_2, fg= '#0D325C', font= candara_bold_font,)

    # radiobutton_bookmark= tk.Radiobutton(label_frame_label, text= 'Bookmark', variable= intvar_label_type, value= 2, background= backgroung_color_2, fg= '#0D325C', font= candara_bold_font,)
    # radiobutton_label.select()

    # strvar_label_1 = tk.StringVar()
    # entey_label_1 = tk.Entry(label_frame_label, width= max(25, int(entry_width*0.4)), textvariable= strvar_label_1, font= entry_font)

    # button_lable1 = ttk.Button(label_frame_label, text= 'Chan1_label', width= button_width, command= lambda: mxr.add_bookmark(choose_type= intvar_label_type.get(), chan= 1, bookmark= strvar_label_1.get().rstrip('\n')))
    # button_delete_label_1 = ttk.Button(label_frame_label, text= 'Delete', width= button_width, command= lambda: mxr.delete_bookmark(chan= 1, choose_type= intvar_label_type.get()))

    # strvar_label_2 = tk.StringVar()
    # entry_label_2 = tk.Entry(label_frame_label, width= max(25, int(entry_width*0.4)), textvariable= strvar_label_2, font= entry_font)

    # button_lable_2 = ttk.Button(label_frame_label, text= 'Chan2_label', width= button_width, command= lambda: mxr.add_bookmark(choose_type= intvar_label_type.get(), chan= 2, bookmark= (strvar_label_2.get().rstrip('\n'))))
    # button_delete_label_2 = ttk.Button(label_frame_label, text= 'Delete', width= button_width, command= lambda: mxr.delete_bookmark(chan= 2, choose_type= intvar_label_type.get()))

    # strvar_label_3 = tk.StringVar()
    # entry_label_3 = tk.Entry(label_frame_label, width= max(25, int(entry_width*0.4)), textvariable= strvar_label_3, font= entry_font)

    # button_lable_3 = ttk.Button(label_frame_label, text= 'Chan3_label', width= button_width, command= lambda: mxr.add_bookmark(choose_type= intvar_label_type.get(), chan= 3, bookmark= (strvar_label_3.get().rstrip('\n'))))
    # button_delete_label_3 = ttk.Button(label_frame_label, text= 'Delete', width= button_width, command= lambda: mxr.delete_bookmark(chan= 3, choose_type= intvar_label_type.get()))

    # strvar_label_4 = tk.StringVar()
    # entry_label_4 = tk.Entry(label_frame_label, width= max(25, int(entry_width*0.4)), textvariable= strvar_label_4, font= entry_font)

    # button_lable_4 = ttk.Button(label_frame_label, text= 'Chan4_label', width= button_width, command= lambda: mxr.add_bookmark(choose_type= intvar_label_type.get(), chan= 4, bookmark= (strvar_label_4.get().rstrip('\n'))))
    # button_delete_label_4 = ttk.Button(label_frame_label, text= 'Delete', width= button_width, command= lambda: mxr.delete_bookmark(chan= 4, choose_type= intvar_label_type.get()))

    # strvar_label_5 = tk.StringVar()
    # entry_label_5 = tk.Entry(label_frame_label, width= max(25, int(entry_width*0.4)), textvariable= strvar_label_5, font= entry_font)

    # button_lable_5 = ttk.Button(label_frame_label, text= 'WMe1_label', width= button_width, command= lambda: mxr.add_bookmark(choose_type= intvar_label_type.get(), chan= 5, bookmark= strvar_label_5.get().rstrip('\n')))
    # button_delete_label_5 = ttk.Button(label_frame_label, text= 'Delete', width= button_width, command= lambda: mxr.delete_bookmark(chan= 5, choose_type= intvar_label_type.get()))

    # strvar_label_6 = tk.StringVar()
    # entry_label_6 = tk.Entry(label_frame_label, width= max(25, int(entry_width*0.4)), textvariable= strvar_label_6, font= entry_font)

    # button_lable_6 = ttk.Button(label_frame_label, text= 'WMe2_label', width= button_width, command= lambda: mxr.add_bookmark(choose_type= intvar_label_type.get(), chan= 6, bookmark= (strvar_label_6.get().rstrip('\n'))))
    # button_delete_label_6 = ttk.Button(label_frame_label, text= 'Delete', width= button_width, command= lambda: mxr.delete_bookmark(chan= 6, choose_type= intvar_label_type.get()))

    # strvar_label_7 = tk.StringVar()
    # entry_label_7 = tk.Entry(label_frame_label, width= max(25, int(entry_width*0.4)), textvariable= strvar_label_7, font= entry_font)

    # button_lable_7 = ttk.Button(label_frame_label, text= 'WMe3_label', width= button_width, command= lambda: mxr.add_bookmark(choose_type= intvar_label_type.get(), chan= 7, bookmark= (strvar_label_7.get().rstrip('\n'))))
    # button_delete_label_7 = ttk.Button(label_frame_label, text= 'Delete', width= button_width, command= lambda: mxr.delete_bookmark(chan= 7, choose_type= intvar_label_type.get()))

    # strvar_label_8 = tk.StringVar()
    # entry_label_8 = tk.Entry(label_frame_label, width= max(25, int(entry_width*0.4)), textvariable= strvar_label_8, font= entry_font)

    # button_lable_8 = ttk.Button(label_frame_label, text= 'WMe4_label', width= button_width, command= lambda: mxr.add_bookmark(choose_type= intvar_label_type.get(), chan= 8, bookmark= (strvar_label_8.get().rstrip('\n'))))
    # button_delete_label_8 = ttk.Button(label_frame_label, text= 'Delete', width= button_width, command= lambda: mxr.delete_bookmark(chan= 8, choose_type= intvar_label_type.get()))

    # # Control Frame ===================================================================================================================================

    # label_frame_control= tk.LabelFrame(window, text= 'Control', background= backgroung_color_2, fg= '#506376', font= ('Candara', 10, 'bold'),)







    # button_run = ttk.Button(label_frame_control, text='RUN', width= button_width, command= lambda: mxr.run())
    # button_stop = ttk.Button(label_frame_control, text='STOP', width= button_width, command= lambda: mxr.stop())
    # button_single = ttk.Button(label_frame_control, text='SINGLE', width= button_width, command= lambda: mxr.single())

    # button_clear_display = ttk.Button(label_frame_control, text='Clear', width= button_width, command= lambda: mxr.clear_diaplay())
    # button_clear_display.config(state= 'disabled')

    # button_autoscale = ttk.Button(label_frame_control, text='Auto Scale', width= button_width, command= lambda: mxr.autoscale())
    # button_autoscale.config(state= 'disabled')

    # button_default = ttk.Button(label_frame_control, text='Default', width= button_width, command= lambda: mxr.default())
    # button_default.config(state= 'disabled')

    # button_trigger = ttk.Button(label_frame_control, text='Trigger Type', width= button_width, command= lambda: mxr.set_trigger_type())

    # button_delete_measurement = ttk.Button(label_frame_control, text='Delete item', width= button_width, command= lambda: mxr.delete_measurement())

    # button_add_marker = ttk.Button(label_frame_control, text='Add Marker', width= button_width, command= lambda: mxr.add_marker())

    # button_delete_marker = ttk.Button(label_frame_control, text='Del Marker', width= button_width, command= lambda: mxr.delete_marker())

    # button_trigger_slope = ttk.Button(label_frame_control, text= 'Trig Slope', width= button_width, command= lambda: mxr.set_trigger_slope())

    # def disable_button():
    #     if button_autoscale["state"] == 'normal':
    #         button_autoscale.config(state="disabled")
    #     else:
    #         button_autoscale.config(state="normal")
    #     if button_default["state"] == 'normal':
    #         button_default.config(state="disabled")
    #     else:
    #         button_default.config(state="normal")
    #     if button_clear_display["state"] == 'normal':
    #         button_clear_display.config(state="disabled")
    #     else:
    #         button_clear_display.config(state="normal")

    # button_disable_button = ttk.Button(label_frame_control, text= 'Disable\nButton', width= button_width, command= disable_button)

    # boolvar_marker_1 = tk.BooleanVar()    
    # checkbutton_marker_1= tk.Checkbutton(label_frame_control, text= 'Meas 1', variable= boolvar_marker_1, background= backgroung_color_2, fg= '#0D325C', font= calibri_base_font)

    # boolvar_marker_2 = tk.BooleanVar()    
    # checkbutton_marker_2= tk.Checkbutton(label_frame_control, text= 'Meas 2', variable= boolvar_marker_2, background= backgroung_color_2, fg= '#0D325C', font= calibri_base_font)

    # boolvar_marker_3 = tk.BooleanVar()    
    # checkbutton_marker_3= tk.Checkbutton(label_frame_control, text= 'Meas 3', variable= boolvar_marker_3, background= backgroung_color_2, fg= '#0D325C', font= calibri_base_font)

    # boolvar_marker_4 = tk.BooleanVar()    
    # checkbutton_marker_4= tk.Checkbutton(label_frame_control, text= 'Meas 4', variable= boolvar_marker_4, background= backgroung_color_2, fg= '#0D325C', font= calibri_base_font)

    # boolvar_marker_5 = tk.BooleanVar()    
    # checkbutton_marker_5= tk.Checkbutton(label_frame_control, text= 'Meas 5', variable= boolvar_marker_5, background= backgroung_color_2, fg= '#0D325C', font= calibri_base_font)

    # boolvar_marker_6 = tk.BooleanVar()    
    # checkbutton_marker_6= tk.Checkbutton(label_frame_control, text= 'Meas 6', variable= boolvar_marker_6, background= backgroung_color_2, fg= '#0D325C', font= calibri_base_font)

    # boolvar_marker_7 = tk.BooleanVar()    
    # checkbutton_marker_7= tk.Checkbutton(label_frame_control, text= 'Meas7', variable= boolvar_marker_7, background= backgroung_color_2, fg= '#0D325C', font= calibri_base_font)

    # boolvar_marker_8 = tk.BooleanVar()    
    # checkbutton_marker_8= tk.Checkbutton(label_frame_control, text= 'Meas8', variable= boolvar_marker_8, background= backgroung_color_2, fg= '#0D325C', font= calibri_base_font)

    # boolvar_marker_9 = tk.BooleanVar()    
    # checkbutton_marker_9= tk.Checkbutton(label_frame_control, text= 'Meas9', variable= boolvar_marker_9, background= backgroung_color_2, fg= '#0D325C', font= calibri_base_font)

    # boolvar_marker_10 = tk.BooleanVar()    
    # checkbutton_marker_10= tk.Checkbutton(label_frame_control, text= 'Meas10', variable= boolvar_marker_10, background= backgroung_color_2, fg= '#0D325C', font= calibri_base_font)

    # boolvar_marker_11 = tk.BooleanVar()    
    # checkbutton_marker_11= tk.Checkbutton(label_frame_control, text= 'Meas11', variable= boolvar_marker_11, background= backgroung_color_2, fg= '#0D325C', font= calibri_base_font)

    # boolvar_marker_12 = tk.BooleanVar()    
    # checkbutton_marker_12= tk.Checkbutton(label_frame_control, text= 'Meas12', variable= boolvar_marker_12, background= backgroung_color_2, fg= '#0D325C', font= calibri_base_font)

    # boolvar_marker_color = tk.BooleanVar()    
    # checkbutton_marker_color= tk.Checkbutton(label_frame_control, text= 'Multi-Marker Color', variable= boolvar_marker_color, background= backgroung_color_2, fg= '#0D325C', font= calibri_bold_font)

    # # Channel Frame ===================================================================================================================================

    # label_frame_channel= tk.LabelFrame(window, text= 'Channel', background= background_color_1, fg= '#506376', font= ('Candara', 10, 'bold'),)




    # button_channel_1 = ttk.Button(label_frame_channel, text='Chan1', width= button_width, command= lambda: mxr.display_channel(chan= 1, bookmark= strvar_label_1.get(), choose_type= intvar_label_type.get()))
    # button_channel_2 = ttk.Button(label_frame_channel, text='Chan2', width= button_width, command= lambda: mxr.display_channel(chan= 2, bookmark= strvar_label_2.get(), choose_type= intvar_label_type.get()))
    # button_channel_3 = ttk.Button(label_frame_channel, text='Chan3', width= button_width, command= lambda: mxr.display_channel(chan= 3, bookmark= strvar_label_3.get(), choose_type= intvar_label_type.get()))
    # button_channel_4 = ttk.Button(label_frame_channel, text='Chan4', width= button_width, command= lambda: mxr.display_channel(chan= 4, bookmark= strvar_label_4.get(), choose_type= intvar_label_type.get()))
    # button_wmemory_1 = ttk.Button(label_frame_channel, text='WMemory1', width= button_width, command= lambda: mxr.display_wmemory(chan= 1, bookmark= strvar_label_5.get(), choose_type= intvar_label_type.get()))
    # button_wmemory_2 = ttk.Button(label_frame_channel, text='WMemory2', width= button_width, command= lambda: mxr.display_wmemory(chan= 2, bookmark= strvar_label_6.get(), choose_type= intvar_label_type.get()))
    # button_wmemory_3 = ttk.Button(label_frame_channel, text='WMemory3', width= button_width, command= lambda: mxr.display_wmemory(chan= 3, bookmark= strvar_label_7.get(), choose_type= intvar_label_type.get()))
    # button_wmemory_4 = ttk.Button(label_frame_channel, text='WMemory4', width= button_width, command= lambda: mxr.display_wmemory(chan= 4, bookmark= strvar_label_8.get(), choose_type= intvar_label_type.get()))

    # intvar_channel = tk.IntVar()    
    # radiobutton_channel_single = tk.Radiobutton(label_frame_channel, text= 'Channel', variable= intvar_channel, value= 1, background= background_color_1, fg= '#0D325C', font= candara_bold_font,)
    # radiobutton_channel_delta = tk.Radiobutton(label_frame_channel, text= 'Channel', variable= intvar_channel, value= 2, background= background_color_1, fg= '#0D325C', font= candara_bold_font,)
    # radiobutton_channel_single.select()
    
    # intvar_channel_single = tk.IntVar()
    # combobox_channel_single = ttk.Combobox(label_frame_channel, width= 5, textvariable= intvar_channel_single, values= [1, 2, 3, 4], font= entry_font)

    # intvar_channel_delta_start = tk.IntVar()
    # combobox_channel_delta_start = ttk.Combobox(label_frame_channel, width= 5, textvariable= intvar_channel_delta_start, values= [1, 2, 3, 4], font= entry_font)

    # label_arrow = tk.Label(label_frame_channel, text= '      ↓', background= background_color_1, fg= '#0D325C', font= calibri_bold_font,)
    # label_channel_delta_stop = tk.Label(label_frame_channel, text= 'Channel', background= background_color_1, fg= '#0D325C', font= candara_bold_font,)
    # intvar_channel_delta_stop = tk.IntVar()
    # combobox_channel_delta_stop = ttk.Combobox(label_frame_channel, width= 5, textvariable= intvar_channel_delta_stop, values= [1, 2, 3, 4], font= entry_font)

    # boolvar_delta_name= tk.BooleanVar()
    # checkbutton_delta_name = tk.Checkbutton(label_frame_channel, text= 'Modify Delta Name', variable= boolvar_delta_name, background= background_color_1, fg= '#0D325C', font= candara_bold_font,)
    # strvar_delta_name = tk.StringVar()
    # combobox_delta_name = ttk.Combobox(label_frame_channel, width= 12, textvariable= strvar_delta_name, values= ['Setup Time', 'Hold Time'], font= entry_font)
    # combobox_delta_name.set(value= 'Setup Time')



    # button_channel_switch = ttk.Button(label_frame_channel, text= 'Delta Channel Switch', width= button_width, command= lambda: switch_string(var_1= intvar_channel_delta_start, var_2= intvar_channel_delta_stop))

    # # Save Frame ===================================================================================================================================

    # label_frame_save_file= tk.LabelFrame(window, text= 'Save', background= backgroung_color_2, fg= '#506376', font= ('Candara', 10, 'bold'),)


    # entry_width= set_entry_width(base_entry_width= 40)


    # # str_image_folder = tk.StringVar()
    # # e_image_folder = tk.Entry(label_frame_save, width= 40, textvariable= str_image_folder)

    # # l_image_folder = tk.Label(label_frame_save, text= 'Image Scope folder', background= bg_color_2, fg= '#0D325C', font= ('Candara', 10,),)

    # # int_img_path_choice = tk.IntVar()
    # # rb_img_desktop_path = tk.Radiobutton(label_frame_save, text= 'Desktop', variable= int_img_path_choice, value= 1, background= bg_color_2, fg= '#0D325C', font= ('Candara', 10,),)
    # # rb_img_server_path = tk.Radiobutton(label_frame_save, text= 'Server', variable= int_img_path_choice, value= 2, background= bg_color_2, fg= '#0D325C', font= ('Candara', 10,),)
    # # # rb_img_desktop_path.select()

    # strvar_image_pc_folder = tk.StringVar()
    # entry_image_pc_folder = tk.Entry(label_frame_save_file, width= max(40, int(entry_width*0.4)), textvariable= strvar_image_pc_folder, font= entry_font)

    # label_image_pc_folder = tk.Label(label_frame_save_file, text= 'Image PC folder [筆電的資料夾路徑]', background= backgroung_color_2, fg= '#0D325C', font= candara_base_font,)

    # button_image_pc_browse = ttk.Button(label_frame_save_file, text= 'Browse', width= button_width, command= lambda: select_folder(entry_var= strvar_image_pc_folder, target_entry= entry_image_pc_folder))
    
    # strvar_image = tk.StringVar()
    # entry_image = tk.Entry(label_frame_save_file, width= max(40, int(entry_width*0.4)), textvariable= strvar_image, font= entry_font)

    # label_image_name = tk.Label(label_frame_save_file, text= '(填 圖檔名)', background= backgroung_color_2, fg= '#0D325C', font= candara_base_font,)

    # # b_image_save_scope = tk.Button(label_frame_save, text= 'Save Image-Scope', command= lambda: mxr.save_image_scope(folder= str_image_folder.get(), image_name= str_image.get(), path_choice= int_img_path_choice.get()))
    # # b_image_save_pc = tk.Button(label_frame_save, text= 'Save Image-PC', command= lambda: mxr.save_waveform_pc(folder= str_image_folder.get(), file_name= str_image.get(), pc_folder= str_image_pc_folder.get()))
    # button_save_image_pc = ttk.Button(label_frame_save_file, text= 'Save Image-PC', width= button_width, command= lambda: mxr.save_pc_image(file_name= strvar_image.get(), pc_folder= strvar_image_pc_folder.get()))
    
    # label_divider = tk.Label(label_frame_save_file, text= '=====================================================================================================================================================', 
    #                      height= 1, background= backgroung_color_2, fg= '#0D325C', font= candara_base_font,)

    # intvar_file_type = tk.IntVar()
    # radiobutton_wmemory = tk.Radiobutton(label_frame_save_file, text= 'WMemory', variable= intvar_file_type, value= 1, background= backgroung_color_2, fg= '#0D325C', font= candara_bold_font,)
    # radiobutton_setup = tk.Radiobutton(label_frame_save_file, text= 'Setup', variable= intvar_file_type, value= 2, background= backgroung_color_2, fg= '#0D325C', font= candara_bold_font,)
    # radiobutton_wmemory.select()

    # strvar_wmemory_folder = tk.StringVar()
    # entry_wmemory_folder = tk.Entry(label_frame_save_file, width= max(40, int(entry_width*0.4)), textvariable= strvar_wmemory_folder, font= entry_font)

    # label_wmemory_folder = tk.Label(label_frame_save_file, text= 'Scope folder', background= backgroung_color_2, fg= '#0D325C', font= candara_base_font,)

    # intvar_wmemory_path_choice = tk.IntVar()
    # radiobutton_wmemory_desktop_path = tk.Radiobutton(label_frame_save_file, text= 'Desktop', variable= intvar_wmemory_path_choice, value= 1, background= backgroung_color_2, fg= '#0D325C', font= candara_base_font,)
    # radiobutton_wmemory_server_path = tk.Radiobutton(label_frame_save_file, text= 'Server', variable= intvar_wmemory_path_choice, value= 2, background= backgroung_color_2, fg= '#0D325C', font= candara_base_font,)
    # # rb_wme_desktop_path.select()

    # strvar_wmemory_pc_folder = tk.StringVar()
    # entry_wmemory_pc_folder = tk.Entry(label_frame_save_file, width= max(40, int(entry_width*0.4)), textvariable= strvar_wmemory_pc_folder, font= entry_font)

    # label_wmemory_pc_folder = tk.Label(label_frame_save_file, text= 'PC folder [筆電的資料夾路徑]', background= backgroung_color_2, fg= '#0D325C', font= candara_base_font,)

    # button_wmemory_pc_browse = ttk.Button(label_frame_save_file, text= 'Browse', width= button_width, command= lambda: select_folder(entry_var= strvar_wmemory_pc_folder, target_entry= entry_wmemory_pc_folder))

    # strvar_other_file = tk.StringVar()
    # entry_other_file = tk.Entry(label_frame_save_file, width= max(40, int(entry_width*0.4)), textvariable= strvar_other_file, font= entry_font)

    # label_other_filename = tk.Label(label_frame_save_file, text= '(填 檔名)', background= backgroung_color_2, fg= '#0D325C', font= candara_base_font,)

    # button_other_file_save_scope = ttk.Button(label_frame_save_file, text= 'Save file in Scope', width= button_width, command= lambda: mxr.save_scope_file(chan= intvar_channel_single.get(), folder= strvar_wmemory_folder.get(), current_file_name= strvar_other_file.get(), ext_type= intvar_file_type.get(), path_choice= intvar_wmemory_path_choice.get()))
    # button_other_file_save_pc = ttk.Button(label_frame_save_file, text= 'Save file in PC', width= button_width, command= lambda: mxr.save_pc_wmemory(folder= strvar_wmemory_folder.get(), file_name= strvar_other_file.get(), pc_folder= strvar_wmemory_pc_folder.get(), ext_type= intvar_file_type.get()))


    # # Load WMemory Frame ===================================================================================================================================

    # label_frame_load_file= tk.LabelFrame(window, text= 'Load WMemory', background= background_color_1, fg= '#506376', font= ('Candara', 10, 'bold'),)


    # entry_width= set_entry_width(base_entry_width= 50)

    # strvar_wmemory_1 = tk.StringVar()
    # entry_wmemory_1 = tk.Entry(label_frame_load_file, width= max(50, int(entry_width*0.4)), textvariable= strvar_wmemory_1, font= entry_font)

    # button_load_wmemory_1 = ttk.Button(label_frame_load_file, text= 'load WMemory1', width= button_width, command= lambda: mxr.load_wmemory(chan= 1, folder= strvar_wmemory_folder.get(), wme_name= strvar_wmemory_1.get(), file_path_choice = intvar_wmemory_path_choice.get()))
    # button_clear_wmemory_1 = ttk.Button(label_frame_load_file, text= 'Clear', width= button_width, command= lambda: mxr.clear_wmemory(chan= 1, string= strvar_wmemory_1))

    # strvar_wmemory_2 = tk.StringVar()
    # entry_wmemory_2 = tk.Entry(label_frame_load_file, width= max(50, int(entry_width*0.4)), textvariable= strvar_wmemory_2, font= entry_font)
    
    # button_load_wmemory_2 = ttk.Button(label_frame_load_file, text= 'load WMemory2', width= button_width, command= lambda: mxr.load_wmemory(chan= 2, folder= strvar_wmemory_folder.get(), wme_name= strvar_wmemory_2.get(), file_path_choice = intvar_wmemory_path_choice.get()))
    # button_clear_wmemory_2 = ttk.Button(label_frame_load_file, text= 'Clear', width= button_width, command= lambda: mxr.clear_wmemory(chan= 2, string= strvar_wmemory_2))

    # strvar_wmemory_3 = tk.StringVar()
    # entry_wmemory_3 = tk.Entry(label_frame_load_file, width= max(50, int(entry_width*0.4)), textvariable= strvar_wmemory_3, font= entry_font)

    # button_load_wmemory_3 = ttk.Button(label_frame_load_file, text= 'load WMemory3', width= button_width, command= lambda: mxr.load_wmemory(chan= 3, folder= strvar_wmemory_folder.get(), wme_name= strvar_wmemory_3.get(), file_path_choice = intvar_wmemory_path_choice.get()))
    # button_clear_wmemory_3 = ttk.Button(label_frame_load_file, text= 'Clear', width= button_width, command= lambda: mxr.clear_wmemory(chan= 3, string= strvar_wmemory_3))

    # strvar_wmemory_4 = tk.StringVar()
    # entry_wmemory_4 = tk.Entry(label_frame_load_file, width= max(50, int(entry_width*0.4)), textvariable= strvar_wmemory_4, font= entry_font)
    
    # button_load_wmemory_4 = ttk.Button(label_frame_load_file, text= 'load WMemory4', width= button_width, command= lambda: mxr.load_wmemory(chan= 4, folder= strvar_wmemory_folder.get(), wme_name= strvar_wmemory_4.get(), file_path_choice = intvar_wmemory_path_choice.get()))
    # button_clear_wmemory_4 = ttk.Button(label_frame_load_file, text= 'Clear', width= button_width, command= lambda: mxr.clear_wmemory(chan= 4, string= strvar_wmemory_4))

    # strvar_setupfile_interface = tk.StringVar()
    # combobox_setupfile_interface = ttk.Combobox(label_frame_load_file, width= 5, textvariable= strvar_setupfile_interface, font= entry_font)

    # strvar_setupfile_class = tk.StringVar()
    # combobox_setupfile_class = ttk.Combobox(label_frame_load_file, width= 18, textvariable= strvar_setupfile_class, font= entry_font)

    # strvar_setup = tk.StringVar()
    # combobox_setup = ttk.Combobox(label_frame_load_file, width= 15, textvariable= strvar_setup, font= entry_font)
    
    # boolvar_setup_timebase = tk.BooleanVar()    
    # checkbutton_setup_timebase= tk.Checkbutton(label_frame_load_file, text= 'Time', variable= boolvar_setup_timebase, background= background_color_1, fg= '#0D325C')
    # checkbutton_setup_timebase.select()

    # boolvar_setup_label = tk.BooleanVar()    
    # checkbutton_setup_label= tk.Checkbutton(label_frame_load_file, text= 'Label', variable= boolvar_setup_label, background= background_color_1, fg= '#0D325C')
    # checkbutton_setup_label.select()

    # boolvar_setup_volt = tk.BooleanVar()    
    # checkbutton_setup_voltage= tk.Checkbutton(label_frame_load_file, text= 'Volt', variable= boolvar_setup_volt, background= background_color_1, fg= '#0D325C')
    # checkbutton_setup_voltage.select()


    # # Extract Results Frame ===================================================================================================================================

    # label_frame_extract_result= tk.LabelFrame(window, text= 'Extract Results', background= background_color_1, fg= '#506376', font= ('Candara', 10, 'bold'),)




    # intvar_result_type = tk.IntVar()   
    # radiobutton_mean_result = tk.Radiobutton(label_frame_extract_result, text= 'Mean', variable= intvar_result_type, value= 1, background= background_color_1, fg= '#0D325C', font= candara_base_font, command= lambda: change_label_text_mean_result())
    # radiobutton_minmax_result = tk.Radiobutton(label_frame_extract_result, text= 'Min & Max', variable= intvar_result_type, value= 2, background= background_color_1, fg= '#0D325C', font= candara_base_font, command= lambda: change_label_text_minmax_result())
    # intvar_result_type.set(value= 1)

    # button_get_result = ttk.Button(label_frame_extract_result, text= 'Get Results (最多取12個)', width= button_width, command= lambda: mxr.extract_result())
    
    # label_result_tag_1 = tk.Label(label_frame_extract_result, text= 'Mean', background= background_color_1, fg= '#516464', font= candara_bold_font,)
    # label_result_tag_2 = tk.Label(label_frame_extract_result, text= '', background= background_color_1, fg= '#516464', font= candara_bold_font,)

    # # l_result_dividing_line = tk.Label(label_frame_extract_result, text= '-------------------------------------------------', background= bg_color_1, fg= '#516464', font= ('Candara', 15, 'bold'),)

    # label_measurement_name_1 = tk.Label(label_frame_extract_result, text= '', background= background_color_1, fg= '#516464', font= candara_bold_font,)
    # text_result_mean_1 = tk.Text(label_frame_extract_result, width= max(8, int(entry_width*0.4)), height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_mean_1.config(state=tk.DISABLED)
    # text_result_minmax_1 = tk.Text(label_frame_extract_result, width= 0, height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_minmax_1.config(state=tk.DISABLED)
    
    # label_measurement_name_2 = tk.Label(label_frame_extract_result, text= '', background= background_color_1, fg= '#516464', font= candara_bold_font,)
    # text_result_mean_2 = tk.Text(label_frame_extract_result, width= max(8, int(entry_width*0.4)), height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_mean_2.config(state=tk.DISABLED)
    # text_result_minmax_2 = tk.Text(label_frame_extract_result, width= 0, height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_minmax_2.config(state=tk.DISABLED)
    
    # label_measurement_name_3 = tk.Label(label_frame_extract_result, text= '', background= background_color_1, fg= '#516464', font= candara_bold_font,)
    # text_result_mean_3 = tk.Text(label_frame_extract_result, width= max(8, int(entry_width*0.4)), height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_mean_3.config(state=tk.DISABLED)
    # text_result_minmax_3 = tk.Text(label_frame_extract_result, width= 0, height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_minmax_3.config(state=tk.DISABLED)
    
    # label_measurement_name_4 = tk.Label(label_frame_extract_result, text= '', background= background_color_1, fg= '#516464', font= candara_bold_font,)
    # text_result_mean_4 = tk.Text(label_frame_extract_result, width= max(8, int(entry_width*0.4)), height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_mean_4.config(state=tk.DISABLED)
    # text_result_minmax_4 = tk.Text(label_frame_extract_result, width= 0, height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_minmax_4.config(state=tk.DISABLED)
    
    # label_measurement_name_5 = tk.Label(label_frame_extract_result, text= '', background= background_color_1, fg= '#516464', font= candara_bold_font,)
    # text_result_mean_5 = tk.Text(label_frame_extract_result, width= max(8, int(entry_width*0.4)), height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_mean_5.config(state=tk.DISABLED)
    # text_result_minmax_5 = tk.Text(label_frame_extract_result, width= 0, height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_minmax_5.config(state=tk.DISABLED)
    
    # label_measurement_name_6 = tk.Label(label_frame_extract_result, text= '', background= background_color_1, fg= '#516464', font= candara_bold_font,)
    # text_result_mean_6 = tk.Text(label_frame_extract_result, width= max(8, int(entry_width*0.4)), height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_mean_6.config(state=tk.DISABLED)
    # text_result_minmax_6 = tk.Text(label_frame_extract_result, width= 0, height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_minmax_6.config(state=tk.DISABLED)
    
    # label_measurement_name_7 = tk.Label(label_frame_extract_result, text= '', background= background_color_1, fg= '#516464', font= candara_bold_font,)
    # text_result_mean_7 = tk.Text(label_frame_extract_result, width= max(8, int(entry_width*0.4)), height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_mean_7.config(state=tk.DISABLED)
    # text_result_minmax_7 = tk.Text(label_frame_extract_result, width= 0, height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_minmax_7.config(state=tk.DISABLED)
    
    # label_measurement_name_8 = tk.Label(label_frame_extract_result, text= '', background= background_color_1, fg= '#516464', font= candara_bold_font,)
    # text_result_mean_8 = tk.Text(label_frame_extract_result, width= max(8, int(entry_width*0.4)), height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_mean_8.config(state=tk.DISABLED)
    # text_result_minmax_8 = tk.Text(label_frame_extract_result, width= 0, height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_minmax_8.config(state=tk.DISABLED)
    
    # label_measurement_name_9 = tk.Label(label_frame_extract_result, text= '', background= background_color_1, fg= '#516464', font= candara_bold_font,)
    # text_result_mean_9 = tk.Text(label_frame_extract_result, width= max(8, int(entry_width*0.4)), height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_mean_9.config(state=tk.DISABLED)
    # text_result_minmax_9 = tk.Text(label_frame_extract_result, width= 0, height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_minmax_9.config(state=tk.DISABLED)
    
    # label_measurement_name_10 = tk.Label(label_frame_extract_result, text= '', background= background_color_1, fg= '#516464', font= candara_bold_font,)
    # text_result_mean_10 = tk.Text(label_frame_extract_result, width= max(8, int(entry_width*0.4)), height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_mean_10.config(state=tk.DISABLED)
    # text_result_minmax_10 = tk.Text(label_frame_extract_result, width= 0, height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_minmax_10.config(state=tk.DISABLED)
    
    # label_measurement_name_11 = tk.Label(label_frame_extract_result, text= '', background= background_color_1, fg= '#516464', font= candara_bold_font,)
    # text_result_mean_11 = tk.Text(label_frame_extract_result, width= max(8, int(entry_width*0.4)), height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_mean_11.config(state=tk.DISABLED)
    # text_result_minmax_11 = tk.Text(label_frame_extract_result, width= 0, height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_minmax_11.config(state=tk.DISABLED)
    
    # label_measurement_name_12 = tk.Label(label_frame_extract_result, text= '', background= background_color_1, fg= '#516464', font= candara_bold_font,)
    # text_result_mean_12 = tk.Text(label_frame_extract_result, width= max(8, int(entry_width*0.4)), height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_mean_12.config(state=tk.DISABLED)
    # text_result_minmax_12 = tk.Text(label_frame_extract_result, width= 0, height= 1, background= '#DBE4F0', fg= '#375050', font= calibri_bold_font,)
    # text_result_minmax_12.config(state=tk.DISABLED)
    
    # # Weight===================================================================================================================================
    # # 拉大或縮小視窗時，設定 weight=1 代表允許該行隨著視窗放大而跟著變大
    # for window_r in range(4):
    #     window.rowconfigure(window_r, weight=1, uniform="row")
    # window.columnconfigure(0 , weight= 2, uniform="col")
    # window.columnconfigure(1 , weight= 1, uniform="col")
    # window.columnconfigure(2 , weight= 3, uniform="col")
    # # window.columnconfigure(3 , weight= 1, uniform="col")
    
    
    # for label_frame_measurement_item_r in range(4):
    #     label_frame_measurement_item.rowconfigure(label_frame_measurement_item_r, weight=1, uniform="row")
    # for label_frame_measurement_item_c in range(4):
    #     label_frame_measurement_item.columnconfigure(label_frame_measurement_item_c, weight=1, uniform="col")

    # for label_frame_scale_r in range(6):
    #     label_frame_scale.rowconfigure(label_frame_scale_r, weight=1, uniform="row")
    # for label_frame_scale_c in range(4):
    #     label_frame_scale.columnconfigure(label_frame_scale_c, weight=1, uniform="col")

    # for label_frame_delta_r in range(5):
    #     label_frame_delta.rowconfigure(label_frame_delta_r, weight=1, uniform="row")
    # for label_frame_delta_c in range(2):
    #     label_frame_delta.columnconfigure(label_frame_delta_c, weight=1, uniform="col")

    # for label_frame_threshold_r in range(6):
    #     label_frame_threshold.rowconfigure(label_frame_threshold_r, weight=1, uniform="row")
    # for label_frame_threshold_c in range(7):
    #     label_frame_threshold.columnconfigure(label_frame_threshold_c, weight=1, uniform="col")

    # for label_frame_label_r in range(5):
    #     label_frame_label.rowconfigure(label_frame_label_r, weight=1, uniform="row")
    # for label_frame_label_c in range(8):
    #     label_frame_label.columnconfigure(label_frame_label_c, weight=1, uniform="col")

    # for label_frame_control_r in range(8):
    #     label_frame_control.rowconfigure(label_frame_control_r, weight=1, uniform="row")
    # for label_frame_control_c in range(3):
    #     label_frame_control.columnconfigure(label_frame_control_c, weight=1, uniform="col")

    # for label_frame_channel_r in range(8):
    #     label_frame_channel.rowconfigure(label_frame_channel_r, weight=1, uniform="row")
    # for label_frame_channel_c in range(8):
    #     label_frame_channel.columnconfigure(label_frame_channel_c, weight=1, uniform="col")

    # for label_frame_save_file_r in range(8):
    #     label_frame_save_file.rowconfigure(label_frame_save_file_r, weight=1, uniform="row")
    # for label_frame_save_file_c in range(4):
    #     label_frame_save_file.columnconfigure(label_frame_save_file_c, weight=1, uniform="col")

    # for label_frame_load_file_r in range(5):
    #     label_frame_load_file.rowconfigure(label_frame_load_file_r, weight=1, uniform="row")
    # for label_frame_load_file_c in range(7):
    #     label_frame_load_file.columnconfigure(label_frame_load_file_c, weight=1, uniform="col")

    # for label_frame_extract_result_r in range(28):
    #     label_frame_extract_result.rowconfigure(label_frame_extract_result_r, weight=1, uniform="row")
    # for label_frame_extract_result_c in range(2):
    #     label_frame_extract_result.columnconfigure(label_frame_extract_result_c, weight=1, uniform="col")


    # # Grid ===================================================================================================================================
    # # LabelFrame grid
    # label_frame_measurement_item.grid(row= 0, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'nesw')
    # label_frame_scale.grid(row= 1, column= 0, padx= 5, pady= 2, sticky= 'nesw')
    # label_frame_delta.grid(row= 1, column= 1, padx= 5, pady= 2, sticky= 'nesw')
    # label_frame_threshold.grid(row= 2, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'nw')
    # label_frame_label.grid(row= 3, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'ew')

    # label_frame_control.grid(row= 0, column= 2, padx= 5, pady= 2, sticky= 'nsew')
    # label_frame_channel.grid(row= 1, column= 2, padx= 5, pady= 2, sticky= 'nsew')
    # label_frame_save_file.grid(row= 2, column= 2, padx= 5, pady= 2, sticky= 'nsew')
    # label_frame_load_file.grid(row= 3, column= 2, padx= 5, pady= 2, sticky= 'nsew')
    
    # label_frame_extract_result.grid(row= 0, column= 3, padx= 5, pady= 2, rowspan= 4, sticky= 'nsew')

    # # Meas grid
    # button_frequency.grid(row= 0, column= 0, padx= 5, pady= 4, sticky= 'nesw')
    # button_period.grid(row= 0, column= 1, padx= 5, pady= 4, sticky= 'nesw')
    # button_dutycycle.grid(row= 0, column= 2, padx= 5, pady= 4, sticky= 'nesw')
    # button_delta_time.grid(row= 0, column= 3, padx= 5, pady= 4, sticky= 'nesw')
    # button_tH.grid(row= 1, column= 0, padx= 5, pady= 4, sticky= 'nesw')
    # button_tL.grid(row= 1, column= 1, padx= 5, pady= 4, sticky= 'nesw')
    # button_tR.grid(row= 1, column= 2, padx= 5, pady= 4, sticky= 'nesw')
    # button_tF.grid(row= 1, column= 3, padx= 5, pady= 4, sticky= 'nesw')
    # button_VIH.grid(row= 2, column= 0, padx= 5, pady= 4, sticky= 'nesw')
    # button_VIL.grid(row= 2, column= 1, padx= 5, pady= 4, sticky= 'nesw')
    # button_slewrate_tR.grid(row= 2, column= 2, padx= 5, pady= 4, sticky= 'nesw')
    # button_slewrate_tF.grid(row= 2, column= 3, padx= 5, pady= 4, sticky= 'nesw')
    # button_VPP.grid(row= 3, column= 0, padx= 5, pady= 4, sticky= 'nesw')
    # button_VMAX.grid(row= 3, column= 1, padx= 5, pady= 4, sticky= 'nesw')
    # button_VMIN.grid(row= 3, column= 2, padx= 5, pady= 4, sticky= 'nesw')
    # button_PeriodtoPeriod.grid(row= 3, column= 3, padx= 5, pady= 4, sticky= 'nesw')

    # # Scale grid
    # label_volt_scale.grid(row= 0, column= 0, padx= 5, pady= 4, sticky= 'w') 
    # combobox_voltage_scale.grid(row= 0, column= 1, padx= 5, pady= 4, sticky= 'ew')
    # label_voltage_offset.grid(row= 1, column= 0, padx= 5, pady= 4, sticky= 'w') 
    # combobox_voltage_offset.grid(row= 1, column= 1, padx= 5, pady= 4, sticky= 'ew')
    # button_voltage_scale.grid(row= 2, column= 0, padx= 5, pady= 4, sticky= 'ew')
    
    # label_trigger_level.grid(row= 3, column= 0, padx= 5, pady= 4, sticky= 'w') 
    # combobox_trigger_level.grid(row= 3, column= 1, padx= 5, pady= 4, sticky= 'ew')
    # label_trigger_channel.grid(row= 4, column= 0, padx= 5, pady= 4, sticky= 'w') 
    # combobox_trigger_channel.grid(row= 4, column= 1, padx= 5, pady= 4, sticky= 'ew')
    # button_trigger_check.grid(row= 5, column= 0, padx= 5, pady= 4, sticky= 'ew')
    
    # label_timebase_scale.grid(row= 0, column= 2, padx= 5, pady= 4, sticky= 'w') 
    # entry_timebase_scale.grid(row= 0, column= 3, padx= 5, pady= 4, sticky= 'ew')
    # label_timebase_offset.grid(row= 1, column= 2, padx= 5, pady= 4, sticky= 'w') 
    # entry_timebase_offset.grid(row= 1, column= 3, padx= 5, pady= 4, sticky= 'ew')
    # button_timebase_scale_check.grid(row= 2, column= 2, padx= 5, pady= 4, sticky= 'ew')
    # button_timebase_offset_check.grid(row= 2, column= 3, padx= 5, pady= 4, sticky= 'ew')
    
    # label_waveform_intensity.grid(row= 3, column= 2, padx= 5, pady= 4, sticky= 'w')
    # entry_waveform_intensity.grid(row= 3, column= 3, padx= 5, pady= 4, sticky= 'ew')
    
    # button_waveform_intensity.grid(row= 4, column= 3, padx= 5, pady= 4, sticky= 'ew')
    # button_set_intensity_50.grid(row= 5, column= 3, padx= 5, pady= 4, sticky= 'ew')

    # # b_meas_all_edge.grid(row= 5, column= 2, padx= 5, pady= 4)

    # # Delta grid
    # label_start.grid(row= 0, column= 0, padx= 5, pady= 5)
    # combobox_start_risefall.grid(row= 1, column= 0, padx=5, pady= 5)
    # combobox_start_N.grid(row= 2, column= 0, padx=5, pady= 5)
    # combobox_start_position.grid(row= 3, column= 0, padx=5, pady= 5)
    # label_stop.grid(row= 0, column= 1, padx= 5, pady= 5)
    # combobox_stop_risefall.grid(row= 1, column= 1, padx=5, pady= 5)
    # combobox_stop_N.grid(row= 2, column= 1, padx=5, pady= 5)
    # combobox_stop_position.grid(row= 3, column= 1, padx=5, pady= 5)
    # button_edge_switch.grid(row= 4, column= 0, padx= 5, pady= 5)
    # button_position_switch.grid(row= 4, column= 1, padx= 5, pady= 5)

    # # Thres grid
    # radiobutton_general_percent_top.grid(row= 0, column= 0, padx= 5, pady= 3, sticky= 'w')
    # combobox_general_percent_top.grid(row= 0, column= 1, sticky= 'w')
    # label_general_percent_middle.grid(row= 1, column= 0, padx= 5, pady= 3, sticky= 'w')
    # combobox_general_percent_middle.grid(row= 1, column= 1, sticky= 'w')
    # label_general_percent_base.grid(row= 2, column= 0, padx= 5, pady= 3, sticky= 'w')
    # combobox_general_percent_base.grid(row= 2, column= 1, sticky= 'w')
    # radiobutton_general_value_top.grid(row= 3, column= 0, padx= 5, pady= 3, sticky= 'w') 
    # combobox_general_value_top.grid(row= 3, column= 1, sticky= 'w')
    # label_general_value_middle.grid(row= 4, column= 0, padx= 5, pady= 3, sticky= 'w') 
    # combobox_general_value_middle.grid(row= 4, column= 1, sticky= 'w')
    # label_general_value_base.grid(row= 5, column= 0, padx= 5, pady= 3, sticky= 'w')
    # combobox_general_value_base.grid(row= 5, column= 1, sticky= 'w')
    # button_general_threshold_check.grid(row= 0, column= 2, padx= 5, pady= 3, sticky= 'ew')
    # radiobutton_risefall_percent_top.grid(row= 0, column= 3, padx= 5, pady= 3, sticky= 'w')
    # label_risefall_percent_base.grid(row= 1, column= 3, padx= 5, pady= 3, sticky= 'w')
    # combobox_risefall_percent_top.grid(row= 0, column= 4, sticky= 'w')
    # combobox_risefall_percent_base.grid(row= 1, column= 4, sticky= 'w')
    # radiobutton_risefall_value_top.grid(row= 2, column= 3, padx= 5, pady= 3, sticky= 'w') 
    # label_risefall_value_base.grid(row= 3, column= 3, padx= 5, pady= 3, sticky= 'w')
    # combobox_risefall_value_top.grid(row= 2, column= 4, sticky= 'w')
    # combobox_risefall_value_base.grid(row= 3, column= 4, sticky= 'w')
    # button_risefall_threshold_check.grid(row= 0, column= 5, padx= 5, pady= 3, columnspan= 2, sticky= 'ew')

    # label_sampling_rate.grid(row= 4, column= 3, sticky= 'w')
    # entry_sampling_rate.grid(row= 4, column= 4, sticky= 'w')
    # button_sampling_rate_check.grid(row= 4, column= 5, padx= 2, sticky= 'w')
    # button_sampling_rate_automode.grid(row= 4, column= 6, padx= 2, sticky= 'w')
    # label_memory_depth.grid(row= 5, column= 3, sticky= 'w')
    # entry_memory_depth.grid(row= 5, column= 4, sticky= 'w')
    # button_memory_depth_check.grid(row= 5, column= 5, padx= 2, sticky= 'w')
    # button_memory_depth_automode.grid(row= 5, column= 6, padx= 2, sticky= 'w')

    # # Label grid
    # radiobutton_label.grid(row= 0, column= 0, padx= 5, sticky= 'w')
    # radiobutton_bookmark.grid(row= 0, column= 1, padx= 5, sticky= 'w')

    # entey_label_1.grid(row= 1, column= 0, padx= 5, pady= 3, columnspan= 2, sticky= 'ew')
    # button_lable1.grid(row= 1, column= 2, padx= 5, pady= 3, sticky= 'w')
    # button_delete_label_1.grid(row= 1, column= 3, padx= 5, pady= 3, sticky= 'w')
    # entry_label_2.grid(row= 2, column= 0, padx= 5, pady= 3, columnspan= 2, sticky= 'ew')
    # button_lable_2.grid(row= 2, column= 2, padx= 5, pady= 3, sticky= 'w')
    # button_delete_label_2.grid(row= 2, column= 3, padx= 5, pady= 3, sticky= 'w')
    # entry_label_3.grid(row= 3, column= 0, padx= 5, pady= 3, columnspan= 2, sticky= 'ew')
    # button_lable_3.grid(row= 3, column= 2, padx= 5, pady= 3, sticky= 'w')
    # button_delete_label_3.grid(row= 3, column= 3, padx= 5, pady= 3, sticky= 'w')
    # entry_label_4.grid(row= 4, column= 0, padx= 5, pady= 3, columnspan= 2, sticky= 'ew')
    # button_lable_4.grid(row= 4, column= 2, padx= 5, pady= 3, sticky= 'w')
    # button_delete_label_4.grid(row= 4, column= 3, padx= 5, pady= 3, sticky= 'w')

    # entry_label_5.grid(row= 1, column= 4, padx= 5, pady= 3, columnspan= 2, sticky= 'ew')
    # button_lable_5.grid(row= 1, column= 6, padx= 5, pady= 3, sticky= 'e')
    # button_delete_label_5.grid(row= 1, column= 7, padx= 5, pady= 3, sticky= 'e')
    # entry_label_6.grid(row= 2, column= 4, padx= 5, pady= 3, columnspan= 2, sticky= 'ew')
    # button_lable_6.grid(row= 2, column= 6, padx= 5, pady= 3, sticky= 'e')
    # button_delete_label_6.grid(row= 2, column= 7, padx= 5, pady= 3, sticky= 'e')
    # entry_label_7.grid(row= 3, column= 4, padx= 5, pady= 3, columnspan= 2, sticky= 'ew')
    # button_lable_7.grid(row= 3, column= 6, padx= 5, pady= 3, sticky= 'e')
    # button_delete_label_7.grid(row= 3, column= 7, padx= 5, pady= 3, sticky= 'e')
    # entry_label_8.grid(row= 4, column= 4, padx= 5, pady= 3, columnspan= 2, sticky= 'ew')
    # button_lable_8.grid(row= 4, column= 6, padx= 5, pady= 3, sticky= 'e')
    # button_delete_label_8.grid(row= 4, column= 7, padx= 5, pady= 3, sticky= 'e')

    # # Control grid
    # button_run.grid(row= 0, column= 0, padx= 5, pady= 3, rowspan= 2, sticky= 'nesw')
    # button_stop.grid(row= 0, column= 1, padx= 5, pady= 3, rowspan= 2, sticky= 'nesw')
    # button_single.grid(row= 0, column= 2, padx= 5, pady= 3, rowspan= 2, sticky= 'nesw')
    # button_autoscale.grid(row= 2, column= 0, padx= 5, pady= 3, rowspan= 2, sticky= 'nesw')
    # button_default.grid(row= 2, column= 1, padx= 5, pady= 3, rowspan= 2, sticky= 'nesw')
    # button_clear_display.grid(row= 2, column= 2, padx= 5, pady= 3, rowspan= 2, sticky= 'nesw')
    # button_trigger.grid(row= 4, column= 0, padx= 5, pady= 3, rowspan= 2, sticky= 'nesw')
    # button_trigger_slope.grid(row= 4, column= 1, padx= 5, pady= 3, rowspan= 2, sticky= 'nesw')
    # button_disable_button.grid(row= 4, column= 2, padx= 5, pady= 3, rowspan= 2, sticky= 'nesw')
    # button_delete_measurement.grid(row= 6, column= 0, padx= 5, pady= 3, rowspan= 2, sticky= 'nesw')
    # button_add_marker.grid(row= 6, column= 1, padx= 5, pady= 3, rowspan= 2, sticky= 'nesw')
    # button_delete_marker.grid(row= 6, column= 2, padx= 5, pady= 3, rowspan= 2, sticky= 'nesw')
    
    # checkbutton_marker_1.grid(row= 0, column= 4, padx= 5, sticky= 'w') 
    # checkbutton_marker_2.grid(row= 1, column= 4, padx= 5, sticky= 'w')
    # checkbutton_marker_3.grid(row= 2, column= 4, padx= 5, sticky= 'w')
    # checkbutton_marker_4.grid(row= 3, column= 4, padx= 5, sticky= 'w')
    # checkbutton_marker_5.grid(row= 4, column= 4, padx= 5, sticky= 'w')
    # checkbutton_marker_6.grid(row= 5, column= 4, padx= 5, sticky= 'w')
    # checkbutton_marker_7.grid(row= 0, column= 5, padx= 5, sticky= 'w') 
    # checkbutton_marker_8.grid(row= 1, column= 5, padx= 5, sticky= 'w') 
    # checkbutton_marker_9.grid(row= 2, column= 5, padx= 5, sticky= 'w') 
    # checkbutton_marker_10.grid(row= 3, column= 5, padx= 5, sticky= 'w') 
    # checkbutton_marker_11.grid(row= 4, column= 5, padx= 5, sticky= 'w') 
    # checkbutton_marker_12.grid(row= 5, column= 5, padx= 5, sticky= 'w') 
    # checkbutton_marker_color.grid(row= 7, column= 4, padx= 5, pady= 3, columnspan= 2, sticky= 'ew')

    # # Chan grid
    # button_channel_1.grid(row= 0, column= 0, padx= 5, pady= 3, rowspan= 2, columnspan= 2, sticky= 'nesw')
    # button_channel_2.grid(row= 0, column= 2, padx= 5, pady= 3, rowspan= 2, columnspan= 2, sticky= 'nesw')
    # button_channel_3.grid(row= 0, column= 4, padx= 5, pady= 3, rowspan= 2, columnspan= 2, sticky= 'nesw')
    # button_channel_4.grid(row= 0, column= 6, padx= 5, pady= 3, rowspan= 2, columnspan= 2, sticky= 'nesw')
    # button_wmemory_1.grid(row= 2, column= 0, padx= 5, pady= 3, rowspan= 2, columnspan= 2, sticky= 'nesw')
    # button_wmemory_2.grid(row= 2, column= 2, padx= 5, pady= 3, rowspan= 2, columnspan= 2, sticky= 'nesw')
    # button_wmemory_3.grid(row= 2, column= 4, padx= 5, pady= 3, rowspan= 2, columnspan= 2, sticky= 'nesw')
    # button_wmemory_4.grid(row= 2, column= 6, padx= 5, pady= 3, rowspan= 2, columnspan= 2, sticky= 'nesw')
    # checkbutton_delta_name.grid(row= 4, column= 2, padx= 5, pady= 3, columnspan= 3, sticky= 'w')
    # combobox_delta_name.grid(row= 4, column= 4, sticky= 'w')
    # radiobutton_channel_single.grid(row= 5, column= 0, sticky= 'w')
    # combobox_channel_single.grid(row= 5, column= 1, sticky= 'w')
    # radiobutton_channel_delta.grid(row= 5, column= 2, sticky= 'w')
    # combobox_channel_delta_start.grid(row= 5, column= 3, sticky= 'nesww')
    # label_arrow.grid(row= 6, column= 2, sticky= 'ew')
    # label_channel_delta_stop.grid(row= 7, column= 2, sticky= 'ew')
    # combobox_channel_delta_stop.grid(row= 7, column= 3, sticky= 'w')
    # button_channel_switch.grid(row= 6, column= 4, sticky= 'w')

    # # Save grid
    # # e_image_folder.grid(row= 0, column= 0, padx= 5, pady= 1)
    # # l_image_folder.grid(row=0, column= 1, columnspan= 2, padx= 5, pady= 1)
    # # rb_img_desktop_path.grid(row= 0, column= 2, padx= 5, pady= 1, sticky= 'nesw')
    # # rb_img_server_path.grid(row= 0, column= 3, padx= 5, pady= 1, sticky= 'nesw')
    # entry_image_pc_folder.grid(row= 1, column= 0, padx= 5, pady= 1, sticky= 'ew')
    # button_image_pc_browse.grid(row= 1, column= 1, padx= 5, pady= 1, sticky= 'w')
    # label_image_pc_folder.grid(row= 1, column= 2, columnspan= 3, padx= 5, pady= 1, sticky= 'w')
    # entry_image.grid(row= 2, column= 0, padx= 5, pady= 1, sticky= 'ew')
    # label_image_name.grid(row= 2, column= 1, padx= 5, pady= 1, sticky= 'w')
    # # b_image_save_scope.grid(row= 2, column= 2, padx= 5, pady= 1, sticky= 'nesw')
    # button_save_image_pc.grid(row= 2, column= 2, padx= 5, pady= 1, columnspan= 2, sticky= 'w')
    
    # label_divider.grid(row= 3, column= 0, columnspan= 4, sticky= 'w')

    # radiobutton_wmemory.grid(row= 4, column= 0, padx= 5, sticky= 'w')
    # radiobutton_setup.grid(row= 4, column= 1, padx= 5, sticky= 'w')

    # entry_wmemory_folder.grid(row= 5, column= 0, padx= 5, pady= 1, sticky= 'ew')
    # label_wmemory_folder.grid(row=5, column= 1, padx= 5, pady= 1, sticky= 'w')
    # radiobutton_wmemory_desktop_path.grid(row= 5, column= 2, padx= 5, pady= 1, sticky= 'w')
    # radiobutton_wmemory_server_path.grid(row= 5, column= 3, padx= 5, pady= 1, sticky= 'w')
    # entry_wmemory_pc_folder.grid(row= 6, column= 0, padx= 5, pady= 1, sticky= 'ew')
    # button_wmemory_pc_browse.grid(row= 6, column= 1, padx= 5, pady= 1, sticky= 'w')
    # label_wmemory_pc_folder.grid(row= 6, column= 2, padx= 5, pady= 1, columnspan= 2, sticky= 'w')
    # entry_other_file.grid(row= 7, column= 0, padx= 5, pady= 1, sticky= 'ew')
    # label_other_filename.grid(row= 7, column= 1, padx= 5, pady= 1, sticky= 'w')
    # button_other_file_save_scope.grid(row= 7, column= 2, padx= 5, pady= 1, sticky= 'w')
    # button_other_file_save_pc.grid(row= 7, column= 3, padx= 5, pady= 1, sticky= 'w')
    
    # #LoadWMe grid
    # entry_wmemory_1.grid(row= 0, column= 0, padx= 5, pady= 2, columnspan= 3, sticky= 'ew')
    # button_load_wmemory_1.grid(row=0, column= 3, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # button_clear_wmemory_1.grid(row= 0, column= 5, padx= 5, pady= 2, sticky= 'w')
    # entry_wmemory_2.grid(row= 1, column= 0, padx= 5, pady= 2, columnspan= 3, sticky= 'ew')
    # button_load_wmemory_2.grid(row=1, column= 3, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # button_clear_wmemory_2.grid(row= 1, column= 5, padx= 5, pady= 2, sticky= 'w')
    # entry_wmemory_3.grid(row= 2, column= 0, padx= 5, pady= 2, columnspan= 3, sticky= 'ew')
    # button_load_wmemory_3.grid(row=2, column= 3, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # button_clear_wmemory_3.grid(row= 2, column= 5, padx= 5, pady= 2, sticky= 'w')
    # entry_wmemory_4.grid(row= 3, column= 0, padx= 5, pady= 2, columnspan= 3, sticky= 'ew')
    # button_load_wmemory_4.grid(row=3, column= 3, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # button_clear_wmemory_4.grid(row= 3, column= 5, padx= 5, pady= 2, sticky= 'w')
    # combobox_setupfile_interface.grid(row= 4, column= 0, padx= 5, pady= 2, sticky= 'w')
    # combobox_setupfile_class.grid(row= 4, column= 1, padx= 5, pady= 2, sticky= 'w')
    # combobox_setup.grid(row= 4, column= 2, padx= 5, pady= 2, sticky= 'w')
    # checkbutton_setup_timebase.grid(row= 4, column= 4, pady= 2, sticky= 'w')
    # checkbutton_setup_label.grid(row= 4, column= 5, pady= 2, sticky= 'w')
    # checkbutton_setup_voltage.grid(row= 4, column= 6, pady= 2, sticky= 'w')

    # #Extract Results grid
    # radiobutton_mean_result.grid(row= 0, column= 0, padx= 5, pady= 2, sticky= 'w')
    # radiobutton_minmax_result.grid(row= 0, column= 1, padx= 5, pady= 2, sticky= 'w')
    # button_get_result.grid(row= 1, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'ew')
    # label_result_tag_1.grid(row= 2, column= 0, sticky= 'w')
    # label_result_tag_2.grid(row= 2, column= 1, sticky= 'w')
    # # l_result_dividing_line.grid(row= 3, column= 0, columnspan= 2, sticky= 'nesw')
    # label_measurement_name_1.grid(row= 4, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # text_result_mean_1.grid(row= 5, column= 0, padx= 5, pady= 2, sticky= 'w')
    # text_result_minmax_1.grid(row= 5, column= 1, padx= 5, pady= 2, sticky= 'w')
    # label_measurement_name_2.grid(row= 6, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # text_result_mean_2.grid(row= 7, column= 0, padx= 5, pady= 2, sticky= 'w')
    # text_result_minmax_2.grid(row= 7, column= 1, padx= 5, pady= 2, sticky= 'w')
    # label_measurement_name_3.grid(row= 8, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # text_result_mean_3.grid(row= 9, column= 0, padx= 5, pady= 2, sticky= 'w')
    # text_result_minmax_3.grid(row= 9, column= 1, padx= 5, pady= 2, sticky= 'w')
    # label_measurement_name_4.grid(row= 10, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # text_result_mean_4.grid(row= 11, column= 0, padx= 5, pady= 2, sticky= 'w')
    # text_result_minmax_4.grid(row= 11, column= 1, padx= 5, pady= 2, sticky= 'w')
    # label_measurement_name_5.grid(row= 12, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # text_result_mean_5.grid(row= 13, column= 0, padx= 5, pady= 2, sticky= 'w')
    # text_result_minmax_5.grid(row= 13, column= 1, padx= 5, pady= 2, sticky= 'w')
    # label_measurement_name_6.grid(row= 14, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # text_result_mean_6.grid(row= 15, column= 0, padx= 5, pady= 2, sticky= 'w')
    # text_result_minmax_6.grid(row= 15, column= 1, padx= 5, pady= 2, sticky= 'w')
    # label_measurement_name_7.grid(row= 16, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # text_result_mean_7.grid(row= 17, column= 0, padx= 5, pady= 2, sticky= 'w')
    # text_result_minmax_7.grid(row= 17, column= 1, padx= 5, pady= 2, sticky= 'w')
    # label_measurement_name_8.grid(row= 18, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # text_result_mean_8.grid(row= 19, column= 0, padx= 5, pady= 2, sticky= 'w')
    # text_result_minmax_8.grid(row= 19, column= 1, padx= 5, pady= 2, sticky= 'w')
    # label_measurement_name_9.grid(row= 20, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # text_result_mean_9.grid(row= 21, column= 0, padx= 5, pady= 2, sticky= 'w')
    # text_result_minmax_9.grid(row= 21, column= 1, padx= 5, pady= 2, sticky= 'w')
    # label_measurement_name_10.grid(row= 22, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # text_result_mean_10.grid(row= 23, column= 0, padx= 5, pady= 2, sticky= 'w')
    # text_result_minmax_10.grid(row= 23, column= 1, padx= 5, pady= 2, sticky= 'w')
    # label_measurement_name_11.grid(row= 24, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # text_result_mean_11.grid(row= 25, column= 0, padx= 5, pady= 2, sticky= 'w')
    # text_result_minmax_11.grid(row= 25, column= 1, padx= 5, pady= 2, sticky= 'w')
    # label_measurement_name_12.grid(row= 26, column= 0, padx= 5, pady= 2, columnspan= 2, sticky= 'w')
    # text_result_mean_12.grid(row= 27, column= 0, padx= 5, pady= 2, sticky= 'w')
    # text_result_minmax_12.grid(row= 27, column= 1, padx= 5, pady= 2, sticky= 'w')

    # ToolTip(combobox_voltage_scale, '可用滑鼠滾輪選擇\n新增選項: 輸入後按Enter\n刪除選項: 選擇後按Delete')
    # ToolTip(combobox_voltage_offset, '可用滑鼠滾輪選擇\n新增選項: 輸入後按Enter\n刪除選項: 選擇後按Delete')
    # ToolTip(combobox_trigger_level, '可用滑鼠滾輪選擇\n新增選項: 輸入後按Enter\n刪除選項: 選擇後按Delete')
    # ToolTip(button_waveform_intensity, '可用滑鼠滾輪調整數字大小')
    # ToolTip(combobox_start_risefall, '嗚啦!')
    # ToolTip(combobox_start_N, '呀哈!')
    # ToolTip(combobox_stop_risefall, '噗嚕!')
    # ToolTip(combobox_general_percent_top, '可用滑鼠滾輪選擇\n新增選項: 輸入後按Enter\n刪除選項: 選擇後按Delete')
    # ToolTip(combobox_general_percent_middle, '可用滑鼠滾輪選擇\n新增選項: 輸入後按Enter\n刪除選項: 選擇後按Delete')
    # ToolTip(combobox_general_percent_base, '可用滑鼠滾輪選擇\n新增選項: 輸入後按Enter\n刪除選項: 選擇後按Delete')
    # ToolTip(combobox_general_value_top, '可用滑鼠滾輪選擇\n新增選項: 輸入後按Enter\n刪除選項: 選擇後按Delete')
    # ToolTip(combobox_general_value_middle, '可用滑鼠滾輪選擇\n新增選項: 輸入後按Enter\n刪除選項: 選擇後按Delete')
    # ToolTip(combobox_general_value_base, '可用滑鼠滾輪選擇\n新增選項: 輸入後按Enter\n刪除選項: 選擇後按Delete')
    # ToolTip(combobox_risefall_percent_top, '可用滑鼠滾輪選擇\n新增選項: 輸入後按Enter\n刪除選項: 選擇後按Delete')
    # ToolTip(combobox_risefall_percent_base, '可用滑鼠滾輪選擇\n新增選項: 輸入後按Enter\n刪除選項: 選擇後按Delete')
    # ToolTip(combobox_risefall_value_top, '可用滑鼠滾輪選擇\n新增選項: 輸入後按Enter\n刪除選項: 選擇後按Delete')
    # ToolTip(combobox_risefall_value_base, '可用滑鼠滾輪選擇\n新增選項: 輸入後按Enter\n刪除選項: 選擇後按Delete')
    # ToolTip(entry_label_4, '133 221 333 123 111')
    # ToolTip(entry_label_6, '電倉鼠!')
    # ToolTip(button_autoscale, '好的不得了')
    # ToolTip(button_clear_display, '嗚嚕嗚啦')
    # ToolTip(button_default, '6666')
    # ToolTip(checkbutton_marker_2, '防塵套不要亂丟')
    # ToolTip(checkbutton_marker_9, '花椒串')
    # ToolTip(combobox_channel_single, '累')
    # ToolTip(combobox_channel_delta_start, '隨波逐流的')
    # ToolTip(combobox_channel_delta_stop, '人生')
    # # ToolTip(e_image_folder, '自己打字，按按鈕會幫你新增資料夾')
    # ToolTip(entry_image, '嗚哩哩')
    # ToolTip(entry_image_pc_folder, '可以直接存電腦啦~')
    # ToolTip(entry_wmemory_folder, '自己打字，按按鈕會幫你新增資料夾')
    # ToolTip(entry_other_file, 'Channel要選對欸')
    # ToolTip(entry_wmemory_pc_folder, '示波器有沒有先存檔ㄏㄚˋ')
    # ToolTip(entry_wmemory_2, '呀哈呀哈')
    # ToolTip(entry_wmemory_4, '噗嚕!')

    # ToolTip(text_result_mean_3, '取小數點後三位')
    # ToolTip(text_result_minmax_7, '無條件捨去')
    # ToolTip(text_result_minmax_9, '芭樂綠茶')
    # ToolTip(text_result_mean_12, '多多檢查')

    # segment_list= initialize()
    

    # b_setup_load = ttk.Button(label_frame_load_file, text= 'load Setup', width= button_width, command= lambda: mxr.load_setup(
    #     folder= strvar_wmemory_folder.get(), setup_name= strvar_setup.get(), 
    #     scope_segment= segment_list[0],
    #     # time_scale= str_time_scale.get(), time_position= str_time_offset.get(), 
    #     choose_type= intvar_label_type.get(), 
    #     file_path_choice = intvar_wmemory_path_choice.get(), 
    #     # volt_scale= str_volt_scale.get(), volt_offset= str_volt_offset.get(), 
    #     # trig_chan= str_trigger_chan.get(), trig_level= str_trigger_level.get(),
    #     g_top= combobox_general_value_top.get(), g_middle= combobox_general_value_middle.get(), g_base= combobox_general_value_base.get(), 
    #     g_top_percent= combobox_general_percent_top.get(), g_middle_percent= combobox_general_percent_middle.get(), g_base_percent= combobox_general_percent_base.get(), 
    #     rf_top= combobox_risefall_value_top.get(),  rf_base= combobox_risefall_value_base.get(), 
    #     rf_top_percent= combobox_risefall_percent_top.get(), rf_base_percent= combobox_risefall_percent_base.get()
    #     ))
    # b_setup_load.grid(row= 4, column= 3, padx= 5, pady= 2, sticky= 'w')
    
    # # cbb_setupfile_interface.config(values= setupfile_interface_list)
    # combobox_setupfile_interface.bind("<<ComboboxSelected>>", lambda e: select_setupfile_interface(e, segment_list= segment_list))
    # combobox_setupfile_class.bind("<<ComboboxSelected>>", lambda e: select_setupfile_class(e, segment_list= segment_list))

    window.protocol('WM_DELETE_WINDOW', close_window)

    # mxr= MXR(scope_ip= scope_ip)


    # init_win_w, init_win_h = win_w, win_h
    # def on_configure(event):
    #     # 避免在初始化時多次觸發
    #     if event.width <= 1 or event.height <= 1:
    #         return
    #     size_ratio_w = event.width / init_win_w
    #     size_ratio_h = event.height / init_win_h
    #     size_ratio = min(size_ratio_w, size_ratio_h)

    #     dynamic_scale = final_scale * size_ratio
    #     new_font = max(6, int(round(base_font_size * dynamic_scale)))
    #     new_w = max(4, int(round(20 * dynamic_scale)))
    #     new_h = max(1, int(round(2 * dynamic_scale)))

    #     if btn_font.cget("size") != new_font:
    #         btn_font.configure(size=new_font)
    #     buttons= [button_frequency, button_period, button_dutycycle, button_delta_time, 
    #               button_tH, button_tL, button_tR, button_tF, button_VIH, button_VIL, 
    #               button_slewrate_tR, button_slewrate_tF, button_VPP, button_VMAX, button_VMIN, button_PeriodtoPeriod]
    #     for b in buttons:
    #         if int(b.cget("width")) != new_w or int(b.cget("height")) != new_h:
    #             b.config(width=new_w, height=new_h)

    # window.bind("<Configure>", on_configure)


    window.mainloop()

# 選擇 Scope IP ============================================================================================================================================

config_initial = configparser.ConfigParser()
config_initial.optionxform = str
config_initial.read(os.path.join(os.path.dirname(__file__), 'InitConfig_setup_new.ini'), encoding='UTF-8',)

scope_ips= []
for i in range(len(config_initial['Scope_IPs'])):
    scope_ips.append(config_initial['Scope_IPs'][f'IP_{i}'])
scope_ips.append('')

# Enable DPI awareness on Windows BEFORE creating Tk
dpi_awared = enable_dpi_awareness_windows()
print("enable_dpi_awareness_windows ->", dpi_awared)

id_window = tk.Tk()
id_window.title(window_name)
id_window.resizable(width= False, height= False)
id_window.geometry('+500+150')
id_window.configure(background= '#91B6E1')

l_scope_ip = tk.Label(id_window, text= 'Enter Scope IP', background= '#91B6E1', fg= '#091E87', font= ('Candara', 12, 'bold'),)
str_scope_ip = tk.StringVar()
cb_scope_ip = ttk.Combobox(id_window, textvariable= str_scope_ip, values= scope_ips)
b_scope_ip = tk.Button(id_window, text= 'OK', width= 10, height= 2, command= lambda: show_main_window(old_scope_ips= scope_ips), )

l_ip = tk.Label(id_window, text= '★★★ 確認電腦IP與Scope在同一網域 ★★★', background= '#91B6E1', fg= '#F6044D', font= ('Candara', 14, 'bold'),)

l_scope_ip.pack(padx= 5, pady= 5)
cb_scope_ip.pack(padx= 5, pady= 5)
b_scope_ip.pack(padx= 5, pady= 5)
l_ip.pack(padx= 5, pady= 5)

id_window.mainloop()
