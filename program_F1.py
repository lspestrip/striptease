#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from program_turnon import TurnOnOffProcedure
import logging as log

DEFAULT_WAITTIME_S = 5.0


class F1Procedure(TurnOnOffProcedure):
    def __init__(self, waittime_s=5, turnon=True):
        super(F1Procedure, self).__init__()

    def run(self):
        turn_on_board = True
        for cur_board in "ROYGBVIW":
            for cur_horn_idx in range(7):
                horn_name = f"{cur_board}{cur_horn_idx}"

                # Horn W0 does not exist
                if horn_name == "W0":
                    continue

                self.set_board_horn_polarimeter(
                    new_board=cur_board, new_horn=horn_name, new_pol=None,
                )

                self.run_turnon(
                    turn_on_board=turn_on_board, stable_acquisition_time_s=300,
                )
                turn_on_board = False

                self.run_turnoff()


if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser, RawDescriptionHelpFormatter

    parser = ArgumentParser(
        description="Produce a command sequence to run the Strip F1 test",
        formatter_class=RawDescriptionHelpFormatter,
        epilog="""

Usage example:

    python3 program_F1.py > f1_procedure.json
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
    parser.add_argument("--bias-steps", dest="bias_steps", action="append")
    parser.add_argument(
        "--wait-time-sec",
        metavar="VALUE",
        type=float,
        dest="waittime_s",
        default=DEFAULT_WAITTIME_S,
        help=f"Time to wait after having altered the bias level for each amplifier "
        "(default: {DEFAULT_WAITTIME_S}, set to 0 to disable)",
    )

    args = parser.parse_args()

    log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    proc = F1Procedure(waittime_s=args.waittime_s)
    proc.run()

    import json

    output = json.dumps(proc.get_command_list(), indent=4)
    if args.output_filename == "":
        print(output)
    else:
        with open(args.output_filename, "wt") as outf:
            outf.write(output)
