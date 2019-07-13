from PyQt5 import QtCore, QtGui, QtWidgets
import sys
import os
import json
import numpy as np
import time
import astropy.time as at
import datetime as dt
from program_polview.ui.main_window import Ui_MainWindow
from web.rest.base import Connection
from web.wamp.base import WampBase
from widgets.login import LoginWidget
from config import Config
import os
from threading import Thread
import asyncio

#colorscale
import matplotlib
from zlib import crc32


def str_to_float(s, encoding="utf-8"):
    return float(crc32(s.encode(encoding)) & 0xffffffff) / 2**32

class StatsAvg(object):
    def __init__(self,widget,span_sec=20):
        self.item = widget
        self.wsec = span_sec
        self.reset()

    def add(self,mjd,val):
        if self.mjd.size == 0 or (mjd - self.mjd[0])*86400 <= self.wsec:
            self.mjd = np.append(self.mjd,mjd)
            self.val = np.append(self.val,val)

        else:
            self.mjd[0] = mjd
            self.val[0] = val

            self.mjd = np.roll(self.mjd,-1)
            self.val = np.roll(self.val,-1)

        #self.item.setText(1,str(self.val.mean()))
        self.item.setText(1,"{:6.2f}".format(self.val.mean()))

    def reset(self):
        self.mjd = np.ndarray([0],dtype=np.float64)
        self.val = np.ndarray([0],dtype=np.float64)
        self.item.setText(1,'NaN')



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

        self.conf = Config()
        self.conf.load(self.conn)


        self.pols = set()
        self.subs = {}

        self.hk = {}

        for board in self.conf.boards:
            t = QtWidgets.QTreeWidgetItem(self.ui.polarimeter_tree)
            t.setText(0,board["name"])

            st = QtWidgets.QTreeWidgetItem(self.ui.stats_tree)
            st.setText(0,board["name"])
            for pol in board['pols']:
                p = QtWidgets.QTreeWidgetItem(t)
                p.setFlags(t.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
                p.setText(0,pol)
                p.setCheckState(0, QtCore.Qt.Unchecked)

                sp = QtWidgets.QTreeWidgetItem(st)
                sp.setText(0,pol)
                self.hk[pol] = {}
                for hk in [x  for x in self.conf.board_addr['BIAS_POL'] if x['name'][-2:] == 'HK' ]:
                    h = QtWidgets.QTreeWidgetItem(sp)
                    h.setText(0,hk['name'])
                    h.setText(1,"NaN")
                    self.hk[pol][hk['name']] = StatsAvg(h,10)



        self.ui.polarimeter_tree.itemChanged.connect(self.check_pol_callback)

        self.th = []
        self.lp = []

        self.wamp  = WampBase(self.conn)
        self.wamp.connect(self.conf.get_wamp_url(),self.conf.get_wamp_realm())

        s = time.time()
        while not self.wamp.session.is_attached():
            if time.time() - s > 5:
                raise RuntimeError('Cannot attach to WAMP session')
            time.sleep(0.1)

        loop = self.new_th_loop()
        self.ui.pwr_q1.title = "Q1"
        self.ui.pwr_q1.set_loop(loop)

        self.ui.pwr_q2.title = "Q2"
        self.ui.pwr_q2.set_loop(loop)

        loop = self.new_th_loop()
        self.ui.pwr_u1.title = "U1"
        self.ui.pwr_u1.set_loop(loop)

        self.ui.pwr_u2.title = "U2"
        self.ui.pwr_u2.set_loop(loop)

        loop = self.new_th_loop()
        self.ui.dem_q1.title = "Q1"
        self.ui.dem_q1.set_loop(loop)

        self.ui.dem_q2.title = "Q2"
        self.ui.dem_q2.set_loop(loop)

        loop = self.new_th_loop()
        self.ui.dem_u1.title = "U1"
        self.ui.dem_u1.set_loop(loop)

        self.ui.dem_u2.title = "U2"
        self.ui.dem_u2.set_loop(loop)

    def check_pol_callback(self,item):
        print(self.subs)
        name = item.text(0)
        state = item.checkState(0)
        if state == 2:
            cmap = matplotlib.cm.get_cmap('plasma')
            col = cmap(str_to_float(name))
            print(col)
            self.pols.add(name)
            self.subs[name] = self.wamp.subscribe(self.recv,self.conf.get_wamp_pol(name))
            self.ui.pwr_q1.add_plot(name,col)
            self.ui.pwr_q2.add_plot(name,col)
            self.ui.pwr_u1.add_plot(name,col)
            self.ui.pwr_u2.add_plot(name,col)

            self.ui.dem_q1.add_plot(name,col)
            self.ui.dem_q2.add_plot(name,col)
            self.ui.dem_u1.add_plot(name,col)
            self.ui.dem_u2.add_plot(name,col)
        elif state == 0:
            if name in self.pols:
                self.pols.remove(name)
                self.subs[name].result().unsubscribe()
            self.ui.pwr_q1.del_plot(name)
            self.ui.pwr_q2.del_plot(name)
            self.ui.pwr_u1.del_plot(name)
            self.ui.pwr_u2.del_plot(name)

            self.ui.dem_q1.del_plot(name)
            self.ui.dem_q2.del_plot(name)
            self.ui.dem_u1.del_plot(name)
            self.ui.dem_u2.del_plot(name)

            for hk in self.hk[name]:
                self.hk[name][hk].reset()


    def stop(self):
        self.wamp.leave()
        for loop in self.lp:
            loop.stop()
        for t in self.th:
            t.join()

    def recv(self,*args,**pkt):
        pol = pkt['pol']
        if pol in self.pols:
            if pkt.get('PWRQ1'):
                self.ui.pwr_q1.add_data(pol,pkt['mjd'],pkt['PWRQ1'])
                self.ui.pwr_q2.add_data(pol,pkt['mjd'],pkt['PWRQ2'])
                self.ui.pwr_u1.add_data(pol,pkt['mjd'],pkt['PWRU1'])
                self.ui.pwr_u2.add_data(pol,pkt['mjd'],pkt['PWRU2'])

                self.ui.dem_q1.add_data(pol,pkt['mjd'],pkt['DEMQ1'])
                self.ui.dem_q2.add_data(pol,pkt['mjd'],pkt['DEMQ2'])
                self.ui.dem_u1.add_data(pol,pkt['mjd'],pkt['DEMU1'])
                self.ui.dem_u2.add_data(pol,pkt['mjd'],pkt['DEMU2'])
            else:
                if pkt.get('bias'):
                    for hk in pkt['bias']:
                        if hk[-2:] == 'HK':
                            self.hk[pol][hk].add(pkt['mjd'],pkt['bias'][hk])
        else:
            print("WTF?!?:",pol)

    def new_th_loop(self):
        loop = asyncio.new_event_loop()
        thread = Thread(target=self.__f,args=[loop])
        thread.start()
        self.th.append(thread)
        self.lp.append(loop)
        return loop

    def __f(self,loop):
        #asyncio.set_event_loop(self.loop)
        loop.run_forever()
