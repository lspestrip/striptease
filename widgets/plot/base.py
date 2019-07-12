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


obj = {
    'label' : 'legend label',
    'mjd' : 580000,
    'val' : 56.34
}

class BaseMplCanvas(MplCanvas):
    '''QtWidget for data plot
    '''
    def __init__(self, *args, **kwargs):
        MplCanvas.__init__(self, *args, **kwargs)
        self.data={}
        self.dict_add = {}
        self.dict_del = {}
        self.wsec = 20
        self.rsec = 1.0
        self.loop = None
        self.title = "PIPPO"
        self.t0 = time.time()
        self.draw()

    def set_loop(self,loop):
        self.loop = loop

    def set_window_sec(self,sec):
        self.wsec = sec

    def set_refresh(self,sec):
        self.rsec = sec


    def add_plot(self,label,color):
        data = {}
        data['color'] = color
        data['mjd'] = np.ndarray([0],dtype=np.float64)
        data['val'] = np.ndarray([0],dtype=np.float64)
        self.data[label] = data
        self.loop.call_soon_threadsafe(self.__replot)

    def del_plot(self,label):
        self.loop.call_soon_threadsafe(self.__del_plot,label)

    def add_data(self,label,mjd,val):
        self.loop.call_soon_threadsafe(self.__append,label,mjd,val)


    def replot(self):
        self.loop.call_soon_threadsafe(self.__replot)

    def __del_plot(self,label):
        if self.data.get(label):
            del self.data[label]
        self.__replot()

    def __replot(self):
        self.axes.cla()
        self.axes.set_title(self.title)

        for l in self.data:
            d = self.data[l]
            d['line'], = self.axes.plot(d['mjd'],d['val'],label=l,color=d['color'])

        self.axes.legend(loc='upper right')
        self.axes.set_xlim([0,self.wsec])
        #self.date = self.axes.text(0.01,0.01,"",verticalalignment='bottom', horizontalalignment='left',transform=self.axes.transAxes)

    def __append(self,label,mjd,val):
        t1 = time.time()
        d = self.data[label]

        if d['mjd'].size == 0 or (mjd - d['mjd'][0])*86400 <= self.wsec:
            d['mjd'] = np.append(d['mjd'],mjd)
            d['val'] = np.append(d['val'],val)

        else:
            d['mjd'][0] = mjd
            d['val'][0] = val

            d['mjd'] = np.roll(d['mjd'],-1)
            d['val'] = np.roll(d['val'],-1)

        if t1 - self.t0 > self.rsec:
            self.t0 = t1
            self.__set_data(mjd)


    def __set_data(self,mjd):
        #date_ts = at.Time(mjd, format='mjd').to_datetime()
        min = np.nan
        max = np.nan

        for l in self.data:
            d = self.data[l]
            if d['val'].size == 0:
                continue
            d['line'].set_xdata((mjd - d['mjd'])*86400)
            d['line'].set_ydata(d['val'])
            min = np.nanmin([np.min(d['val']),min])
            max = np.nanmax([np.max(d['val']),max])

        if not (np.isnan(min) or np.isnan(max)):
            exc = (max-min) / 100 * 2
            self.axes.set_ylim([min-exc,max+exc])
            #self.date.set_text(date_ts.strftime("%H:%M:%S.%f"))
            self.flush_events()
            self.draw()
