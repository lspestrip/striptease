
from web.rest.base import Connection
from web.wamp.base import WampBase
from config import Config
import multiprocessing as mp
import numpy as np
import time
import queue
from copy import deepcopy
import sys
from threading import Thread


#colorscale
import matplotlib.cm

def get_color():
    c = np.random.rand(1)[0]
    cmap = matplotlib.cm.get_cmap('plasma')
    return cmap(c)

class Engine(object):
    def __init__(self,conn,pol,color=None,window_sec=30.0):
        if color is None:
            self.color = get_color()
        else:
            self.color = color

        self.key_sci = ['PWRQ1','PWRQ2','PWRU1','PWRU2','DEMQ1','DEMQ2','DEMU1','DEMU2']
        self.key_lna = []
        for lna in ['0','1','2','3','4','5','4a','5a']:
            up = lna.upper()
            self.key_lna.append('VD'+up+'_HK')
            self.key_lna.append('ID'+up+'_HK')
            self.key_lna.append('VG'+up+'_HK')
            self.key_lna.append('IG'+up+'_HK')
        self.key_hk = []

        self.lock = mp.Lock()
        self.sync_data_plot = {}
        self.sync_data_stats = {}
        self.sync_ws = window_sec

        self.data_plot = {}
        self.data_stats = {}

        self.pol = pol
        self.conn = conn
        self.conf = Config()
        self.conf.load(self.conn)
        self.queue_data = mp.Queue()

        self.request_queue = mp.Queue()
        self.response_queue = mp.Queue()

    def start(self):
        self.p = mp.Process(target=self.__process_loop)
        self.p.start()

    def stop(self):
        self.request_queue.put(['stop'])

    def __process_loop(self):
        self.wamp = WampBase(self.conn)
        self.wamp.connect(self.conf.get_wamp_url(),self.conf.get_wamp_realm())

        s = time.time()
        while not self.wamp.session.is_attached():
            if time.time() - s > 5:
                raise RuntimeError('Cannot attach to WAMP session')
            time.sleep(0.1)

        for i in self.key_sci:
            self.__create_plot(i,self.color)
        for lna in self.key_lna:
            self.__create_plot(lna)

        for hk_dict in [x  for x in self.conf.board_addr['BIAS_POL'] if x['name'][-2:] == 'HK' ]:
            hk = hk_dict['name']
            self.key_hk.append(hk)
            self.data_stats[hk] = {}
            self.data_stats[hk]['val'] = np.ndarray([0],dtype=np.float64)
            self.data_stats[hk]['mjd'] = np.ndarray([0],dtype=np.float64)

            self.sync_data_stats[hk] = {}
            self.sync_data_stats[hk]['avg'] = np.nan
            self.sync_data_stats[hk]['std'] = np.nan


        self.wamp.subscribe(self.recv,self.conf.get_wamp_pol(self.pol))
        self.th_cmd = Thread(target=self.__req_loop)
        self.th_cmd.start()

        while True:
            pkt = self.queue_data.get()
            self.process_pkt(pkt)


    def __create_plot(self,key,color=None):
        self.sync_data_plot[key] = {}
        self.data_plot[key] = {}
        if color is not None:
            self.sync_data_plot[key]['color'] = color
        else:
            self.sync_data_plot[key]['color'] = get_color()

        self.sync_data_plot[key]['mjd'] = np.ndarray([0],dtype=np.float64)
        self.sync_data_plot[key]['val'] = np.ndarray([0],dtype=np.float64)
        self.data_plot[key]['mjd'] = np.ndarray([0],dtype=np.float64)
        self.data_plot[key]['val'] = np.ndarray([0],dtype=np.float64)

    def get_window_sec(self):
        self.request_queue.put(['get_ws'])
        ws = self.response_queue.get()
        return ws

    def set_window_sec(self,ws):
        self.request_queue.put(['set_ws',ws])

    def get_data_plot(self):
        self.request_queue.put(['sync_data_plot'])
        data = self.response_queue.get()
        return data

    def get_data_stats(self):
        self.request_queue.put(['sync_data_stats'])
        data = self.response_queue.get()
        return data

    def recv(self,*args,**pkt):
        self.queue_data.put(pkt)

    def process_cmd(self,cmd):
        if cmd[0] == 'get_ws':
            self.response_queue.put(self.sync_ws)
        elif cmd[0] == 'set_ws':
            self.sync_ws = cmd[1]
        elif cmd[0] == 'sync_data_plot':
            self.response_queue.put(self.sync_data_plot)
        elif cmd[0] == 'sync_data_stats':
            self.response_queue.put(self.sync_data_stats)
        elif cmd[0] == 'stop':
            self.wamp.leave()
            self.wamp.stop()
            sys.exit(0)
        else:
            print('bad command:',cmd)

    def process_pkt(self,pkt):
        wsec = self.sync_ws
        mjd = pkt['mjd']
        if pkt.get('PWRQ1'):
            for i in self.key_sci:
                self.__add2plot(wsec,i,mjd,pkt[i])
        elif pkt.get('bias'):
            for hk in pkt['bias']:
                if hk in self.key_lna:
                    self.__add2plot(wsec,hk,mjd,pkt['bias'][hk])
                if hk in self.key_hk:
                    self.__add2stats(wsec,hk,mjd,pkt['bias'][hk])

            for key in self.data_plot:
                self.sync_data_plot[key]['mjd'] = (mjd - self.data_plot[key]['mjd'])*86400
                self.sync_data_plot[key]['val'] = self.data_plot[key]['val']

    def __add(self,wsec,d,mjd,val):
        if d['mjd'].size == 0 or (mjd - d['mjd'][0])*86400 <= wsec:
            d['mjd'] = np.append(d['mjd'],mjd)
            d['val'] = np.append(d['val'],val)

        else:
            d['mjd'][0] = mjd
            d['val'][0] = val

            d['mjd'] = np.roll(d['mjd'],-1)
            d['val'] = np.roll(d['val'],-1)

    def __add2stats(self,wsec,label,mjd,val):
        self.__add(wsec,self.data_stats[label],mjd,val)
        self.sync_data_stats[label]['avg'] = self.data_stats[label]['val'].mean()
        self.sync_data_stats[label]['std'] = np.std(self.data_stats[label]['val'])

    def __add2plot(self,wsec,label,mjd,val):
        self.__add(wsec,self.data_plot[label],mjd,val)


    def __req_loop(self):
        while True:
            cmd = self.request_queue.get()
            self.process_cmd(cmd)



if __name__ == '__main__':
    con = Connection()
    con.login()

    e = Engine(con,'G0')
    e.start()
