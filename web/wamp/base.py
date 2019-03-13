# web/ws/base.py --- Base websocket handling
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it
import websockets
import json
import asyncio
from web.rest.base import Connection
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from threading import Thread

class WampBase(object):
    '''Base class for websocket streaming
    '''
    def __init__(self,con):
        ''':param web.rest.base.Connection con: the base http connection
        '''
        self.conn    = con
        self.runner  = None
        self.url     = None
        self.loop    = None
        self.session = None
        self.th      = None

    def connect(self,url,realm):
        '''connect to websocket
           :param str url: url to which connect
        '''
        self.url = url
        if self.conn.id is None:
            self.conn.login()

        self.th = Thread(target=self.__f)
        self.runner = ApplicationRunner(url=url, ssl=True, realm=realm, headers={'cookie':'sessionid=%s' % self.conn.id})
        self.loop = asyncio.get_event_loop()
        self.session = ApplicationSession()
        coro = self.runner.run(self.session,start_loop = False)
        (self.__transport, self.__protocol) = self.loop.run_until_complete(coro)
        self.th.start()

    def subscribe(self,callback,topic):
        if self.session is None:
            raise RuntimeError('no Connection active')
        return self.session.subscribe(callback,topic)


    def leave(self):
        if self.session is not None:
            self.session.leave()
            self.stop()

    def stop(self):
        if self.loop is not None:
            self.loop.stop()
            self.loop = None

    def __f(self):
        #asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
