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

def biases_to_str(biases):
    return "Biases: " + ",".join([
        str(biases.vd0),
        str(biases.vd1),
        str(biases.vd2),
        str(biases.vd3),
        str(biases.vd4),
        str(biases.vd5),
        str(biases.vg0),
        str(biases.vg1),
        str(biases.vg2),
        str(biases.vg3),
        str(biases.vg4),
        str(biases.vg5),
        str(biases.vg4a),
        str(biases.vg5a),
        str(biases.vpin0),
        str(biases.vpin1),
        str(biases.vpin2),
        str(biases.vpin3),
        str(biases.ipin0),
        str(biases.ipin1),
        str(biases.ipin2),
        str(biases.ipin3),
        str(biases.id0),
        str(biases.id1),
        str(biases.id2),
        str(biases.id3),
        str(biases.id4),
        str(biases.id5),
    ])

class TurnOnOffProcedure(StripProcedure):
    def __init__(self, waittime_s=5, turnon=True):
        super(TurnOnOffProcedure, self).__init__()
        self.board = None
        self.horn = None
        self.polarimeter = None
        self.waittime_s = waittime_s
        self.turnon = turnon

    def set_board_horn_polarimeter(self, new_board, new_horn, new_pol=None):
        self.board = new_board
        self.horn = new_horn
        self.polarimeter = new_pol

    def run(self):
        if self.turnon:
            self.run_turnon()
        else:
            self.run_turnoff()

    def run_turnon(self):
        assert self.horn
        board_setup = SetupBoard(
            config=self.conf, board_name=self.board, post_command=self.command_emitter
        )

        current_time = datetime.now().strftime("%A %Y-%m-%d %H:%M:%S (%Z)")
        board_setup.log(
            f"Here begins the turnon procedure for polarimeter {self.horn}, "
            + f"created on {current_time} using program_turnon.py"
        )
        board_setup.log(f"We are using the setup for board {self.board}")
        if self.polarimeter:
            board_setup.log(
                f"This procedure assumes that horn {self.horn} is connected to polarimeter {self.polarimeter}"
            )

        # 1
        with StripTag(
            conn=self.command_emitter,
            name="BOARD_TURN_ON",
            comment=f"Turning on board for {self.horn}",
        ):
            board_setup.log("Going to set up the board…")
            board_setup.board_setup()
            board_setup.log("Board has been set up")

        # 2
        with StripTag(
            conn=self.command_emitter,
            name=f"ELECTRONICS_ENABLE_{self.horn}",
            comment=f"Enabling electronics for {self.horn}",
        ):
            board_setup.log(f"Enabling electronics for {self.horn}…")
            board_setup.enable_electronics(polarimeter=self.horn)
            board_setup.log("The electronics has been enabled")

        # 3
        for idx in (0, 1, 2, 3):
            with StripTag(
                conn=self.command_emitter,
                name=f"DETECTOR_TURN_ON_{idx}",
                comment=f"Turning on detector {idx} in {self.horn}",
            ):
                board_setup.turn_on_detector(self.horn, idx)

        # 4
        if self.polarimeter:
            biases = self.biases.get_biases(polarimeter_name=self.polarimeter)
            board_setup.log(f"{self.polarimeter}: {biases_to_str(biases)}")
        else:
            biases = self.biases.get_biases(module_name=self.horn)
            board_setup.log(f"{self.horn}: {biases_to_str(biases)}")

        for (index, vpin, ipin) in zip(
            range(4),
            [biases.vpin0, biases.vpin1, biases.vpin2, biases.vpin3],
            [biases.ipin0, biases.ipin1, biases.ipin2, biases.ipin3],
        ):
            try:
                with StripTag(
                    conn=self.command_emitter,
                    name=f"PHSW_BIAS_{index}",
                    comment=f"Setting biases for PH/SW {index} in {self.horn}",
                ):
                    board_setup.set_phsw_bias(self.horn, index, vpin, ipin)
            except:
                log.warning(f"Unable to set bias for detector #{index}")

        # 5
        for idx in (0, 1, 2, 3):
            with StripTag(
                conn=self.command_emitter,
                name=f"PHSW_STATUS_{idx}",
                comment=f"Setting status for PH/SW {idx} in {self.horn}",
            ):
                board_setup.set_phsw_status(self.horn, idx, status=7)

        # 6
        for lna in ("HA3", "HA2", "HA1", "HB3", "HB2", "HB1"):
            for step_idx, cur_step in enumerate([0.0, 0.5, 1.0]):
                with StripTag(
                    conn=self.command_emitter,
                    name=f"VD_SET_{lna}",
                    comment=f"Setting drain voltages for LNA {lna} in {self.horn}",
                ):
                    board_setup.setup_VD(self.horn, lna, step=cur_step)

                    if step_idx == 0:
                        board_setup.setup_VG(self.horn, lna, step=1.0)

                    if False and cur_step == 1.0:
                        # In mode 5, the following command should be useless…
                        board_setup.setup_ID(self.horn, lna, step=1.0)

                if self.waittime_s > 0:
                    self.wait(seconds=self.waittime_s)

    def run_turnoff(self):
        assert self.horn
        board_setup = SetupBoard(
            config=self.conf, board_name=self.board, post_command=self.command_emitter
        )

        current_time = datetime.now().strftime("%A %Y-%m-%d %H:%M:%S (%Z)")
        board_setup.log(
            f"Here begins the turnoff procedure for polarimeter {self.horn}, "
            + f"created on {current_time} using program_turnon.py"
        )
        board_setup.log(f"We are using the setup for board {self.board}")
        if self.polarimeter:
            board_setup.log(
                f"This procedure assumes that horn {self.horn} is connected to polarimeter {self.polarimeter}"
            )

        # 1
        with StripTag(
            conn=self.command_emitter,
            name="BOARD_TURN_OFF",
            comment=f"Turning off board for {self.horn}",
        ):
            board_setup.log("Going to set up the board…")
            board_setup.board_setup()
            board_setup.log("Board has been set up")

        # 6
        for lna in reversed(["HA3", "HA2", "HA1", "HB3", "HB2", "HB1"]):
            for step_idx, cur_step in enumerate(reversed([0.0, 0.5, 1.0])):
                with StripTag(
                    conn=self.command_emitter,
                    name="VD_SET",
                    comment=f"Setting drain voltages for LNA {lna} in {self.horn}",
                ):
                    board_setup.setup_VD(self.horn, lna, step=cur_step)

                    if step_idx == 0:
                        board_setup.setup_VG(self.horn, lna, step=1.0)

                    if False and cur_step == 1.0:
                        # In mode 5, the following command should be useless…
                        board_setup.setup_ID(self.horn, lna, step=1.0)

                if self.waittime_s > 0:
                    self.wait(seconds=self.waittime_s)

        # 2
        with StripTag(
            conn=self.command_emitter,
            name="ELECTRONICS_DISABLE",
            comment=f"Enabling electronics for {self.horn}",
        ):
            board_setup.log(f"Disabling electronics for {self.horn}…")
            board_setup.disable_electronics(polarimeter=self.horn)
            board_setup.log("The electronics has been disabled")

        board_setup.log(f"Turnoff procedure for {self.horn} completed")

def unroll_polarimeters(pol_list):
    board_horn_pol = re.compile(r"([GBPROYW][0-6]):(STRIP[0-9][0-9])")
    for cur_pol in pol_list:
        if cur_pol in ("V", "G", "B", "P", "R", "O", "Y"):
            for idx in range(7):
                yield (f"{cur_pol}{idx}", None)
            continue
        else:
            # Is this polarimeter in a form like "G0:STRIP33"?
            m = board_horn_pol.match(cur_pol)
            if m:
                yield (m.group(1), m.group(2))
            else:
                yield (cur_pol, None)


if __name__ == "__main__":
    import sys
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
        help='Name of the board to use',
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

    proc = TurnOnOffProcedure(waittime_s=args.waittime_s, turnon=not args.turnoff)
    for cur_horn, cur_polarimeter in unroll_polarimeters(args.polarimeters):
        proc.set_board_horn_polarimeter(args.board, cur_horn, cur_polarimeter)
        proc.run()

    import json

    output = json.dumps(proc.get_command_list(), indent=4)
    if args.output_filename == "":
        print(output)
    else:
        with open(args.output_filename, "wt") as outf:
            outf.write(output)
