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
        else:
            kind = "command"

        url_components = urlparse(url)
        new_command = {
            "path": url_components.path,
            "kind": kind,
            "command": cmd}
        self.command_list.append(new_command)
        return

    def tag_start(self, name, comment=""):
        # Making this command share the same name and parameters as
        # StripConnection allows us to use StripTag on a Worker class
        # instead of a StripConnection object!
        self.conn.tag_start(name, comment)

    def tag_stop(self, name, comment=""):
        # See the comment for tag_stop
        self.conn.tag_stop(name, comment)

    def __call__(self, url, cmd):
        self.post_command(url, cmd)


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

    def run(self):
        pass

    def get_command_list(self):
        return self.command_emitter.command_list
