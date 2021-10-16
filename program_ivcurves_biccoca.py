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
    get_lna_num,
    get_lna_list,
)
from striptease.biases import InstrumentBiases
from striptease.procedures import StripProcedure
from striptease.unittests import get_unit_test, load_unit_test_data, UnitTestDC
from program_turnon import TurnOnOffProcedure


class IVProcedure(StripProcedure):
    def __init__(self, args, waittime_perconf_s=1.8):
        super(IVProcedure, self).__init__()
        self.args = args
        self.waittime_perconf_s = waittime_perconf_s

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
                new_board=board, new_horn=polname, new_pol=None
            )
            turnon_proc.run()

        return turnon_proc.get_command_list()

    def run(self):
        # Turn on the polarimeter(s)
        for cur_board in STRIP_BOARD_NAMES:
            # Append the sequence of commands to turnon this board to
            # the JSON object
            # self.command_emitter.command_list += self.turn_on_board(cur_board)
            pass

        # Verification step
        with StripTag(conn=self.command_emitter, name="IVTEST_VERIFICATION_TURNON"):
            # Wait a while after having turned on all the boards
            self.wait(seconds=10)

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
            " The polarimeter %s corresponds to module %s",
            self.bicocca_test.polarimeter_name,
            module_name,
        )

        calibr = CalibrationTables()
        defaultBias = InstrumentBiases()
        lna_list = get_lna_list(pol_name=self.bicocca_test.polarimeter_name)

        # --> First test: ID vs VD --> For each VG, we used VD curves
        self.conn.tag_start(name=f"IVTEST_IDVD_{module_name}")

        for lna in lna_list:
            lna_number = get_lna_num(lna)
            # Read default configuration
            with StripTag(
                conn=self.command_emitter, name=f"{module_name}_{lna}_READDEFAULT_VGVD"
            ):
                # read bias in mV
                default_vg_adu = calibr.physical_units_to_adu(
                    polarimeter=module_name,
                    hk="vgate",
                    component=lna,
                    value=defaultBias.get_biases(
                        module_name, param_hk=f"VG{lna_number}"
                    ),
                )

                # read bias in mV
                default_vd_adu = calibr.physical_units_to_adu(
                    polarimeter=module_name,
                    hk="vdrain",
                    component=lna,
                    value=defaultBias.get_biases(
                        module_name, param_hk=f"VD{lna_number}"
                    ),
                )

            # Get the data matrix and the Gate Voltage vector.
            matrixIDVD = self.bicocca_data.components[lna].curves["IDVD"]

            # from V to mV
            vgate = np.mean(matrixIDVD["GateV"], axis=0) * 1000
            selvg = vgate >= -360
            vgate = vgate[selvg]

            # For each Vg, we have several curves varing Vd
            for vg_idx, vg in enumerate(vgate):
                vg_adu = calibr.physical_units_to_adu(
                    polarimeter=module_name, hk="vgate", component=lna, value=vg
                )
                self.conn.set_vg(polarimeter=module_name, lna=lna, value_adu=vg_adu)

                # from V to mV
                curve_vdrain = matrixIDVD["DrainV"][:, vg_idx] * 1000

                for vd_idx, vd in enumerate(curve_vdrain):
                    vd_adu = calibr.physical_units_to_adu(
                        polarimeter=module_name, hk="vdrain", component=lna, value=vd
                    )
                    self.conn.set_vd(polarimeter=module_name, lna=lna, value_adu=vd_adu)

                    with StripTag(
                        conn=self.command_emitter,
                        name=f"{module_name}_{lna}_SET_VGVD_{vg_idx}_{vd_idx}",
                        comment=f"VG_{vg:.2f}mV_VD_{vd:.2f}mV",
                    ):
                        self.conn.set_hk_scan(allboards=True)
                        self.conn.wait(self.waittime_perconf_s)

            # Back to the default values of vd and vg (for each LNA)
            with StripTag(
                conn=self.command_emitter, name=f"{module_name}_{lna}_BACK2DEFAULT_VGVD"
            ):
                self.conn.set_vg(
                    polarimeter=module_name, lna=lna, value_adu=default_vg_adu
                )
                self.conn.set_vd(
                    polarimeter=module_name, lna=lna, value_adu=default_vd_adu
                )
                self.conn.wait(self.waittime_perconf_s)

        self.conn.tag_stop(name=f"IVTEST_IDVD_{module_name}")

        #
        # --> Second test: ID vs VG --> For each VD, we used VG curves

        self.conn.tag_start(name=f"IVTEST_IDVG_{module_name}")

        for lna in lna_list:
            lna_number = get_lna_num(lna)
            # Read default configuration
            with StripTag(
                conn=self.command_emitter, name=f"{module_name}_{lna}_READDEFAULT_VDVG"
            ):
                # read bias in mV
                default_vg_adu = calibr.physical_units_to_adu(
                    polarimeter=module_name,
                    hk="vgate",
                    component=lna,
                    value=defaultBias.get_biases(
                        module_name, param_hk=f"VG{lna_number}"
                    ),
                )

                # read bias in mV
                default_vd_adu = calibr.physical_units_to_adu(
                    polarimeter=module_name,
                    hk="vdrain",
                    component=lna,
                    value=defaultBias.get_biases(
                        module_name, param_hk=f"VD{lna_number}"
                    ),
                )
            # Get the data matrix and the Gate Voltage vector.
            matrixIDVG = self.bicocca_data.components[lna].curves["IDVG"]

            # from V to mV
            vdrain = np.mean(matrixIDVG["DrainV"], axis=0) * 1000

            # For each Vd, we have several curves varing Vg
            for vd_idx, vd in enumerate(vdrain):
                vd_adu = calibr.physical_units_to_adu(
                    polarimeter=module_name, hk="vdrain", component=lna, value=vd
                )
                self.conn.set_vg(polarimeter=module_name, lna=lna, value_adu=vd_adu)

                # from V to mV
                curve_vgate = matrixIDVG["GateV"][:, vd_idx] * 1000.0
                selcurvg = curve_vgate >= -360
                curve_vgate = vgate[selvg]

                for vg_idx, vg in enumerate(curve_vgate):
                    vg_adu = calibr.physical_units_to_adu(
                        polarimeter=module_name, hk="vgate", component=lna, value=vg
                    )
                    self.conn.set_vd(polarimeter=module_name, lna=lna, value_adu=vg_adu)

                    with StripTag(
                        conn=self.command_emitter,
                        name=f"{module_name}_{lna}_VDVG_{vd_idx}_{vg_idx}",
                        comment=f"VD_{vd:0.2f}mV_VG_{vg:.2f}mV",
                    ):
                        #
                        self.conn.set_hk_scan(allboards=True)
                        self.conn.wait(self.waittime_perconf_s)
            # Back to the default values of vd and vg (for each LNA)
            with StripTag(
                conn=self.command_emitter,
                name=f"IVTEST_IDVG_{module_name}_{lna}_BACK2DEFAULT_VDVG",
            ):
                self.conn.set_vg(
                    polarimeter=module_name, lna=lna, value_adu=default_vg_adu
                )
                self.conn.set_vd(
                    polarimeter=module_name, lna=lna, value_adu=default_vd_adu
                )

                self.conn.wait(self.waittime_perconf_s)

        self.conn.tag_stop(name=f"IVTEST_IDVG_{module_name}")


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
