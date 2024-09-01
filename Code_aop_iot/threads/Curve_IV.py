from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import *
import socket
import time
from aspects import timeit, log_calls, handle_exceptions

class Curve_IV(QThread):
    # Signals definition to main UI
    curve_signal = pyqtSignal(bool)
    log_signal = pyqtSignal(str)  # Señal para enviar mensajes de log

    def __init__(self, queue_curve):
        super().__init__()
        self.parar = False  # Señal para parar la lectura
        self.llegir = True  # Señal para leer
        self.input_data_prev_1 = []
        self.input_data_error_1 = ['$GSTR', '1', '000000', '00', '00', '0000', "-999", '1', "-999", "-999", '2', "-999", "-999",
                                   '3', "-999", "-999", '4', "-999", "-999", '5', "-999", "-999"]
        self.n_errors_list_1 = [0] * 3006
        self.n_errors_1 = 0
        self.missing_1 = True           # Variable para controlar si se ha recibido información del concentrador 1
        self.conectat = False
        self.queue_curve = queue_curve
        self.data = []

    def run(self):
        while not self.parar:  # Loop mientras no se cierra el programa
            self.curve_signal.emit(not self.parar)
            while not self.conectat and not self.parar:  # Si no está conectado, reintentamos la conexión
                self.configuracio()
                time.sleep(1)
            if self.llegir:
                self.missing_1 = True
                self.data = []
            else:
                #time.sleep(1)
                continue
            while self.llegir and self.missing_1 and not self.parar:
                self.read_iv_curve()
                #time.sleep(1)
            time.sleep(1)
        self.curve_signal.emit(not self.parar)

    @log_calls
    @timeit
    @handle_exceptions
    def configuracio(self):
        try:
            self.concentradors = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.concentradors.bind(('0.0.0.0', 1560))  # Escuchar en el puerto 1560
            self.conectat = True
            return "Sensor connected"
        except Exception:
            self.conectat = False
            return "Sensor not connected"

    @log_calls
    @timeit
    @handle_exceptions
    def read_iv_curve(self):
        if not self.conectat:
            self.configuracio()
        try:
            self.concentradors.settimeout(None)#
            data, _ = self.concentradors.recvfrom(18192)
            response = data.decode().strip()
            input_data = response.split(',')
            
        except Exception as ex:
            if not self.conectat:
                return "No connection. Retrying..."
        else:
            if len(input_data) == 1205:
                #self.log_with_timestamp("IV-Curve data received")
                data_individual = self.tractar_dades(input_data)
                self.input_data_prev_1 = input_data
                self.queue_curve.put(data_individual)
            else:
                return "Incorrect Data received"
            return "Data received"

    #@log_calls
    @timeit
    @log_calls
    @handle_exceptions
    def tractar_dades(self, idata):
        data_individual = []
        utc_time = idata[1][:-1]  # Extraer UTC time
        device_id = idata[2]  # Device ID

        current_data_indices = range(4, 604)
        voltage_data_indices = range(605, 1205)

        current_range = (0, 2.3)
        voltage_range = (0, 50)

        current_data = [float(idata[i]) if idata[i].strip() else None for i in current_data_indices]
        processed_current_data = self.process_values(current_data, current_range)

        voltage_data = [float(idata[i]) if i < len(idata) and idata[i].strip() else None for i in voltage_data_indices]
        processed_voltage_data = self.process_values(voltage_data, voltage_range)

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

    @timeit
    @log_calls
    @handle_exceptions
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

    @log_calls
    def stop_thread(self):
        self.parar = True 
        self.llegir = False
        return "stopping thread"

    def re_start_thread(self):
        self.parar = False
        self.llegir = True
        self.start()
        return "restarting thread"
