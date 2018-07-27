# web/rest/base.py --- Base REST wraping classes
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it

from config import Config
import json
import requests
import web.rest.errors as err

class Connection(object):
    """Class Handling login and session"""

    def __init__(self):
        self.conf = Config()
        self.session = requests.Session()
        self.id = None

    def login(self,user=None,password=None):
        """login function, if user or password are not provided, it tries to
            find login credentials stored in user config file.        """
        if user is None or password is None:
            user = self.conf.get_user()
            password = self.conf.get_password()

        if user is None or password is None:
            raise err.InputLogin()

        auth = json.dumps({'user':user,'password':password})
        response = self.session.post(self.conf.get_login(), data=auth)
        if response.status_code != 200:
            response.raise_for_status()
        else:
            self.id = self.session.cookies.get('sessionid')

    def logout(self):
        response = self.session.post(self.conf.get_logout(), data=json.dumps({}))
        if response.status_code != 200:
            response.raise_for_status()
        else:
            self.id = None