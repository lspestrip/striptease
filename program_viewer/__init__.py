#from program_viewer import main
from PyQt5 import QtCore, QtWidgets
import sys
import os
import websocket
import json
import numpy as np
import time
import astropy.time as at
import datetime as dt
from program_viewer.ui.main_window import Ui_MainWindow
from web.rest.base import Connection
from web.ws.base import WsBase
import os

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(ApplicationWindow, self).__init__()

        self.conn = Connection()
        self.conn.login()

        self.ws_dx =  WsBase(self.conn)
        self.ws_sx =  WsBase(self.conn)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.plot_sx.start(self.conn,'R0')
        self.ui.plot_dx.start(self.conn,'R1',items=['VD0_HK','VD1_HK'])
        self.ui.plot_sx_b.start(self.conn,'R0',items=['PWRQ1','PWRQ2','PWRU1','PWRU2'])
        self.ui.plot_dx_b.start(self.conn,'R0',items=['DEMU1','DEMU2','DEMQ1','DEMQ2'])

    def stop(self):
        self.ui.plot_sx.stop()
        self.ui.plot_dx.stop()
        self.ui.plot_sx_b.stop()
        self.ui.plot_dx_b.stop()
