#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# Procedura 3: Seguito di Procedura 2

import logging as log
from calibration import CalibrationTables
from reference_test import (
    proc_1,
)
from striptease import (
    STRIP_BOARD_NAMES,
    PhswPinMode,
    polarimeter_iterator,
    StripProcedure,
    StripTag,
    wait_with_tag,
)
from turnon import TurnOnOffProcedure


DEFAULT_WAIT_TIME_S = 120.0
DEFAULT_LONG_WAIT_TIME_S = 1800.0


class ReferenceTestProcedure(StripProcedure):
    def __init__(self, turn_on_polarimeters, wait_time_s, long_wait_time_s):
        super().__init__()
        self.calib = CalibrationTables()
        self.turn_on_polarimeters = turn_on_polarimeters
        self.wait_time_s = wait_time_s
        self.long_wait_time_s = long_wait_time_s

    def run(self):
        # turn on polarimeter

        if self.turn_on_polarimeters:
            turnon_proc = TurnOnOffProcedure(waittime_s=1.0, turnon=True)
            for cur_board, pol_idx, polname in polarimeter_iterator(args.board):
                with StripTag(
                    conn=self.command_emitter, name=f"ref3_turnon_pol_{polname}"
                ):

                    turnon_proc.set_board_horn_polarimeter(
                        new_board=cur_board,
                        new_horn=polname,
                        new_pol=None,
                    )
                    turnon_proc.run()
                    self.command_emitter.command_list += turnon_proc.get_command_list()
                    turnon_proc.clear_command_list()

                proc_1(self, polname, cur_board, 3, wait_time_s=self.wait_time_s)

                self.conn.log(message="ref3_set phsw state to default bias")
                # set phsw modulation to default bias
                for h in range(4):
                    with StripTag(
                        conn=self.command_emitter,
                        name=f"ref3_set_pol{polname}_phsw_default_end",
                    ):
                        self.conn.set_phsw_status(
                            polarimeter=polname,
                            phsw_index=h,
                            status=PhswPinMode.DEFAULT_STATE,
                        )

                self.conn.set_hk_scan(boards=cur_board, allboards=False, time_ms=500)
                wait_with_tag(
                    conn=self.conn,
                    seconds=self.wait_time_s,
                    name=f"ref3_acquisition_pol{polname}_phsw_default_end",
                )

        ####################################################################################################################
        # -------------------------------------------------------------------------------------------------------------------
        # Procedura 3
        # -------------------------------------------------------------------------------------------------------------------

        # RUN 1
        for cur_board, pol_idx, polname in polarimeter_iterator(args.board):

            for h in range(4):
                with StripTag(
                    conn=self.command_emitter,
                    name=f"ref3_set_pol_{polname}_phsw_{h}_default",
                ):
                    self.conn.set_phsw_status(
                        polarimeter=polname,
                        phsw_index=h,
                        status=PhswPinMode.DEFAULT_STATE,
                    )

        wait_with_tag(
            conn=self.conn,
            seconds=self.long_wait_time_s,
            name="ref3_acquisition_phsw_default",
        )

        # RUN 2
        for cur_board, pol_idx, polname in polarimeter_iterator(args.board):

            with StripTag(
                conn=self.command_emitter,
                name=f"ref3_set_pol{polname}_phsw_{h}_default_inv",
            ):
                for h, s in enumerate(
                    [
                        PhswPinMode.SLOW_SWITCHING_FORWARD,
                        PhswPinMode.SLOW_SWITCHING_REVERSE,
                        PhswPinMode.FAST_SWITCHING_FORWARD,
                        PhswPinMode.FAST_SWITCHING_REVERSE,
                    ]
                ):
                    self.conn.set_phsw_status(
                        polarimeter=polname, phsw_index=h, status=s
                    )

        wait_with_tag(
            conn=self.conn,
            seconds=self.long_wait_time_s,
            name="ref3_acquisition_phsw_default_inv",
        )


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
        help="Name of the file where to write the output (in JSON format)."
        "If not provided, the output will be sent to stdout",
    )

    parser.add_argument(
        "--turn-on",
        action="store_true",
        default=False,
        help="Include the commands necessary to turn on the polarimeters",
    )

    parser.add_argument(
        "--wait-time-s",
        "-w",
        metavar="SECONDS",
        type=float,
        dest="wait_time_s",
        default=DEFAULT_WAIT_TIME_S,
        help=f"""Short time to spend in each stable configuration
        (default: {DEFAULT_WAIT_TIME_S})""",
    )

    parser.add_argument(
        "--long-wait-time-s",
        metavar="SECONDS",
        type=float,
        dest="long_wait_time_s",
        default=DEFAULT_LONG_WAIT_TIME_S,
        help=f"""Long time to spend in each stable configuration
        (default: {DEFAULT_LONG_WAIT_TIME_S})""",
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

    proc = ReferenceTestProcedure(
        turn_on_polarimeters=args.turn_on,
        wait_time_s=args.wait_time_s,
        long_wait_time_s=args.long_wait_time_s,
    )
    proc.run()
    proc.output_json(args.output_filename)
