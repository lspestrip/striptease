import websockets
import json
import asyncio
from web.rest.base import Connection

class WsBase(object):
    def __init__(self,con):
        self.conn = con
        self.ws =  None
        self.is_connected = False
        self.url = None

    async def connect(self,url):
        self.url = url
        if self.conn.id is None:
            self.conn.login()

        self.ws = await websockets.connect(url,extra_headers=[('Cookie','sessionid=%s'%self.conn.id)])
        self.is_connected = True

    async def recv(self):
        message = await self.ws.recv()
        pkt = json.loads(message)
        return pkt
