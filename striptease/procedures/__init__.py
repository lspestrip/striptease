# -*- encoding: utf-8 -*-

from copy import deepcopy
from urllib.parse import urlparse
import json

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
        self.command_list.append(deepcopy(new_command))
        return {"status": "OK", "data": [0]}

    def wait(self, seconds):
        return self.post_command("", {"wait_time_s": seconds})

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
    """A test procedure that records commands in JSON objects

    This is a base class to be used when you need to implement a test
    procedure. Instead of sending commands to the true instrument, the
    class records all the commands in a JSON object, which can be
    saved in a text file and ran using the command-line program
    ``program_batch_runner.py``.

    You must define a new class from this, and redefine the ``run``
    method. In this method, you can use `self.conn` as a
    :class:`.StripConnection` object.

    """

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
        self.conn = conn

    def wait(self, seconds):
        "Make the test procedure wait for some time before continuing"
        return self.command_emitter.wait(seconds)

    def run(self):
        "Redefine this method in derived classes"
        pass

    def get_command_list(self):
        """Return a list object containing the commands executed so far.

        This list will be dumped as a JSON object by :meth:`.output_json`.
        """
        return self.command_emitter.command_list

    def output_json(self, output_filename=None):
        """Write the list of commands executed so far in a JSON object.

        Args
        ----

            output_filename (str or Path): path to the file to be
                created that will contain the list of commands in JSON
                format. If ``None`` is used, the commands will be
                printed to ``stdout``.

        """
        output = json.dumps(self.get_command_list(), indent=4)

        if (not output_filename) or (output_filename == ""):
            print(output)
        else:
            with open(str(output_filename), "wt") as outf:
                outf.write(output)
