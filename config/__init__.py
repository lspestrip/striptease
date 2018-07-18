# config/__init__.py --- Simple cnfiguration wrapper
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it

import json
import os.path

class Config(object):
    def __init__(self):
        path_dir = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(path_dir, "conf.json")
        with open(path,'rt') as c:
            js = c.read()
            self.conf = json.loads(js)

        user_path = os.path.expandvars(self.conf['user_conf'])
        user_path = os.path.expanduser(user_path)
        if os.path.isfile(user_path):
            with open(user_path,'rt') as conf:
                jss = conf.read()
                js = json.loads(js)
                self.user = js['user']
                self.password = js['password']
        else:
            self.user=None
            self.password=None

    def get_login(self):
        return self.conf['urls']['schema']+'://'+self.conf['urls']['base']+self.conf['urls']['login']

    def get_logout(self):
        return self.conf['urls']['schema']+'://'+self.conf['urls']['base']+self.conf['urls']['logout']

    def get_user(self):
        return self.user

    def get_password(self):
        return self.password

    def get_ws_pol(pol):
        return 'ws://' + self.conf['urls']['ws_pol_base'] + '/' + pol
