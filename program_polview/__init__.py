from PyQt5 import QtCore, QtGui, QtWidgets
import sys
import os
import json
import numpy as np
import time
import astropy.time as at
import datetime as dt
from program_polview.ui.main_window import Ui_MainWindow
from program_polview.engine import Engine
from web.rest.base import Connection
from web.wamp.base import WampBase
from widgets.login import LoginWidget
from config import Config
import os
from threading import Thread
import asyncio

#colorscale
import matplotlib


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

class LNAplot(object):
    def __init__(self, lna, data,tree,ui):
        self.lna = lna
        self.data = data
        self.tree = tree
        self.ui = ui

    def callback(self,val):
        if val == 0:
            if self.lna in self.data:
                self.data.remove(self.lna)
            for item in self.tree:
                if item.checkState(0) == 2:
                    pol = item.text(0)
                    col = get_color()
                    self.ui.id.del_plot(pol+"_"+self.lna)
                    self.ui.ig.del_plot(pol+"_"+self.lna)
                    self.ui.vd.del_plot(pol+"_"+self.lna)
                    self.ui.vg.del_plot(pol+"_"+self.lna)

        elif val == 2:
            for item in self.tree:
                if item.checkState(0) == 2:
                    pol = item.text(0)
                    col = get_color()
                    self.ui.id.add_plot(pol+"_"+self.lna,col)
                    self.ui.ig.add_plot(pol+"_"+self.lna,col)
                    self.ui.vd.add_plot(pol+"_"+self.lna,col)
                    self.ui.vg.add_plot(pol+"_"+self.lna,col)

            self.data.add(self.lna)


