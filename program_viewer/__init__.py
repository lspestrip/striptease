#from program_viewer import main
from PyQt5 import QtCore, QtWidgets
import sys
import os
from program_viewer.ui.main_window import Ui_MainWindow


class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(ApplicationWindow, self).__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
