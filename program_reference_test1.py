#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# Procedura 1

import logging as log
from calibration import CalibrationTables
from reference_test import (
    proc_1,
)
from striptease import (
    STRIP_BOARD_NAMES,
    polarimeter_iterator,
    StripProcedure,
    StripTag,
)
from turnon import TurnOnOffProcedure


class ReferenceTestProcedure(StripProcedure):
    def __init__(self):
        super(ReferenceTestProcedure, self).__init__()
        self.calib = CalibrationTables()

    def run(self):
        turnon_proc = TurnOnOffProcedure(waittime_s=1.0, turnon=True)
        turnoff_proc = TurnOnOffProcedure(waittime_s=1.0, turnon=False)

        for cur_board, pol_idx, polname in polarimeter_iterator(args.board):
            self.conn.log(message=f"turning on {polname} for reference procedure 1…")
            with StripTag(conn=self.command_emitter, name=f"ref1_turnon_pol_{polname}"):

                turnon_proc.set_board_horn_polarimeter(
                    new_board=cur_board,
                    new_horn=polname,
                    new_pol=None,
                )
                turnon_proc.run()
                self.command_emitter.command_list += turnon_proc.get_command_list()
                turnon_proc.clear_command_list()

            self.conn.log(message=f"{polname} is now on, start the reference procedure 1")
            proc_1(self, polname, cur_board, '1')
            self.conn.log(
                message=f"reference procedure 1 for {polname} has been completed, turning {polname} off…"
            )

            with StripTag(conn=self.command_emitter, name=f"ref1_turnoff_pol_{polname}"):
                # turn off polarimeter
                turnoff_proc.set_board_horn_polarimeter(
                    new_board=cur_board,
                    new_horn=polname,
                    new_pol=None,
                )
                turnoff_proc.run()
                self.command_emitter.command_list += turnoff_proc.get_command_list()
                turnoff_proc.clear_command_list()


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Procedure a command sequence to turn on the boards",
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILENAME",
        type=str,
        dest="output_filename",
        default="",
        help="""Name of the file where to write the output (in JSON format).
        If not provided, the output will be sent to stdout""",
    )

    parser.add_argument(
        "board",
        type=str,
        nargs="?",
        default=STRIP_BOARD_NAMES,
        help="ref_turn on one or more boards",
    )

    args = parser.parse_args()

    log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s]%(message)s")

    proc = ReferenceTestProcedure()
    proc.run()
    proc.output_json(args.output_filename)
