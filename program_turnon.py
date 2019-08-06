#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from collections import namedtuple
from urllib.parse import urlparse
import logging as log
import os.path
import sys

from config import Config
from striptease import StripConnection, StripTag

from program_turnon import SetupBoard
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


class TurnOnProcedure(StripProcedure):
    def __init__(self):
        super(TurnOnProcedure, self).__init__()
        self.board = None
        self.polarimeter = None

    def set_board_and_polarimeter(self, new_board, new_pol):
        self.board = new_board
        self.polarimeter = new_pol

    def run(self):
        assert self.polarimeter
        board_setup = SetupBoard(
            config=self.conf, board_name=self.board, post_command=self.command_emitter
        )

        # 1
        with StripTag(
            conn=self.command_emitter,
            name="BOARD_TURN_ON",
            comment=f"Turning on board for {self.polarimeter}",
        ):
            board_setup.log("Going to set up the board…")
            board_setup.board_setup()
            board_setup.log("Board has been set up")

        # 2
        with StripTag(
            conn=self.command_emitter,
            name="ELECTRONICS_ENABLE",
            comment=f"Enabling electronics for {self.polarimeter}",
        ):
            board_setup.log(f"Enabling electronics for {self.polarimeter}…")
            board_setup.enable_electronics(polarimeter=self.polarimeter)
            board_setup.log("The electronics has been enabled")

        # 3
        for idx in (0, 1, 2, 3):
            with StripTag(
                conn=self.command_emitter,
                name="DETECTOR_TURN_ON",
                comment=f"Turning on detector {idx} in {self.polarimeter}",
            ):
                board_setup.turn_on_detector(self.polarimeter, idx)

        # 4
        biases = self.biases.get_biases(module_name=self.polarimeter)
        for (index, vpin, ipin) in zip(
            range(4),
            [biases.vpin0, biases.vpin1, biases.vpin2, biases.vpin3],
            [biases.ipin0, biases.ipin1, biases.ipin2, biases.ipin3],
        ):
            try:
                with StripTag(
                    conn=self.command_emitter,
                    name="PHSW_BIAS",
                    comment=f"Setting biases for PH/SW {index} in {self.polarimeter}",
                ):
                    board_setup.set_phsw_bias(self.polarimeter, index, vpin, ipin)
            except:
                log.warning(f"Unable to set bias for detector #{index}")

        # 5
        for idx in (0, 1, 2, 3):
            with StripTag(
                conn=self.command_emitter,
                name="PHSW_STATUS",
                comment=f"Setting status for PH/SW {idx} in {self.polarimeter}",
            ):
                board_setup.set_phsw_status(self.polarimeter, idx, status=7)

        # 6
        for lna in ("HA3", "HA2", "HA1", "HB3", "HB2", "HB1"):
            for step_idx, cur_step in enumerate([0.0, 0.5, 1.0]):
                with StripTag(
                    conn=self.command_emitter,
                    name="VD_SET",
                    comment=f"Setting drain voltages for LNA {lna} in {self.polarimeter}",
                ):
                    board_setup.setup_VD(self.polarimeter, lna, step=cur_step)

                    if step_idx == 0:
                        board_setup.setup_VG(self.polarimeter, lna, step=1.0)

                    if False and cur_step == 1.0:
                        # In mode 5, the following command should be useless…
                        board_setup.setup_ID(self.polarimeter, lna, step=1.0)


def unroll_polarimeters(pol_list):
    for cur_pol in pol_list:
        if cur_pol in ("V", "G", "B", "P", "R", "O", "Y"):
            for idx in range(7):
                yield f"{cur_pol}{idx}"
            continue

        yield cur_pol


if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Produce a command sequence to turn on one or more polarimeters"
    )
    parser.add_argument(
        "polarimeters",
        metavar="POLARIMETER",
        type=str,
        nargs="+",
        help="Name of the polarimeters/module to turn on. Valid names "
        'are "G4", "Y" (meaning that all the 7 polarimeters will '
        "be turned on, one after another), etc.",
    )
    parser.add_argument(
        "--board",
        metavar="NAME",
        type=str,
        dest="board",
        default="G",
        help='Name of the board to use (default: "%(default)s")',
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILENAME",
        type=str,
        dest="output_filename",
        default="",
        help="Name of the file where to write the output (in JSON format). "
        "If not provided, the output will be sent to stdout.",
    )
    parser.add_argument("--bias-steps", dest="bias_steps", action="append")
    args = parser.parse_args()

    log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    proc = TurnOnProcedure()
    for cur_polarimeter in unroll_polarimeters(args.polarimeters):
        proc.set_board_and_polarimeter(args.board, cur_polarimeter)
        proc.run()

    import json

    output = json.dumps(proc.get_command_list(), indent=4)
    if args.output_filename == "":
        print(output)
    else:
        with open(args.output_filename, "wt") as outf:
            outf.write(output)
