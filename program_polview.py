import sys
import os
import asyncio
from program_polview.worker import Worker
from web.rest.base import Connection
from widgets.login import LoginWidget
from config import Config
from PyQt5 import QtCore, QtWidgets
from threading import Thread
import subprocess as sp
import json

class UnixProtocolR(asyncio.Protocol):
    def __init__(self):
        self.workers = {}
        self.len=0
        self.transport = None

    def set_con(self,con):
        self.conn = con

    def connection_made(self, transport):
        self.transport = transport
        print('connection made:',transport)

    def connection_lost(self, exc):
        print('program exiting...')
        self.transport = None
        sys.exit(0)

    def data_received(self, data):
        try:
            a = json.loads(data)
            if a.get("cmd"):
                print('CMD:', a)
                if a['cmd'] == "attach_pipe":
                    pol  = a['pol']
                    path = a['path']
                    w = Worker(self.conn,pol,path)
                    w.start()
                    self.workers[pol] = w
                if a['cmd'] == "detach_pipe":
                    print('detach')
                    pol  = a['pol']
                    self.workers[pol].stop()
                    del self.workers[pol]

            #print('json',a)
        except json.JSONDecodeError as e:
            print('STDOUT:',str(data,encoding='utf-8'),"END")
            #pass

        self.len += len(data)

class UnixProtocolW(asyncio.Protocol):
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

loop = None

def th_loop():
    global loop
    if loop:
        loop.run_forever()

if __name__ == "__main__":
    loop  = asyncio.new_event_loop()
    th = Thread(target=th_loop)
    th.start()

    conn = Connection()
    if conn.has_login():
        conn.login()
    else:
        app = QtWidgets.QApplication(sys.argv)
        dialog = LoginWidget()
        dialog.exec_()
        conn.login(dialog.user,dialog.password)

    conf = Config()
    conf.load(conn)

    gui = sp.Popen(["program_polview/bin/program_polview","-u",conn.user,"-p",conn.password],stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    coro = loop.connect_read_pipe(UnixProtocolR, gui.stdout)
    fut = asyncio.run_coroutine_threadsafe(coro,loop)
    (_,inpipe) = fut.result()
    inpipe.set_con(conn)

    coro = loop.connect_write_pipe(UnixProtocolW, gui.stdin)
    fut = asyncio.run_coroutine_threadsafe(coro,loop)
    (_,outpipe) = fut.result()

    outpipe.write(json.dumps(conf.boards).encode())
    #th.join()
