# -*- encoding: utf-8 -*-

"""
Striptease
"""

from .unittests import *
from .biases import *
from .diagnostics import *
from .hdf5files import *

__version__ = "0.1.0"

from urllib.parse import urljoin
from web.rest.base import Connection

# This dictionary associates the name of a board with the W-band
# polarimeter associated with it.
BOARD_TO_W_BAND_POL = {
    "Y": "W1",
    "O": "W2",
    "R": "W3",
    "V": "W4",
    "B": "W5",
    "G": "W6",
    "I": None,
}


def normalize_polarimeter_name(name: str):
    """Translate the name of W-band polarimeters

    This function returns the name of a W-band polarimeter as if it
    were named as the Q-band polarimeters in its own board::

        >>> normalize_polarimeter_name("W2")
        "O7"

    """
    result = name.upper()
    if name[0] != "W":
        return result

    for board, w_pol in BOARD_TO_W_BAND_POL.items():
        if w_pol == result:
            return f"{board}7"

    raise KeyError(f"unknown polarimeter {result}")


def get_polarimeter_index(pol_name):
    """Return the progressive number of the polarimeter within the board (0…7)

    Args:
        pol_name (str): Name of the polarimeter, like ``R0`` or ``W3``.

    Returns:
        An integer from 0 to 7.
    """

    if pol_name[0] == "W":
        return 7
    else:
        return int(pol_name[1])


def get_lna_num(name):
    """Return the number of an LNA, in the range 0…5

    Valid values for the parameter `name` can be:
    - The official name, e.g., HA1
    - The UniMIB convention, e.g., H0
    - The JPL convention, e.g., Q1
    - An integer number, which will be returned identically
    """

    if type(name) is int:
        # Assume that the index refers to the proper firmware register
        return name
    elif (len(name) == 3) and (name[0:2] in ["HA", "HB"]):
        # Official names
        d = {
            "HA1": 0,
            "HA2": 2,
            "HA3": 4,
            "HB1": 1,
            "HB2": 3,
            "HB3": 5,
        }
        return d[name]
    elif (len(name) == 2) and (name[0] == "H"):
        # UniMiB
        d = {
            "H0": 0,
            "H1": 1,
            "H2": 2,
            "H3": 3,
            "H4": 4,
            "H5": 5,
        }
        return d[name]
    elif (len(name) == 2) and (name[0] == "Q"):
        # JPL
        d = {
            "Q1": 0,
            "Q2": 1,
            "Q3": 2,
            "Q4": 3,
            "Q5": 4,
            "Q6": 5,
        }
        return d[name]
    else:
        raise ValueError(f"Invalid amplifier name '{name}'")


