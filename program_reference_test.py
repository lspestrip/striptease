#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from collections import namedtuple
from datetime import datetime
import logging as log
import os.path
import re
import sys

from config import Config
from striptease import StripTag
from program_turnon import SetupBoard

from striptease.procedures import StripProcedure

DEFAULT_WAITTIME_S = 5.0


class ReferenceTestProcedure(StripProcedure):
    def __init__(self, waittime_s=5):
        super(ReferenceTestProcedure, self).__init__()
        self.board = None
        self.horn = None
        self.polarimeter = None
        self.waittime_s = waittime_s

    def set_board_and_horn(self, new_board, new_horn):
        self.board = new_board
        self.horn = new_horn

    def run(self):
        assert self.horn
        board_setup = SetupBoard(
            config=self.conf, board_name=self.board, post_command=self.command_emitter
        )

        board_setup.log(
            f"Test procedure for the phase switches of {self.horn} (board {self.board})"
        )

        with StripTag(
            conn=self.command_emitter,
            name="PHSW_STATUS_NOMINAL_7_START",
            comment=f"Setting status for phase switches in {self.horn}",
        ):
            for idx in (0, 1, 2, 3):
                board_setup.set_phsw_status(self.horn, idx, status=7)

            if self.waittime_s > 0:
                self.wait(seconds=self.waittime_s)

        with StripTag(
            conn=self.command_emitter,
            name="PHSW_STATUS_NOMINAL_0",
            comment=f"Setting status for phase switches in {self.horn}",
        ):
            for idx in (0, 1, 2, 3):
                board_setup.set_phsw_status(self.horn, idx, status=0)

            if self.waittime_s > 0:
                self.wait(seconds=self.waittime_s)

        with StripTag(
            conn=self.command_emitter,
            name=f"PHSW_STATUS_EXPLICIT",
            comment=f"Setting status for phase switches in {self.horn}",
        ):
            for idx, status in [
                (0, 1),
                (1, 3),
                (2, 2),
                (3, 4),
            ]:
                board_setup.set_phsw_status(self.horn, idx, status=status)

            if self.waittime_s > 0:
                self.wait(seconds=self.waittime_s)

        with StripTag(
            conn=self.command_emitter,
            name=f"PHSW_STATUS_EXPLICIT_INVERSE",
            comment=f"Setting status for phase switches in {self.horn}",
        ):
            for idx, status in [
                (0, 3),
                (1, 1),
                (2, 4),
                (3, 2),
            ]:
                board_setup.set_phsw_status(self.horn, idx, status=status)

            if self.waittime_s > 0:
                self.wait(seconds=self.waittime_s)

        with StripTag(
            conn=self.command_emitter,
            name="PHSW_STATUS_NOSWITCH_1010",
            comment=f"Setting status for phase switches in {self.horn}",
        ):
            for idx, status in [
                (0, 5),
                (1, 6),
                (2, 5),
                (3, 6),
            ]:
                board_setup.set_phsw_status(self.horn, idx, status=status)

            if self.waittime_s > 0:
                self.wait(seconds=self.waittime_s)

        with StripTag(
            conn=self.command_emitter,
            name="PHSW_STATUS_NOSWITCH_0101",
            comment=f"Setting status for phase switches in {self.horn}",
        ):
            for idx, status in [
                (0, 6),
                (1, 5),
                (2, 6),
                (3, 5),
            ]:
                board_setup.set_phsw_status(self.horn, idx, status=status)

            if self.waittime_s > 0:
                self.wait(seconds=self.waittime_s)

        with StripTag(
            conn=self.command_emitter,
            name="PHSW_STATUS_NOSWITCH_0110",
            comment=f"Setting status for phase switches in {self.horn}",
        ):
            for idx, status in [
                (0, 6),
                (1, 5),
                (2, 5),
                (3, 6),
            ]:
                board_setup.set_phsw_status(self.horn, idx, status=status)

            if self.waittime_s > 0:
                self.wait(seconds=self.waittime_s)

        with StripTag(
            conn=self.command_emitter,
            name="PHSW_STATUS_NOSWITCH_1001",
            comment=f"Setting status for phase switches in {self.horn}",
        ):
            for idx, status in [
                (0, 5),
                (1, 6),
                (2, 6),
                (3, 5),
            ]:
                board_setup.set_phsw_status(self.horn, idx, status=status)

            if self.waittime_s > 0:
                self.wait(seconds=self.waittime_s)

        with StripTag(
            conn=self.command_emitter,
            name="PHSW_STATUS_NOMINAL_7_END",
            comment=f"Setting status for phase switches in {self.horn}",
        ):
            for idx in (0, 1, 2, 3):
                board_setup.set_phsw_status(self.horn, idx, status=7)

            if self.waittime_s > 0:
                self.wait(seconds=self.waittime_s)

        board_setup.log(
            f"Test procedure for the phase switches of {self.horn} (board {self.board}) has completed"
        )


################################################################################

if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser, RawDescriptionHelpFormatter

    parser = ArgumentParser(
        description="Produce a command sequence to test one or more polarimeters",
        formatter_class=RawDescriptionHelpFormatter,
        epilog="""

Usage example:

    python3 program_turnon.py G0 G4
""",
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
    parser.add_argument(
        "--wait-time-sec",
        metavar="VALUE",
        type=float,
        dest="waittime_s",
        default=DEFAULT_WAITTIME_S,
        help=f"Time to wait after having altered the bias level for each amplifier "
        f"(default: {DEFAULT_WAITTIME_S}, set to 0 to disable)",
    )
    parser.add_argument(
        "--board",
        metavar="NAME",
        type=str,
        dest="board",
        required=True,
        help="Name of the board to use",
    )
    parser.add_argument(
        "polarimeters",
        metavar="POLARIMETER",
        type=str,
        nargs="+",
        help="Name of the polarimeters/module to turn on. Valid names "
        'are "G4", "I0", etc.',
    )

    args = parser.parse_args()

    log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    proc = ReferenceTestProcedure(waittime_s=args.waittime_s)
    for cur_horn in args.polarimeters:
        proc.set_board_and_horn(args.board, cur_horn)
        proc.run()

    import json

    output = json.dumps(proc.get_command_list(), indent=4)
    if args.output_filename == "":
        print(output)
    else:
        with open(args.output_filename, "wt") as outf:
            outf.write(output)
