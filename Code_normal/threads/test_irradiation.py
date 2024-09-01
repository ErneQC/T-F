from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton
from Irradiation import Irradiation
import queue
import sys
from PyQt5.QtWidgets import QApplication
from timeit import timeit
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.queue_data_irradiation = queue.Queue()
        self.irradiation_thread = Irradiation(self.queue_data_irradiation)

        self.start_button = QPushButton('Start Thread', self)
        self.start_button.clicked.connect(self.start_thread)

        self.stop_button = QPushButton('Stop Thread', self)
        self.stop_button.clicked.connect(self.stop_thread)

        layout = QVBoxLayout(self)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)

    def start_thread(self):
        self.irradiation_thread.start()

    def stop_thread(self):
        self.irradiation_thread.stop_thread()
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()