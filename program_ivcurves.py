#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging as log

import numpy as np

from calibration import CalibrationTables
from striptease import (
    STRIP_BOARD_NAMES,
    BOARD_TO_W_BAND_POL,
    StripTag,
    normalize_polarimeter_name,
)
from striptease.biases import InstrumentBiases
from striptease.procedures import StripProcedure
from striptease.unittests import get_unit_test, load_unit_test_data, UnitTestDC
from program_turnon import TurnOnOffProcedure


class IVProcedure(StripProcedure):
    def __init__(self, args):
        super(IVProcedure, self).__init__()
        self.args = args

    def turn_on_board(self, board):
        log.info(f"Turnon of board {board}")
        turnon_proc = TurnOnOffProcedure(waittime_s=1.0, turnon=True)

        for cur_horn_idx in range(8):
            if board == "I" and cur_horn_idx == 7:
                continue

            if cur_horn_idx != 7:
                polname = f"{board}{cur_horn_idx}"
            else:
                polname = BOARD_TO_W_BAND_POL[board]

            turnon_proc.set_board_horn_polarimeter(
                new_board=board, new_horn=polname, new_pol=None,
            )
            turnon_proc.run()

        return turnon_proc.get_command_list()

    def run(self):
        # Load the matrices of the unit-test measurements done in
        # Bicocca and save them in "self.bicocca_data"
        self.bicocca_test = get_unit_test(args.bicocca_test_id)
        module_name = InstrumentBiases().polarimeter_to_module_name(
            self.bicocca_test.polarimeter_name
        )

        log.info(
            "Test %d for %s (%s) loaded from %s, is_cryogenic=%s",
            args.bicocca_test_id,
            self.bicocca_test.polarimeter_name,
            module_name,
            self.bicocca_test.url,
            str(self.bicocca_test.is_cryogenic),
        )

        self.bicocca_data = load_unit_test_data(self.bicocca_test)
        assert isinstance(self.bicocca_data, UnitTestDC)

        log.info(
            "The polarimeter %s corresponds to module %s",
            self.bicocca_test.polarimeter_name,
            module_name,
        )
        # Turn on the polarimeter(s)
        calibr = CalibrationTables()

        for cur_board in STRIP_BOARD_NAMES:
            # Append the sequence of commands to turnon this board to
            # the JSON object
            # self.command_emitter.command_list += self.turn_on_board(cur_board)
            pass

        # Verification step
        with StripTag(
            conn=self.command_emitter, name="IVTEST_VERIFICATION_1",
        ):
            # Wait a while after having turned on all the boards
            self.wait(seconds=10)

        # First step: for each Vd, move Vg

        # TODO: the list of LNAs must be fixed for W-band polarimeters
        for lna in ("HA3", "HB3", "HA2", "HB2", "HA1", "HB1"):
            matrix = self.bicocca_data.components[lna].curves["IDVD"]
            vgate = np.mean(matrix["GateV"], axis=0)

            # Unit tests in Bicocca acquire several curves with
            # varying Vd, each using a different value for Vg
            for curve_idx in range(len(vgate)):
                # Set Vg before acquiring the curve
                self.conn.set_vg(
                    polarimeter=module_name,
                    lna=lna,
                    value_adu=calibr.physical_units_to_adu(
                        polarimeter=module_name,
                        hk="vgate",
                        component=lna,
                        value=vgate[curve_idx],
                    ),
                )

                vdrain = matrix[:, curve_idx]["DrainV"]
                # idrain = matrix[:, curve_idx]["DrainI"]
                for sample_idx in range(len(vdrain)):
                    cur_vdrain_V = calibr.physical_units_to_adu(
                        polarimeter=module_name,
                        hk="vdrain",
                        component=lna,
                        value=vdrain[sample_idx],
                    )
                    self.conn.set_vd(
                        polarimeter=module_name, lna=lna, value_adu=cur_vdrain_V,
                    )

                    with StripTag(
                        conn=self.command_emitter,
                        name=f"IVTEST_{module_name}_{lna}_IDVD_{curve_idx:02d}_{cur_vdrain_V:.2f}V",
                    ):
                        self.conn.wait(6)


if __name__ == "__main__":
    from argparse import ArgumentParser, RawDescriptionHelpFormatter

    parser = ArgumentParser(
        description="Produce a command sequence to run the I-V curve test on a polarimeter",
        formatter_class=RawDescriptionHelpFormatter,
        epilog="""

Usage example:

    python3 program_ivcurves.py
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
        "bicocca_test_id",
        type=int,
        help="Number of the test acquired in Bicocca, to be used as reference",
    )
    args = parser.parse_args()

    log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    proc = IVProcedure(args=args)
    proc.run()
    proc.output_json(args.output_filename)
