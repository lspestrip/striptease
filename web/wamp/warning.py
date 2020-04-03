# web/ws/warning.py --- class handling the real time warnigns
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it

from web.rest.base import Connection
from config import Config
from calibration import Calibration
from .base import WsBase
import warnings
import asyncio


class WsWarning(object):
    def __init__(self, con, loop=None):
        """:param web.rest.base.Connection con: the base http connection
        """
        self.conn = con
        conf = Config()
        self.ws = None
        self.cal = Calibration()
        self.url = conf.get_rest_base() + "/warning"
        self.ws_url = conf.get_ws_base() + "/warn"
        self.configs = []
        if loop is not None:
            self.loop = loop
        else:
            self.loop = asyncio.new_event_loop()

        self.__current = {}

    def get_configs(self):
        if len(self.configs) == 0:
            try:
                pkt = self.conn.get(self.url)
                if pkt["status"] == "OK":
                    for c in pkt["configs"]:
                        u = self.url + "/" + str(c["id"])
                        pkt_c = self.conn.get(u)
                        if pkt_c["status"] == "OK":
                            c = {"id": c["id"], "name": pkt_c["name"], "config": []}
                            for w in pkt_c["data"]:
                                pol = w["pol"]
                                hk = w["warn"]
                                c["config"].append(
                                    {
                                        "pol": pol,
                                        "hk": hk,
                                        "min_a": self.cal.calibrate(
                                            pol, hk, w["min_a"]
                                        ),
                                        "min_w": self.cal.calibrate(
                                            pol, hk, w["min_w"]
                                        ),
                                        "max_w": self.cal.calibrate(
                                            pol, hk, w["max_w"]
                                        ),
                                        "max_a": self.cal.calibrate(
                                            pol, hk, w["max_a"]
                                        ),
                                    }
                                )
                            self.configs.append(c)
                        else:
                            warnings.warn(
                                "error while loading configuration", RuntimeWarning
                            )
                else:
                    warnings.warn("error while loading configurations", RuntimeWarning)
            except Exception as e:
                warnings.warn(str(e), RuntimeWarning)
        return self.configs

    def set_config(self, conf):
        if type(conf) == int:  # load conf from id
            self.get_configs()
            for i in self.configs:
                if conf == i["id"]:
                    self.__set_config(i)
                    break
            else:
                raise RuntimeError("config not found")
        elif type(conf) == str:
            self.get_configs()
            for i in self.configs:
                if conf == i["name"]:
                    self.__set_config(i)
                    break
            else:
                raise RuntimeError("config not found")
        elif type(conf) == dict:  # set new config
            self.__set_config(conf)
        else:
            raise RuntimeError("Bad Configuration")

    def add_warning(self, pol, hk, min_a, min_w, max_w, max_a):
        warn = {
            "pol": pol,
            "warn": hk,
            "min_a": self.cal.reverse(pol, hk, min_a),
            "min_w": self.cal.reverse(pol, hk, min_w),
            "max_w": self.cal.reverse(pol, hk, max_w),
            "max_a": self.cal.reverse(pol, hk, max_a),
        }
        if self.__current.get("config") is None:
            self.__current["config"] = []
        self.__current["config"].append(warn)

        if self.ws is not None:
            self.__add_warning(warn)

    async def connect(self):
        if self.ws is None:
            self.ws = WsBase(self.conn)
            await self.ws.connect(self.ws_url)

    def clear_config(self):
        if self.ws is not None and self.__current.get("config") is not None:
            for c in self.__current["config"]:
                pkt = {"pol": c["pol"], "remove": c["warn"]}
                self.loop.call_soon_threadsafe(asyncio.async, self.ws.send(pkt))
        self.__current = {}

    def save_config(self, name=None, force_new=False):
        if force_new and self.__current.get("id") is not None:
            del self.__current["id"]

        if name is not None:
            self.__current["name"] = name
        pkt = {
            "save": self.__current.get("name", "unnamed_config"),
            "config": self.__current.get("config", []),
        }
        res = {"status": "ERROR"}
        if self.__current.get("id") is None:  # save new config
            res = self.conn.post(self.url, message)
        else:  # update existing conf
            url = self.url + "/" + str(self.__current["id"])
            res = self.conn.put(self.url, pkt)
        if res["status"] == "OK":
            self.__current["id"] = res["id"]

    async def recv(self):
        """ waits for warning packet and decodes it from json string
           :return: dictionary of the decoded json.
        """
        pkt = await self.ws.recv()
        return pkt

    def __set_config(self, conf):
        self.clear_config()
        self.__current = {"config": []}
        self.__current["id"] = conf.get("id")
        self.__current["name"] = conf.get("name")
        for c in conf["config"]:
            pol = c["pol"]
            hk = c["hk"]
            warn = {
                "pol": pol,
                "warn": hk,
                "min_a": self.cal.reverse(pol, hk, c["min_a"]),
                "min_w": self.cal.reverse(pol, hk, c["min_w"]),
                "max_w": self.cal.reverse(pol, hk, c["max_w"]),
                "max_a": self.cal.reverse(pol, hk, c["max_a"]),
            }
            self.__current["config"].append(warn)
            if self.ws is not None:
                self.__add_warning(warn)

    def __add_warning(self, warn):
        self.loop.call_soon_threadsafe(asyncio.async, self.ws.send(warn))
