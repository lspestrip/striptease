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
        self.title = "None"
        self.t0 = time.time()

        self.p = self.addPlot()

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
        self.replot()

    def set_data(self,label,mjd,val):
        self.data[label]['mjd'] = mjd
        self.data[label]['val'] = val

    def update(self):
        for l in self.data:
            d = self.data[l]
            d['line'].setData(d['mjd'],d['val'])

    def del_plot(self,label):
        if self.data.get(label):
            del self.data[label]
        self.replot()

    def replot(self):
        self.p.clear()
        for l in self.data:
            d = self.data[l]
            c =  (d['color'][0]*255,d['color'][1]*255,d['color'][2]*255)
            pen = pg.mkPen(pg.mkColor(c),width=2)
            print(d['color'])
            d['line'] = self.p.plot(d['mjd'],d['val'],pen=pen)
