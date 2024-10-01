import pyvisa
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
import configparser
import os



def initialize():
    config_initial = configparser.ConfigParser()
    config_initial.optionxform = str
    config_initial.read(os.path.join(os.path.dirname(__file__), 'InitialConfiguration_mxr_tool.ini'), encoding='UTF-8',)
    
    VoltScale = config_initial['Scale_Offset_Config']['VoltScale']
    VoltOffset = config_initial['Scale_Offset_Config']['VoltOffset']
    TimebaseScale = config_initial['Scale_Offset_Config']['TimebaseScale']
    TimebaseOffset = config_initial['Scale_Offset_Config']['TimebaseOffset']
    TriggerLevel = config_initial['Scale_Offset_Config']['TriggerLevel']
    TriggerChan = config_initial['Scale_Offset_Config']['TriggerChan']

    DeltaStartEdge = config_initial['Delta_Setup_Config']['DeltaStartEdge']
    DeltaStartNum = config_initial['Delta_Setup_Config']['DeltaStartNum']
    DeltaStartPosition = config_initial['Delta_Setup_Config']['DeltaStartPosition']
    DeltaStopEdge = config_initial['Delta_Setup_Config']['DeltaStopEdge']
    DeltaStopNum = config_initial['Delta_Setup_Config']['DeltaStopNum']
    DeltaStopPosition = config_initial['Delta_Setup_Config']['DeltaStopPosition']

    GeneralTop = config_initial['Threshold_Setup_Config']['GeneralTop']
    GeneralMiddle = config_initial['Threshold_Setup_Config']['GeneralMiddle']
    GeneralBase = config_initial['Threshold_Setup_Config']['GeneralBase']
    RFTop = config_initial['Threshold_Setup_Config']['RFTop']
    RFBase = config_initial['Threshold_Setup_Config']['RFBase']

    ChanLabel1 = config_initial['Lable_Setup_Config']['ChanLabel1']
    ChanLabel2 = config_initial['Lable_Setup_Config']['ChanLabel2']
    ChanLabel3 = config_initial['Lable_Setup_Config']['ChanLabel3']

    SaveImgFolder = config_initial['Save_Setup_Config']['SaveImgFolder']
    SaveImgName = config_initial['Save_Setup_Config']['SaveImgName']
    SaveWMeFolder = config_initial['Save_Setup_Config']['SaveWMeFolder']
    SaveWMeName = config_initial['Save_Setup_Config']['SaveWMeName']

    LoadWMe1 = config_initial['Load_WMemory_Setup_Config']['LoadWMe1']
    LoadWMe2 = config_initial['Load_WMemory_Setup_Config']['LoadWMe2']
    LoadWMe3 = config_initial['Load_WMemory_Setup_Config']['LoadWMe3']

    str_volt_scale.set(value= VoltScale)
    str_volt_offset.set(value= VoltOffset)
    str_time_scale.set(value= TimebaseScale)
    str_time_offset.set(value= TimebaseOffset)
    str_trigger_level.set(value= TriggerLevel)
    str_trigger_chan.set(value= TriggerChan)

    start_rf.set(value= DeltaStartEdge)
    start_num.set(value= DeltaStartNum)
    start_pos.set(value= DeltaStartPosition)
    stop_rf.set(value= DeltaStopEdge)
    stop_num.set(value= DeltaStopNum)
    stop_pos.set(value= DeltaStopPosition)

    str_gen_top.set(value= GeneralTop)
    str_gen_mid.set(value= GeneralMiddle)
    str_gen_base.set(value= GeneralBase)
    str_rf_top.set(value= RFTop)
    str_rf_base.set(value= RFBase)

    str_label_1.set(value= ChanLabel1)
    str_label_2.set(value= ChanLabel2)
    str_label_3.set(value= ChanLabel3)

    str_image_folder.set(value= SaveImgFolder)
    str_image.set(value= SaveImgName)
    str_WMe_folder.set(value= SaveWMeFolder)
    str_WMe.set(value= SaveWMeName)

    str_WMe1.set(value= LoadWMe1)
    str_WMe2.set(value= LoadWMe2)
    str_WMe3.set(value= LoadWMe3)