class StripConnection(Connection):
    """Connection to the Strip instrument

    This class allows to communicate with the Strip Control Software
    by means of the web API interface. Using this class allows your
    code to fully control the Strip instrument; possible operations
    are:

    1. Turn amplifiers and other components on and off

    2. Acquire scientific and housekeeping data

    3. Modify the settings of amplifiers and phase switch

    4. Inspect and update calibration curves for housekeeping
       parameters

    5. Etc.

    To create the object, you can pass one or more of the
    following parameters:

    - `user` (None or str): a string containing the username. If
      None

    - `password` (None or str): the password to use while
      establishing the connection

    - `addr` (None or str): the hostname of the server, optionally
      followed by the port, e.g., "myserver.foo.bar:8123".

    - `schema` (None or str): either "http" or "https"

    - `post_command` (None or function): if it is not none, the
      function will be called every time a command must be sent to the
      electronics. This can be used to capture a list of commands
      instead of directly commanding the board. The function must
      accept two parameters: the URL and a dictionary describing the
      command (in this order).

    The following code shows how to connect to a machine. It
    assumes that the user has properly configured the library
    following the documentation
    (https://lspestrip.github.io/striptease/authentication.html)::

        from stripeline import StripConnection

        conn = StripConnection()
        conn.login()
        print("I am connected to Strip, the ID is ", conn.id)
        conn.logout()


    Another alternative is to use it as a context manager::

         from stripeline import StripConnection

         with StripConnection(server="foo.bar.org:1234",
                              schema="https") as conn:
             # No need to call conn.login() and conn.logout()
             print("I am connected to Strip, the ID is ", conn.id)

    Once a connection is established, a `StripConnection` object
    implements the following methods:

    - `slo_command`

    - `system_command`

    - `query_file`

    - `request_data`

    - `tag_query`

    - `tag_start`

    - `tag_stop`

    - `log`

    Attributes:

        last_response (dictionary): The last response received from the
            server. It is useful for debugging.

    """

    def __init__(
        self, user=None, password=None, addr=None, schema=None, post_command=None
    ):
        super(StripConnection, self).__init__()

        self.__user = user
        self.__password = password
        self.post_command = post_command

        if addr:
            self.conf.conf["urls"]["base"] = addr

        if schema:
            self.conf.conf["urls"]["schema"] = schema

    def __enter__(self):
        self.login(self.__user, self.__password)

        # Reset the user and password so that they are not kept in the
        # object during its lifetime
        self.__user = None
        self.__password = None

        return self

    def __exit__(self, typ, value, traceback):
        self.logout()

    def __rel2abs_url(self, rel_url):
        return urljoin(self.conf.get_rest_base(), rel_url)

    def login(self, user=None, password=None):
        """Connect to the Strip control software

        Establish a connection with Strip. If the parameters `user`
        and `password` are not specified, they are either taken from
        the configuration file (see
        https://lspestrip.github.io/striptease/authentication.html).
        """

        if user:
            cur_user = user
        else:
            cur_user = self.__user

        if password:
            cur_password = password
        else:
            cur_password = self.__password

        super(StripConnection, self).login(cur_user, cur_password)

    def post(self, rel_url, message):
        """Post a request to the Strip control software

        This command sends a request to the instrument. Requests can
        ask the instrument to do one of the following things:

        1. Query the value of an housekeeping parameter
        2. Query the output of a polarimeter
        3. Change some settings of the instrument (biases, currents, etc.)

        Args:

            rel_url (str): Relative path to the URL to use, e.g.,
                ``rest/slo``. See the Wep API to know what are the
                available URLs.

            message (any): Message to be sent. It should be a
                dictionary, which will be encoded as JSON. You can
                paste here the text displayed by the "Show JSON"
                button in the STRIP Web portal.

        Returns:

            A dictionary indicating the status of the operation.

        """
        abs_url = self.__rel2abs_url(rel_url)
        if self.post_command:
            result = self.post_command(abs_url, message)
        else:
            # abs_url is null only for "wait" messages, which are only used in
            # JSON scripts: in those cases, self.post_command is always set,
            # and this "if" has no effect.
            if abs_url != "":
                result = super(StripConnection, self).post(url=abs_url, message=message)
                assert result["status"] == "OK", "Error in POST ({0}): '{1}'".format(
                    result["status"]
                )
            else:
                return True

        return result

    def wait(self, seconds):
        self.post("", {"wait_time_s": seconds})

    @staticmethod
    def __normalize_board_and_pol(board, pol, allow_board):
        """Normalize "board" and "polarimeter" arguments

        Returns:

            A 2-element tuple containing the following elements:

                - Either None or a one-character string containing the
                  name of the board (e.g., "R")

                - Either "BOARD" or the full name of the polarimeter
                  (e.g., "R5")

        """

        if board:
            assert board in [
                "R",
                "O",
                "Y",
                "G",
                "B",
                "I",
                "V",
                "",  # Empty case is allowed if "pol" == "BOARD"
            ], "Invalid BOARD: '{0}'".format(board)

            if board == "":
                board = None

        if not board:
            assert pol == "BOARD", "Mismatch between parameters 'board' and 'pol'"

        # It is annoying to accept polarimeters in the form "R0"; in
        # this case, we convert them into an integer number. We'll
        # convert them back to strings later.
        if type(pol) is str:
            if pol != "BOARD":
                assert len(pol) == 2
                assert pol[0] == board, "Wrong polarimeter ({0}) for board {1}".format(
                    pol, board
                )
                pol = int(pol[1])
            else:
                assert not board, "Pass None to the 'board=' parameter"

        assert pol in ["BOARD", 0, 1, 2, 3, 4, 5, 6]

        if type(pol) is int:
            pol = "{0}{1}".format(board, pol)

        if not allow_board:
            assert board, "You must specify a board"

        return board, pol

    def slo_command(
        self, method, board, pol, kind, base_addr, data=None, timeout_ms=500
    ):
        """Send a SLO (housekeeping) command.

        Use this function to get/set the value of a housekeeping parameter.

        Args:

            method (str): either "GET" (read a housekeeping parameter)
                or "SET" (set the value of a housekeeping parameter)

            board (str): one-character string identifying the board to
                target. It can be "R", "O", "Y", "G", "B", "I", or
                "V". Leave it empty or pass None if your action
                targets the whole board.

            pol (str, int): either the number of the polarimeter (0-6)
                or the full name (e.g., "R0"). If you are targeting
                the whole board, pass None or an empty string.

            kind (str): either "BIAS", "PREAMP", or "CRYO".

            base_addr (str): name of the parameter to set, e.g., "VD0_HK"

            data (integer, list, or None): if method is "GET", it is unused.
                Otherwise, it is the value to set. More than one value can be
                provided; in this case, the registers following "base_addr"
                will be set too.

            timeout (int): Number of milliseconds to wait for an
                answer from the instrument before signalling an error.

        Returns:

            An integer value containing the result of the
            operation. For SET commands, it should be the same value
            as the one having been sent. For GET, it is the reading
            itself.

        """
        method = method.upper()
        kind = kind.upper()

        assert method in ["GET", "SET"], "Invalid method '{}'".format(method)

        board, pol = self.__normalize_board_and_pol(board, pol, allow_board=True)

        assert kind in [
            "BIAS",
            "PREAMP",
            "CRYO",
        ], "Invalid value for 'kind=' ({})".format(kind)

        dic = {
            "board": board,
            "pol": pol,
            "base_addr": base_addr,
            "type": kind,
            "method": method,
            "size": 1,
            "timeout": timeout_ms,
        }

        if data:
            if type(data) in [int, float]:
                dic["data"] = [data]
            else:
                dic["data"] = data

        self.last_response = self.post("rest/slo", dic)
        assert len(self.last_response["data"]) == 1

        return self.last_response["data"][0]

    def system_command(self, command):
        """Send a command to the acquisition system.

        Args:

            command (str): the name of the command to be
                sent. Possible values are:

                - `round_all_files`
                - `round_hdf5_files`
                - `round_raw_files`

        Returns:

            Nothing.
        """

        self.last_response = self.post("rest/command", {"command": command})

    def round_all_files(self):
        """Close all the files being written by the web server and start new ones.

        This command is useful when you are going to start a long
        acquisition and do not want the data to be split by the server
        at some arbitrary point.  (The server flushes all its data to
        files once its buffers have been filled.)
        """

        self.system_command("round_all_files")

    def round_hdf5_files(self):
        """Close all the HDF5 files being written by the web server.

        This function should never be called. See
        meth:`striptease.StripConnection.round_all_files` for a good
        alternative.
        """
        self.system_command("round_hdf5_files")

    def round_raw_files(self):
        """Close all the raw files being written by the web server.

        This function should never be called. See
        meth:`striptease.StripConnection.round_all_files` for a good
        alternative.
        """
        self.system_command("round_raw_files")

    def query_file(self, start_mjd=None, end_mjd=None):

        """Return a list of the files within some specified time interval.

        Args:

            start_mjd (float or None): if not None, the initial
                Modified Julian Date (MJD).

            end_mjd (float or None): if not None, the final MJD.

        Returns:

            An array of dictionaries containing information about each
            file. Each dictionary in the array has the following
            fields:

                - `protocol`: the file transfer service to use,
                  typically 'sftp'

                - `port`: number of the port to use for downloading

                - `path`: Path to the HDF5 file

                - `start`: first MJD in the file

                - `stop`: last MJD in the file

        """

        dic = {}
        if start_mjd:
            dic["start"] = start_mjd

        if end_mjd:
            dic["stop"] = end_mjd

        self.last_response = self.post("rest/file_query", dic)
        return self.last_response["files"]

    def request_data(self, board, pol, start_mjd, end_mjd):
        """Load scientific data from the instrument

        Args:

            board (str): one-character string identifying the board to
                target. It can be "R", "O", "Y", "G", "B", "I", or
                "V". Leave it empty or pass None if your action
                targets the whole board.

            pol (str, int): either the number of the polarimeter (0-6)
                or the full name (e.g., "R0"). If you are targeting
                the whole board, pass None or an empty string.

        Returns:

            An array of dictionaries. Each dictionary contains the
            following field:

                - `pol`: name of the polarimeter, e.g., "R0"

                - `time_stamp`: timestamp of the sample (in units of 0.01 s)

                - `mjd`: Modified Julian Date of the sample

                - `dem`, `tpw`: demodulated and total-power data, in
                  ADU (only for scientific data)

                - `hk`: dictionary associating the name of a
                  housekeeping parameter with its value

        """

        board, pol = self.__normalize_board_and_pol(board, pol, allow_board=False)

        dic = {"board": board, "pol": pol, "start": start_mjd, "stop": end_mjd}

        self.last_response = self.post("rest/data", dic)
        return self.last_response["data"]

    def tag_query(self, tag=None, tag_id=None, start_mjd=None, end_mjd=None, id=None):
        """Query a list of tags

        The function can filter the tags

        Args:

            tag (str or None): the name of the tag to search, e.g.,
                "linearity_test"

            start_mjd (float or None): if not None, the initial
                Modified Julian Date (MJD).

            end_mjd (float or None): if not None, the final MJD.

            id (integer or None): the ID of the tag

        Returns:

            An array of dictionaries. Each dictionary contains the
            following field:

                - `id`: unique ID of the tag (integer number)

                - `tag`: name of the tag (string)

                - `start`: MJD timestamp for the start of the tag (float)

                - `stop`: MJD timestamp for the end of the tag (float)

                - `start_comment`: comment associated with the start of the tag (string)

                - `stop_comment`: comment associated with the end of the tag (string)

        """

        dic = {}

        if tag:
            dic["tag"] = tag

        if start_mjd:
            dic["start"] = start_mjd

        if end_mjd:
            dic["stop"] = end_mjd

        if tag_id:
            dic["id"] = tag_id

        self.last_response = self.post("rest/tag_query", dic)
        return self.last_response["tags"]

    def tag_start(self, name, comment=""):
        """Start a new tag

        Signal the beginning of a tag. When you want to stop it, use
        `tag_stop`.

        Args:

            name (str): name of the tag

            comment (str, optional): comment to be associated with the tag

        Returns:

            Nothing

        """

        dic = {"type": "START", "tag": name, "comment": comment}
        self.last_response = self.post("rest/tag", dic)

    def tag_stop(self, name, comment=""):
        """Stop a running tag tag

        The tag must have already been started by `tag_start`, but no
        check of this is actually done by the code.

        Args:

            name (str): name of the tag

            comment (str, optional): comment to be associated with the tag

        Returns:

            Nothing
        """

        dic = {"type": "STOP", "tag": name, "comment": comment}
        self.last_response = self.post("rest/tag", dic)

    def log(self, message, level="INFO"):
        """Save a log message

        This method allows the user to save a log message, represented
        by a textual string and a message level. The latter is useful
        when you want to filter log messages saved in a HDF5 file, for
        instance because you are looking for errors.

        Args:

            message (str): the message to save

            level (str, optional): either "ERROR", "WARNING", "INFO"
                                   (the default), "DEBUG"

        Returns:

            Nothing
        """

        level_toupper = level.upper()
        assert level_toupper in ["ERROR", "WARNING", "INFO", "DEFAULT"]
        dic = {"message": message, "level": level_toupper}
        self.last_response = self.post("rest/log", dic)


class StripTag:

    """Context manager for tags.

    When you are running a test and want to record tag start/stop, you
    can use this to easily match tag names between the ``START`` and
    ``STOP`` commands::

        conn = StripConnection(...)
        with StripTag(
            conn,
            name="BIAS_TUNING",
            comment="Bias tuning for G0",
        ):
            conn.post_command(...)
            # etc.

    You can either provide a comment using the keyword ``comment`` (in
    this case, it will be reused for the ``START`` and ``STOP`` tags),
    or you can pass two separate comments using ``start_comment`` and
    ``stop_comment``.

    """

    def __init__(
        self, conn, name, comment="", start_comment="", stop_comment="", dry_run=False
    ):
        self.conn = conn
        self.name = name

        self.start_comment = comment
        self.stop_comment = comment

        if start_comment != "":
            self.start_comment = start_comment

        if stop_comment != "":
            self.stop_comment = stop_comment

        self.dry_run = dry_run

    def __enter__(self):
        if not self.dry_run:
            self.conn.tag_start(name=self.name, comment=self.start_comment)

    def __exit__(self, exc_type, exc_value, traceback):
        # We must close the tag even if an exception has been raised
        if not self.dry_run:
            self.conn.tag_stop(name=self.name, comment=self.stop_comment)
