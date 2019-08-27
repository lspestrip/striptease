
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
import pipes
import asyncio
import os
import json

class UnixProtocol(asyncio.Protocol):
    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        print('connection made:',transport)

    def connection_lost(self, exc):
        print('The server closed the connection')
        self.transport = None

    def write(self,data):
        if self.transport is not None:
            self.transport.write(data)


class Worker(object):
    def __init__(self,conn,pol,path):

        self.pol = pol
        self.path = path
        self.conn = conn
        self.conf = Config()
        self.conf.load(self.conn)
        #t = pipes.Template()
        #self.pipe = t.open(path, 'w')

    def start(self):
        #self.p = mp.Process(target=self.__process_loop)
        #self.p.start()
        self.__process_loop()

    def stop(self):
        self.p.terminate()

    def __process_loop(self):
        print('process loop')
        self.wamp = WampBase(self.conn)
        self.wamp.connect(self.conf.get_wamp_url(),self.conf.get_wamp_realm())

        s = time.time()
        while not self.wamp.session.is_attached():
            if time.time() - s > 5:
                raise RuntimeError('Cannot attach to WAMP session')
            time.sleep(0.1)

        print('session attached')
        f = open(self.path,'wb',buffering=2048)
        print('file opened')
        coro = self.wamp.loop.connect_write_pipe(UnixProtocol, f)
        print('created coro')
        fut = asyncio.run_coroutine_threadsafe(coro,self.wamp.loop)
        print('prima fut')
        (_,self.outpipe) = fut.result()

        self.wamp.subscribe(self.recv,self.conf.get_wamp_pol(self.pol))
        self.wamp.th.join()

    def recv(self,*args,**pkt):
        self.outpipe.write(json.dumps(pkt).encode())


path = '/tmp/strip.pol.G0'

def read_loop():
    global path
    os.mkfifo(path)
    #f = open(path,'rt')
    while(True):
        time.sleep(10)

if __name__ == '__main__':
    con = Connection()
    con.login()

    th = Thread(target=read_loop)
    th.start()


    e = Worker(con,'G0',path)
    e.start()
