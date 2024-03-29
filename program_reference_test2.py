#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# Procedura 2: accensione progressiva

import logging as log
from calibration import CalibrationTables
from reference_test import (
    proc_1,
)
from striptease import (
    STRIP_BOARD_NAMES,
    polarimeter_iterator,
    PhswPinMode,
    StripProcedure,
    StripTag,
    wait_with_tag,
)
from turnon import TurnOnOffProcedure


DEFAULT_WAIT_TIME_S = 120.0


class ReferenceTestProcedure(StripProcedure):
    def __init__(self, wait_time_s):
        super(ReferenceTestProcedure, self).__init__()
        self.calib = CalibrationTables()
        self.wait_time_s = wait_time_s

    def run(self):
        # turn on polarimeter
        turnon_proc = TurnOnOffProcedure(waittime_s=1.0, turnon=True)
        for cur_board, pol_idx, polname in polarimeter_iterator(args.board):
            with StripTag(conn=self.command_emitter, name=f"ref2_turnon_pol_{polname}"):

                turnon_proc.set_board_horn_polarimeter(
                    new_board=cur_board,
                    new_horn=polname,
                    new_pol=None,
                )
                turnon_proc.run()
                self.command_emitter.command_list += turnon_proc.get_command_list()
                turnon_proc.clear_command_list()

            proc_1(self, polname, cur_board, 2, wait_time_s=self.wait_time_s)

            self.conn.log(message="ref2_set phsw state to default bias")
            # set phsw modulation to default bias
            with StripTag(
                conn=self.command_emitter,
                name=f"ref2_set_pol{polname}_phsw_default_end",
            ):
                for h in range(4):
                    self.conn.set_phsw_status(
                        polarimeter=polname,
                        phsw_index=h,
                        status=PhswPinMode.DEFAULT_STATE,
                    )

            self.conn.set_hk_scan(boards=cur_board, allboards=False, time_ms=500)
            wait_with_tag(
                conn=self.conn,
                seconds=self.wait_time_s,
                name=f"ref2_acquisition_pol{polname}_phsw_default_end",
            )


if __name__ == "__main__":
    from argparse import ArgumentParser, RawDescriptionHelpFormatter

    parser = ArgumentParser(
        description="Procedure a command sequence to turn on the boards",
        formatter_class=RawDescriptionHelpFormatter,
        epilog=""""

        python3 amalia_reference.py
        """,
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILENAME",
        type=str,
        dest="output_filename",
        default="",
        help="Name of the file where to write the output (in JSON format)."
        "If not provided, the output will be sent to stdout",
    )

    parser.add_argument(
        "--wait-time-s",
        "-w",
        metavar="SECONDS",
        type=float,
        dest="wait_time_s",
        default=DEFAULT_WAIT_TIME_S,
        help="Time to spend in each stable configuration (default: {DEFAULT_WAIT_TIME_S})",
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

    proc = ReferenceTestProcedure(wait_time_s=args.wait_time_s)
    proc.run()
    proc.output_json(args.output_filename)
