from PyQt5.QtCore import QThread, pyqtSignal, QMutexLocker
from PyQt5.QtWidgets import *
import serial
import threading
import time
import socket
from aspects import timeit, log_calls, handle_exceptions

class Concentrator(QThread):
    #Signals definition to main UI
    conn_signal = pyqtSignal(bool)
    string1_signal = pyqtSignal(bool)
    string2_signal = pyqtSignal(bool)
    def __init__(self, queue_data_string_1, queue_data_string_2):
        super().__init__()
        self.parar = False # senyal per para la lectura
        self.llegir = True # senyal per llegir
        self.input_data_prev_1 = []
        self.input_data_error_1 = ['$GSTR','1','000000','00','00','0000',"-999",'1',"-999","-999",'2',"-999","-999",
                           '3',"-999","-999",'4',"-999","-999",'5',"-999","-999"]
        self.input_data_prev_2 = []
        self.input_data_error_2 = ['$GSTR','2','000000','00','00','0000',"-999",'1',"-999","-999",'2',"-999","-999",
                           '3',"-999","-999",'4',"-999","-999",'5',"-999","-999",'6',"-999","-999"]
        self.n_errors_list_1 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        self.n_errors_list_2 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        self.n_errors_1 = 0
        self.n_errors_2 = 0
        self.missing_1 = True           # Variable per controlar si s'ha rebut info del concentrador 1
        self.missing_2 = True           # Variable per controlar si s'ha rebut info del concentrador 2
        self.conectat = False
        self.queue_data_string_1 = queue_data_string_1
        self.queue_data_string_2 = queue_data_string_2
        self.data = []
    
    def run(self):
        while not self.parar:  
            self.conn_signal.emit(not self.parar)
            while not self.conectat and not self.parar:                                  
                self.configuracio()
                time.sleep(1)                         
            if self.llegir:        
                self.missing_1 = True
                self.missing_2 = True 
                self.data = []
            else:                                                   
                time.sleep(1)
                continue
            while self.llegir and (self.missing_1 or self.missing_2) and not self.parar:   #if
                self.read_concentrator()
                time.sleep(1)
            if self.missing_1 and self.missing_2:
                self.string1_signal.emit(not self.missing_1)
                self.string2_signal.emit(not self.missing_2)
                if len(self.input_data_prev_1) > 0 and self.n_errors_1 < 6:
                    self.data = self.tractar_dades(self.input_data_prev_1, 1)
                    self.n_errors_1 = self.n_errors_1 + 1
                else:
                    self.data = self.tractar_dades(self.input_data_error_1, 1)
                if len(self.input_data_prev_2) > 0 and self.n_errors_2 < 6:
                    self.data = self.data + self.tractar_dades(self.input_data_prev_2, 2)
                    self.n_errors_2 = self.n_errors_2 + 1
                else:
                    self.data = self.data + self.tractar_dades(self.input_data_error_2, 2)
                temps_lectura = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime())
                self.data.append({"variable": "gateway_error", "value": '01', "timestamp": temps_lectura})
                return "No data received. Filling with previous data"
            if self.missing_1 and not self.missing_2:
                self.string1_signal.emit(not self.missing_1)
                if len(self.input_data_prev_1) > 0 and self.n_errors_1 < 6:
                    self.data = self.data + self.tractar_dades(self.input_data_prev_1, 1)
                    self.n_errors_1 = self.n_errors_1 + 1
                else:
                    self.data = self.data + self.tractar_dades(self.input_data_error_1, 1)
                temps_lectura = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime())
                self.data.append({"variable": "gateway_error", "value": '01', "timestamp": temps_lectura})
                self.n_errors_2 = 0
                return "No data from concentrador #1. filling with previous data"
            if self.missing_2 and not self.missing_1:
                self.string2_signal.emit(not self.missing_2)
                if len(self.input_data_prev_2) > 0 and self.n_errors_2 < 6:
                    self.data = self.data + self.tractar_dades(self.input_data_prev_2, 2)
                    self.n_errors_2 = self.n_errors_2 + 1
                else:
                    self.data = self.data + self.tractar_dades(self.input_data_error_2, 2)
                temps_lectura = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime())
                self.data.append({"variable": "gateway_error", "value": '01', "timestamp": temps_lectura})
                self.n_errors_1 = 0
                return "No data from concentrador #2. filling with previous data"
            if not self.missing_1 and not self.missing_2:
                self.string1_signal.emit(not self.missing_1)
                self.string2_signal.emit(not self.missing_2)
                self.n_errors_1 = 0
                self.n_errors_2 = 0
                return "Data received"
            time.sleep(1)
        self.conn_signal.emit(not self.parar)
    @timeit
    @log_calls
    @handle_exceptions
    def configuracio(self):                                                         # Configuració de la connexió
        try:
            self.concentradors = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.concentradors.bind(('0.0.0.0', 1573))  # Escuchar en el puerto 55555 + 1570
        except Exception:
            self.conectat = False
            return "No connection"
        else:
            self.conectat = True
            return "Connected"
    @timeit
    @log_calls
    def read_concentrator(self):                                                            # Petició i lectura dels concentradors
        if not self.conectat:
            self.configuracio()
        try:
            self.concentradors.settimeout(5)
            data, _ = self.concentradors.recvfrom(1024)
            response = data.decode().strip()
            input_data = response.split(',')
        except Exception as ex: 
            if not self.conectat:
                return "No connection"
        else:
            if input_data[1]=='1':
                if len(input_data) == 22:                                           # Si s'han rebut dades i el format es correcte passem les dades al format que toca
                    data_individual = self.tractar_dades(input_data, 1)
                    self.input_data_prev_1 = input_data 
                    print(data_individual)
                    self.queue_data_string_1.put(data_individual) #item
                    for item in data_individual:
                        self.data.append(item)
                    return "String #1 received"
                else:
                    return "String #1 no received"
            elif input_data[1]=='2':
                if len(input_data) == 25:   
                    data_individual = self.tractar_dades(input_data, 2)
                    self.input_data_prev_2 = input_data 
                    self.queue_data_string_2.put(data_individual) 
                    for item in data_individual:
                        self.data.append(item)
                    return "String #2 received"
                else:
                    return "String #2 no received"
            else:
                return ("Incorrect Data")
    @timeit
    @log_calls
    def tractar_dades(self, idata, n):
        data_individual = []
        index_dades = ["$GSTR","number of string","utc time","day","month","year","string current",
                       "panel 1 id","panel 1 voltage","panel 1 temperature","panel 2 id","panel 2 voltage","panel 2 temperature",
                       "panel 3 id","panel 3 voltage","panel 3 temperature","panel 4 id","panel 4 voltage","panel 4 temperature",
                       "panel 5 id","panel 5 voltage","panel 5 temperature","panel 6 id","panel 6 voltage","panel 6 temperature"]
        int_min = 0
        int_max = 15
        volt_min = 0
        volt_max = 55
        temp_min = 0
        temp_max = 90
        error_data = False
                    
        if n == 1:
            if "-999" not in idata:
                for ind, elem in enumerate(idata):                              # Mirem si falten dades o si estan fora de rang
                    if elem == '':
                        error_data = True
                        if len(self.input_data_prev_1) > 0 and self.n_errors_list_1[ind] < 6:
                            idata[ind] = self.input_data_prev_1[ind]        # Omplim amb dades anteriors
                            self.n_errors_list_1[ind] += 1
                        else:
                            idata[ind] = "-999"
                    else:
                        if ind == 6:
                            if not(int_min <= float(elem) <= int_max):
                                error_data = True
                                if len(self.input_data_prev_1) > 0 and self.n_errors_list_1[ind] < 6:
                                    idata[ind] = self.input_data_prev_1[ind]        # Omplim amb dades anteriors
                                    self.n_errors_list_1[ind] += 1
                                else:
                                    idata[ind] = "-999"
                            else:
                                self.n_errors_list_1[ind] = 0
                        elif ind in (8,11,14,17,20):
                            if not(volt_min <= float(elem) <= volt_max):
                                error_data = True
                                if len(self.input_data_prev_1) > 0 and self.n_errors_list_1[ind] < 6:
                                    idata[ind] = self.input_data_prev_1[ind]        # Omplim amb dades anteriors
                                    self.n_errors_list_1[ind] += 1
                                else:
                                    idata[ind] = "-999"
                            else:
                                self.n_errors_list_1[ind] = 0
                        elif ind in (9,12,15,18,21):
                            if not(temp_min <= float(elem) <= temp_max):
                                error_data = True
                                if len(self.input_data_prev_1) > 0 and self.n_errors_list_1[ind] < 6:
                                    idata[ind] = self.input_data_prev_1[ind]        # Omplim amb dades anteriors
                                    self.n_errors_list_1[ind] += 1
                                else:
                                    idata[ind] = "-999"
                            else:
                                self.n_errors_list_1[ind] = 0
        if n == 2:
            if "-999" not in idata:
                for ind, elem in enumerate(idata):                              # Mirem si falten dades o si estan fora de rang
                    if elem == '':
                        error_data = True
                        if len(self.input_data_prev_2) > 0 and self.n_errors_list_2[ind] < 6:
                            idata[ind] = self.input_data_prev_2[ind]        # Omplim amb dades anteriors
                            self.n_errors_list_2[ind] += 1
                        else:
                            idata[ind] = "-999"
                    else:
                        if ind == 6:
                            if not(int_min <= float(elem) <= int_max):
                                error_data = True
                                if len(self.input_data_prev_2) > 0 and self.n_errors_list_2[ind] < 6:
                                    idata[ind] = self.input_data_prev_2[ind]        # Omplim amb dades anteriors
                                    self.n_errors_list_2[ind] += 1
                                else:
                                    idata[ind] = "-999"
                            else:
                                self.n_errors_list_2[ind] = 0
                        elif ind in (8,11,14,17,20,23):
                            if not(volt_min <= float(elem) <= volt_max):
                                error_data = True
                                if len(self.input_data_prev_2) > 0 and self.n_errors_list_2[ind] < 6:
                                    idata[ind] = self.input_data_prev_2[ind]        # Omplim amb dades anteriors
                                    self.n_errors_list_2[ind] += 1
                                else:
                                    idata[ind] = "-999"
                            else:
                                self.n_errors_list_2[ind] = 0
                        elif ind in (9,12,15,18,21,24):
                            if not(temp_min <= float(elem) <= temp_max):
                                error_data = True
                                if len(self.input_data_prev_2) > 0 and self.n_errors_list_2[ind] < 6:
                                    idata[ind] = self.input_data_prev_2[ind]        # Omplim amb dades anteriors
                                    self.n_errors_list_2[ind] += 1
                                else:
                                    idata[ind] = "-999"
                            else:
                                self.n_errors_list_2[ind] = 0

        if error_data:
            temps_lectura = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime())
            data_individual.append({"variable": "gateway_error", "value": '01', "timestamp": temps_lectura})
    
            
        string_id, dia, mes, anys, string_current = idata[1], idata[3], idata[4], idata[5], idata[6]
        timestamp = anys + '-' + mes + '-' + dia + 'T' + idata[2][0:2] + ':' + idata[2][2:4] + ':' + idata[2][4:6]
        if timestamp == '0000-00-00T00:00:00':
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime())
        lectures_moduls = idata[7:]

        data_individual.append({"variable": "s" + string_id + "_current", "value": float(string_current), "timestamp": timestamp})

        if n==1:
            for idx in range(0, 13, 3):
                id_modul = lectures_moduls[idx]
                volt_modul = lectures_moduls[idx+1]
                temp_modul = lectures_moduls[idx+2]
                #data_individual.append({"variable": "p" + string_id + id_modul + "_voltage", "value": volt_modul, "timestamp": timestamp})
                #data_individual.append({"variable": "p" + string_id + id_modul + "_temperature", "value": temp_modul, "timestamp": timestamp})
                data_individual.append({"variable":  id_modul + "_voltage", "value": float(volt_modul), "timestamp": timestamp})
                data_individual.append({"variable":  id_modul + "_temperature", "value": float(temp_modul), "timestamp": timestamp})
        elif n==2:
            for idx in range(0, 16, 3):
                id_modul = lectures_moduls[idx]
                volt_modul = lectures_moduls[idx+1]
                temp_modul = lectures_moduls[idx+2]
                #data_individual.append({"variable": "p" + string_id + id_modul + "_voltage", "value": volt_modul, "timestamp": timestamp})
                #data_individual.append({"variable": "p" + string_id + id_modul + "_temperature", "value": temp_modul, "timestamp": timestamp})
                data_individual.append({"variable": id_modul + "_voltage", "value": float(volt_modul), "timestamp": timestamp})
                data_individual.append({"variable": id_modul + "_temperature", "value": float(temp_modul), "timestamp": timestamp})

        else:
            return "Data error"
        return data_individual
    def stop_thread(self):
        self.parar = True 
        self.llegir = False
        return "STOPPING CONCENTRADOR THREAD...."
        
