# program_viewer/__ini__.py --- Example program
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it
from PyQt5 import QtCore, QtWidgets
import sys
import os
import json
import numpy as np
import time
import astropy.time as at
import datetime as dt
from program_viewer.ui.main_window import Ui_MainWindow
from web.rest.base import Connection
from widgets.login import LoginWidget
from config import Config
import os


class CheckBoxCallBack(object):
    '''CheckBox callback container
    '''
    def __init__(self,plot,table,hk):
        self.plot  = plot
        self.table = table
        self.hk    = hk

    def callback(self,val):
        '''called when the registred checkbox changes status
        '''
        #print(self.hk,val)
        if val == 0:
            self.plot.del_plot(self.table,self.hk)
        elif val == 2:
            self.plot.add_plot(self.table,self.hk)

class ApplicationWindow(QtWidgets.QMainWindow):
    '''Main window class'''
    def __init__(self):
        '''initializes the ui and polulates the housekeeping table'''
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
        conf.load(self.conn)
        self.callbacks=[]

        t = self.ui.hk_table
        t.setRowCount(sum([len(conf.board_addr[x])  for x in conf.board_addr if x.endswith('POL')]))
        t.setColumnCount(3)
        i = 0
#        for s in SCI:
#            cb = QtWidgets.QCheckBox(t)
#            cb.setText(s)
#            cb.setCheckState(2)
#            callb = CheckBoxCallBack(self.ui.plot,s)
#            cb.stateChanged.connect(callb.callback)
#            self.callbacks.append((cb,callb))
#            t.setCellWidget(i,0,cb)
#            i += 1

        for table in conf.board_addr:
            if not table.endswith('POL'):
                continue
            for hk in conf.board_addr[table]:
                cb = QtWidgets.QCheckBox(t)
                #cb.setText(hk['name'])
                callb = CheckBoxCallBack(self.ui.plot,table,hk['name'])
                cb.stateChanged.connect(callb.callback)
                self.callbacks.append((cb,callb))

                item_table = QtWidgets.QTableWidgetItem()
                item_table.setText(table)
                t.setItem(i, 1, item_table)

                item_hk = QtWidgets.QTableWidgetItem()
                item_hk.setText(hk['name'])
                t.setItem(i, 2, item_hk)

                t.setCellWidget(i,0,cb)
                i += 1

        for b in conf.boards:
            for p in b['pols']:
                self.ui.polList.addItem(p)

        self.ui.polList.currentIndexChanged.connect(self.polChanged)

        self.ui.plot.start(self.conn,self.ui.polList.currentText())

    def polChanged(self,i):
        '''callback for polarimer change on the dropdown list.
           stops the current polatimeter streaming and starts a new streaming
           for the selected polarimeter.
        '''
        pol = self.ui.polList.currentText()
        hkdict = {}
        for cb,call in self.callbacks:
            if cb.checkState() == 2:
                if hkdict.get(call.table) is None:
                    hkdict[call.table] = set()
                hkdict[call.table].add(call.hk)

        print(hkdict)

        self.ui.plot.stop()
        self.ui.plot.start(self.conn,pol,items=hkdict)

    def stop(self):
        self.ui.plot.stop()
