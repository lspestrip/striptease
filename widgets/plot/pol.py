from widgets.plot import MplCanvas
from web.ws.base import WsBase
from config import Config
import asyncio
from threading import Thread
import numpy as np
import time
import astropy.time as at
import datetime as dt
import gc

def f(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


SCI = ['DEMU1','DEMU2','DEMQ1','DEMQ2','PWRQ1','PWRQ2','PWRU1','PWRU2']

class PolMplCanvas(MplCanvas):
    def __init__(self, *args, **kwargs):
        MplCanvas.__init__(self, *args, **kwargs)
        self.conf = Config()
        self.loop = asyncio.new_event_loop()
        self.th = Thread(target=f, args=(self.loop,))
        self.data={}

        for s in SCI:
            self.data[s] = np.ndarray([0], dtype=np.float64)

        self.data['ts'] = np.ndarray([0],dtype=dt.datetime)

        for hk in self.conf.conf['daq_addr']['hk']:
            self.data[hk['name']] = {
                'data': np.ndarray([0], dtype=np.float64),
                'ts'  : np.ndarray([0], dtype=dt.datetime)
                }

    def start(self,conn,pol,sec=30,items=SCI):
        self.url = self.conf.get_ws_pol(pol)
        self.ws  = WsBase(conn)
        self.sec = sec
        self.items = items

        self.loop.call_soon_threadsafe(asyncio.async,self.recv())
        self.th.start()

    def __append(self,pkt):
        ts = at.Time(pkt['mjd'], format='mjd').to_datetime()

        if self.data['ts'].size == 0 or (ts - self.data['ts'][0]).total_seconds() <= self.sec:
            for s in SCI:
                self.data[s] = np.append(self.data[s],pkt[s]) #TODO do calibration

            self.data['ts']  = np.append(self.data['ts'],ts)

            for hk,val in pkt.get('hk',{}).items():
                self.data[hk]['data'] =  np.append(self.data[hk]['data'],val) #TODO do calibration
                self.data[hk]['ts']  = np.append(self.data[hk]['ts'],ts)
        else:
            for s in SCI:
                self.data[s][0] = pkt[s] #TODO do calibration
                self.data[s] = np.roll(self.data[s],-1)

            self.data['ts'][0]  = ts
            self.data['ts'] = np.roll(self.data['ts'],-1)

            for hk,val in pkt.get('hk',{}).items():
                self.data[hk]['data'][0] = val #TODO do calibration
                self.data[hk]['data'] = np.roll(self.data[hk]['data'],-1)

                self.data[hk]['ts'][0] = ts
                self.data[hk]['ts'] = np.roll(self.data[hk]['ts'],-1)

    def stop(self):
        self.loop.stop()
        if self.th.is_alive():
            self.th.join()

    async def recv(self):
        await self.ws.connect(self.url)
        t0 = time.time()

        while True:
            pkt = await self.ws.recv()

            t1 = time.time()
            self.__append(pkt)

            if t1 - t0 > 0.5:
                t0 = t1
                dt0=time.time()
                self.axes.cla()
                for i in self.items:
                    if i in SCI:
                        self.axes.plot(self.data['ts'],self.data[i])
                    else:
                        self.axes.plot(self.data[i]['ts'],self.data[i]['data'])

                self.draw()
                print((time.time()-dt0)*1000)
