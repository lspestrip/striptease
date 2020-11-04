# config/__init__.py --- Simple cnfiguration wrapper
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it

import json
import os


class Config(object):
    """the Config class parses the configuration file and provides shortcuts for
    common functionalities.

    Attributes:
       conf     dictionary with all the configuration settings
    """

    def __init__(self):
        path_dir = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(path_dir, "conf.json")
        with open(path, "rt") as c:
            js = c.read()
            self.conf = json.loads(js)

        user_path = os.path.expandvars(self.conf["user_conf"])
        user_path = os.path.expanduser(user_path)
        user_path = os.path.abspath(user_path)

        if (
            os.environ.get("STRIP_USER") is not None
            and os.environ.get("STRIP_PASSWORD") is not None
        ):
            self.user = os.environ["STRIP_USER"]
            self.password = os.environ["STRIP_PASSWORD"]
        elif os.path.isfile(user_path):
            with open(user_path, "rt") as conf:
                jss = conf.read()
                js = json.loads(jss)
                self.user = js["user"]
                self.password = js["password"]
        else:
            self.user = None
            self.password = None

    def load(self, con):
        """requests the instrument configuration from the server and populates the attributes boards, board_addr, addr_str, addr_int

        :param web.rest.base.Connection con: the backend http connection
        :return str: 'OK' if the request went fine, "ERROR_XX" otherwise
        """
        res = con.get(self.get_rest_base() + "/config")

        if res["status"] != "OK":
            return res["status"]

        self.boards = res["boards"]
        self.board_addr = res["board_addr"]

        self.addr_str = {}
        self.addr_int = {}

        for k in self.board_addr:
            self.addr_str[k] = {}
            self.addr_int[k] = {}
            for i in self.board_addr[k]:
                self.addr_str[k][i["name"]] = i
                self.addr_int[k][int(i["addr"], 16)] = i

        return res["status"]

    def get_rest_base(self):
        """returns the base url for REST requests"""
        return self.conf["urls"]["schema"] + "://" + self.conf["urls"]["base"] + "/rest"

    def get_login(self):
        """returns the full url for the REST login"""
        return (
            self.conf["urls"]["schema"]
            + "://"
            + self.conf["urls"]["base"]
            + self.conf["urls"]["login"]
        )

    def get_logout(self):
        """returns the full url for the REST logout"""
        return (
            self.conf["urls"]["schema"]
            + "://"
            + self.conf["urls"]["base"]
            + self.conf["urls"]["logout"]
        )

    def get_user(self):
        """returns the username. It looks first in the STRIP_USER env variable,
        and then in the user config file. Returns None if no user is found
        """
        return self.user

    def get_password(self):
        """returns the password for the user. It looks first in the STRIP_PASSWORD env variable,
        and then in the user config file. Returns None if no password is found
        """
        return self.password

    def get_ws_base(self):
        """returns the base url for ws connections"""
        return "ws://" + self.conf["urls"]["base"] + "/ws"

    def get_ws_pol(self, pol):
        """return the full url for the 'pol' polarimeter
        :param pol: the polarimeter name
        :type pol: string
        """
        return (
            "ws://"
            + self.conf["urls"]["base"]
            + self.conf["urls"]["ws_pol_base"]
            + "/"
            + pol
        )

    def get_wamp_url(self):
        return "wss://" + self.conf["urls"]["base"] + self.conf["urls"]["wamp_url"]

    def get_wamp_pol(self, pol):
        """return the topic for the 'pol' polarimeter
        :param pol: the polarimeter name
        :type pol: string
        """
        return "strip.fp.pol." + pol.upper()

    def get_wamp_realm(self):
        return self.conf["urls"]["wamp_realm"]

    def get_board_bias_file(self, board_num):
        "Return the name of the Excel file containing the biases for a board"

        return self.conf["board_associations"][board_num]