class MXR:

    def __init__(self):
        rm = pyvisa.ResourceManager()
        inst_name = 'MXR608A'
        self.inst = rm.open_resource(f'TCPIP0::KEYSIGH-MUTUU36::inst0::INSTR')
        idn = self.inst.query('*IDN?').strip()
        print(f'[{inst_name}] Connect successfully! / {idn}')

    def RF_threshold(self, rf_top, rf_base):
        if int_gen_thres.get() == 1:
            self.inst.write(f':MEASure:THResholds:RFALl:METHod ALL,PERCent')
            self.inst.write(f':MEASure:THResholds:RFALl:TOPBase:PERCent ALL,90,10')
        elif int_gen_thres.get() == 2:
            self.inst.write(f':MEASure:THResholds:RFALl:METHod ALL,PERCent')
            self.inst.write(f':MEASure:THResholds:RFALl:TOPBase:PERCent ALL,80,20')
        elif int_gen_thres.get() == 3:
            self.inst.write(f':MEASure:THResholds:RFALl:METHod ALL,PERCent')
            self.inst.write(f':MEASure:THResholds:RFALl:TOPBase:PERCent ALL,70,30')
        elif int_gen_thres.get() == 4:
            self.inst.write(f':MEASure:THResholds:RFALl:METHod ALL,ABSolute')
            self.inst.write(f':MEASure:THResholds:RFALl:TOPBase:ABSolute ALL,{rf_top},{rf_base}')

    def gen_threshold(self, g_top, g_middle, g_base):
        if int_gen_thres.get() == 1:
            self.inst.write(f':MEASure:THResholds:GENeral:METHod ALL,PERCent')
            self.inst.write(f':MEASure:THResholds:GENeral:PERCent ALL,90,50,10')
        elif int_gen_thres.get() == 2:
            self.inst.write(f':MEASure:THResholds:GENeral:METHod ALL,PERCent')
            self.inst.write(f':MEASure:THResholds:GENeral:PERCent ALL,80,50,20')
        elif int_gen_thres.get() == 3:
            self.inst.write(f':MEASure:THResholds:GENeral:METHod ALL,PERCent')
            self.inst.write(f':MEASure:THResholds:GENeral:PERCent ALL,70,50,30')
        elif int_gen_thres.get() == 4:
            self.inst.write(f':MEASure:THResholds:GENeral:METHod ALL,ABSolute')
            self.inst.write(f':MEASure:THResholds:ABSolute ALL,{g_top},{g_middle},{g_base}')

    def volt_check(self, scale, offset): # 科學記號
        # res_ch1= self.inst.query(f':CHANnel1:DISPlay?')
        # res_ch2= self.inst.query(f':CHANnel2:DISPlay?')
        # res_ch3= self.inst.query(f':CHANnel3:DISPlay?')

        # display_on_list= [res_ch1, res_ch2, res_ch3]
        # for index, value in enumerate(display_on_list):
        #     if value == '1\n':
        #         self.inst.write(f':CHANnel{index+1}:SCALe {scale}')
        #         self.inst.write(f':CHANnel{index+1}:OFFSet {offset}')

        for i in range(1, 4):
            self.inst.write(f':CHANnel{i}:SCALe {scale}')
            self.inst.write(f':CHANnel{i}:OFFSet {offset}')
        # for i in range(1, 4):
        #     self.inst.write(f':WMEMory{i}:SCALe {scale}')
        #     self.inst.write(f':WMEMory{i}:YOFFset {offset}')   

    def timebase_check(self, scale, position): # 科學記號
        self.inst.write(f':TIMebase:SCALe {scale}')
        self.inst.write(f':TIMebase:POSition {position}')

    def trig_check(self, chan, level):
        self.inst.write(f':TRIGger:EDGE:SOURce CHANnel{chan}')
        self.inst.write(f':TRIGger:LEVel CHANnel{chan},{level}')

    def display_Chan(self, chan):
        res= self.inst.query(f':CHANnel{chan}:DISPlay?')
        if res == '1\n':
            self.inst.write(f':CHANnel{chan}:DISPlay OFF')
        else:
            self.inst.write(f':CHANnel{chan}:DISPlay ON')

    def display_WMemory(self, chan):
        res= self.inst.query(f':WMEMory{chan}:DISPlay?')
        if res == '1\n':
            self.inst.write(f':WMEMory{chan}:DISPlay OFF')
        else:
            self.inst.write(f':WMEMory{chan}:DISPlay ON')
            
    def freq(self, chan):
        res= self.judge_chan_wme(chan= chan)
        self.inst.write(f':MEASure:FREQuency {res}{chan}')

    def period(self, chan):
        res= self.judge_chan_wme(chan= chan)
        self.inst.write(f':MEASure:PERiod {res}{chan}')
   
    def dutycycle(self, chan):
        res= self.judge_chan_wme(chan= chan)
        self.inst.write(f':MEASure:DUTYcycle {res}{chan}')

    def slewrate(self, chan, direction):
        res= self.judge_chan_wme(chan= chan)
        self.inst.write(f':MEASure:SLEWrate {res}{chan},{direction}')

    def tH(self, chan):
        res= self.judge_chan_wme(chan= chan)
        self.inst.write(f':MEASure:PWIDth {res}{chan},')

    def tL(self, chan):
        res= self.judge_chan_wme(chan= chan)
        self.inst.write(f':MEASure:NWIDth {res}{chan}')

    def tR(self, chan):
        res= self.judge_chan_wme(chan= chan)
        self.inst.write(f':MEASure:RISetime {res}{chan}')

    def tF(self, chan):
        res= self.judge_chan_wme(chan= chan)
        self.inst.write(f':MEASure:FALLtime {res}{chan}')

    def VIH(self, chan):
        res= self.judge_chan_wme(chan= chan)
        self.inst.write(f':MEASure:VTOP {res}{chan}')

    def VIL(self, chan):
        res= self.judge_chan_wme(chan= chan)
        self.inst.write(f':MEASure:VBASe {res}{chan}')

    def tSU_tHO(self, edge_1, num_1, pos_1, edge_2, num_2, pos_2, chan):
        res= self.judge_chan_wme(chan= chan)
        if chan == 4:
            self.inst.write(f':MEASure:DELTatime:DEFine {edge_1},{num_1},{pos_1},{edge_2},{num_2},{pos_2}')
            self.inst.write(f':MEASure:DELTatime {res}1, {res}2')
        elif chan == 5:
            self.inst.write(f':MEASure:DELTatime:DEFine {edge_1},{num_1},{pos_1},{edge_2},{num_2},{pos_2}')
            self.inst.write(f':MEASure:DELTatime {res}2, {res}1')
        elif chan == 6:
            self.inst.write(f':MEASure:DELTatime:DEFine {edge_1},{num_1},{pos_1},{edge_2},{num_2},{pos_2}')
            self.inst.write(f':MEASure:DELTatime {res}1, {res}3')
        elif chan == 7:
            self.inst.write(f':MEASure:DELTatime:DEFine {edge_1},{num_1},{pos_1},{edge_2},{num_2},{pos_2}')
            self.inst.write(f':MEASure:DELTatime {res}3, {res}1')
        elif chan == 8:
            self.inst.write(f':MEASure:DELTatime:DEFine {edge_1},{num_1},{pos_1},{edge_2},{num_2},{pos_2}')
            self.inst.write(f':MEASure:DELTatime {res}1, {res}1')
        elif chan == 9:
            self.inst.write(f':MEASure:DELTatime:DEFine {edge_1},{num_1},{pos_1},{edge_2},{num_2},{pos_2}')
            self.inst.write(f':MEASure:DELTatime {res}2, {res}2')
        elif chan == 10:
            self.inst.write(f':MEASure:DELTatime:DEFine {edge_1},{num_1},{pos_1},{edge_2},{num_2},{pos_2}')
            self.inst.write(f':MEASure:DELTatime {res}3, {res}3')
        else:
            pass

    # def tHO(self, edge_1, num_1, pos_1, edge_2, num_2, pos_2, chan_start, chan_stop):
    #     self.inst.write(f':MEASure:DELTatime:DEFine {edge_1},{num_1},{pos_1},{edge_2},{num_2},{pos_2}')
    #     self.inst.write(f':MEASure:DELTatime CHANnel{chan_start}, CHANnel{chan_stop}')

    def run(self):
        self.inst.write(':RUN')

    def stop(self):
        self.inst.write(':STOP')

    def single(self):
        self.inst.write(':SINGLE')

    def autoscale(self):
        self.inst.write(':AUToscale')

    def default(self):
        self.inst.write(':SYSTem:PRESet DEFault')

    def trig_type(self):
        res= self.inst.query(f':TRIGger:SWEep?')
        if res == 'AUTO\n':
            self.inst.write(':TRIGger:SWEep TRIGgered')
        else:
            self.inst.write(':TRIGger:SWEep AUTO')
              
    def delete_item(self):
        tuple_marker = (boolvar_marker_1, boolvar_marker_2, boolvar_marker_3, boolvar_marker_4,
                        # boolvar_marker_5, boolvar_marker_6, boolvar_marker_7, boolvar_marker_8
                        )
        for i, boolvar in enumerate(tuple_marker):
            if boolvar.get():
                self.inst.write(f'MEASurement{i+1}:CLEar')

    def add_marker(self):
        tuple_marker = (boolvar_marker_1, boolvar_marker_2, boolvar_marker_3, boolvar_marker_4,
                        # boolvar_marker_5, boolvar_marker_6, boolvar_marker_7, boolvar_marker_8
                        )
    
        for i, boolvar in enumerate(tuple_marker):
            self.inst.write(f':MARKer:MEASurement:MEASurement MEASurement{i+1},OFF')

        for i, boolvar in enumerate(tuple_marker):
            if boolvar.get():
                self.inst.write(f':MARKer:MEASurement:MEASurement MEASurement{i+1},ON')

    def add_label(self, chan, label):
        res= self.judge_chan_wme(chan= chan)
        if label == '':
            self.inst.write(f':DISPlay:LABel OFF')
        else:
            self.inst.write(f':DISPlay:LABel ON')
            self.inst.write(f':{res}{chan}:LABel "{label}"')

    def load_wmemory(self, chan, folder, wme_name):
        self.inst.write(f':WMEMory:TIETimebase 1')
        self.inst.write(f':DISPlay:SCOLor WMEMory1,17,100,100')
        self.inst.write(f':DISPlay:SCOLor WMEMory2,38,100,84')
        self.inst.write(f':DISPlay:SCOLor WMEMory3,60,80,100')
        self.inst.write(f':DISK:LOAD "C:/Users/Administrator/Desktop/{folder}/{wme_name}.h5",WMEMory{chan},OFF')
    
    def clear_wmemory(self, chan, string):
        self.inst.write(f':WMEMory{chan}:CLEar')
        string.set('')

    def save_waveform(self, folder, image_name):
        # self.inst.write(f'GHC? "{image_name}.png", D')
        # image_binary_data = self.inst.read_raw()
        # img = open(
        #     rf'{folder}\{image_name}.png', 'wb'
        # )
        # img.write(image_binary_data[7:])
        # img.close()

        self.inst.write(f':DISK:SAVE:IMAGe "C:/Users/Administrator/Desktop/{folder}/{image_name}",PNG,SCReen,OFF,NORMal,OFF')

    def save_wmemory(self, chan, folder, wme_name):
        # self.inst.write(f'GHC? "{image_name}.png", D')
        # image_binary_data = self.inst.read_raw()
        # img = open(
        #     rf'{folder}\{image_name}.png', 'wb'
        # )
        # img.write(image_binary_data[7:])
        # img.close()

        self.inst.write(f':DISK:SAVE:WAVeform CHANnel{chan},"C:/Users/Administrator/Desktop/{folder}/{wme_name}",H5,OFF')

    def judge_chan_wme(self, chan):
        for i in range(1, 4):
            chan_res= self.inst.query(f':CHANnel{i}:DISPlay?')
            wme_res= self.inst.query(f':WMEMory{i}:DISPlay?')

            if chan_res == '1\n' and not wme_res == '1\n':
                return 'CHANnel'
            elif not chan_res == '1\n' and wme_res == '1\n':
                return 'WMEMory'
            # else:
            #     continue

