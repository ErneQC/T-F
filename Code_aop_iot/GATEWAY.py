### ----------------- BLOCK DESCRIPTION --------------- ###
### --------------------------------------------------- ###

### -------- IMPORTS -------- ###
from UI_GTW import Ui_MainWindow
from threads import Concentrator, Inversor, Irradiation, Nuvol, Curve_IV, aspects
import sys
import time
import queue
import logging
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QMutex, QMutexLocker
from PyQt5.QtWidgets import *

### ------- Classe de la interficie d'usuari ------- ###
class UiActions(QMainWindow):
    def __init__(self):
        super().__init__()

        # Crea una instancia de la interfaz de usuario
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Crear cues para comunicarse entre threads
        self.queue_concentrador_1 = queue.Queue()
        self.queue_concentrador_2 = queue.Queue()
        self.queue_inversor = queue.Queue()
        self.queue_irradiation = queue.Queue()
        self.queue_iv_curve = queue.Queue()

        # Crear instancia dels threads i el mutex de recurs compartit
        #self.mutex = QMutex()
        self.concentrator_thread = Concentrator.Concentrator( self.queue_concentrador_1, self.queue_concentrador_2)
        self.inversor_thread = Inversor.Inversor(self.queue_inversor)
        self.irradiation_thread = Irradiation.Irradiation(self.queue_irradiation)
        self.iv_curve_thread = Curve_IV.Curve_IV(self.queue_iv_curve)
        self.nuvol_thread = Nuvol.Nuvol(self.queue_concentrador_1, self.queue_concentrador_2, self.queue_inversor, self.queue_irradiation, self.queue_iv_curve)
        

        # Fer logiques per inicialitzar els threads
        self.init_concentrator()
        self.init_inversor()
        self.init_irradiation()
        self.init_nuvol()
        self.init_iv_curve()

        # afegir accions als diferents elements i botons de la UI
        self.ui.pushButton.clicked.connect(self.stop_threads)
        self.ui.label_2.setStyleSheet("background-color: rgb(98, 252, 147);")
                
        # self.ui.pushButton_2.clicked.connect(self.restart_threads)
        # self.ui.pushButton_2.setEnabled(False)
        #definir la senyal que para tots els threads amb destroyed
        self.destroyed.connect(self.stop_all_threads)

    def update_status(self, label, running):
        if running:
            label.setStyleSheet("background-color: rgb(98, 252, 147);")
            label.setText("RUNNING")
        else:
            label.setStyleSheet("background-color: rgb(93, 93, 93);")
            label.setText("STOPPED")        
    def statConcentrator(self, bool):
        self.update_status(self.ui.label_string1_2, bool)
    def statString1Concentrador(self, bool):
        if bool:
            self.ui.label_string1.setStyleSheet("background-color: rgb(98, 252, 147);")
        else:
            self.ui.label_string1.setStyleSheet("background-color: rgb(93, 93, 93);")
    def statString2Concentrador(self, bool):
        if bool:
            self.ui.label_string2.setStyleSheet("background-color: rgb(98, 252, 147);")
        else:
            self.ui.label_string2.setStyleSheet("background-color: rgb(93, 93, 93);")
    def statInversor(self, bool):
        self.update_status(self.ui.label_string1_4, bool)
    def statInverter(self, bool):
        if bool:
            self.ui.label_inversor1.setStyleSheet("background-color: rgb(98, 252, 147);")
        else:
            self.ui.label_inversor1.setStyleSheet("background-color: rgb(93, 93, 93);")
    def statIrradiation(self, bool):
        self.update_status(self.ui.label_string1_3, bool)
    def statSensorIrradiation(self, bool):
        if bool:
            self.ui.label_irradiation.setStyleSheet("background-color: rgb(98, 252, 147);")
        else:
            self.ui.label_irradiation.setStyleSheet("background-color: rgb(93, 93, 93);")
    #FUNCIÓ PER AFEGIR AL TEXT EDIT:
    def logTextEdit(self,text):
        self.ui.textEdit_log.append(text)            
    def statNuvol(self, bool):
        self.update_status(self.ui.label_string1_5, bool)
           #self.ui.pushButton_2.setEnabled(True)
            # self.ui.pushButton.setEnabled(False)

    #DEFINICIÓ FUNCIONS PER INICIALITZAR ELS THREADS
    def init_iv_curve(self):
        self.iv_curve_thread.start()
        #self.iv_curve_thread.log_signal.connect(self.logTextEdit)

    def init_concentrator(self):
        #agregar las señaes que conectan con los hilos para vincular a las funcions
        self.concentrator_thread.conn_signal.connect(self.statConcentrator)
        self.concentrator_thread.string1_signal.connect(self.statString1Concentrador)
        self.concentrator_thread.string2_signal.connect(self.statString2Concentrador)
        self.concentrator_thread.start()
    def init_inversor(self):
        #afegir les senyals que connecten amb els threads per vincularles a les funcions
        self.inversor_thread.conn_signal.connect(self.statInversor)
        self.inversor_thread.inversor_stat_signal.connect(self.statInverter)
        self.inversor_thread.start()
    def init_irradiation(self):
        #afegir les senyals que connecten amb els threads per vincularles a les funcions
        self.irradiation_thread.conn_signal.connect(self.statIrradiation)
        self.irradiation_thread.irr_stat_signal.connect(self.statSensorIrradiation)
        self.irradiation_thread.start()
    def init_nuvol(self):
        #afegir les senyals que connecten amb els threads per vincularles a les funcions
        self.nuvol_thread.conn_signal.connect(self.statNuvol)
        self.nuvol_thread.start()
    #DEFINICIÓ FUNCIONS PER PARAR i RESTART DE TOTS ELS THREADS
    def stop_all_threads(self):
        self.concentrator_thread.stop_thread()
        self.inversor_thread.stop_thread()
        self.irradiation_thread.stop_thread()
        self.nuvol_thread.stop_thread()
        self.iv_curve_thread.stop_thread()
    
    def stop_threads(self):
        print("Stoping ALL threads!!")
        self.ui.pushButton.setEnabled(False)
        self.concentrator_thread.stop_thread()
        self.inversor_thread.stop_thread()
        self.irradiation_thread.stop_thread()
        self.nuvol_thread.stop_thread()
        self.iv_curve_thread.stop_thread()      
        self.ui.label_2.setStyleSheet("background-color: rgb(93, 93, 93);")  
    
    def restart_threads(self):
        print(self.concentrator_thread)
        print(self.inversor_thread)
        print(self.irradiation_thread)
        print(self.nuvol_thread)
        print(self.iv_curve_thread)
        # self.init_concentrator()
        # self.init_inversor()
        # self.init_irradiation()
        # self.init_nuvol()
        self.concentrator_thread.re_start_thread()
        self.inversor_thread.re_start_thread()
        self.irradiation_thread.re_start_thread()
        self.nuvol_thread.re_start_thread()
        self.iv_curve_thread.re_start_thread()
        self.ui.label_2.setStyleSheet("background-color: rgb(0, 85, 0);")
        self.ui.pushButton.setEnabled(True)
        self.ui.pushButton_2.setEnabled(False)
            

def main():
    app = QApplication(sys.argv)
    window = UiActions()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()