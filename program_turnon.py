#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging as log
import re

from rich.logging import RichHandler

from turnon import TurnOnOffProcedure
from striptease import BOARD_TO_W_BAND_POL

DEFAULT_WAITTIME_S = 5.0


def unroll_polarimeters(pol_list):
    board_horn_pol = re.compile(r"([GBPROYW][0-6]):(STRIP[0-9][0-9])")
    for cur_pol in pol_list:
        if cur_pol in ("V", "R", "O", "Y", "G", "B", "I"):
            for idx in range(7):
                yield (f"{cur_pol}{idx}", None)

            # Include the W-band polarimeter
            if cur_pol != "I":
                yield (BOARD_TO_W_BAND_POL[cur_pol], None)

            continue
        else:
            # Is this polarimeter in a form like "G0:STRIP33"?
            m = board_horn_pol.match(cur_pol)
            if m:
                yield (m.group(1), m.group(2))
            else:
                yield (cur_pol, None)


if __name__ == "__main__":
    from argparse import ArgumentParser, RawDescriptionHelpFormatter

    parser = ArgumentParser(
        description="Produce a command sequence to turn on one or more polarimeters",
        formatter_class=RawDescriptionHelpFormatter,
        epilog="""

Usage example:

    python3 program_turnon.py --board 2 G0 G3 G4:STRIP33
""",
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
        required=True,
        help="Name of the board to use",
    )
    parser.add_argument(
        "--zero-bias",
        action="store_true",
        default=False,
        help="Only set the LNAs to zero bias instead of turning them on to full nominal bias",
    )
    parser.add_argument(
        "--bias-table-file",
        metavar="FILE",
        type=str,
        default=None,
        required=True,
        help="Path to the Excel file containing the biases to use",
    )
    parser.add_argument(
        "--turnoff",
        action="store_true",
        default=False,
        help="If this flag is present, the procedure will turn the polarimeter *off*",
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
        help="Time to wait after having altered the bias level for each amplifier "
        f"(default: {DEFAULT_WAITTIME_S}, set to 0 to disable)",
    )

    args = parser.parse_args()

    log.basicConfig(
        level=log.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
    )

    proc = TurnOnOffProcedure(
        waittime_s=args.waittime_s,
        turnon=not args.turnoff,
        zero_bias=args.zero_bias,
        bias_file_name=args.bias_table_file,
    )
    for cur_horn, cur_polarimeter in unroll_polarimeters(args.polarimeters):
        log.info("Processing horn %s, polarimeter %s", cur_horn, cur_polarimeter)
        proc.set_board_horn_polarimeter(args.board, cur_horn, cur_polarimeter)
        proc.run()

    proc.output_json(args.output_filename)
