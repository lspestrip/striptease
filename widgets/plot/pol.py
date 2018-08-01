from widgets.plot import MplCanvas
from web.ws.base import WsBase
from config import Config
import asyncio
from threading import Thread, Semaphore
import numpy as np
import time
import astropy.time as at
import datetime as dt
import gc
import matplotlib.pyplot as plt
from copy import deepcopy


def f(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


SCI = ['DEMU1','DEMU2','DEMQ1','DEMQ2','PWRQ1','PWRQ2','PWRU1','PWRU2']


class PolMplCanvas(MplCanvas):
    def __init__(self, *args, **kwargs):
        MplCanvas.__init__(self, *args, **kwargs)
        self.conf = Config()
        self.loop = asyncio.new_event_loop()
        self.data={}
        self.mtx = Semaphore()

        self.list_add = []
        self.list_del = []

        self.__clear_data()

    def add_plot(self,hk):
        self.mtx.acquire()
        self.list_add.append(hk)
        self.mtx.release()

    def del_plot(self,hk):
        self.mtx.acquire()
        self.list_del.append(hk)
        self.mtx.release()

    def __replot(self):
        self.axes.cla()
        self.axes.set_title(self.pol)
        for i in self.items:
            if i in SCI:
                self.data[i]['line'], = self.axes.plot(self.data['ts'],self.data[i]['data'],label=i)
            else:
                self.data[i]['line'], = self.axes.plot(self.data[i]['ts'],self.data[i]['data'],label=i)

        self.axes.legend(loc='upper right')
        self.axes.set_xlim([0,self.wsec])
        self.date = self.axes.text(0.01,0.01,"",verticalalignment='bottom', horizontalalignment='left',transform=self.axes.transAxes)


    def prepare_canvas(self):
        self.draw()   # note that the first draw comes before setting data
        self.__replot()


    def start(self,conn,pol,window_sec=30,items=SCI,refresh=0.33):
        self.th = Thread(target=f, args=(self.loop,))
        self.url = self.conf.get_ws_pol(pol)
        self.pol = pol
        self.ws  = WsBase(conn)
        self.wsec = window_sec
        self.rsec = refresh
        self.items = deepcopy(items)

        self.prepare_canvas()

        self.loop.call_soon_threadsafe(asyncio.async,self.recv())
        self.th.start()


    def stop(self):
        self.loop.stop()

        if self.th.is_alive():
            self.th.join()

        self.loop.run_until_complete(self.ws.ws.close())
        self.th = None
        self.ws = None
        self.__clear_data()

    def __append(self,pkt):
        ts = pkt['mjd']

        if self.data['ts'].size == 0 or (ts - self.data['ts'][0])*86400 <= self.wsec:
            for s in SCI:
                self.data[s]['data'] = np.append(self.data[s]['data'],pkt[s]) #TODO do calibration

            self.data['ts']  = np.append(self.data['ts'],ts)

            for hk,val in pkt.get('hk',{}).items():
                self.data[hk]['data'] =  np.append(self.data[hk]['data'],val) #TODO do calibration
                self.data[hk]['ts']  = np.append(self.data[hk]['ts'],ts)
        else:
            for s in SCI:
                self.data[s]['data'][0] = pkt[s] #TODO do calibration
                self.data[s]['data'] = np.roll(self.data[s]['data'],-1)

            self.data['ts'][0]  = ts
            self.data['ts'] = np.roll(self.data['ts'],-1)

            for hk,val in pkt.get('hk',{}).items():
                self.data[hk]['data'][0] = val #TODO do calibration
                self.data[hk]['data'] = np.roll(self.data[hk]['data'],-1)

                self.data[hk]['ts'][0] = ts
                self.data[hk]['ts'] = np.roll(self.data[hk]['ts'],-1)


    def __set_data(self,pkt):
        date_ts = at.Time(pkt['mjd'], format='mjd').to_datetime()
        min = np.nan
        max = np.nan
        for i in self.items:
            if i in SCI:
                self.data[i]['line'].set_xdata((pkt['mjd'] - self.data['ts'])*86400)
                self.data[i]['line'].set_ydata(self.data[i]['data'])
                min = np.nanmin([np.min(self.data[i]['data']),min])
                max = np.nanmax([np.max(self.data[i]['data']),max])
            else:
                if self.data[i]['data'].size > 0:
                    self.data[i]['line'].set_xdata((pkt['mjd'] - self.data[i]['ts'])*86400)
                    self.data[i]['line'].set_ydata(self.data[i]['data'])
                    min = np.nanmin([np.min(self.data[i]['data']),min])
                    max = np.nanmax([np.max(self.data[i]['data']),max])

        if not (np.isnan(min) or np.isnan(max)):
            exc = (max-min) / 100 * 2
            self.axes.set_ylim([min-exc,max+exc])
            self.date.set_text(date_ts.strftime("%H:%M:%S.%f"))
            self.flush_events()
            self.draw()


    def __clear_data(self):
        for s in SCI:
            self.data[s] = {'data':np.ndarray([0],dtype=np.float64)}

        self.data['ts'] = np.ndarray([0],dtype=np.float64)

        for hk in self.conf.conf['daq_addr']['hk']:
            self.data[hk['name']] = {
                'data': np.ndarray([0], dtype=np.float64),
                'ts'  : np.ndarray([0], dtype=np.float64)
                }

    async def recv(self):
        await self.ws.connect(self.url)
        t0 = time.time()

        while True:
            try:
                pkt = await self.ws.recv()
            except Exception as e:
                print(e)
                break

            t1 = time.time()
            self.__append(pkt)

            if t1 - t0 > self.rsec:
                t0 = t1
                if len(self.list_add) != 0 or len(self.list_del) != 0:
                    self.mtx.acquire()
                    for i in self.list_add:
                        if i not in self.items:
                            self.items.append(i)
                    for i in self.list_del:
                        if i in self.items:
                            self.items.remove(i)
                    self.list_add.clear()
                    self.list_del.clear()
                    self.mtx.release()
                    self.__replot()
                else:
                    self.__set_data(pkt)
