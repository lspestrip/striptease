# -*- encoding: utf-8 -*-

from copy import deepcopy
from urllib.parse import urlparse
import json
import sys

from config import Config
from striptease.stripconn import StripConnection
from striptease.biases import InstrumentBiases


def dump_procedure_as_json(outf, obj, indent_level=0, use_newlines=True):
    """
    Dump a list of commands into a JSON file.

    This is similar to what the standard function ``json.dump`` does,
    but it uses less carriage returns to make the output easier to
    read and to search with ``grep``.
    """

    def dump_newline(indent_level):
        if use_newlines:
            outf.write("\n")
            outf.write(" " * indent_level)

    if isinstance(obj, list):
        outf.write("[")
        indent_level += 2
        dump_newline(indent_level)

        for idx, elem in enumerate(obj):
            dump_procedure_as_json(
                outf, elem, indent_level=indent_level, use_newlines=use_newlines
            )
            if idx < len(obj) - 1:
                outf.write(", ")
            dump_newline(indent_level)
        indent_level -= 2
        outf.write("]")
    elif isinstance(obj, dict):
        # A better visually-looking alternative (which however does not work
        # well with `grep` is
        #
        #     use_newlines and (obj.get("kind", "") in ["log"])
        use_newlines_here = False

        outf.write("{")
        indent_level += 2
        if use_newlines_here:
            dump_newline(indent_level)

        for idx, elem in enumerate(obj):
            outf.write(f'"{elem}": ')
            dump_procedure_as_json(
                outf,
                obj[elem],
                indent_level=indent_level,
                use_newlines=use_newlines_here,
            )
            if idx < len(obj) - 1:
                outf.write(", ")

            if use_newlines_here:
                dump_newline(indent_level)
        indent_level -= 2
        outf.write("}")
    else:
        outf.write(json.dumps(obj))


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

        new_command = {"path": path, "kind": kind, "command": cmd}
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

    def clear_command_list(self):
        "Remove all the commands produced so far from memory"

        self.command_emitter.command_list = []

    def output_json(self, output_filename=None):
        """Write the list of commands executed so far in a JSON object.

        Args
        ----

            output_filename (str or Path): path to the file to be
                created that will contain the list of commands in JSON
                format. If ``None`` is used, the commands will be
                printed to ``stdout``.

        """
        if (not output_filename) or (output_filename == ""):
            dump_procedure_as_json(sys.stdout, self.get_command_list())
        else:
            with open(str(output_filename), "wt") as outf:
                dump_procedure_as_json(outf, self.get_command_list())
