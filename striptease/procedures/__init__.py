# -*- encoding: utf-8 -*-

from urllib.parse import urlparse

from config import Config
from striptease import StripConnection
from striptease.biases import InstrumentBiases

class JSONCommandEmitter:
    """This class captures commands sent to the board and outputs a JSON
    representation on some text stream.
    """

    def __init__(self, conn):
        self.command_list = []
        self.conn = conn

    def post_command(self, url, cmd):
        if "tag" in cmd:
            kind = "tag"
        elif "message" in cmd.keys():
            kind = "log"
        elif "wait_time_s" in cmd.keys():
            kind = "wait"
        else:
            kind = "command"

        if url != "":
            url_components = urlparse(url)
            path = url_components.path
        else:
            path = ""
            
        new_command = {
            "path": path,
            "kind": kind,
            "command": cmd,
        }
        self.command_list.append(new_command)
        return True

    def wait(self, seconds):
        return self.post_command("", { "wait_time_s": seconds })

    def tag_start(self, name, comment=""):
        # Making this command share the same name and parameters as
        # StripConnection allows us to use StripTag on a Worker class
        # instead of a StripConnection object!
        return self.conn.tag_start(name, comment)

    def tag_stop(self, name, comment=""):
        # See the comment for tag_stop
        return self.conn.tag_stop(name, comment)

    def __call__(self, url, cmd):
        return self.post_command(url, cmd)


class StripProcedure:
    def __init__(self):
        self.command_history = []
        self.biases = InstrumentBiases()

        with StripConnection() as conn:
            # We need to load the configuration from the server, as it
            # includes vital information about the board
            # configuration. This information is needed to properly
            # initialize the hardware
            self.conf = Config()
            self.conf.load(conn)

            self.command_emitter = JSONCommandEmitter(conn)
            conn.post_command = self.command_emitter

    def wait(self, seconds):
        return self.command_emitter.wait(seconds)
        
    def run(self):
        pass

    def get_command_list(self):
        return self.command_emitter.command_list
