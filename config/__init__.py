# config/__init__.py --- Simple cnfiguration wrapper
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it

import json
import os

class Config(object):
    '''the Config class parses the configuration file and provides shortcuts for
       common functionalities.

       Attributes:
          conf     dictionary with all the configuration settings
    '''
    def __init__(self):
        path_dir = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(path_dir, "conf.json")
        with open(path,'rt') as c:
            js = c.read()
            self.conf = json.loads(js)

        user_path = os.path.expandvars(self.conf['user_conf'])
        user_path = os.path.expanduser(user_path)
        user_path = os.path.abspath(user_path)

        if os.environ.get('STRIP_USER') is not None and os.environ.get('STRIP_PASSWORD') is not None:
            self.user = os.environ['STRIP_USER']
            self.password = os.environ['STRIP_PASSWORD']
        elif os.path.isfile(user_path):
            with open(user_path,'rt') as conf:
                jss = conf.read()
                js = json.loads(jss)
                self.user = js['user']
                self.password = js['password']
        else:
            self.user=None
            self.password=None

    def get_login(self):
        '''returns the full url for the REST login'''
        return self.conf['urls']['schema']+'://'+self.conf['urls']['base']+self.conf['urls']['login']

    def get_logout(self):
        '''returns the full url for the REST logout'''
        return self.conf['urls']['schema']+'://'+self.conf['urls']['base']+self.conf['urls']['logout']

    def get_user(self):
        '''returns the username. It looks first in the STRIP_USER env variable,
           and then in the user config file. Returns None if no user is found
        '''
        return self.user

    def get_password(self):
        '''returns the password for the user. It looks first in the STRIP_PASSWORD env variable,
           and then in the user config file. Returns None if no password is found
        '''
        return self.password

    def get_ws_pol(self,pol):
        '''return the full url for the 'pol' polarimeter
        :param pol: the polarimeter name
        :type pol: string
        '''
        return 'ws://' + self.conf['urls']['base'] + self.conf['urls']['ws_pol_base'] + '/' + pol
