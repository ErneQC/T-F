from PyQt5.QtCore import QThread, pyqtSignal, QMutexLocker
from PyQt5.QtWidgets import *
import time
import socket
import logging
from umodbus import conf
from umodbus.client import tcp
from timerit import timeit
# Configuración del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Inversor(QThread):
    #Signals definition to main UI
    conn_signal = pyqtSignal(bool)
    inversor_stat_signal = pyqtSignal(bool)
    log_signal = pyqtSignal(str)
    
    def __init__(self, queue_data_inversor):
        super().__init__()
        conf.SIGNED_VALUES = True
        self.parar = False # senyal de parar
        self.llegir = True # senyal de llegir
        self.update_event = False  #update???
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime())
        self.data_inv_prev = []
        self.data_inv_error = [{'variable': 'inverter_ac_power_p1', 'value': "NaN", 'timestamp': timestamp},
                              {'variable': 'inverter_ac_current_p1', 'value': "NaN", 'timestamp': timestamp},
                              {'variable': 'inverter_ac_voltage_p1', 'value': "NaN", 'timestamp': timestamp},
                              {'variable': 'frequency', 'value': "NaN", 'timestamp': timestamp},
                              {'variable': 'inverter_dc_power', 'value': "NaN", 'timestamp': timestamp},
                              {'variable': 'inverter_dc_power_2', 'value': "NaN", 'timestamp': timestamp},
                              {'variable': 'inverter_dc_current', 'value': "NaN", 'timestamp': timestamp},
                              {'variable': 'inverter_dc_current_2', 'value': "NaN", 'timestamp': timestamp},
                              {'variable': 'inverter_dc_voltage', 'value': "NaN", 'timestamp': timestamp},
                              {'variable': 'inverter_dc_voltage_2', 'value': "NaN", 'timestamp': timestamp},
                              {'variable': 'inverter_temperature', 'value': "NaN", 'timestamp': timestamp},
                              {'variable': 'inverter_warnings', 'value': "NaN", 'timestamp': timestamp}]
        self.n_errors_inv = 0
        self.llista_rebuts = []
        self.queue_data_inversor = queue_data_inversor
        self.conectat = False
        self.data = []
        # Configuración del logger
        self.logger = logging.getLogger('CurveInversor')
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
        while not self.parar:
            self.conn_signal.emit(not self.parar)
            self.inversor_stat_signal.emit(self.conectat)
            while not self.conectat and not self.parar:
                self.configuracio()
                time.sleep(10)
            if self.llegir: #not
                self.data = []
                self.llista_rebuts = []
            else:
                time.sleep(1)
                continue
            
            while self.llegir and len(self.data) < 12 and not self.parar:
                self.read_inv()
                time.sleep(2)

            if len(self.data) == 12:
                self.data_inv_prev = self.data.copy()
                print('Inverter data received')
                self.logger.info('Inverter data received')
                self.n_errors_inv = 0
                #App.update_inversor_status(True)
            elif self.data == []:
                print('No inverter data received. Filling with previous data')
                self.logger.info('No inverter data received. Filling with previous data')
                if len(self.data_inv_prev) > 0 and self.n_errors_inv < 6:
                    self.data = self.data_inv_prev.copy()
                    temps_lectura = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime())
                    self.data.append({"variable": "gateway_error", "value": '00', "timestamp": temps_lectura})
                    self.n_errors_inv = self.n_errors_inv + 1
                else:
                    self.data = self.data_inv_error.copy()
                    temps_lectura = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime())
                    self.data.append({"variable": "gateway_error", "value": '00', "timestamp": temps_lectura})
            elif len(self.data) < 12:
                print('Some inverter data received. Filling the rest with previous data')
                self.logger.info('Some inverter data received. Filling the rest with previous data')
                if len(self.data_inv_prev) > 0 and self.n_errors_inv < 6:
                    self.n_errors_inv = self.n_errors_inv + 1
                    for valor in self.data_inv_prev:
                        if valor['variable'] not in self.llista_rebuts:
                            #self.queue_data_inversor.put(valor)
                            self.data.append(valor)
                else:
                    for valor in self.data_inv_error:
                        if valor['variable'] not in self.llista_rebuts:
                            #self.queue_data_inversor.put(valor)
                            self.data.append(valor)
            
            #fem put de la tota la data
            self.queue_data_inversor.put(self.data)
            time.sleep(60)
      
        #FORA DEL WHILE
        self.conn_signal.emit(not self.parar)
        print("STOPPED INVERSOR THREAD!")  
        self.logger.info( "STOPPED INVERSOR THREAD!")
    @timeit
    def configuracio(self):
        try:
            #self.sock_inv.close()
            self.sock_inv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_inv.settimeout(3)
            self.sock_inv.connect(("11.11.78.52", 502))  #52
            self.sock_inv.settimeout(0.1)
        except Exception:
            print('No connection to inverter. Retrying...')
            self.logger.info('No connection to inverter. Retrying...')
            self.conectat = False
            self.inversor_stat_signal.emit(self.conectat)
            return
        else:
            self.conectat = True
            self.inversor_stat_signal.emit(self.conectat)
            print('Connected to inverter')
            self.logger.info('Connected to inverter')

    @timeit
    def read_inv(self):
        temps_lectura = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime())
        if not self.conectat:
            self.configuracio()
        try:
            self._read_variable('inverter_ac_power_p1', 30775, 2, lambda x: float(x[1]))
            self._read_variable('inverter_ac_current_p1', 30795, 2, lambda x: float(x[1])/1000)
            self._read_variable('inverter_ac_voltage_p1', 30783, 2, lambda x: float(x[1])/100)
            self._read_variable('frequency', 30803, 2, lambda x: float(x[1])/100)
            self._read_variable('inverter_dc_power', 30773, 2, lambda x: float(x[1]))
            self._read_variable('inverter_dc_power_2', 30961, 2, lambda x: float(x[1]))
            self._read_variable('inverter_dc_current', 30769, 2, lambda x: float(x[1])/1000)
            self._read_variable('inverter_dc_current_2', 30957, 2, lambda x: float(x[1])/1000)
            self._read_variable('inverter_dc_voltage', 30771, 2, lambda x: float(x[1])/100)
            self._read_variable('inverter_dc_voltage_2', 30959, 2, lambda x: float(x[1])/100)
            self._read_variable('inverter_temperature', 30953, 2, lambda x: float(x[1])/10)
            self._read_variable('inverter_warnings', 30213, 2, lambda x: float(x[1]))
        except Exception as e:
            self.log_with_timestamp('error', f"Error reading variables: {e}")
        self.queue_data_inversor.put(self.data)


    def _read_variable(self, variable, address, quantity, transform):
        temps_lectura = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        if variable not in self.llista_rebuts:
            try:
                message = tcp.read_holding_registers(slave_id=3, starting_address=address, quantity=quantity)
                response = tcp.send_message(message, self.sock_inv)
                value = transform(response)
                self.data.append({"variable": variable, "value": value, "timestamp": temps_lectura})
                self.llista_rebuts.append(variable)
            except Exception:
                self.logger.info(f'No {variable} data')
                self.conectat = False


    def stop_thread(self):
        self.parar = True 
        self.llegir = False
        print("STOPPING INVERSOR THREAD....")
        self.logger.info("STOPPING INVERSOR THREAD....")


    def re_start_thread(self):
        self.parar = False
        self.llegir = True
        self.run()
       