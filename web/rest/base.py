# web/rest/base.py --- Base REST wraping classes
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it
import logging
from copy import copy
from typing import Dict, Optional

from config import Config
import json
import random
import requests
import time
import socket
import web.rest.errors as err

# This is used by the code that sends commands directly to the socket
_URL_TO_OPCODE: Dict[str, Optional[str]] = {
    "/rest/tag": "TAG",
    "/rest/slo": "SLO",
    "/rest/log": None,  # This must not be sent to the socket
}


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class Connection(object):
    """Class Handling login and session"""

    def __init__(self, use_fast_socket=True):
        self.conf = Config()
        self.session = requests.Session()
        self.socket = None
        self.id = None
        self.use_fast_socket = use_fast_socket

    def is_connected(self):
        """
        Return True if there is a running connection active

        Example
        =======

        The following example shows how to use this function::

            from striptease import StripConnection

            with StripConnection() as conn:
                print("Am I logged in? ", conn.is_connected())

            print("Am I logged in now? ", conn.is_connected())

        The output should be ``True`` and ``False``.
        """

        return not (self.id is None)

    def has_login(self):
        return self.conf.get_user() is not None and self.conf.get_password() is not None

    def login(self, user=None, password=None):
        """login function, if user or password are not provided, it tries to
        find login credentials from Config class.
        On succesful login it sets the sessiondid self.id

        :raises HTTPError: any error that occours while communicating with the server.
        """
        if user is None or password is None:
            user = self.conf.get_user()
            password = self.conf.get_password()

        if user is None or password is None:
            raise err.InputLogin()

        auth = json.dumps({"user": user, "password": password})
        response = self.session.post(self.conf.get_login(), data=auth)
        if response.status_code != 200:
            response.raise_for_status()
        else:
            self.user = user
            self.password = password
            self.id = self.session.cookies.get("sessionid")

        if self.use_fast_socket:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server, port = self.conf.get_direct_server(), self.conf.get_direct_port()
            if server:
                if not port:
                    self.socket.connect(server)
                else:
                    self.socket.connect((server, port))
            else:
                logging.warning(
                    "No 'direct_server' entry in the configuration file, "
                    "falling back to HTTP"
                )

    def logout(self):
        """logout the user and delete the sessionid.

        :raises HTTPError: any error that occours while communicating with the server.
        """

        response = self.session.post(self.conf.get_logout(), data=json.dumps({}))
        if response.status_code != 200:
            response.raise_for_status()
        else:
            self.id = None

        if self.socket:
            self.socket.close()
            self.socket = None

    def post(self, url, message, retry_count=10, retry_delay_s=None, force_https=False):
        """encode the message in json format and send it using POST http method.
        :param str url: url to send the message.
        :param message: dictionary or list to send.
        :param retry_count: number of times to retry the command if error 503 happens
        :param retry_delay_s: time to wait before retrying to send the command
        :param force_https: if set to ``True``, always use the slow HTTPS connection
            even if a direct socket is available. This is required for some commands
            (like tag_query), which must always be handled by the webserver.
        :return: dictionary of the decoded json response.
        :raises HTTPError: any error that occours while communicating with the server.
        """
        if self.socket and (not force_https):
            socket_msg = copy(message)
            socket_msg["user"] = self.conf.get_direct_username()
            socket_msg["opcode"] = None
            found = False
            for cur_url_part, cur_opcode in _URL_TO_OPCODE.items():
                if cur_url_part in url:
                    found = True
                    socket_msg["opcode"] = cur_opcode

            if socket_msg["opcode"]:
                self.socket.sendall(json.dumps(socket_msg).encode("utf-8"))
                return json.loads(self.socket.recv(2048).decode("utf-8"))
            elif not found:
                # Emit a warning and fall back to HTTPS
                logging.warning(
                    f"Unable to translate {message=} into command {socket_msg=} and send it "
                    + f"to socket through {url=}, falling back to HTTP"
                )
            else:
                # Quietly fall back to HTTPS
                pass

        pkt = json.dumps(message)

        count = 1
        while True:
            response = self.session.post(url, data=pkt)
            if (response.status_code == 503) and (count <= retry_count):
                print(
                    bcolors.WARNING
                    + bcolors.BOLD
                    + f"Got error 503, response is {response.json()}, retrying ({count}/{retry_count})"
                    + bcolors.ENDC
                )

                if retry_delay_s:
                    time.sleep(retry_delay_s)
                else:
                    time.sleep(random.uniform(2.0, 7.0))
                count += 1
            else:
                break

        if not (response is None):
            if response.status_code != 200:
                response.raise_for_status()
            else:
                return response.json()
        else:
            return {}

    def get(self, url):
        """send a get request to the url using GET http method.
        :param str url: url to send the message.
        :return: dictionary of the decoded json response.
        :raises HTTPError: any error that occours while communicating with the server.
        """
        response = self.session.get(url)
        if response.status_code != 200:
            try:
                print(response.json())
            except AttributeError:
                pass
            response.raise_for_status()
        else:
            return response.json()
