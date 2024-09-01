from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton
from Concentrator import Concentrator
import queue
import sys
from PyQt5.QtWidgets import QApplication

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.queue_data_string_1 = queue.Queue()
        self.queue_data_string_2 = queue.Queue()
        self.concentrator_thread = Concentrator(self.queue_data_string_1, self.queue_data_string_2)

        self.start_button = QPushButton('Start Thread', self)
        self.start_button.clicked.connect(self.start_thread)

        self.stop_button = QPushButton('Stop Thread', self)
        self.stop_button.clicked.connect(self.stop_thread)

        layout = QVBoxLayout(self)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)

    def start_thread(self):
        self.concentrator_thread.start()

    def stop_thread(self):
        self.concentrator_thread.stop_thread()
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()