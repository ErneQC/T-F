from PyQt5.QtCore import QThread, pyqtSignal, QMutexLocker
from PyQt5.QtWidgets import *
import serial
import threading
import time
import logging
import socket
from timeit import timeit
class Curve_IV(QThread):
    #Signals definition to main UI
    curve_signal = pyqtSignal(bool)
    log_signal = pyqtSignal(str)  # Señal para enviar mensajes de log

    def __init__(self, queue_curve):
        super().__init__()
        self.parar = False # senyal per para la lectura
        self.llegir = True # senyal per llegir
        self.input_data_prev_1 = []
        self.input_data_error_1 = ['$GSTR','1','000000','00','00','0000',"-999",'1',"-999","-999",'2',"-999","-999",
                           '3',"-999","-999",'4',"-999","-999",'5',"-999","-999"]
        self.n_errors_list_1 = [0] * 3006
        self.n_errors_1 = 0
        self.missing_1 = True           # Variable per controlar si s'ha rebut info del concentrador 1
        self.conectat = False
        self.queue_curve = queue_curve
        self.data = []

        # Configuración del logger
        self.logger = logging.getLogger('CurveIVLogger')
        self.logger.setLevel(logging.DEBUG)
        # Archivo para logging
        file_handler = logging.FileHandler('logger.log')
        file_handler.setLevel(logging.DEBUG)
        # Consola para logging
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        # Formato para el logging
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def run(self):
        while not self.parar:  # Loop mientras no se cierra el programa
            self.curve_signal.emit(not self.parar)
            self.logger.info("Running IV-Curve thread...")
            print("Running IV-Curve thread...")
            while not self.conectat and not self.parar:                                       # Si no està connectat reintentem la connexió
                self.configuracio()
                time.sleep(1)                         
            if self.llegir:        #not                     # Si l'ordre de llegir no està activada esperem a que s'activi
                #self.llegir.wait()
                self.missing_1 = True
                self.data = []
            else:                                                   # Si ja s'han rebut les dades el programa espera una nova ordre de lectura
                time.sleep(1)
                continue
            while self.llegir and (self.missing_1) and not self.parar:   #if
                 # Bucle de lectura de dades, només es surt si es desactiva l'ordre de llegir, es reben totes les dades o si s'atura el programa
                self.read_iv_curve()
                time.sleep(1)
               # Mirem quines dades s'han rebut i omplim amb dades anteriors les que falten. Enviem error si ha fallat alguna lectura
            time.sleep(1)
        #fora del while
        self.curve_signal.emit(not self.parar)
        self.logger.info("STOPPED THREAD IV-CURVE!")
        print("STOPPED THREAD IV-CURVE!")
    @timeit
    def configuracio(self):                                                         # Configuració de la connexió
        try:
            self.concentradors = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.concentradors.bind(('0.0.0.0', 1560))  # Escuchar en el puerto 55555 + 1570
            self.logger.info("Connected to sensor Curve-IV")
        except Exception:
            print('No connection to sensor Curve-IV. Retrying...')
            self.logger.info('No connection to sensor Curve-IV. Retrying...')
            self.conectat = False
        else:
            self.conectat = True
    @timeit            
    def read_iv_curve(self):                                                            # Petició i lectura dels concentradors
        if not self.conectat:
            self.configuracio()
        try:
            self.concentradors.settimeout(5)
            data, _ = self.concentradors.recvfrom(18192)
            response = data.decode().strip()
            input_data = response.split(',')
        except Exception as ex: 
            if not self.conectat:
                print('No connection to sensor Curve-IV. Retrying...')
                self.logger.info('No connection to sensor Curve-IV. Retrying...')
                return
        else:
            if len(input_data) == 1205:                                           # Si s'han rebut dades i el format es correcte passem les dades al format que toca
                print("IV-Curve data received")
                self.logger.info("IV-Curve data received")
                data_individual = self.tractar_dades(input_data)
                self.input_data_prev_1 = input_data 
                self.queue_curve.put(data_individual) #item
            else:
                self.logger.info("No data received/incorrect data from sensor iv-sensor")
                print("No data received/incorrect data from sensor iv-sensor")
    def process_values(self, values, value_range):
        processed_values = []
        for i, val in enumerate(values):
            if val is not None and value_range[0] <= val <= value_range[1]:
                processed_values.append(val)
            else:
                prev_val = values[i - 1] if i > 0 else None
                next_val = values[i + 1] if i < len(values) - 1 else None
                if prev_val is not None and value_range[0] <= prev_val <= value_range[1] \
                        and next_val is not None and value_range[0] <= next_val <= value_range[1]:
                    corrected_val = (prev_val + next_val) / 2
                    processed_values.append(corrected_val)
                else:
                    processed_values.append(-999)  # Valor no corregible

        return processed_values   
    @timeit             
    def tractar_dades(self, idata):
        data_individual = []
        utc_time = idata[1][:-1]  # Extracting UTC time
        device_id = idata[2]  # Device ID
        
        # Indices de los datos de corriente y voltaje
        current_data_indices = range(4, 604)
        voltage_data_indices = range(605, 1205)

        # Rangos de valores para corriente y voltaje
        current_range = (0, 2.3)
        voltage_range = (0, 50)

        # Procesamiento de datos de corriente
        current_data = [float(idata[i]) if idata[i].strip() else None for i in current_data_indices]
        processed_current_data = self.process_values(current_data, current_range)

        # Procesamiento de datos de voltaje
        voltage_data = [float(idata[i]) if i < len(idata) and idata[i].strip() else None for i in voltage_data_indices]
        processed_voltage_data = self.process_values(voltage_data, voltage_range)
       
        # Crear la estructura curva_iv
        curva_iv = {
            "panel_id": device_id,
            "timestamp": utc_time,
            "data": {
                "current": processed_current_data,
                "voltage": processed_voltage_data
            }
        }


        data_individual.append(curva_iv)
        return data_individual
    def stop_thread(self):
        self.parar = True 
        print("STOPPING IV-CURVE THREAD....")
        self.logger.info("STOPPING IV-CURVE THREAD...")
        self.llegir = False
    def re_start_thread(self):
        self.parar = False
        self.llegir = True
        self.run()        