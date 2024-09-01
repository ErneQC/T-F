import socket
import time
import csv
from datetime import datetime

def enviar_trama(datos):
    # Configuración del servidor UDP para recibir tramas
    puerto_servidor = 1573  # Puerto al que se enviarán las tramas
    servidor = ('localhost', puerto_servidor)

    # Crear un socket UDP para enviar tramas
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as cliente_socket:
        try:
            # Enviar la trama al servidor
            cliente_socket.sendto(datos.encode(), servidor)
            print("Trama enviada exitosamente:", datos)

        except Exception as ex:
            print("Error al enviar la trama:", ex)

# Función para leer el archivo CSV y enviar las tramas
def enviar_tramas_desde_csv(archivo_csv):
    while True:
        with open(archivo_csv, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            for row in reader:
                hora_trama = row[2]
                hora_trama = int(str(hora_trama)[:-2])
                ahora = datetime.now()
                time_comp = ahora.hour*100+ahora.minute
                if hora_trama == time_comp:
                    # Reemplazar los datos de día, mes y año con los datos actuales
                    datos = ','.join([row[0], row[1], row[2], ahora.strftime("%d"), ahora.strftime("%m"), ahora.strftime("%Y")] + row[6:])
                    enviar_trama(datos)
        time.sleep(60)
        print("loop")

# Bucle principal
if __name__ == "__main__":
    try:
        archivo_csv = "simulacion_string1.csv"
        enviar_tramas_desde_csv(archivo_csv)
    except KeyboardInterrupt:
        print("Detenido por el usuario.")
