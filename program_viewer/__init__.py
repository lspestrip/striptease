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
from widgets.login import LoginWidget
from config import Config
from widgets.plot.pol import SCI
import os


class CheckBoxCallBack(object):
    def __init__(self,plot,hk):
        self.plot = plot
        self.hk = hk

    def callback(self,val):
        #print(self.hk,val)
        if val == 0:
            self.plot.del_plot(self.hk)
        elif val == 2:
            self.plot.add_plot(self.hk)

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(ApplicationWindow, self).__init__()

        self.conn = Connection()
        if self.conn.has_login():
            self.conn.login()
        else:
            dialog = LoginWidget()
            dialog.exec_()
            self.conn.login(dialog.user,dialog.password)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        conf = Config()
        self.callbacks=[]

        t = self.ui.hk_table
        t.setRowCount(len(conf.conf['daq_addr']['hk'])+len(SCI))
        t.setColumnCount(1)
        i = 0
        for s in SCI:
            cb = QtWidgets.QCheckBox(t)
            cb.setText(s)
            cb.setCheckState(2)
            callb = CheckBoxCallBack(self.ui.plot,s)
            cb.stateChanged.connect(callb.callback)
            self.callbacks.append((cb,callb))
            t.setCellWidget(i,0,cb)
            i += 1

        for hk in conf.conf['daq_addr']['hk']:
            cb = QtWidgets.QCheckBox(t)
            cb.setText(hk['name'])
            callb = CheckBoxCallBack(self.ui.plot,hk['name'])
            cb.stateChanged.connect(callb.callback)
            self.callbacks.append((cb,callb))
            t.setCellWidget(i,0,cb)
            i += 1

        for b in conf.conf['daq_boards']:
            for p in b['pols']:
                self.ui.polList.addItem(p)

        self.ui.polList.currentIndexChanged.connect(self.polChanged)

        self.ui.plot.start(self.conn,self.ui.polList.currentText())

    def polChanged(self,i):
        pol = self.ui.polList.currentText()
        hklist = []
        for cb,call in self.callbacks:
            if cb.checkState() == 2:
                hklist.append(call.hk)

        self.ui.plot.stop()
        self.ui.plot.start(self.conn,pol,items=hklist)

    def stop(self):
        self.ui.plot.stop()
