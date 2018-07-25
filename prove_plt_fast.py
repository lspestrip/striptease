import time
from matplotlib import pyplot as plt
import numpy as np
from web.ws.base import WsBase
from config import Config
import asyncio
from web.rest.base import Connection
import astropy.time as at
import matplotlib
matplotlib.use('Qt5Agg')

SAMPLES=5000

SCI = ['DEMU1','DEMU2','DEMQ1','DEMQ2','PWRQ1','PWRQ2','PWRU1','PWRU2']

conf = Config()
conn = Connection()
conn.login('stefano.sartor','lucciola88')
ws =  WsBase(conn)

data={}
for s in SCI:
    data[s] = np.ndarray([SAMPLES], dtype=np.float64)
    data[s].fill(np.NAN)

data['ts'] = np.ndarray([SAMPLES],dtype=np.float64)
data['ts'].fill(np.NAN)

for hk in conf.conf['daq_addr']['hk']:
    data[hk['name']] = {
        'data': np.ndarray([SAMPLES], dtype=np.float64),
        'ts'  : np.ndarray([SAMPLES], dtype=np.float64)
        }
    data[hk['name']]['data'].fill(np.NAN)
    data[hk['name']]['ts'].fill(np.NAN)



loop = asyncio.get_event_loop()
url = conf.get_ws_pol('R0')


async def recv():
    global data,ts
    pkt = await ws.recv()
    ts = pkt['mjd']

    for s in SCI:
        data[s][0] = pkt[s] #TODO do calibration
        data[s] = np.roll(data[s],-1)

    data['ts'][0]  = ts
    data['ts'] = np.roll(data['ts'],-1)

    for hk,val in pkt.get('hk',{}).items():
        data[hk]['data'][0] = val #TODO do calibration
        data[hk]['data'] = np.roll(data[hk]['data'],-1)

        data[hk]['ts'][0] = ts
        data[hk]['ts'] = np.roll(data[hk]['ts'],-1)


def live_update_demo(blit = False):
    global data,ts
    loop.run_until_complete(ws.connect(url))


    fig = plt.figure()
    ax2 = fig.add_subplot(2, 1, 2)

    fig.canvas.draw()   # note that the first draw comes before setting data


    h2, = ax2.plot(data['ts'], data['DEMU1'])
    text = ax2.text(0.8,1.5, "")
    ax2.set_ylim([-200,200])
    ax2.set_xlim([0,30])


    if blit:
        # cache the background
        ax2background = fig.canvas.copy_from_bbox(ax2.bbox)

    t_start = time.time()
    k=0.
    i=0
    while True:
        t0=time.time()
        loop.run_until_complete(recv())
        tr = time.time()-t0
        tts = data['ts'][-1]

        h2.set_xdata((tts-data['ts'])*86400)
        h2.set_ydata(data['DEMU1'])
        tx = 'Mean Frame Rate:\n {fps:.3f}Time\n Queue:{queue:d}'.format(fps= (((time.time() - t_start)/(i+1)-tr)*1000), queue=ws.ws.messages.qsize() )
        text.set_text(tx)
        #print tx
        k+=0.11
        if blit:
            # restore background
            #fig.canvas.restore_region(axbackground)
            fig.canvas.restore_region(ax2background)

            # redraw just the points
            ax2.draw_artist(h2)

            # fill in the axes rectangle
            ##fig.canvas.blit(ax2.bbox)
            # in this post http://bastibe.de/2013-05-30-speeding-up-matplotlib.html
            # it is mentionned that blit causes strong memory leakage.
            # however, I did not observe that.
        else:
            # redraw everything
            fig.canvas.draw()
            fig.canvas.flush_events()

        plt.pause(0.000000000001)
        i += 1
        #plt.pause calls canvas.draw(), as can be read here:
        #http://bastibe.de/2013-05-30-speeding-up-matplotlib.html
        #however with Qt4 (and TkAgg??) this is needed. It seems,using a different backend,
        #one can avoid plt.pause() and gain even more speed.


live_update_demo(True) # 28 fps
#live_update_demo(False) # 18 fps
