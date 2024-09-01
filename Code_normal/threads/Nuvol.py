from PyQt5.QtCore import QThread, pyqtSignal, QMutexLocker
from PyQt5.QtWidgets import *
import serial
import threading
import time
import json
import logging
import requests
from paho.mqtt import client as mqtt_client
from PyQt5.QtCore import QThread, pyqtSignal, QMutex
import paho.mqtt.client as mqtt
import random
from timerit import timeit
class Nuvol(QThread):

    conn_signal = pyqtSignal(bool)
    data_send_signal = pyqtSignal(str, bool)  # Se emite el nombre de la cola junto con la señal
    log_signal = pyqtSignal(str)  # Señal para enviar mensajes de log

    def __init__(self, queue_data_concentrator_1, queue_data_concentrator_2, queue_data_inversor, queue_data_irradiation, queue_iv_curve):
        super().__init__()
        self.output_data = {}
        self.parar = False

        self.queue_data_concentrator_1 = queue_data_concentrator_1
        self.queue_data_concentrator_2 = queue_data_concentrator_2
        self.queue_data_inversor = queue_data_inversor
        self.queue_data_irradiation = queue_data_irradiation
        self.queue_iv_curve = queue_iv_curve

        # Crear un mutex para cada cola
        self.mutex_concentrator_1 = QMutex()
        self.mutex_concentrator_2 = QMutex()
        self.mutex_inversor = QMutex()
        self.mutex_irradiation = QMutex()
        self.mutex_iv_curve = QMutex()

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
        url_curve = "http://192.168.194.82:5005/ext/vidata"
        headers_curve = {'Content-Type': 'application/json'}

        self.start_mqtt_client()
        
        while not self.parar:
            self.conn_signal.emit(not self.parar)
            self.logger.info("Analyzing data for sending...")
            print("Analyzing data for sending...")
            queues = [
                ("Concentrator 1", self.queue_data_concentrator_1, self.mutex_concentrator_1),
                ("Concentrator 2", self.queue_data_concentrator_2, self.mutex_concentrator_2),
                ("Inversor", self.queue_data_inversor, self.mutex_inversor),
                ("Irradiation", self.queue_data_irradiation, self.mutex_irradiation),
                ("IV Curve", self.queue_iv_curve, self.mutex_iv_curve)
            ]

            for queue_name, queue, mutex in queues:
                with QMutexLocker(mutex):
                    if queue.empty():
                        self.logger.info(f"{queue_name} queue is empty")
                        print(f"{queue_name} queue is empty")
                    else:
                        if queue_name == "IV Curve":
                            data_list = []
                            for _ in range(12):
                                if not queue.empty():
                                    data_list.append(queue.get())
                            data = data_list
                        else:
                            data = queue.get()

                        self.output_data = {"data": data}
                        our_payload = json.dumps(self.output_data)

                        self.send_mqtt_data(our_payload, "gateway/upc-vilanova/data")
                        print(f"Sending data from {queue_name} queue to cloud")
                        self.logger.info(f"Sending data from {queue_name} queue to cloud")

                        if queue_name == "IV Curve":
                            try:
                                response = requests.post(url_curve, data=our_payload, headers=headers_curve, timeout=8)
                            except Exception as e:
                                self.logger.info(f'Error sending data from {queue_name} queue: {e}. Retrying...')
                                self.data_send_signal.emit(queue_name, False)
                                print(f"Error sending data from {queue_name} queue: {e}. Retrying...")
                                time.sleep(1)
                            else:
                                if response.ok:
                                    self.self.logger.info(f"Upload successful for {queue_name} queue")
                                    self.data_send_signal.emit(queue_name, True)
                                    print(f"Upload successful for {queue_name} queue")
                                else:
                                    self.self.logger.info(f"Upload failed for {queue_name} queue: {response}. Retrying...")
                                    self.data_send_signal.emit(queue_name, False)
                                    print(f"Upload failed for {queue_name} queue: {response}. Retrying...")
                                    time.sleep(1)                                

            time.sleep(20)  # Esperar 20 segundos antes de volver a verificar

        self.conn_signal.emit(not self.parar)
        self.logger.info("STOPPED NUVOL THREAD!")
        print("Thread stopped")

    def stop_thread(self):
        self.parar = True
        self.logger.info("STOPPING NUVOL THREAD...")
        print("Stopping thread...")

    def re_start_thread(self):
        self.parar = False
        self.run()
    @timeit 
    def start_mqtt_client(self):
        global mqtt_client
        self.logger.info("Starting MQTT client")
        print("Starting MQTT client")
        broker = '192.168.194.92'
        port = 1883
        client_id = f'gateway-upcVilanova-{int(random.random()*100)}' 
        username = 'user-aliter'
        password = 'aliter1234'

        mqtt_client = mqtt.Client(client_id)
        mqtt_client.username_pw_set(username, password)
        
        mqtt_client.connect(broker, port)
        mqtt_client.loop_start()
        
        time.sleep(4)
    @timeit
    def send_mqtt_data(self, data, topic):
        mqtt_client.publish(topic, str(data))
        self.logger.info(f"MQTT data sent: {data}")
        print(f"MQTT data sent: {data}")


