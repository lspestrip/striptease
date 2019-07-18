import sys
import pyqtgraph as pg
import pyqtgraph.widgets.RemoteGraphicsView
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
import time



obj = {
    'label' : 'legend label',
    'mjd' : 580000,
    'val' : 56.34
}

class CustomWidget(pg.GraphicsWindow):
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')
    '''QtWidget for data plot
    '''
    def __init__(self, parent=None, **kwargs):
        pg.GraphicsWindow.__init__(self, **kwargs)
        self.setParent(parent)
        self.data={}
        self.wsec = 20
        self.rsec = 0.034
        self.loop = None
        self.title = "PIPPO"
        self.t0 = time.time()

        self.p = self.addPlot()

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

    def add_data(self,label,mjd,val):
        self.loop.call_soon_threadsafe(self.__append,label,mjd,val)

    def del_plot(self,label):
        self.loop.call_soon_threadsafe(self.__del_plot,label)

    def replot(self):
        self.loop.call_soon_threadsafe(self.__replot)

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
        for l in self.data:
            d = self.data[l]
            d['line'].setData((mjd - d['mjd'])*86400,d['val'])

    def __del_plot(self,label):
        if self.data.get(label):
            del self.data[label]
        self.replot()

    def __replot(self):
        self.p.clear()
        for l in self.data:
            d = self.data[l]
            c =  (d['color'][0]*255,d['color'][1]*255,d['color'][2]*255)
            pen = pg.mkPen(pg.mkColor(c),width=2)
            print(d['color'])
            d['line'] = self.p.plot(d['mjd'],d['val'],pen=pen)
