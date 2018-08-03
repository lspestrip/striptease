# web/ws/base.py --- Base websocket handling
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it
import websockets
import json
import asyncio
from web.rest.base import Connection

class WsBase(object):
    '''Base class for websocket streaming
    '''
    def __init__(self,con):
        ''':param web.rest.base.Connection con: the base http connection
        '''
        self.conn = con
        self.ws =  None
        self.is_connected = False
        self.url = None

    async def connect(self,url):
        '''connect to websocket
           :param str url: url to which connect
        '''
        self.url = url
        if self.conn.id is None:
            self.conn.login()

        self.ws = await websockets.connect(url,extra_headers=[('Cookie','sessionid=%s'%self.conn.id)])
        self.is_connected = True

    async def recv(self):
        '''receive one packet and decode it from json string
           :return: dictionary of the decoded json.
        '''
        message = await self.ws.recv()
        pkt = json.loads(message)
        return pkt
