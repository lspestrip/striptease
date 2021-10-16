# widgets/plot/pol.py --- Polarimeter plot classes
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it
from widgets.plot import MplCanvas
import numpy as np
import time


obj = {"label": "legend label", "mjd": 580000, "val": 56.34}


class BaseMplCanvas(MplCanvas):
    """QtWidget for data plot"""

    def __init__(self, *args, **kwargs):
        MplCanvas.__init__(self, *args, **kwargs)
        self.data = {}
        self.wsec = 20
        self.rsec = 1.0
        self.loop = None
        self.title = ""
        self.t0 = time.time()
        self.draw()

    def set_loop(self, loop):
        self.loop = loop

    def set_window_sec(self, sec):
        self.wsec = sec

    def set_refresh(self, sec):
        self.rsec = sec

    def add_plot(self, label, color):
        data = {}
        data["color"] = color
        data["mjd"] = np.ndarray([0], dtype=np.float64)
        data["val"] = np.ndarray([0], dtype=np.float64)
        self.data[label] = data
        self.loop.call_soon_threadsafe(self.__replot)

    def del_plot(self, label):
        self.loop.call_soon_threadsafe(self.__del_plot, label)

    def set_data(self, label, mjd, val):
        self.loop.call_soon_threadsafe(self.__set_data, label, mjd, val)

    def commit_plot(self):
        self.loop.call_soon_threadsafe(self.__commit_plot)

    def replot(self):
        self.loop.call_soon_threadsafe(self.__replot)

    def __del_plot(self, label):
        if self.data.get(label):
            del self.data[label]
        self.__replot()

    def __replot(self):
        self.axes.cla()
        self.axes.set_title(self.title)

        for l in self.data:
            d = self.data[l]
            (d["line"],) = self.axes.plot(d["mjd"], d["val"], label=l, color=d["color"])

        self.axes.legend(loc="upper right")
        self.axes.set_xlim([0, self.wsec])

    def __set_data(self, label, mjd, val):
        self.data[label]["mjd"] = mjd
        self.data[label]["val"] = val

    def __commit_plot(self):
        min = np.nan
        max = np.nan

        for l in self.data:
            d = self.data[l]
            if d["val"].size == 0:
                continue
            d["line"].set_xdata(d["mjd"])
            d["line"].set_ydata(d["val"])
            min = np.nanmin([np.min(d["val"]), min])
            max = np.nanmax([np.max(d["val"]), max])

        if not (np.isnan(min) or np.isnan(max)):
            exc = (max - min) / 100 * 2
            self.axes.set_ylim([min - exc, max + exc])
            self.flush_events()
            self.draw()