def get_color():
    c = np.random.rand(1)[0]
    cmap = matplotlib.cm.get_cmap('plasma')
    return cmap(c)

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

        self.lna_callbacks = []
        self.lna  = set()
        self.pols = set()

        self.hk = {}
        self.tree_items = []

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
                self.tree_items.append(p)

                sp = QtWidgets.QTreeWidgetItem(st)
                sp.setText(0,pol)
                self.hk[pol] = {}
                for hk in [x  for x in self.conf.board_addr['BIAS_POL'] if x['name'][-2:] == 'HK' ]:
                    h = QtWidgets.QTreeWidgetItem(sp)
                    h.setText(0,hk['name'])
                    h.setText(1,"NaN")
                    h.setText(2,"NaN")
                    self.hk[pol][hk['name']] = StatsAvg(h,10)



        self.ui.polarimeter_tree.itemChanged.connect(self.check_pol_callback)

        self.th = []
        self.lp = []

        self.engines = {}

        loop = self.new_th_loop()
        self.ui.pwr_q1.title = "Q1"
        self.ui.pwr_q1.set_loop(loop)

        self.ui.pwr_q2.title = "Q2"
        self.ui.pwr_q2.set_loop(loop)

        self.ui.pwr_u1.title = "U1"
        self.ui.pwr_u1.set_loop(loop)

        self.ui.pwr_u2.title = "U2"
        self.ui.pwr_u2.set_loop(loop)

        loop = self.new_th_loop()
        self.ui.dem_q1.title = "Q1"
        self.ui.dem_q1.set_loop(loop)

        self.ui.dem_q2.title = "Q2"
        self.ui.dem_q2.set_loop(loop)

        self.ui.dem_u1.title = "U1"
        self.ui.dem_u1.set_loop(loop)

        self.ui.dem_u2.title = "U2"
        self.ui.dem_u2.set_loop(loop)

        loop = self.new_th_loop()
        self.ui.id.title = "ID"
        self.ui.id.set_loop(loop)

        self.ui.ig.title = "IG"
        self.ui.ig.set_loop(loop)

        self.ui.vd.title = "VD"
        self.ui.vd.set_loop(loop)

        self.ui.vg.title = "VG"
        self.ui.vg.set_loop(loop)

        lna = LNAplot('hk0',self.lna,self.tree_items,self.ui)
        self.ui.hk0.stateChanged.connect(lna.callback)
        self.lna_callbacks.append(lna)

        lna = LNAplot('hk1',self.lna,self.tree_items,self.ui)
        self.ui.hk1.stateChanged.connect(lna.callback)
        self.lna_callbacks.append(lna)

        lna = LNAplot('hk2',self.lna,self.tree_items,self.ui)
        self.ui.hk2.stateChanged.connect(lna.callback)
        self.lna_callbacks.append(lna)

        lna = LNAplot('hk3',self.lna,self.tree_items,self.ui)
        self.ui.hk3.stateChanged.connect(lna.callback)
        self.lna_callbacks.append(lna)

        lna = LNAplot('hk4',self.lna,self.tree_items,self.ui)
        self.ui.hk4.stateChanged.connect(lna.callback)
        self.lna_callbacks.append(lna)

        lna = LNAplot('hk5',self.lna,self.tree_items,self.ui)
        self.ui.hk5.stateChanged.connect(lna.callback)
        self.lna_callbacks.append(lna)

        lna = LNAplot('hk4a',self.lna,self.tree_items,self.ui)
        self.ui.hk4a.stateChanged.connect(lna.callback)
        self.lna_callbacks.append(lna)

        lna = LNAplot('hk5a',self.lna,self.tree_items,self.ui)
        self.ui.hk5a.stateChanged.connect(lna.callback)
        self.lna_callbacks.append(lna)



        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.pippo)
        self.timer.start(1000)

    def check_pol_callback(self,item):
        name = item.text(0)
        state = item.checkState(0)
        if state == 2:
            col = get_color()
            self.pols.add(name)
            e = Engine(self.conn,name,col,20.)
            e.start()
            self.engines[name] = e
            self.ui.pwr_q1.add_plot(name,col)
            self.ui.pwr_q2.add_plot(name,col)
            self.ui.pwr_u1.add_plot(name,col)
            self.ui.pwr_u2.add_plot(name,col)

            self.ui.dem_q1.add_plot(name,col)
            self.ui.dem_q2.add_plot(name,col)
            self.ui.dem_u1.add_plot(name,col)
            self.ui.dem_u2.add_plot(name,col)

            for h in ['hk0','hk1','hk2','hk3','hk4','hk5','hk4a','hk5a']:
                if h in self.lna:
                    col = get_color()
                    self.ui.id.add_plot(name+"_"+h,col)
                    self.ui.ig.add_plot(name+"_"+h,col)
                    self.ui.vd.add_plot(name+"_"+h,col)
                    self.ui.vg.add_plot(name+"_"+h,col)



        elif state == 0:
            if name in self.pols:
                self.pols.remove(name)
            if name in self.engines:
                self.engines[name].stop()
                del self.engines[name]
            self.ui.pwr_q1.del_plot(name)
            self.ui.pwr_q2.del_plot(name)
            self.ui.pwr_u1.del_plot(name)
            self.ui.pwr_u2.del_plot(name)

            self.ui.dem_q1.del_plot(name)
            self.ui.dem_q2.del_plot(name)
            self.ui.dem_u1.del_plot(name)
            self.ui.dem_u2.del_plot(name)

            for h in ['hk0','hk1','hk2','hk3','hk4','hk5','hk4a','hk5a']:
                if h in self.lna:
                    col = get_color()
                    self.ui.id.del_plot(name+"_"+h)
                    self.ui.ig.del_plot(name+"_"+h)
                    self.ui.vd.del_plot(name+"_"+h)
                    self.ui.vg.del_plot(name+"_"+h)

            for hk in self.hk[name]:
                self.hk[name][hk].reset()


    def stop(self):
        pass

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
                    for lna in ['0','1','2','3','4','5','4a','5a']:
                        if 'hk'+lna in self.lna:
                            up = lna.upper()
                            if 'VD'+up+'_HK' in pkt['bias']:
                                self.ui.vd.add_data(pol+"_hk"+up,pkt['mjd'],pkt['bias']['VD'+up+'_HK'])
                            if 'ID'+up+'_HK' in pkt['bias']:
                                self.ui.id.add_data(pol+"_hk"+up,pkt['mjd'],pkt['bias']['ID'+up+'_HK'])
                            if 'VG'+up+'_HK' in pkt['bias']:
                                self.ui.vg.add_data(pol+"_hk"+up,pkt['mjd'],pkt['bias']['VG'+up+'_HK'])
                            if 'IG'+up+'_HK' in pkt['bias']:
                                self.ui.ig.add_data(pol+"_hk"+up,pkt['mjd'],pkt['bias']['IG'+up+'_HK'])
                    for hk in pkt['bias']:
                        if hk[-2:] == 'HK':
                            self.hk[pol][hk].add(pkt['mjd'],pkt['bias'][hk])

    def pippo(self):
        tab = self.ui.tab_group.currentWidget().objectName()
        for pol in self.engines:
            e = self.engines[pol]
            data = e.get_data_plot()
            if tab == 'tab_pwr':
                self.ui.pwr_q1.set_data(pol,data['PWRQ1']['mjd'],data['PWRQ1']['val'])
                self.ui.pwr_q2.set_data(pol,data['PWRQ2']['mjd'],data['PWRQ2']['val'])
                self.ui.pwr_u1.set_data(pol,data['PWRU1']['mjd'],data['PWRU1']['val'])
                self.ui.pwr_u2.set_data(pol,data['PWRU2']['mjd'],data['PWRU2']['val'])

            elif tab == 'tab_dem':
                self.ui.dem_q1.set_data(pol,data['DEMQ1']['mjd'],data['DEMQ1']['val'])
                self.ui.dem_q2.set_data(pol,data['DEMQ2']['mjd'],data['DEMQ2']['val'])
                self.ui.dem_u1.set_data(pol,data['DEMU1']['mjd'],data['DEMU1']['val'])
                self.ui.dem_u2.set_data(pol,data['DEMU2']['mjd'],data['DEMU2']['val'])

            elif tab == 'tab_lna':
                for lna in ['0','1','2','3','4','5','4a','5a']:
                    if 'hk'+lna in self.lna:
                        up = lna.upper()
                        self.ui.vd.set_data(pol+"_hk"+up,data['VD'+up+'_HK']['mjd'],data['VD'+up+'_HK']['val'])
                        self.ui.id.set_data(pol+"_hk"+up,data['ID'+up+'_HK']['mjd'],data['ID'+up+'_HK']['val'])
                        self.ui.vg.set_data(pol+"_hk"+up,data['VG'+up+'_HK']['mjd'],data['VG'+up+'_HK']['val'])
                        self.ui.ig.set_data(pol+"_hk"+up,data['IG'+up+'_HK']['mjd'],data['IG'+up+'_HK']['val'])


        if tab == 'tab_pwr':
            self.ui.pwr_q1.commit_plot()
            self.ui.pwr_q2.commit_plot()
            self.ui.pwr_u1.commit_plot()
            self.ui.pwr_u2.commit_plot()
            
        elif tab == 'tab_dem':
            self.ui.dem_q1.commit_plot()
            self.ui.dem_q2.commit_plot()
            self.ui.dem_u1.commit_plot()
            self.ui.dem_u2.commit_plot()

        elif tab == 'tab_lna':
            self.ui.id.commit_plot()
            self.ui.ig.commit_plot()
            self.ui.vd.commit_plot()
            self.ui.vg.commit_plot()




    def new_th_loop(self):
        loop = asyncio.new_event_loop()
        thread = Thread(target=self.__th_lp,args=[loop])
        thread.start()
        self.th.append(thread)
        self.lp.append(loop)
        return loop


    def __th_lp(self,loop):
        #asyncio.set_event_loop(self.loop)
        loop.run_forever()

    def __f(self):
        while True:
            self.update()
            time.sleep(1)