def clear(string):
    string.set('')

def close_window():
    if messagebox.askyesno('Message', 'Exit?'):
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read( os.path.join(os.path.dirname(__file__), 'InitialConfiguration_mxr_tool.ini'), encoding='utf-8',)
        
        config.set('Scale_Offset_Config', 'VoltScale', str_volt_scale.get())
        config.set('Scale_Offset_Config', 'VoltOffset', str_volt_offset.get())
        config.set('Scale_Offset_Config', 'TimebaseScale', str_time_scale.get())
        config.set('Scale_Offset_Config', 'TimebaseOffset', str_time_offset.get())
        config.set('Scale_Offset_Config', 'TriggerLevel', str_trigger_level.get())
        config.set('Scale_Offset_Config', 'TriggerChan', str_trigger_chan.get())
        
        config.set('Delta_Setup_Config', 'DeltaStartEdge', start_rf.get())
        config.set('Delta_Setup_Config', 'DeltaStartNum', start_num.get())
        config.set('Delta_Setup_Config', 'DeltaStartPosition', start_pos.get())
        config.set('Delta_Setup_Config', 'DeltaStopEdge', stop_rf.get())
        config.set('Delta_Setup_Config', 'DeltaStopNum', stop_num.get())
        config.set('Delta_Setup_Config', 'DeltaStopPosition', stop_pos.get())

        config.set('Threshold_Setup_Config', 'GeneralTop', str_gen_top.get())
        config.set('Threshold_Setup_Config', 'GeneralMiddle', str_gen_mid.get())
        config.set('Threshold_Setup_Config', 'GeneralBase', str_gen_base.get())
        config.set('Threshold_Setup_Config', 'RFTop', str_rf_top.get())
        config.set('Threshold_Setup_Config', 'RFBase', str_rf_base.get())

        config.set('Lable_Setup_Config', 'ChanLabel1', str_label_1.get())
        config.set('Lable_Setup_Config', 'ChanLabel2', str_label_2.get())
        config.set('Lable_Setup_Config', 'ChanLabel3', str_label_3.get())

        config.set('Save_Setup_Config', 'SaveImgFolder', str_image_folder.get())
        config.set('Save_Setup_Config', 'SaveImgName', str_image.get())
        config.set('Save_Setup_Config', 'SaveWMeFolder', str_WMe_folder.get())
        config.set('Save_Setup_Config', 'SaveWMeName', str_WMe.get())

        config.set('Load_WMemory_Setup_Config', 'LoadWMe1', str_WMe1.get())
        config.set('Load_WMemory_Setup_Config', 'LoadWMe2', str_WMe2.get())
        config.set('Load_WMemory_Setup_Config', 'LoadWMe3', str_WMe3.get())
        
        config.write(open(os.path.join(os.path.dirname(__file__), 'InitialConfiguration_mxr_tool.ini'), 'w'))

        # formatted_time= self.current_time()
        # print(f'\n{formatted_time} [GUI Message] Window Closed.')
        window.destroy()




