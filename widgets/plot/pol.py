# widgets/plot/pol.py --- Polarimeter plot classes
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it
from widgets.plot import MplCanvas
from web.wamp.base import WampBase
from config import Config
import asyncio
from threading import Thread
import numpy as np
import time
import astropy.time as at
import datetime as dt
import time
import gc
import matplotlib.pyplot as plt
from copy import deepcopy


class PolMplCanvas(MplCanvas):
    '''QtWidget for polarimer data plot
    '''
    def __init__(self, *args, **kwargs):
        MplCanvas.__init__(self, *args, **kwargs)
        self.conf = Config()
        self.data={}
        self.dict_add = {}
        self.dict_del = {}


    def add_plot(self,table,hk):
        '''add an housekeeping to the plot
          :param str hk: housekeeping or scientific parameter name
        '''
        self.items[table].add(hk)
        self.replot()


    def del_plot(self,table,hk):
        '''remove an housekeeping to the plot
          :param str hk: housekeeping or scientific parameter name
        '''
        self.items[table].remove(hk)
        self.replot()


    def start(self,conn,pol,window_sec=60,items={},refresh=0.09):
        '''starts the stream listening and plot in a dedicated thread.

           :param web.rest.base.Connection conn: the backend http connection
           :param str pol: the polarimer name
           :param float window_sec: the time interval in seconds to display. default=30.0
           :param {str:{str,str}} items: the dictionary (table: set of hk names) of housekeeping to display from the start. Default is scientific data only.
           :param float refresh: choose the number of seconds to wait between one plot and the next one. If you experience
            poor performance, think about increase this number. Please note that the data acquisition continues even if the
            graph is not redrawn. Default value is 0.33
        '''
        self.url = self.conf.get_wamp_url()
        self.pol = pol
        self.wamp  = WampBase(conn)
        self.wsec = window_sec
        self.rsec = refresh
        self.items = {}
        self.conf.load(conn)
        self.__clear_data()

        for t in [x for x in self.conf.board_addr.keys() if x.endswith('POL')]:
            self.items[t]=set()

        for t in items:
            for hk in items[t]:
                self.items[t].add(hk)

        self.__prepare_canvas()
        self.sub = self.__connect()

    def stop(self):
        '''Stops to listen to the data stream, closes websocket connection, stops the worker thread
           and clears the plot data.
        '''
        self.wamp.leave()
        self.wamp = None
        self.__clear_data()

    def replot(self):
        self.wamp.loop.call_soon_threadsafe(self.__replot)

    def set_data(self,pkt):
        self.wamp.loop.call_soon_threadsafe(self.__set_data,pkt)

    def append(self,pkt):
        self.wamp.loop.call_soon_threadsafe(self.__append,pkt)

    def __replot(self):
        self.axes.cla()
        self.axes.set_title(self.pol)

        items = deepcopy(self.items)

        for t in items:
            for hk in items[t]:
                if t == 'SCI_POL':
                    self.data['SCI_POL'][hk]['line'], = self.axes.plot(self.data['ts'],self.data['SCI_POL'][hk]['data'],label=t+"-"+hk)
                else:
                    self.data[t][hk]['line'], = self.axes.plot(self.data[t][hk]['ts'],self.data[t][hk]['data'],label=t+"-"+hk)

        self.axes.legend(loc='upper right')
        self.axes.set_xlim([0,self.wsec])
        self.date = self.axes.text(0.01,0.01,"",verticalalignment='bottom', horizontalalignment='left',transform=self.axes.transAxes)


    def __prepare_canvas(self):
        self.draw()   # note that the first draw comes before setting data
        self.__replot()

    def __connect(self):
        self.wamp.connect(self.url,self.conf.get_wamp_realm())

        s = time.time()
        while not self.wamp.session.is_attached():
            if time.time() - s > 5:
                raise RuntimeError('Cannot attach to WAMP session')
            time.sleep(0.1)

        self.t0 = time.time()
        return self.wamp.subscribe(self.__recv,self.conf.get_wamp_pol(self.pol))

    def __recv(self,*args,**pkt):
        t1 = time.time()
        self.append(pkt)

        if t1 - self.t0 > self.rsec:
            self.t0 = t1
            self.set_data(pkt)


    def __append(self,pkt):
        ts = pkt['mjd']
        if self.data['ts'].size == 0 or (ts - self.data['ts'][0])*86400 <= self.wsec:
            if 'DEMU1' in pkt.keys():
                for s in self.data['SCI_POL'].keys():
                    self.data['SCI_POL'][s]['data'] = np.append(self.data['SCI_POL'][s]['data'],pkt[s]) #TODO do calibration

                self.data['ts']  = np.append(self.data['ts'],ts)

            for hk,val in pkt.get('bias',{}).items():
                self.data['BIAS_POL'][hk]['data'] =  np.append(self.data['BIAS_POL'][hk]['data'],val) #TODO do calibration
                self.data['BIAS_POL'][hk]['ts']  = np.append(self.data['BIAS_POL'][hk]['ts'],ts)
            for hk,val in pkt.get('daq',{}).items():
                self.data['DAQ_POL'][hk]['data'] =  np.append(self.data['DAQ_POL'][hk]['data'],val) #TODO do calibration
                self.data['DAQ_POL'][hk]['ts']  = np.append(self.data['DAQ_POL'][hk]['ts'],ts)
        else:
            if 'DEMU1' in pkt.keys():
                for s in self.data['SCI_POL'].keys():
                    self.data['SCI_POL'][s]['data'][0] = pkt[s] #TODO do calibration
                    self.data['SCI_POL'][s]['data'] = np.roll(self.data['SCI_POL'][s]['data'],-1)

                self.data['ts'][0]  = ts
                self.data['ts'] = np.roll(self.data['ts'],-1)

            for hk,val in pkt.get('bias',{}).items():
                self.data['BIAS_POL'][hk]['data'][0] = val #TODO do calibration
                self.data['BIAS_POL'][hk]['data'] = np.roll(self.data['BIAS_POL'][hk]['data'],-1)

                self.data['BIAS_POL'][hk]['ts'][0] = ts
                self.data['BIAS_POL'][hk]['ts'] = np.roll(self.data['BIAS_POL'][hk]['ts'],-1)

            for hk,val in pkt.get('daq',{}).items():
                self.data['DAQ_POL'][hk]['data'][0] = val #TODO do calibration
                self.data['DAQ_POL'][hk]['data'] = np.roll(self.data['DAQ_POL'][hk]['data'],-1)

                self.data['DAQ_POL'][hk]['ts'][0] = ts
                self.data['DAQ_POL'][hk]['ts'] = np.roll(self.data['DAQ_POL'][hk]['ts'],-1)


    def __set_data(self,pkt):
        date_ts = at.Time(pkt['mjd'], format='mjd').to_datetime()
        min = np.nan
        max = np.nan

        for t in self.items:
            for hk in self.items[t]:
                if t == 'SCI_POL':
                    self.data['SCI_POL'][hk]['line'].set_xdata((pkt['mjd'] - self.data['ts'])*86400)
                    self.data['SCI_POL'][hk]['line'].set_ydata(self.data['SCI_POL'][hk]['data'])
                    min = np.nanmin([np.min(self.data['SCI_POL'][hk]['data']),min])
                    max = np.nanmax([np.max(self.data['SCI_POL'][hk]['data']),max])
                else:
                    if self.data[t][hk]['data'].size > 0:
                        self.data[t][hk]['line'].set_xdata((pkt['mjd'] - self.data[t][hk]['ts'])*86400)
                        self.data[t][hk]['line'].set_ydata(self.data[t][hk]['data'])
                        min = np.nanmin([np.min(self.data[t][hk]['data']),min])
                        max = np.nanmax([np.max(self.data[t][hk]['data']),max])

        if not (np.isnan(min) or np.isnan(max)):
            exc = (max-min) / 100 * 2
            self.axes.set_ylim([min-exc,max+exc])
            self.date.set_text(date_ts.strftime("%H:%M:%S.%f"))
            self.flush_events()
            self.draw()


    def __clear_data(self):
        self.data={}
        self.data['SCI_POL'] = {}
        for s in self.conf.board_addr['SCI_POL']:
            self.data['SCI_POL'][s['name']] = {'data':np.ndarray([0],dtype=np.float64)}

        self.data['ts'] = np.ndarray([0],dtype=np.float64)

        for table in ['BIAS_POL','DAQ_POL']:
            self.data[table] = {}
            for hk in self.conf.board_addr[table]:
                self.data[table][hk['name']] = {
                    'data': np.ndarray([0], dtype=np.float64),
                    'ts'  : np.ndarray([0], dtype=np.float64)
                    }
