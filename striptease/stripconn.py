# -*- encoding: utf-8 -*-

from urllib.parse import urljoin
from web.rest.base import Connection


class StripConnection(Connection):
    """
    Connection to the Strip instrument

    This class allows to communicate with the Strip Control Software by means
    of the web API interface. Using this class allows your code to fully control
    the Strip instrument; possible operations are:

    1. Turn amplifiers and other components on and off

    2. Acquire scientific and housekeeping data

    3. Modify the settings of amplifiers and phase switch

    4. Inspect and update calibration curves for housekeeping parameters

    5. Etc.

    Example
    =======

    The following code shows how to connect to a machine. It assumes that the
    user has properly configured the library following the
    `documentation <https://lspestrip.github.io/striptease/authentication.html>`_::

        from stripeline import StripConnection

        conn = StripConnection()
        conn.login()
        print("I am connected to the Strip control software, the ID is ", conn.id)
        conn.logout()

    Another alternative is to use the :class:`connect` context manager.
    """

    def __init__(self, user=None, password=None, addr=None, schema=None):
        super(StripConnection, self).__init__()

        self.user = user
        self.password = password

        if addr:
            self.conf.conf["urls"]["base"] = addr

        if schema:
            self.conf.conf["urls"]["schema"] = schema

    def __enter__(self):
        self.login(self.user, self.password)

        # Reset the user and password so that they are not kept in the
        # object during its lifetime
        self.user = None
        self.password = None

        return self

    def __exit__(self, typ, value, traceback):
        self.logout()

    def __rel2abs_url(self, rel_url):
        return urljoin(super(self.conf.get_rest_base(), rel_url))

    def login(self, user=None, password=None):
        if user:
            cur_user = user
        else:
            cur_user = self.user

        if password:
            cur_password = password
        else:
            cur_password = self.password

        super(StripConnection, self).login(cur_user, cur_password)

    def post(self, rel_url, message):
        super(StripConnection, self).post(
            url=self.__rel2abs_url(rel_url), message=message
        )

    def put(self, rel_url, message):
        super(StripConnection, self).put(
            url=self.__rel2abs_url(rel_url), message=message
        )

    def get(self, rel_url, message):
        super(StripConnection, self).get(
            url=self.__rel2abs_url(rel_url), message=message
        )
