#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# phaseswitch test procedure

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

DEFAULT_PRE_ACQUISITION_TIME_S = 120.0


class PSProcedure(StripProcedure):
    def __init__(self, pre_acquisition_time_s, reverse_test, forward_test):
        super(PSProcedure, self).__init__()
        data_file_path = (
            Path(__file__).parent / "data" / "corrispondenze_FH_testDC.xlsx"
        )
        log.info(f'Reading correspondences from file "{data_file_path}"')
        self.dfs = pd.read_excel(data_file_path, index_col=0)
        self.pre_acquisition_time_s = pre_acquisition_time_s
        self.reverse_test = reverse_test
        self.forward_test = forward_test

    def run(self):
        calibr = CalibrationTables()
        turnon_proc = TurnOnOffProcedure(
            waittime_s=1.0, turnon=True, stable_acquisition_time_s=600
        )
        turnoff_proc = TurnOnOffProcedure(waittime_s=1.0, turnon=False)
        for cur_board, pol_idx, pol_name in polarimeter_iterator(args.board):
            # turnon pol
            with StripTag(
                conn=self.command_emitter, name=f"phsw_turnon_pol_{pol_name}"
            ):
                turnon_proc.set_board_horn_polarimeter(
                    new_board=cur_board,
                    new_horn=pol_name,
                    new_pol=None,
                )
                turnon_proc.run()

                self.command_emitter.command_list += turnon_proc.get_command_list()
                turnon_proc.clear_command_list()

            self.conn.log(message="set pol state to unswitching 0101")

            # set pol state to unswitching 0101

            with StripTag(conn=self.command_emitter, name=f"phsw_set_unsw_{pol_name}"):
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

            if self.pre_acquisition_time_s > 0:
                wait_with_tag(
                    conn=self.command_emitter,
                    seconds=self.pre_acquisition_time_s,
                    name=f"phsw_acq_unsw0101_pol{pol_name}",
                )

            # cuves

            val = self.dfs.loc[pol_name]["RT"]
            test_number = self.dfs.loc[pol_name]["RT"]
            log.info("Going to download unit-level test {}".format(test_number))
            try:
                test = get_unit_test(test_number)
            except HTTPError as e:
                log.error(f"Unable to load test {test_number}, reason: {e}")
            unit_test_data = load_unit_test_data(test)
            log.info(f"Loading test {val} of {pol_name}")

            if self.reverse_test:
                for pin, ps in [
                    (0, "PSA1"),
                    (1, "PSA2"),
                    (2, "PSB1"),
                    (3, "PSB2"),
                ]:
                    try:
                        irvr = unit_test_data.components[ps].curves["IRVR"]
                        Vrev = irvr["AnodeV"][:, 0] * 1e3  # convert from volt to mV
                    except KeyError:
                        log.warning(f"IRVR does not exist for {pol_name} {ps}")
                        Vrev = np.linspace(start=0, stop=1900, num=50)
                    self.conn.log(message=f"curve {pol_name} {ps} Vpin{pin}")
                    with StripTag(
                        conn=self.command_emitter,
                        name=f"phsw_curve_{pol_name}_{ps}_vpin{pin}",
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
                                name=f"phsw_set_v_{pol_name}_{ps}_vpin{pin}",
                            )

            if self.forward_test:
                for pin, ps in [
                    (0, "PSA1"),
                    (1, "PSA2"),
                    (2, "PSB1"),
                    (3, "PSB2"),
                ]:
                    try:
                        ifvf = unit_test_data.components[ps].curves["IFVF"]
                        Ifor = ifvf["AnodeI"][:, 0] * 1e6
                    except KeyError:
                        log.warning(f"IFVF does not exist for {pol_name} {ps}")
                        Ifor = np.arange(start=0, stop=1050, step=50)
                    self.conn.log(message=f"curve {pol_name} {ps} Ipin{pin}")
                    with StripTag(
                        conn=self.command_emitter,
                        name=f"phsw_curve_{pol_name}_{ps}_ipin{pin}",
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
                                name=f"phsw_set_I_{pol_name}_{ps}_vpin{pin}",
                            )

            self.conn.log(message="set pol state to default bias 7")
            # Set default bias
            with StripTag(
                conn=self.command_emitter, name=f"phsw_set_default_{pol_name}"
            ):
                for pin_idx in range(4):
                    self.conn.set_phsw_status(
                        polarimeter=pol_name,
                        phsw_index=pin_idx,
                        status=PhswPinMode.NOMINAL_SWITCHING,
                    )

            # turnoff pol
            with StripTag(
                conn=self.command_emitter, name=f"phsw_turnoff_pol_{pol_name}"
            ):
                turnoff_proc.set_board_horn_polarimeter(
                    new_board=cur_board,
                    new_horn=pol_name,
                    new_pol=None,
                )
                turnoff_proc.run()
                self.command_emitter.command_list += turnoff_proc.get_command_list()
                turnoff_proc.clear_command_list()


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
        "--reverse-test",
        default=False,
        action="store_true",
        help="""Acquire the IRVR curves. By default they are skipped, as the
        electronics prevents this test from being done.""",
    )

    parser.add_argument(
        "--pre-acquisition-time",
        metavar="SECONDS",
        default=DEFAULT_PRE_ACQUISITION_TIME_S,
        dest="pre_acquisition_time_s",
        type=float,
        help=f"""Before starting the test, the procedure acquires data
        in stable conditions for some time. With this switch you can
        either change the duration of the acquisition (the default is
        {DEFAULT_PRE_ACQUISITION_TIME_S} s), or switch it off entirely
        by passing 0.""",
    )

    parser.add_argument(
        "board",
        type=str,
        nargs="?",
        default=STRIP_BOARD_NAMES,
        help="turn on one or more boards",
    )

    args = parser.parse_args()

    # For the moment we do not provide a command-line switch for this
    args.__setattr__("forward_test", True)

    log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    proc = PSProcedure(
        pre_acquisition_time_s=args.pre_acquisition_time_s,
        reverse_test=args.reverse_test,
        forward_test=args.forward_test,
    )
    proc.run()
    proc.output_json(args.output_filename)
