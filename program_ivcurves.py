#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging as log

import numpy as np
from pathlib import Path
import pandas as pd

from calibration import CalibrationTables
from striptease import (
    STRIP_BOARD_NAMES,
    BOARD_TO_W_BAND_POL,
    StripProcedure,
    StripTag,
    get_lna_num,
    get_lna_list,
)
from striptease.biases import InstrumentBiases
from turnon import TurnOnOffProcedure


class IVProcedure(StripProcedure):
    def __init__(self, args, waittime_perconf_s=1.8):
        super(IVProcedure, self).__init__()
        #
        if args.filename == "":
            self.filename = str(
                Path(__file__).absolute().parent.parent
                / "striptease"
                / "data"
                / "input_bias_IVtest.xlsx"
            )
        else:
            self.filename = args.filename

        self.inputBiasIV = pd.read_excel(self.filename, header=0, index_col=1)

        if args.polarimeters.upper() == "ALL":
            self.polarimeters = list(self.inputBiasIV.index)
        else:
            self.polarimeters = args.polarimeters.split(" ")

        self.hk_scan = str(args.hkscan)
        self.waittime_perconf_s = waittime_perconf_s

        print(f"hk_scan {self.hk_scan} (type: {type(self.hk_scan)})")
        log.info(
            "Input polarimeters %s (hk_scan is %s)\n Loading inputBiasIV from %s",
            args.polarimeters,
            self.hk_scan,
            self.filename,
        )

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

    def get_bias_curve(self, pol_name, lna):
        vmin = self.inputBiasIV[f"{lna}/VG0 MIN"][pol_name]
        vmax = self.inputBiasIV[f"{lna}/VG0 MAX"][pol_name]
        vstep = self.inputBiasIV[f"{lna}/VG0 STEP"][pol_name]

        return np.arange(vmin, vmax, vstep)

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

        # Load the matriix with the min, max and step for
        # each LNA for each polarimeter
        count_conf = 0
        for pol_name in self.polarimeters:
            module_name = self.inputBiasIV["Module"][pol_name]
            log.info("-->Polarimeter %s (%s)", pol_name, module_name)
            calibr = CalibrationTables()
            defaultBias = InstrumentBiases()
            lna_list = get_lna_list(pol_name=pol_name)

            # --> First test: ID vs VD --> For each VG, we used VD curves
            self.conn.tag_start(name=f"IVTEST_{module_name}")

            for lna in lna_list:
                lna_number = get_lna_num(lna)
                # Read default configuration
                with StripTag(
                    conn=self.command_emitter,
                    name=f"{module_name}_{lna}_READDEFAULT_VGVD",
                ):
                    # read bias in mV
                    default_vg_adu = calibr.physical_units_to_adu(
                        polarimeter=module_name,
                        hk="vgate",
                        component=lna,
                        value=getattr(
                            defaultBias.get_biases(module_name), f"vg{lna_number}"
                        ),
                    )

                    # read bias in mV
                    default_vd_adu = calibr.physical_units_to_adu(
                        polarimeter=module_name,
                        hk="vdrain",
                        component=lna,
                        value=getattr(
                            defaultBias.get_biases(module_name), f"vd{lna_number}"
                        ),
                    )

                # Get the data matrix and the Gate Voltage vector.
                # in mV
                vgate = self.get_bias_curve(pol_name, lna)
                vdrain = np.arange(0, 900, 50)
                count_conf += len(vgate) * len(vdrain)

                # For each Vg, we have several curves varing Vd
                for vg_idx, vg in enumerate(vgate):
                    vg_adu = calibr.physical_units_to_adu(
                        polarimeter=module_name, hk="vgate", component=lna, value=vg
                    )
                    self.conn.set_vg(polarimeter=module_name, lna=lna, value_adu=vg_adu)

                    for vd_idx, vd in enumerate(vdrain):
                        vd_adu = calibr.physical_units_to_adu(
                            polarimeter=module_name,
                            hk="vdrain",
                            component=lna,
                            value=vd,
                        )
                        self.conn.set_vd(
                            polarimeter=module_name, lna=lna, value_adu=vd_adu
                        )

                        with StripTag(
                            conn=self.command_emitter,
                            name=f"{module_name}_{lna}_SET_VGVD_{vg_idx}_{vd_idx}",
                            comment=f"VG_{vg:.2f}mV_VD_{vd:.2f}mV",
                        ):
                            if self.hk_scan == "True":
                                # print(f"hk_scan is {self.hk_scan}")
                                self.conn.set_hk_scan(allboards=True)
                            self.conn.wait(self.waittime_perconf_s)

                # Back to the default values of vd and vg (for each LNA)
                with StripTag(
                    conn=self.command_emitter,
                    name=f"{module_name}_{lna}_BACK2DEFAULT_VGVD",
                ):
                    self.conn.set_vg(
                        polarimeter=module_name, lna=lna, value_adu=default_vg_adu
                    )
                    self.conn.set_vd(
                        polarimeter=module_name, lna=lna, value_adu=default_vd_adu
                    )
                    self.conn.wait(self.waittime_perconf_s)
                    count_conf += 1

            self.conn.tag_stop(name=f"IVTEST_IDVD_{module_name}")
            log.info(
                "Number of configuration and time [hrs, days]: %s  [%s, %s]\n",
                int(count_conf),
                np.around(count_conf * self.waittime_perconf_s / 3600.0, 1),
                np.around(count_conf * self.waittime_perconf_s / 3600 / 24, 3),
            )


if __name__ == "__main__":
    from argparse import ArgumentParser, RawDescriptionHelpFormatter

    parser = ArgumentParser(
        description="Produce a command sequence to run the I-V curve test on a polarimeter(s)",
        formatter_class=RawDescriptionHelpFormatter,
        epilog="""

Usage example:

    python3 program_ivcurves.py "STRIP07" >> jsonFile_IVtest_strip07
    python3 program_ivcurves.py --output jsonFile_IVtest_startChannels "STRIP07 STRIP8 STRIP13 STRIP15 STRIP61 STRIP24 STRIP36"
    python3 program_ivcurves.py --output jsonFile_IVtest_Allpolarimeters "ALL"

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
        "--input",
        "-i",
        metavar="FILENAME",
        type=str,
        dest="filename",
        default="",
        help="Name of the excel bias file to be used (in agree format)."
        "If not provided, the input_bias_IVtest.xlsx in ./data is loaded.",
    )
    parser.add_argument(
        "--hkscan",
        "-hk",
        metavar="False",
        type=str,
        dest="hkscan",
        default="True",
        help="Activation of the set_hk_scan. If not provided, the set_hk_scan is used",
    )
    parser.add_argument(
        "polarimeters",
        type=str,
        default="",
        help="String with the polarimeter name or polarimeter names. "
        "For example, "
        "'STRIP07 STRIP61 STRIP24' separated by one space, or "
        "'ALL' for all polarimeters.",
    )
    args = parser.parse_args()

    log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    proc = IVProcedure(args=args)
    proc.run()
    proc.output_json(args.output_filename)
