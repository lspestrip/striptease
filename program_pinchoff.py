#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging as log

from calibration import CalibrationTables
from striptease import (
    BOARD_TO_W_BAND_POL,
    StripTag,
    normalize_polarimeter_name,
    get_lna_num,
)
from striptease.procedures import StripProcedure
from program_turnon import TurnOnOffProcedure, SetupBoard


class PinchOffProcedure(StripProcedure):
    def __init__(self):
        super(PinchOffProcedure, self).__init__()
        self.cal = CalibrationTables()

    def turn_on_board(self, conn, board_setup, board):
        log.info(f"Turnon of board {board}")
        turnon_proc = TurnOnOffProcedure(waittime_s=1.0, turnon=True)

        for cur_horn_idx in range(7):
            turnon_proc.set_board_horn_polarimeter(
                new_board=board,
                new_horn=normalize_polarimeter_name(f"{board}{cur_horn_idx}"),
                new_pol=None,
            )
            turnon_proc.run()

        return turnon_proc.get_command_list()

    def run(self):
        conn = self.command_emitter

        for cur_board in ["R", "V", "G", "B", "Y", "O", "I"]:
            board_setup = SetupBoard(
                config=self.conf,
                board_name=cur_board,
                post_command=self.command_emitter,
            )

            self.command_emitter.command_list += self.turn_on_board(
                conn, board_setup, cur_board
            )

            # Wait a while after having turned on the board
            self.wait(seconds=5)

            # Now run the pinch-off procedure
            for cur_horn_idx in range(8):
                if cur_board == "I" and cur_horn_idx == 7:
                    continue

                if cur_horn_idx == 7:
                    cur_horn_name = BOARD_TO_W_BAND_POL[cur_board]
                else:
                    cur_horn_name = f"{cur_board}{cur_horn_idx}"

                board_setup.enable_electronics(polarimeter=cur_horn_name, mode=0)

                for id_value in (100, 4_000, 8_000, 12_000):
                    for cur_lna in ("HA3", "HA2", "HA1", "HB3", "HB2", "HB1"):
                        board_setup.setup_ID(cur_horn_name, cur_lna, value=id_value)

                        with StripTag(
                            conn=self.command_emitter,
                            name=f"PINCHOFF_IDSET_{cur_horn_name}_{cur_lna}_{id_value:.0f}muA",
                        ):
                            conn.wait(seconds=5)


if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser, RawDescriptionHelpFormatter

    parser = ArgumentParser(
        description="Produce a command sequence to turn on one or more polarimeters",
        formatter_class=RawDescriptionHelpFormatter,
        epilog="""

Usage example:

    python3 program_pinchoff.py
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
    args = parser.parse_args()

    log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    proc = PinchOffProcedure()
    proc.run()

    import json

    output = json.dumps(proc.get_command_list(), indent=4)

    if args.output_filename == "":
        print(output)
    else:
        with open(args.output_filename, "wt") as outf:
            outf.write(output)
