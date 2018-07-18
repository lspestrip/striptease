from widgets.plot import MplCanvas
from web.ws.base import WsBase
from config import Config
import asyncio
from threading import Thread
import numpy as np
import time
import astropy.time as at
import datetime as dt

def f(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

class PolMplCanvas(MplCanvas):
    def __init__(self, *args, **kwargs):
        MyMplCanvas.__init__(self, *args, **kwargs)
        self.loop = asyncio.new_event_loop()
        self.th = Thread(target=f, args=(self.loop,))

    def start(self,conn,pol,sec=30,data=['DEMU1','DEMU1','DEMQ1','DEMQ2','PWRQ1','PWRQ2','PWRU1','PWRU2']):
        self.url = Config().get_ws_pol(pol)
        self.ws  = WsBase(conn)
        self.sec = sec
        self.items = data

        self.loop.call_soon_threadsafe(asyncio.async,self.recv())
        self.th.start()

    async def recv(self):
        await ws.connect(self.url)
        t0 = time.time()

        data = np.ndarray([0], dtype=np.int32)
        ts = np.ndarray([0],dtype=dt.datetime)

            while True:
            pkt = await ws.recv()
            t1 = time.time()
            tt = at.Time(pkt['mjd'], format='mjd')
            data = np.append(data,pkt['DEMU1'])
            ts   = np.append(ts,tt.to_datetime())

            if t1 - t0 > 0.2:
                t0 = t1
                wdg.axes.cla()
                wdg.axes.plot(ts,data)
                wdg.draw()
            if (ts[-1] - ts[0]).total_seconds() >= N_SEC:
                break
        print("rotating buffer from now on")
        while True:
            pkt = await ws.recv()

            data[0] = pkt['DEMU1']
            data = np.roll(data,-1)

            tt = at.Time(pkt['mjd'], format='mjd')
            ts[0] = tt.to_datetime()
            #print(ts[0])
            ts = np.roll(ts,-1)
            t1 = time.time()
            if t1 - t0 > 0.2:
                t0 = t1
                wdg.axes.cla()
                wdg.axes.plot(ts,data)
                wdg.draw()
