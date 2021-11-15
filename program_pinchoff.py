#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging as log

from calibration import CalibrationTables
from striptease import (
    STRIP_BOARD_NAMES,
    StripProcedure,
    StripTag,
    polarimeter_iterator,
    wait_with_tag,
)
from program_turnon import TurnOnOffProcedure


class PinchOffProcedure(StripProcedure):
    def __init__(self):
        super(PinchOffProcedure, self).__init__()

    def turn_on_board(self, board):
        log.info(f"Turnon of board {board}")
        turnon_proc = TurnOnOffProcedure(waittime_s=1.0, turnon=True)

        for _, pol_idx, pol_name in polarimeter_iterator(boards=board):
            turnon_proc.set_board_horn_polarimeter(
                new_board=board, new_horn=pol_name, new_pol=None
            )
            turnon_proc.run()

        return turnon_proc.get_command_list()

    def run(self):
        calibr = CalibrationTables()

        for cur_board in STRIP_BOARD_NAMES:
            # Append the sequence of commands to turnon this board to
            # the JSON object
            self.command_emitter.command_list += self.turn_on_board(cur_board)

            # Wait a while after having turned on the board
            self.wait(seconds=5)

        # Verification step
        wait_with_tag(
            conn=self.command_emitter, name="PINCHOFF_VERIFICATION_1", seconds=300
        )

        for cur_board in STRIP_BOARD_NAMES:
            # Now run the pinch-off procedure for each board
            with StripTag(conn=self.command_emitter, name=f"PINCHOFF_TILE_{cur_board}"):
                for _, pol_idx, pol_name in polarimeter_iterator(boards=cur_board):
                    self.conn.enable_electronics(polarimeter=pol_name, pol_mode=5)

                    for id_value_muA in (100, 4_000, 8_000, 12_000):
                        for cur_lna in ("HA3", "HA2", "HA1", "HB3", "HB2", "HB1"):
                            # Convert the current (μA) in ADU
                            adu = calibr.physical_units_to_adu(
                                polarimeter=pol_name,
                                hk="idrain",
                                component=cur_lna,
                                value=id_value_muA,
                            )
                            self.conn.set_id(pol_name, cur_lna, value_adu=adu)

                            wait_with_tag(
                                conn=self.command_emitter,
                                name=f"PINCHOFF_IDSET_{pol_name}_{cur_lna}_{id_value_muA:.0f}muA",
                                seconds=18,
                            )


if __name__ == "__main__":
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
    proc.output_json(args.output_filename)
