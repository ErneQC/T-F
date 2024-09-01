import socket
import time
import csv
from datetime import datetime, timedelta

def enviar_trama(datos):
    # Configuración del servidor UDP para recibir tramas
    puerto_servidor = 1560  # Puerto al que se enviarán las tramas
    servidor = ('localhost', puerto_servidor)

    # Crear un socket UDP para enviar tramas
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as cliente_socket:
        try:
            # Enviar la trama al servidor
            cliente_socket.sendto(datos.encode(), servidor)
            print("Trama enviada exitosamente:")

        except Exception as ex:
            print("Error al enviar la trama:", ex)

# Función para leer el archivo CSV y enviar las tramas
# Función para enviar las tramas cada 5 minutos desde un archivo CSV
def enviar_tramas_desde_csv(archivo_csv):
    while True:
        with open(archivo_csv, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                trama = row
                fecha_trama = trama[1]  # Extraer la fecha de la trama
                ahora = datetime.now()
                # Reemplazar la fecha en la trama con la fecha actual
                trama[1] = ahora.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                datos = ','.join(trama)
                enviar_trama(datos)
                
        # Esperar 5 minutos antes de enviar la próxima trama
        time.sleep(60)  # 300 segundos = 5 minutos


# Bucle principal
if __name__ == "__main__":
    try:
        archivo_csv = "2024-04-23T093703Z.csv"
        enviar_tramas_desde_csv(archivo_csv)
    except KeyboardInterrupt:
        print("Detenido por el usuario.")

