#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# Procedura 4: seguito di Procedura 2

import logging as log
from calibration import CalibrationTables
from .reference_test import (
    proc_1,
)
from striptease import (
    STRIP_BOARD_NAMES,
    PhswPinMode,
    polarimeter_iterator,
    StripTag,
    StripProcedure,
    TurnOnOffProcedure,
    wait_with_tag,
)


class ReferenceTestProcedure(StripProcedure):
    def __init__(self):
        super(ReferenceTestProcedure, self).__init__()
        self.calib = CalibrationTables()

    def run(self):
        # turn on polarimeter
        turnon_proc = TurnOnOffProcedure(waittime_s=1.0, turnon=True)
        for cur_board, pol_idx, polname in polarimeter_iterator(args.board):
            with StripTag(conn=self.command_emitter, name=f"ref_turnon_pol_{polname}"):

                turnon_proc.set_board_horn_polarimeter(
                    new_board=cur_board,
                    new_horn=polname,
                    new_pol=None,
                )
                turnon_proc.run()
                self.command_emitter.command_list += turnon_proc.get_command_list()

            print(polname)
            proc_1(self, polname, cur_board)

            self.conn.log(message="ref_set phsw state to default bias")
            # set phsw modulation to default bias
            for h in range(4):
                with StripTag(
                    conn=self.command_emitter, name=f"ref_set_pol_state{polname}"
                ):
                    self.conn.set_phsw_status(
                        polarimeter=polname,
                        phsw_index=h,
                        status=PhswPinMode.DEFAULT_STATE,
                    )

            self.conn.set_hk_scan(boards=cur_board, allboards=False, time_ms=500)
            wait_with_tag(
                conn=self.conn, seconds=120, name="ref_acquisition_default_pol{polname}"
            )

        ####################################################################################################################
        # -------------------------------------------------------------------------------------------------------------------
        # Procedura 4
        # -------------------------------------------------------------------------------------------------------------------

        # STATE 1
        for cur_board, pol_idx, polname in polarimeter_iterator(args.board):

            with StripTag(
                conn=self.command_emitter, name=f"ref_set_pol_{polname}_phsw_{h}_STATE1"
            ):
                for h, s in enumerate(
                    [
                        PhswPinMode.STILL_SIGNAL,
                        PhswPinMode.DEFAULT_STATE,
                        PhswPinMode.STILL_SIGNAL,
                        PhswPinMode.DEFAULT_STATE,
                    ]
                ):
                    self.conn.set_phsw_status(
                        polarimeter=polname, phsw_index=h, status=s
                    )

        wait_with_tag(conn=self.conn, seconds=7200, name="ref_wait_PHSW_STATE1")

        # STATE 2
        for cur_board, pol_idx, polname in polarimeter_iterator(args.board):

            with StripTag(
                conn=self.command_emitter, name=f"ref_set_pol_{polname}_phsw_{h}_STATE2"
            ):
                for h, s in enumerate(
                    [
                        PhswPinMode.DEFAULT_STATE,
                        PhswPinMode.STILL_SIGNAL,
                        PhswPinMode.DEFAULT_STATE,
                        PhswPinMode.STILL_SIGNAL,
                    ]
                ):
                    self.conn.set_phsw_status(
                        polarimeter=polname, phsw_index=h, status=s
                    )

        wait_with_tag(conn=self.conn, seconds=7200, name="ref_wait_PHSW_STATE2")

        # STATE 3
        for cur_board, pol_idx, polname in polarimeter_iterator(args.board):

            with StripTag(
                conn=self.command_emitter, name=f"ref_set_pol_{polname}_phsw_{h}_STATE3"
            ):

                for h, s in enumerate(
                    [
                        PhswPinMode.DEFAULT_STATE,
                        PhswPinMode.STILL_SIGNAL,
                        PhswPinMode.STILL_SIGNAL,
                        PhswPinMode.DEFAULT_STATE,
                    ]
                ):
                    self.conn.set_phsw_status(
                        polarimeter=polname, phsw_index=h, status=s
                    )

        wait_with_tag(conn=self.conn, seconds=7200, name="ref_wait_PHSW_STATE3")

        # STATE 4
        for cur_board, pol_idx, polname in polarimeter_iterator(args.board):

            with StripTag(
                conn=self.command_emitter, name=f"ref_set_pol_{polname}_phsw_{h}_STATE4"
            ):

                for h, s in enumerate(
                    [
                        PhswPinMode.STILL_SIGNAL,
                        PhswPinMode.DEFAULT_STATE,
                        PhswPinMode.DEFAULT_STATE,
                        PhswPinMode.STILL_SIGNAL,
                    ]
                ):
                    self.conn.set_phsw_status(
                        polarimeter=polname, phsw_index=h, status=s
                    )

        wait_with_tag(conn=self.conn, seconds=7200, name="ref_wait_PHSW_STATE4")


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
