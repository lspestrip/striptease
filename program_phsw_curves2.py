#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging as log
from pathlib import Path
from urllib.error import HTTPError

import pandas as pd
import numpy as np

from calibration import CalibrationTables
from striptease import (
    STRIP_BOARD_NAMES,
    get_unit_test,
    load_unit_test_data,
    PhswPinMode,
    polarimeter_iterator,
    StripProcedure,
    StripTag,
    wait_with_tag,
)
from program_turnon import TurnOnOffProcedure


class PSProcedure(StripProcedure):
    def __init__(self):
        super(PSProcedure, self).__init__()
        data_file_path = (
            Path(__file__).parent / "data" / "corrispondenze_FH_testDC.xlsx"
        )
        log.info(f'Reading correspondences from file "{data_file_path}"')
        self.dfs = pd.read_excel(data_file_path, index_col=0)

    def run(self):
        calibr = CalibrationTables()
        turnon_proc = TurnOnOffProcedure(waittime_s=1.0, turnon=True)
        with StripTag(conn=self.command_emitter, name="turnon_all_pol"):
            for cur_board, pol_idx, pol_name in polarimeter_iterator(args.board):

                # turnon pol

                turnon_proc.set_board_horn_polarimeter(
                    new_board=cur_board,
                    new_horn=pol_name,
                    new_pol=None,
                )
                turnon_proc.run()

                self.command_emitter.command_list += turnon_proc.get_command_list()
            self.conn.wait(seconds=1800)
        self.conn.log(message="set pol state to unswitching 0101")
        for cur_board, pol_idx, pol_name in polarimeter_iterator(args.board):

            with StripTag(conn=self.command_emitter, name=f"Set_unsw_{pol_name}"):
                for pin_idx, status in enumerate(
                    [
                        PhswPinMode.STILL_SIGNAL,
                        PhswPinMode.STILL_NO_SIGNAL,
                        PhswPinMode.STILL_SIGNAL,
                        PhswPinMode.STILL_NO_SIGNAL,
                    ]
                ):
                    self.conn.set_phsw_status(
                        polarimeter=pol_name, phsw_index=pin_idx, status=status
                    )

            wait_with_tag(
                conn=self.command_emitter,
                seconds=120,
                name=f"acquisition_unsw0101_pol{pol_name}",
            )
            # cuves
            test_number = self.dfs.loc[pol_name]["RT"]
            log.info("Going to download unit-level test {}".format(test_number))
            try:
                test = get_unit_test(test_number)
            except HTTPError as e:
                log.error(f"Unable to load test {test_number}, reason: {e}")
            data = load_unit_test_data(test)
            log.info(f"Loading test {test_number} of {pol_name}")

            for pin, ps in [
                (0, "PSA1"),
                (1, "PSA2"),
                (2, "PSB1"),
                (3, "PSB2"),
            ]:
                try:
                    irvr = data.components[ps].curves["IRVR"]
                    Vrev = irvr["AnodeV"][:, 0] * 1e3  # convert from volt to mV
                except KeyError:
                    log.warning(f"IRVR does not exist for {pol_name} {ps}")
                    Vrev = np.linspace(start=0, stop=1900, num=50)
                self.conn.log(message=f"curve {pol_name} {ps} Vpin{pin}")
                with StripTag(
                    conn=self.command_emitter,
                    name=f"curve {pol_name} {ps} Vpin{pin}",
                ):

                    for v in Vrev:
                        adu = calibr.physical_units_to_adu(
                            pol_name, hk="vphsw", component=pin, value=v
                        )
                        self.conn.set_phsw_bias(
                            pol_name, phsw_index=pin, vpin_adu=adu, ipin_adu=None
                        )
                        self.conn.set_hk_scan(cur_board)
                        self.conn.log(message=f"Set V={v:.1f} mV = {adu} ADU")
                        wait_with_tag(
                            conn=self.command_emitter,
                            seconds=10,
                            name=f"Set V {pol_name} {ps} Vpin{pin}",
                        )

            for pin, ps in [
                (0, "PSA1"),
                (1, "PSA2"),
                (2, "PSB1"),
                (3, "PSB2"),
            ]:
                try:
                    ifvf = data.components[ps].curves["IFVF"]
                    Ifor = ifvf["AnodeI"][:, 0] * 1e6
                except KeyError:
                    log.warning(f"IFVF does not exist for {pol_name} {ps}")
                    Ifor = np.arange(start=0, stop=1050, step=50)
                self.conn.log(message=f"curve {pol_name} {ps} Ipin{pin}")
                with StripTag(
                    conn=self.command_emitter,
                    name=f"curve {pol_name} {ps} Ipin{pin}",
                ):

                    for i in Ifor:
                        adu = calibr.physical_units_to_adu(
                            pol_name, hk="iphsw", component=pin, value=i
                        )
                        self.conn.set_phsw_bias(
                            pol_name, phsw_index=pin, vpin_adu=None, ipin_adu=adu
                        )
                        self.conn.set_hk_scan(cur_board)
                        self.conn.log(message=f"Set I={i:.1f} uA = {adu} ADU")
                        wait_with_tag(
                            conn=self.command_emitter,
                            seconds=10,
                            name=f"Set I {pol_name} {ps} Vpin{pin}",
                        )

            self.conn.log(message="set pol state to default bias 7")
            # Set default bias
            with StripTag(
                conn=self.command_emitter, name=f"set_default_bias{pol_name}"
            ):
                for pin_idx in range(4):
                    self.conn.set_phsw_status(
                        polarimeter=pol_name,
                        phsw_index=pin_idx,
                        status=PhswPinMode.NOMINAL_SWITCHING,
                    )


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Produce a command sequence to turn on one or boards",
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
        "board",
        type=str,
        nargs="?",
        default=STRIP_BOARD_NAMES,
        help="turn on one or more boards",
    )

    args = parser.parse_args()

    log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    proc = PSProcedure()
    proc.run()
    proc.output_json(args.output_filename)