if __name__ == '__main__':
    mxr= MXR()

    # folder_name= fr'Avatar/Alice/POC/08_RGMII/U8 to U48/write'

    window = tk.Tk()
    window.title('MXR Button')
    window.geometry('1265x785+2+2')

    label_frame_meas_item= tk.LabelFrame(window, text= 'Measurement')
    label_frame_meas_item.grid(row= 0, column= 0, padx= 5, pady= 5, columnspan= 2, sticky= 'nsew')

    b_freq = tk.Button(label_frame_meas_item, text='Frequency', width= 20, height= 2, command= lambda: mxr.freq(chan= int_ch.get()))
    b_freq.grid(row= 0, column= 0, padx= 5, pady= 5)

    b_period = tk.Button(label_frame_meas_item, text='Period', width= 20, height= 2, command= lambda: mxr.period(chan= int_ch.get()))
    b_period.grid(row= 0, column= 1, padx= 5, pady= 5)

    b_dutycycle = tk.Button(label_frame_meas_item, text='Duty Cycle', width= 20, height= 2, command= lambda: mxr.dutycycle(chan= int_ch.get()))
    b_dutycycle.grid(row= 0, column= 2, padx= 5, pady= 5)

    b_tSU = tk.Button(label_frame_meas_item, text='Delta Time', width= 20, height= 2, command= lambda: mxr.tSU_tHO(edge_1= start_rf.get(), num_1= start_num.get(), pos_1= start_pos.get(), edge_2= stop_rf.get(), num_2= stop_num.get(), pos_2= stop_pos.get(), chan= int_ch.get()))
    b_tSU.grid(row= 0, column= 3, padx= 5, pady= 5)

    b_tH = tk.Button(label_frame_meas_item, text='tH', width= 20, height= 2, command= lambda: mxr.tH(chan= int_ch.get()))
    b_tH.grid(row= 1, column= 0, padx= 5, pady= 5)

    b_tL = tk.Button(label_frame_meas_item, text='tL', width= 20, height= 2, command= lambda: mxr.tL(chan= int_ch.get()))
    b_tL.grid(row= 1, column= 1, padx= 5, pady= 5)

    b_tR = tk.Button(label_frame_meas_item, text='tR', width= 20, height= 2, command= lambda: mxr.tR(chan= int_ch.get()))
    b_tR.grid(row= 1, column= 2, padx= 5, pady= 5)

    b_tF= tk.Button(label_frame_meas_item, text='tF', width= 20, height= 2, command= lambda: mxr.tF(chan= int_ch.get()))
    b_tF.grid(row= 1, column= 3, padx= 5, pady= 5)

    b_VIH = tk.Button(label_frame_meas_item, text='VIH', width= 20, height= 2, command= lambda: mxr.VIH(chan= int_ch.get()))
    b_VIH.grid(row= 2, column= 0, padx= 5, pady= 5)

    b_VIL= tk.Button(label_frame_meas_item, text='VIL', width= 20, height= 2, command= lambda: mxr.VIL(chan= int_ch.get()))
    b_VIL.grid(row= 2, column= 1, padx= 5, pady= 5)

    b_slewrate_tR = tk.Button(label_frame_meas_item, text='Slew Rate tR', width= 20, height= 2, command= lambda: mxr.slewrate(chan= int_ch.get(), direction= 'RISing'))
    b_slewrate_tR.grid(row= 2, column= 2, padx= 5, pady= 5)

    b_slewrate_tF = tk.Button(label_frame_meas_item, text='Slew Rate tF', width= 20, height= 2, command= lambda: mxr.slewrate(chan= int_ch.get(), direction= 'FALLing'))
    b_slewrate_tF.grid(row= 2, column= 3, padx= 5, pady= 5)

    # b_tHO = tk.Button(window, text='tHO', width= 20, height= 5, command= lambda: mxr.tSU_tHO(edge_1= start_rf.get(), num_1= start_num.get(), pos_1= start_pos.get(), edge_2= stop_rf.get(), num_2= stop_num.get(), pos_2= stop_pos.get(), chan= int_ch.get()))
    # b_tHO.grid(row= 2, column= 3, padx= 5, pady= 5)



    label_frame_scale= tk.LabelFrame(window, text= 'Scale / Offset')
    label_frame_scale.grid(row= 1, column= 0, padx= 5, pady= 5, sticky= 'nsew')

    l_volt_scale = tk.Label(label_frame_scale, text= 'Voltage Scale (V)')
    l_volt_scale.grid(row= 0, column= 0, padx= 5, pady= 5) 

    str_volt_scale = tk.StringVar()
    e_volt_scale = tk.Entry(label_frame_scale, width= 7, textvariable= str_volt_scale)
    e_volt_scale.grid(row= 0, column= 1, padx= 5, pady= 5)

    l_volt_offset = tk.Label(label_frame_scale, text= 'Voltage Offset (V)')
    l_volt_offset.grid(row= 1, column= 0, padx= 5, pady= 5) 

    str_volt_offset = tk.StringVar()
    e_volt_offset = tk.Entry(label_frame_scale, width= 7, textvariable= str_volt_offset)
    e_volt_offset.grid(row= 1, column= 1, padx= 5, pady= 5)
    str_volt_offset.set('0.9')

    b_volt_scale = tk.Button(label_frame_scale, text= 'Volt Check', width= 10, height= 1, command= lambda: mxr.volt_check(scale= str_volt_scale.get(), offset= str_volt_offset.get()))
    b_volt_scale.grid(row= 2, column= 0, padx= 5, pady= 5, sticky= 'e')

    l_trigger_level = tk.Label(label_frame_scale, text= 'Trigger level (V)')
    l_trigger_level.grid(row= 3, column= 0, padx= 5, pady= 5) 

    str_trigger_level = tk.StringVar()
    e_trigger_level = tk.Entry(label_frame_scale, width= 7, textvariable= str_trigger_level)
    e_trigger_level.grid(row= 3, column= 1, padx= 5, pady= 5)
    # str_trigger_level.set('1E+0')

    l_trigger_chan = tk.Label(label_frame_scale, text= 'Trigger Chan')
    l_trigger_chan.grid(row= 4, column= 0, padx= 5, pady= 5) 

    str_trigger_chan = tk.StringVar()
    e_trigger_chan = tk.Entry(label_frame_scale, width= 7, textvariable= str_trigger_chan)
    e_trigger_chan.grid(row= 4, column= 1, padx= 5, pady= 5)
    # str_trigger_chan.set('2')

    b_str_trigger_check = tk.Button(label_frame_scale, text= 'Trig Check', width= 10, height= 1, command= lambda: mxr.trig_check(chan= str_trigger_chan.get(), level= str_trigger_level.get()))
    b_str_trigger_check.grid(row= 4, column= 2, padx= 5, pady= 5)

    l_time_scale = tk.Label(label_frame_scale, text= 'Timebase Scale (sec)')
    l_time_scale.grid(row= 0, column= 2, padx= 5, pady= 5) 

    str_time_scale = tk.StringVar()
    e_time_scale = tk.Entry(label_frame_scale, width= 7, textvariable= str_time_scale)
    e_time_scale.grid(row= 0, column= 3, padx= 5, pady= 5)
    # str_time_scale.set('50E-6')

    l_time_offset = tk.Label(label_frame_scale, text= 'Timebase Offset (sec)')
    l_time_offset.grid(row= 1, column= 2, padx= 5, pady= 5) 

    str_time_offset = tk.StringVar()
    e_time_offset = tk.Entry(label_frame_scale, width= 7, textvariable= str_time_offset)
    e_time_offset.grid(row= 1, column= 3, padx= 5, pady= 5)
    str_time_offset.set('0E-6')

    b_time_check = tk.Button(label_frame_scale, text= 'Timebase Check', height= 1, command= lambda: mxr.timebase_check(scale= str_time_scale.get(), position= str_time_offset.get()))
    b_time_check.grid(row= 2, column= 2, padx= 5, pady= 5)



    label_frame_thres= tk.LabelFrame(window, text= 'Threshold')
    label_frame_thres.grid(row= 2, column= 0, padx= 5, pady= 5, columnspan= 2, rowspan= 3, sticky= 'nsew')

    int_gen_thres = tk.IntVar()    
    rb_gen_threshold_1= tk.Radiobutton(label_frame_thres, text= 'Gen Thres 10%~90%', variable= int_gen_thres, value= 1)
    rb_gen_threshold_1.grid(row= 0, column= 0, padx= 5, pady= 5)

    rb_gen_threshold_2= tk.Radiobutton(label_frame_thres, text= 'Gen Thres 20%~80%', variable= int_gen_thres, value= 2)
    rb_gen_threshold_2.grid(row= 1, column= 0, padx= 5, pady= 5) 

    rb_gen_threshold_3= tk.Radiobutton(label_frame_thres, text= 'Gen Thres 30%~70%', variable= int_gen_thres, value= 3)
    rb_gen_threshold_3.grid(row= 2, column= 0, padx= 5, pady= 5) 

    rb_gen_threshold_4= tk.Radiobutton(label_frame_thres, text= 'Gen Thres Top (V)', variable= int_gen_thres, value= 4)
    rb_gen_threshold_4.grid(row= 3, column= 0, padx= 5, pady= 5) 
    rb_gen_threshold_4.select()

    str_gen_top = tk.StringVar()
    e_gen_top = tk.Entry(label_frame_thres, width= 10, textvariable= str_gen_top)
    e_gen_top.grid(row= 3, column= 1, sticky= 'w')
    # str_gen_top.set('1.26')

    l_gen_threshold_4= tk.Label(label_frame_thres, text= '            Gen Thres Middle (V)')
    l_gen_threshold_4.grid(row= 4, column= 0, padx= 5, pady= 5) 

    str_gen_mid = tk.StringVar()
    e_gen_mid = tk.Entry(label_frame_thres, width= 10, textvariable= str_gen_mid)
    e_gen_mid.grid(row= 4, column= 1, sticky= 'w')
    # str_gen_mid.set('0.9')

    l_gen_threshold_5= tk.Label(label_frame_thres, text= '        Gen Thres Base (V)')
    l_gen_threshold_5.grid(row= 5, column= 0, padx= 5, pady= 5) 

    str_gen_base = tk.StringVar()
    e_gen_base = tk.Entry(label_frame_thres, width= 10, textvariable= str_gen_base)
    e_gen_base.grid(row= 5, column= 1, sticky= 'w')
    # str_gen_base.set('0.54')

    b_gen_check = tk.Button(label_frame_thres, text= 'Gen Thres Check', command= lambda: mxr.gen_threshold(g_top= e_gen_top.get(), g_middle= e_gen_mid.get(), g_base= e_gen_base.get()))
    b_gen_check.grid(row= 0, column= 1, padx= 5, pady= 5, sticky= 'e')


    int_rf_thres = tk.IntVar()    
    rb_rf_threshold_1= tk.Radiobutton(label_frame_thres, text= 'tRtF Thres 10%~90%', variable= int_rf_thres, value= 1)
    rb_rf_threshold_1.grid(row= 0, column= 2, padx= 5, pady= 5)

    rb_rf_threshold_2= tk.Radiobutton(label_frame_thres, text= 'tRtF Thres 20%~80%', variable= int_rf_thres, value= 2)
    rb_rf_threshold_2.grid(row= 1, column= 2, padx= 5, pady= 5) 

    rb_rf_threshold_3= tk.Radiobutton(label_frame_thres, text= 'tRtF Thres 30%~70%', variable= int_rf_thres, value= 3)
    rb_rf_threshold_3.grid(row= 2, column= 2, padx= 5, pady= 5) 

    rb_rf_threshold_4= tk.Radiobutton(label_frame_thres, text= 'tRtF Thres Top (V)', variable= int_rf_thres, value= 4)
    rb_rf_threshold_4.grid(row= 3, column= 2, padx= 5, pady= 5) 
    rb_rf_threshold_4.select()

    l_rf_threshold_4= tk.Label(label_frame_thres, text= '       tRtF Thres Base (V)')
    l_rf_threshold_4.grid(row= 4, column= 2, padx= 5, pady= 5) 
    
    str_rf_top = tk.StringVar()
    e_rf_top = tk.Entry(label_frame_thres, width= 10, textvariable= str_rf_top)
    e_rf_top.grid(row= 3, column= 3, sticky= 'w')
    # str_rf_top.set('1.26')

    str_rf_base = tk.StringVar()
    e_rf_base = tk.Entry(label_frame_thres, width= 10, textvariable= str_rf_base)
    e_rf_base.grid(row= 4, column= 3, sticky= 'w')
    str_rf_base.set('0.54')

    b_rf_check = tk.Button(label_frame_thres, text= 'RF Thres Check', command= lambda: mxr.RF_threshold(rf_top= e_rf_top.get(), rf_base= e_rf_base.get()))
    b_rf_check.grid(row= 0, column= 3, padx= 5, pady= 5, sticky= 'e')




    label_frame_label= tk.LabelFrame(window, text= 'Label')
    label_frame_label.grid(row= 5, column= 0, padx= 5, pady= 5, columnspan= 2, sticky= 'nsew')

    # l_blank = tk.Label(text= '')
    # l_blank.grid(row= 8, column= 0, padx= 5, pady= 5)

    str_label_1 = tk.StringVar()
    e_label_1 = tk.Entry(label_frame_label, width= 50, textvariable= str_label_1)
    e_label_1.grid(row= 0, column= 0, padx= 5, pady= 5, columnspan= 2, sticky= 'nsew')

    b_lable1 = tk.Button(label_frame_label, text= 'Chan1_label', command= lambda: mxr.add_label(chan= 1, label= str_label_1.get().rstrip('\n')))
    b_lable1.grid(row= 0, column= 2, padx= 5, pady= 5)

    b_clear1 = tk.Button(label_frame_label, text= 'Clear', command= lambda: clear(string= str_label_1))
    b_clear1.grid(row= 0, column= 3, padx= 5, pady= 5)

    str_label_2 = tk.StringVar()
    e_label_2 = tk.Entry(label_frame_label, width= 50, textvariable= str_label_2)
    e_label_2.grid(row= 1, column= 0, padx= 5, pady= 5, columnspan= 2)

    b_lable2 = tk.Button(label_frame_label, text= 'Chan2_label', command= lambda: mxr.add_label(chan= 2, label= (str_label_2.get().rstrip('\n'))))
    b_lable2.grid(row= 1, column= 2, padx= 5, pady= 5)

    b_clear2 = tk.Button(label_frame_label, text= 'Clear', command= lambda: clear(string= str_label_2))
    b_clear2.grid(row= 1, column= 3, padx= 5, pady= 5)

    str_label_3 = tk.StringVar()
    e_label_3 = tk.Entry(label_frame_label, width= 50, textvariable= str_label_3)
    e_label_3.grid(row= 2, column= 0, padx= 5, pady= 5, columnspan= 2)

    b_lable3 = tk.Button(label_frame_label, text= 'Chan3_label', command= lambda: mxr.add_label(chan= 3, label= (str_label_3.get().rstrip('\n'))))
    b_lable3.grid(row= 2, column= 2, padx= 5, pady= 5)

    b_clear3 = tk.Button(label_frame_label, text= 'Clear', command= lambda: clear(string= str_label_3))
    b_clear3.grid(row= 2, column= 3, padx= 5, pady= 5)


    # l_blank = tk.Label(window, text='', width= 10)
    # l_blank.grid(row= 0, column= 1, padx= 5, pady= 5, columnspan= 2)



    label_frame_control= tk.LabelFrame(window, text= 'Control')
    label_frame_control.grid(row= 0, column= 2, padx= 5, pady= 5, sticky= 'nsew')

    b_run = tk.Button(label_frame_control, text='RUN', width= 20, height= 2, command= lambda: mxr.run())
    b_run.grid(row= 0, column= 0, padx= 5, pady= 5, rowspan= 2)

    b_stop = tk.Button(label_frame_control, text='STOP', width= 20, height= 2, command= lambda: mxr.stop())
    b_stop.grid(row= 0, column= 1, padx= 5, pady= 5, rowspan= 2)

    b_single = tk.Button(label_frame_control, text='SINGLE', width= 20, height= 2, command= lambda: mxr.single())
    b_single.grid(row= 0, column= 2, padx= 5, pady= 5, rowspan= 2)

    b_autoscale = tk.Button(label_frame_control, text='Auto Scale', width= 20, height= 2, command= lambda: mxr.autoscale())
    b_autoscale.grid(row= 2, column= 0, padx= 5, pady= 5, rowspan= 2)

    b_default = tk.Button(label_frame_control, text='Default', width= 20, height= 2, command= lambda: mxr.default())
    b_default.grid(row= 2, column= 1, padx= 5, pady= 5, rowspan= 2)

    # b_trigger = tk.Button(label_frame_control, text='Trigger Type', width= 20, height= 2, command= lambda: mxr.trig_type())
    # b_trigger.grid(row= 2, column= 2, padx= 5, pady= 5, rowspan= 2)
    
    b_del = tk.Button(label_frame_control, text='Delete item', width= 20, height= 2, command= lambda: mxr.delete_item())
    b_del.grid(row= 4, column= 0, padx= 5, pady= 5, rowspan= 2)

    b_marker = tk.Button(label_frame_control, text='Add Marker', width= 20, height= 2, command= lambda: mxr.add_marker())
    b_marker.grid(row= 4, column= 1, padx= 5, pady= 5, rowspan= 2)

    b_trigger = tk.Button(label_frame_control, text='Trigger Type', width= 20, height= 2, command= lambda: mxr.trig_type())
    b_trigger.grid(row= 4, column= 2, padx= 5, pady= 5, rowspan= 2)

    boolvar_marker_1 = tk.BooleanVar()    
    cb_marker_1= tk.Checkbutton(label_frame_control, text= 'Meas1', variable= boolvar_marker_1)
    cb_marker_1.grid(row= 2, column= 3, padx= 5) 

    boolvar_marker_2 = tk.BooleanVar()    
    cb_marker_2= tk.Checkbutton(label_frame_control, text= 'Meas2', variable= boolvar_marker_2)
    cb_marker_2.grid(row= 3, column= 3, padx= 5) 

    boolvar_marker_3 = tk.BooleanVar()    
    cb_marker_3= tk.Checkbutton(label_frame_control, text= 'Meas3', variable= boolvar_marker_3)
    cb_marker_3.grid(row= 4, column= 3, padx= 5) 

    boolvar_marker_4 = tk.BooleanVar()    
    cb_marker_4= tk.Checkbutton(label_frame_control, text= 'Meas4', variable= boolvar_marker_4)
    cb_marker_4.grid(row= 5, column= 3, padx= 5) 

    # boolvar_marker_5 = tk.BooleanVar()    
    # cb_marker_5= tk.Checkbutton(window, text= 'Meas5', variable= boolvar_marker_5)
    # cb_marker_5.grid(row= 8, column= 11, padx= 5, pady= 5) 

    # boolvar_marker_6 = tk.BooleanVar()    
    # cb_marker_6= tk.Checkbutton(window, text= 'Meas6', variable= boolvar_marker_6)
    # cb_marker_6.grid(row= 9, column= 11, padx= 5, pady= 5) 

    # boolvar_marker_7 = tk.BooleanVar()    
    # cb_marker_7= tk.Checkbutton(window, text= 'Meas7', variable= boolvar_marker_7)
    # cb_marker_7.grid(row= 10, column= 11, padx= 5, pady= 5) 

    # boolvar_marker_8 = tk.BooleanVar()    
    # cb_marker_8= tk.Checkbutton(window, text= 'Meas8', variable= boolvar_marker_8)
    # cb_marker_8.grid(row= 11, column= 11, padx= 5, pady= 5) 



    label_frame_chan= tk.LabelFrame(window, text= 'Channel')
    label_frame_chan.grid(row= 1, column= 2, padx= 5, pady= 5, rowspan= 3, sticky= 'nsew')

    b_Chan1 = tk.Button(label_frame_chan, text='Chan1', width= 20, height= 2, command= lambda: mxr.display_Chan(chan= 1))
    b_Chan1.grid(row= 0, column= 0, padx= 5, pady= 5)

    b_Chan2 = tk.Button(label_frame_chan, text='Chan2', width= 20, height= 2, command= lambda: mxr.display_Chan(chan= 2))
    b_Chan2.grid(row= 0, column= 1, padx= 5, pady= 5)

    b_Chan3 = tk.Button(label_frame_chan, text='Chan3', width= 20, height= 2, command= lambda: mxr.display_Chan(chan= 3))
    b_Chan3.grid(row= 0, column= 2, padx= 5, pady= 5)

    b_WMe1 = tk.Button(label_frame_chan, text='WMemory1', width= 20, height= 2, command= lambda: mxr.display_WMemory(chan= 1))
    b_WMe1.grid(row= 1, column= 0, padx= 5, pady= 5)

    b_WMe2 = tk.Button(label_frame_chan, text='WMemory2', width= 20, height= 2, command= lambda: mxr.display_WMemory(chan= 2))
    b_WMe2.grid(row= 1, column= 1, padx= 5, pady= 5)

    b_WMe3 = tk.Button(label_frame_chan, text='WMemory3', width= 20, height= 2, command= lambda: mxr.display_WMemory(chan= 3))
    b_WMe3.grid(row= 1, column= 2, padx= 5, pady= 5)

    int_ch = tk.IntVar()    
    rb_ch_1= tk.Radiobutton(label_frame_chan, text= 'Chan1 test', variable= int_ch, value= 1)
    rb_ch_1.grid(row= 2, column= 0, padx= 5, pady= 5)
    rb_ch_1.select()

    rb_ch_2= tk.Radiobutton(label_frame_chan, text= 'Chan2 test', variable= int_ch, value= 2)
    rb_ch_2.grid(row= 3, column= 0, padx= 5, pady= 5) 

    rb_ch_3= tk.Radiobutton(label_frame_chan, text= 'Chan3 test', variable= int_ch, value= 3)
    rb_ch_3.grid(row= 4, column= 0, padx= 5, pady= 5) 

    rb_ch_1_2= tk.Radiobutton(label_frame_chan, text= 'Chan1-Chan2 test', variable= int_ch, value= 4)
    rb_ch_1_2.grid(row= 2, column= 1, padx= 5, pady= 5) 

    rb_ch_2_1= tk.Radiobutton(label_frame_chan, text= 'Chan2-Chan1 test', variable= int_ch, value= 5)
    rb_ch_2_1.grid(row= 3, column= 1, padx= 5, pady= 5) 

    rb_ch_1_2= tk.Radiobutton(label_frame_chan, text= 'Chan1-Chan3 test', variable= int_ch, value= 6)
    rb_ch_1_2.grid(row= 4, column= 1, padx= 5, pady= 5) 

    rb_ch_2_1= tk.Radiobutton(label_frame_chan, text= 'Chan3-Chan1 test', variable= int_ch, value= 7)
    rb_ch_2_1.grid(row= 5, column= 1, padx= 5, pady= 5) 

    rb_ch_1_1= tk.Radiobutton(label_frame_chan, text= 'Chan1-Chan1 test', variable= int_ch, value= 8)
    rb_ch_1_1.grid(row= 2, column= 2, padx= 5, pady= 5) 

    rb_ch_2_2= tk.Radiobutton(label_frame_chan, text= 'Chan2-Chan2 test', variable= int_ch, value= 9)
    rb_ch_2_2.grid(row= 3, column= 2, padx= 5, pady= 5) 

    rb_ch_3_3= tk.Radiobutton(label_frame_chan, text= 'Chan3-Chan3 test', variable= int_ch, value= 10)
    rb_ch_3_3.grid(row= 4, column= 2, padx= 5, pady= 5) 


    label_frame_delta= tk.LabelFrame(window, text= 'Delta Setup')
    label_frame_delta.grid(row= 1, column= 1, padx= 5, pady= 5, sticky= 'nsew')

    l_start = tk.Label(label_frame_delta, text= 'Delta Start', background= 'yellow')
    l_start.grid(row= 0, column= 0, padx= 5, pady= 5)

    start_rf = tk.StringVar()
    cb_start_rf = ttk.Combobox(label_frame_delta, width= 15, textvariable= start_rf, values= ['RISING', 'FALLING'])
    cb_start_rf.grid(row= 1, column= 0, padx=5, pady= 5)

    start_num = tk.StringVar()
    cb_start_num = tk.Entry(label_frame_delta, width= 15, textvariable= start_num)
    cb_start_num.grid(row= 2, column= 0, padx=5, pady= 5)
    
    start_pos = tk.StringVar()
    cb_start_pos = ttk.Combobox(label_frame_delta, width= 15, textvariable= start_pos, values= ['UPPER', 'MIDDLE', 'LOWER'])
    cb_start_pos.grid(row= 3, column= 0, padx=5, pady= 5)


    l_stop = tk.Label(label_frame_delta, text= 'Delta Stop', background= 'yellow')
    l_stop.grid(row= 0, column= 1, padx= 5, pady= 5)

    stop_rf = tk.StringVar()
    cb_stop_rf = ttk.Combobox(label_frame_delta, width= 15, textvariable= stop_rf, values= ['RISING', 'FALLING'])
    cb_stop_rf.grid(row= 1, column= 1, padx=5, pady= 5)

    stop_num = tk.StringVar()
    cb_stop_num = tk.Entry(label_frame_delta, width= 15, textvariable= stop_num)
    cb_stop_num.grid(row= 2, column= 1, padx=5, pady= 5)
    
    stop_pos = tk.StringVar()
    cb_stop_pos = ttk.Combobox(label_frame_delta, width= 15, textvariable= stop_pos, values= ['UPPER', 'MIDDLE', 'LOWER'])
    cb_stop_pos.grid(row= 3, column= 1, padx=5, pady= 5)



    label_frame_save= tk.LabelFrame(window, text= 'Save')
    label_frame_save.grid(row= 4, column= 2, padx= 5, pady= 5, sticky= 'nsew')

    str_image_folder = tk.StringVar()
    e_image_folder = tk.Entry(label_frame_save, width= 50, textvariable= str_image_folder)
    e_image_folder.grid(row= 0, column= 0, padx= 5, pady= 5, 
                        # columnspan= 3
                        )
    # str_image_folder.set(f'{folder_name}')

    l_image_folder = tk.Label(label_frame_save, text= 'Waveform folder\n(填Desktop之後的資料夾路徑)')
    l_image_folder.grid(row=0, column= 1, padx= 5, pady= 5)
    
    str_image = tk.StringVar()
    e_image = tk.Entry(label_frame_save, width= 50, textvariable= str_image)
    e_image.grid(row= 1, column= 0, padx= 5, pady= 5, 
                #  columnspan= 3
                 )

    b_image_save = tk.Button(label_frame_save, text= 'Save Waveform', command= lambda: mxr.save_waveform(folder= str_image_folder.get(), image_name= str_image.get()))
    b_image_save.grid(row=1, column= 1, padx= 5, pady= 5)

    str_WMe_folder = tk.StringVar()
    e_WMe_folder = tk.Entry(label_frame_save, width= 50, textvariable= str_WMe_folder)
    e_WMe_folder.grid(row= 2, column= 0, padx= 5, pady= 5, 
                    #   columnspan= 3
                      )
    # str_WMe_folder.set(f'{folder_name}/waveform_files')

    l_WMe_folder = tk.Label(label_frame_save, text= 'WMemory folder\n(填Desktop之後的資料夾路徑)')
    l_WMe_folder.grid(row=2, column= 1, padx= 5, pady= 5)
    
    str_WMe = tk.StringVar()
    e_WMe = tk.Entry(label_frame_save, width= 50, textvariable= str_WMe)
    e_WMe.grid(row= 3, column= 0, padx= 5, pady= 5, 
            #    columnspan= 3
               )

    b_WMe_save = tk.Button(label_frame_save, text= 'Save WMemory', command= lambda: mxr.save_wmemory(chan= int_ch.get(), folder= str_WMe_folder.get(), wme_name= str_WMe.get()))
    b_WMe_save.grid(row=3, column= 1, padx= 5, pady= 5)


    label_frame_load_wme= tk.LabelFrame(window, text= 'Load WMemory')
    label_frame_load_wme.grid(row= 5, column= 2, padx= 5, pady= 5, sticky= 'nsew')

    str_WMe1 = tk.StringVar()
    e_WMe1 = tk.Entry(label_frame_load_wme, width= 50, textvariable= str_WMe1)
    e_WMe1.grid(row= 0, column= 0, padx= 5, pady= 5, 
            #    columnspan= 3
               )
    
    b_WMe1_load = tk.Button(label_frame_load_wme, text= 'load WMemory1', command= lambda: mxr.load_wmemory(chan= 1, folder= str_WMe_folder.get(), wme_name= str_WMe1.get()))
    b_WMe1_load.grid(row=0, column= 1, padx= 5, pady= 5)

    b_wme_clear1 = tk.Button(label_frame_load_wme, text= 'Clear', command= lambda: mxr.clear_wmemory(chan= 1, string= str_WMe1))
    b_wme_clear1.grid(row= 0, column= 2, padx= 5, pady= 5)

    str_WMe2 = tk.StringVar()
    e_WMe2 = tk.Entry(label_frame_load_wme, width= 50, textvariable= str_WMe2)
    e_WMe2.grid(row= 1, column= 0, padx= 5, pady= 5, 
            #    columnspan= 3
               )

    b_WMe2_load = tk.Button(label_frame_load_wme, text= 'load WMemory2', command= lambda: mxr.load_wmemory(chan= 2, folder= str_WMe_folder.get(), wme_name= str_WMe2.get()))
    b_WMe2_load.grid(row=1, column= 1, padx= 5, pady= 5)

    b_wme_clear2 = tk.Button(label_frame_load_wme, text= 'Clear', command= lambda: mxr.clear_wmemory(chan= 2, string= str_WMe2))
    b_wme_clear2.grid(row= 1, column= 2, padx= 5, pady= 5)

    str_WMe3 = tk.StringVar()
    e_WMe3 = tk.Entry(label_frame_load_wme, width= 50, textvariable= str_WMe3)
    e_WMe3.grid(row= 2, column= 0, padx= 5, pady= 5, 
            #    columnspan= 3
               )

    b_WMe3_load = tk.Button(label_frame_load_wme, text= 'load WMemory3', command= lambda: mxr.load_wmemory(chan= 3, folder= str_WMe_folder.get(), wme_name= str_WMe3.get()))
    b_WMe3_load.grid(row=2, column= 1, padx= 5, pady= 5)

    b_wme_clear3 = tk.Button(label_frame_load_wme, text= 'Clear', command= lambda: mxr.clear_wmemory(chan= 3, string= str_WMe3))
    b_wme_clear3.grid(row= 2, column= 2, padx= 5, pady= 5)

    initialize()

    window.protocol('WM_DELETE_WINDOW', close_window)

    window.mainloop()
 