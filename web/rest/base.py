# web/rest/base.py --- Base REST wraping classes
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it

from config import Config
import json
import requests
import time
import web.rest.errors as err


class Connection(object):
    """Class Handling login and session"""

    def __init__(self):
        self.conf = Config()
        self.session = requests.Session()
        self.id = None

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
            self.id = self.session.cookies.get("sessionid")

    def logout(self):
        """logout the user and delete the sessionid.

            :raises HTTPError: any error that occours while communicating with the server.
        """
        response = self.session.post(self.conf.get_logout(), data=json.dumps({}))
        if response.status_code != 200:
            response.raise_for_status()
        else:
            self.id = None

    def post(self, url, message, retry_count=5, retry_delay_s=5.0):
        """encode the message in json format and send it using POST http method.
           :param str url: url to send the message.
           :param message: dictionary or list to send.
           :param retry_count: number of times to retry the command if error 503 happens
           :param retry_delay_s: time to wait before retrying to send the command
           :return: dictionary of the decoded json response.
           :raises HTTPError: any error that occours while communicating with the server.
        """
        pkt = json.dumps(message)
        count = 1
        while True:
            response = self.session.post(url, data=pkt)
            if (response.status_code == 503) and (count <= retry_count):
                print(f"Got error 503, retrying ({count}/{retry_count})")
                time.sleep(retry_delay_s)
                count += 1
            else:
                break

        if response.status_code != 200:
            try:
                print(response.json())
            except:
                pass
            response.raise_for_status()
        else:
            return response.json()

    def put(self, url, message):
        """encode the message in json format and send it using PUT http method.
           :param str url: url to send the message.
           :param message: dictionary or list to send.
           :return: dictionary of the decoded json response.
           :raises HTTPError: any error that occours while communicating with the server.
        """
        pkt = json.dumps(message)
        response = self.session.put(url, data=pkt)
        if response.status_code != 200:
            try:
                print(response.json())
            except:
                pass
            response.raise_for_status()
        else:
            return response.json()

    def delete(self, url):
        """send a delete request to the url using DELETE http method.
           :param str url: url to send the message.
           :return: dictionary of the decoded json response.
           :raises HTTPError: any error that occours while communicating with the server.
        """
        response = self.session.delete(url)
        if response.status_code != 200:
            response.raise_for_status()
            try:
                print(response.json())
            except:
                pass
        else:
            return response.json()

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
            except:
                pass
            response.raise_for_status()
        else:
            return response.json()
