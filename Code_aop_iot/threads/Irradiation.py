from PyQt5.QtCore import QThread, pyqtSignal, QMutexLocker
from PyQt5.QtWidgets import *
import serial
import threading
import time
import json
import minimalmodbus
from aspects import timeit, log_calls, handle_exceptions

class Irradiation(QThread):
    # Señales para la UI principal
    conn_signal = pyqtSignal(bool)
    irr_stat_signal = pyqtSignal(bool)
    
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

    @timeit
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
        #print("STOPPED IRRADIATION THREAD!")

    @log_calls
    @timeit     
    @handle_exceptions           
    def configuracio(self):
        try:
            self.instrument = minimalmodbus.Instrument('/dev/ttyACM0', 1)
            self.instrument.serial.baudrate = 9600
        except minimalmodbus.NoResponseError:
            return "No Connection"
        except Exception as e:
            return 'Error configuring: {e}'
        else:
            self.conectat = True
            self.irr_stat_signal.emit(self.conectat)
            self.log_with_timestamp('Connected to the radiation sensor')
            return "Connected"

    @log_calls
    @timeit
    @handle_exceptions
    def read_radiation(self):
        temps_lectura = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        if not self.conectat:
            self.configuracio()
        if 'solar_irradiance' not in self.llista_rebuts:
            self.read_sensor_data('solar_irradiance', 0, temps_lectura)
            return "Reading solar irradiance"
        if 'air_temperature' not in self.llista_rebuts:
            self.read_sensor_data('air_temperature', 8, temps_lectura)
            return "Reading air temperature"

    @log_calls
    @timeit
    @handle_exceptions
    def read_sensor_data(self, variable, register, timestamp):
        try:
            value = (self.instrument.read_register(register, 0, functioncode=4)) / 10
        except minimalmodbus.NoResponseError:
            self.irr_stat_signal.emit(self.conectat)
            self.conectat = False
            return f"No {variable} data"
        except Exception as e:
            self.irr_stat_signal.emit(self.conectat)
            self.conectat = False
            return f'Error reading {variable}: {e}'
        else:
            self.data.append({"variable": variable, "value": float(value), "timestamp": timestamp})
            self.llista_rebuts.append(variable)
        return "Data Readed"

    @log_calls        
    def handle_no_data_received(self):
        if self.data_rad_prev and self.n_errors_rad < 6:
            self.data = self.data_rad_prev.copy()
            self.add_gateway_error()
            self.n_errors_rad += 1
        else:
            self.data = self.data_rad_error.copy()
            self.add_gateway_error()
        return "No data, filling with previous data"

    @log_calls            
    def handle_partial_data_received(self):
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
        return "Some data received. Filling with previous data"

    @log_calls
    def handle_data_received(self):
        self.data_rad_prev = self.data
        self.n_errors_rad = 0
        return "Data Received"

    def add_gateway_error(self):
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        self.data.append({"variable": "gateway_error", "value": '02', "timestamp": timestamp})

    @log_calls
    def stop_thread(self):
        self.parar = True 
        self.llegir = False
        self.wait()  # Esperar a que el hilo termine
        return "STOPPING IRRADIATION THREAD...."

    def re_start_thread(self):
        self.parar = False
        self.llegir = True
        self.start()  # Reiniciar el hilo correctamente
