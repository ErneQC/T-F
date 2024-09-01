from PyQt5.QtCore import QThread, pyqtSignal, QMutexLocker
from PyQt5.QtWidgets import *
import serial
import threading
import time
import logging
import json
import minimalmodbus
from timeit import timeit
class Irradiation(QThread):
    # Señales para la UI principal
    conn_signal = pyqtSignal(bool)
    irr_stat_signal = pyqtSignal(bool)
    log_signal = pyqtSignal(str)
    
    def __init__(self, queue_data_irradiation):
        super().__init__()
        self.parar = False  # Señal para parar
        self.llegir = True  # Señal para leer
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        self.data_rad_prev = []
        self.data_rad_error = [
            {"variable": "solar_irradiance", "value": "9999", "timestamp": timestamp},
            {"variable": "air_temperature", "value": "9999", "timestamp": timestamp}
        ]
        self.n_errors_rad = 0
        self.queue_data_irradiacion = queue_data_irradiation
        self.conectat = False
        self.data = []
        self.llista_rebuts = []

        # Configuración del logger
        self.logger = logging.getLogger('IrradiationLogger')
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
            self.irr_stat_signal.emit(self.conectat)
            if not self.conectat and not self.parar:
                self.configuracio()
            if self.llegir:
                self.data = []
                self.llista_rebuts = []
            else:
                time.sleep(1)
                continue

            while self.llegir and len(self.data) < 2 and not self.parar:
                self.read_radiation()
                time.sleep(60)
                
            if not self.data:
                self.handle_no_data_received()
            elif len(self.data) == 1:
                self.handle_partial_data_received()
            else:
                self.handle_data_received()

            self.queue_data_irradiacion.put(self.data)
            time.sleep(3)

        self.conn_signal.emit(not self.parar)
        self.logger.info("STOPPED IRRADIATION THREAD!")
        print("STOPPED IRRADIATION THREAD!")
    @timeit            
    def configuracio(self):
        try:
            self.instrument = minimalmodbus.Instrument('/dev/ttyACM0', 1)
            self.instrument.serial.baudrate = 9600
        except minimalmodbus.NoResponseError:
            self.logger.info('No connection to the radiation sensor')
            print('No connection to the radiation sensor')
        except Exception as e:
            self.logger.info(f'Error configuring sensor: {e}')
            print(f'Error configuring sensor: {e}')
        else:
            self.conectat = True
            self.irr_stat_signal.emit(self.conectat)
            self.logger.info('Connected to the radiation sensor')
            print('Connected to the radiation sensor')
    @timeit
    def read_radiation(self):
        temps_lectura = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        if not self.conectat:
            self.configuracio()
        if 'solar_irradiance' not in self.llista_rebuts:
            self.read_sensor_data('solar_irradiance', 0, temps_lectura)
        if 'air_temperature' not in self.llista_rebuts:
            self.read_sensor_data('air_temperature', 8, temps_lectura)
    @timeit
    def read_sensor_data(self, variable, register, timestamp):
        try:
            value = (self.instrument.read_register(register, 0, functioncode=4)) / 10
        except minimalmodbus.NoResponseError:
            self.logger.info(f'No {variable} data')
            print(f'No {variable} data')
            self.conectat = False
        except Exception as e:
            self.logger.info(f'Error reading {variable}: {e}')
            print(f'Error reading {variable}: {e}')
            self.conectat = False
        else:
            self.data.append({"variable": variable, "value": float(value), "timestamp": timestamp})
            self.llista_rebuts.append(variable)
        
    def handle_no_data_received(self):
        self.logger.info('No radiation data received. Filling with previous data')
        print('No radiation data received. Filling with previous data')
        if self.data_rad_prev and self.n_errors_rad < 6:
            self.data = self.data_rad_prev.copy()
            self.add_gateway_error()
            self.n_errors_rad += 1
        else:
            self.data = self.data_rad_error.copy()
            self.add_gateway_error()
                
    def handle_partial_data_received(self):
        self.logger.info('Some radiation data received. Filling rest with previous data')
        print('Some radiation data received. Filling rest with previous data')
        if self.data_rad_prev and self.n_errors_rad < 6:
            if 'solar_irradiance' in self.llista_rebuts:
                self.data.append(self.data_rad_prev[1])
            elif 'air_temperature' in self.llista_rebuts:
                self.data = [self.data_rad_prev[0]] + self.data
        else:
            if 'solar_irradiance' in self.llista_rebuts:
                self.data.append(self.data_rad_error[1])
            elif 'air_temperature' in self.llista_rebuts:
                self.data = [self.data_rad_error[0]] + self.data
        
        self.add_gateway_error()
        
    def handle_data_received(self):
        self.data_rad_prev = self.data
        self.logger.info("Radiation data received")
        print("Radiation data received")
        self.n_errors_rad = 0

    def add_gateway_error(self):
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        self.data.append({"variable": "gateway_error", "value": '02', "timestamp": timestamp})

    def stop_thread(self):
        self.parar = True 
        self.llegir = False
        self.wait()  # Esperar a que el hilo termine
        self.logger.info("STOPPING IRRADIATION THREAD....")
        print("STOPPING IRRADIATION THREAD....")

    def re_start_thread(self):
        self.parar = False
        self.llegir = True
        self.start()  # Reiniciar el hilo correctamente
