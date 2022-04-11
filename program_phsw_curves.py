#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# phaseswitch test procedure

import logging as log
from pathlib import Path
from urllib.error import HTTPError
from typing import Optional, Tuple
import sys

import pandas as pd
import numpy as np
from rich.logging import RichHandler

from calibration import CalibrationTables
from striptease import (
    STRIP_BOARD_NAMES,
    get_unit_test,
    load_unit_test_data,
    PhswPinMode,
    polarimeter_iterator,
    StripProcedure,
    StripTag,
    UnitTestDC,
    wait_with_tag,
)
from program_turnon import TurnOnOffProcedure

DEFAULT_PRE_ACQUISITION1_TIME_S = 120.0
DEFAULT_PRE_ACQUISITION2_TIME_S = 1800.0

# Tuples containing the pin number, the diode name, and the phase switch
# condition to be used before the acquisition
PIN_PS_STATE_COMBINATIONS = [
    (0, "PSA1", "0111"),
    (1, "PSA2", "1011"),
    (2, "PSB1", "1101"),
    (3, "PSB2", "1110"),
]


def load_unit_level_test(
    pol_unittest_associations,
    pol_name: str,
    no_unit_level_tests: bool,
) -> Tuple[Optional[int], Optional[UnitTestDC]]:
    """Given the Excel table and a polarimeter, load the associated unit-level test

    The Excel table must provide matches between a polarimeter name and the
    number of the unit-level DC test.
    """

    if no_unit_level_tests:
        return None, None

    test_number = pol_unittest_associations.loc[pol_name]["RT"]
    log.info("Going to download unit-level test {}".format(test_number))

    try:
        test = get_unit_test(test_number)
    except HTTPError as e:
        log.error(f"Unable to load test {test_number}, reason: {e}")
        return None, None

    unit_test_data = load_unit_test_data(test)
    log.info(f"Test {test_number} for {pol_name} has been loaded")

    return test_number, unit_test_data


def get_sequence_of_biases(unit_test_data: Optional[UnitTestDC], ps: str, curve: str):
    if unit_test_data is not None:
        matr = unit_test_data.components[ps].curves[curve]

        return matr["AnodeI"][:, 0] if curve == "IFVF" else matr["AnodeV"][:0]

    # If we are here, it means that we must not follow the same points as one of the
    # unit-level tests.

    if curve == "IFVF":
        # Return a synthetic sequence of currents (in Ampere)
        return np.linspace(start=150e-6, stop=1e-3, num=35)

    if curve == "IRVR":
        # Return a synthetic sequence of voltages (in V)
        return np.linspace(start=0, stop=-1.9, num=20)


class PSProcedure(StripProcedure):
    def __init__(
        self,
        pre_acquisition_time_s: float,
        reverse_test: bool,
        forward_test: bool,
        turn_on: bool,
        no_unit_level_tests: bool,
        bias_file_name: str,
    ):
        super(PSProcedure, self).__init__()
        data_file_path = (
            Path(__file__).parent / "data" / "corrispondenze_FH_testDC.xlsx"
        )
        log.info(f'Reading correspondences from file "{data_file_path}"')
        self.pol_unittest_associations = pd.read_excel(data_file_path, index_col=0)
        self.pre_acquisition_time_s = pre_acquisition_time_s
        self.reverse_test = reverse_test
        self.forward_test = forward_test
        self.turn_on = turn_on
        self.no_unit_level_tests = no_unit_level_tests
        self.bias_file_name = bias_file_name

    def _stable_acquisition(self, pol_name: str, state: str, proc_number: int):
        assert (
            len(state) == 4
        ), f'The state must be in the form BBBB, with B either 0 or 1, not "{state}"'

        # Convert a string like "0101" into a set of four `PhswPinMode` constants
        # using the correspondences
        # 1 → STILL_NO_SIGNAL
        # 0 → STILL_SIGNAL
        state_constants = [
            PhswPinMode.STILL_NO_SIGNAL if x == "1" else PhswPinMode.STILL_SIGNAL
            for x in state
        ]

        self.conn.log(
            f"set phsw to {state} and acquiring for {self.pre_acquisition_time_s} s"
        )

        with StripTag(
            conn=self.command_emitter, name=f"phsw_proc{proc_number}_{pol_name}_{state}"
        ):
            for pin_idx, status in enumerate(state_constants):
                self.conn.set_phsw_status(
                    polarimeter=pol_name, phsw_index=pin_idx, status=status
                )

        if self.pre_acquisition_time_s > 0:
            wait_with_tag(
                conn=self.command_emitter,
                seconds=self.pre_acquisition_time_s,
                name=f"phsw_acq_pol{pol_name}_{state}",
            )

    def _reverse(
        self,
        calibr: CalibrationTables,
        cur_board: str,
        pol_name: str,
        unit_test_data: UnitTestDC,
        proc_number: int,
    ):
        for pin, ps, phsw_state in PIN_PS_STATE_COMBINATIONS:
            # First do a stable acquisition…
            self.stable_acquisition(pol_name, phsw_state)

            # …and then acquire the curves
            try:
                Vrev = get_sequence_of_biases(unit_test_data, ps, "IRVR")
            except KeyError:
                log.warning(f"IRVR does not exist for {pol_name} {ps}")
                self.conn.log(
                    message=f"IRVR does not exist for {pol_name} {ps} in unit-level tests. "
                    "Using a synthetic curve instead"
                )
                Vrev = get_sequence_of_biases(None, ps, "IRVR")

            Vrev *= 1e3  # convert from V to mV

            self.conn.log(
                message=f"Acquiring PH/SW reverse curve for {pol_name}, {ps} Vpin{pin}"
            )

            with StripTag(
                conn=self.command_emitter,
                name=f"phsw_proc{proc_number}_rcurve_{pol_name}_{ps}_ipin{pin}",
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
                        seconds=5,
                        name=f"phsw_proc{proc_number}_set_v_{pol_name}_{ps}_vpin{pin}",
                    )

    def _forward(
        self,
        calibr: CalibrationTables,
        cur_board: str,
        pol_name: str,
        unit_test_data: UnitTestDC,
        proc_number: int,
    ):
        for pin, ps, phsw_state in PIN_PS_STATE_COMBINATIONS:
            # First do a stable acquisition…
            self._stable_acquisition(pol_name, phsw_state, proc_number=proc_number)

            # …and then acquire the curves
            try:
                Ifor = get_sequence_of_biases(unit_test_data, ps, "IFVF")
            except KeyError:
                log.warning(f"IFVF does not exist for {pol_name} {ps}")
                self.conn.log(
                    message=f"IFVF does not exist for {pol_name} {ps} in unit-level tests. "
                    "Using a synthetic curve instead"
                )
                Ifor = get_sequence_of_biases(None, ps, "IFVF")

            Ifor *= 1e6  # Convert from A to µA

            self.conn.log(
                message=f"Acquiring PH/SW forward curve for {pol_name}, {ps} Vpin{pin}"
            )

            with StripTag(
                conn=self.command_emitter,
                name=f"phsw_proc{proc_number}_fcurve_{pol_name}_{ps}_ipin{pin}",
            ):

                for i in Ifor:
                    adu = calibr.physical_units_to_adu(
                        pol_name, hk="iphsw", component=pin, value=i
                    )
                    self.conn.set_phsw_bias(
                        pol_name, phsw_index=pin, vpin_adu=None, ipin_adu=adu
                    )
                    self.conn.set_hk_scan(cur_board)
                    self.conn.log(message=f"Set I={i:.1f} µA = {adu} ADU")
                    wait_with_tag(
                        conn=self.command_emitter,
                        seconds=5,
                        name=f"phsw_proc{proc_number}_set_i_{pol_name}_{ps}_vpin{pin}",
                    )

    def _restore_phsw_state(self, pol_name: str, proc_number: int):
        self.conn.log(message=f"set phsw for {pol_name} to nominal switching")
        # Set default bias
        with StripTag(
            conn=self.command_emitter,
            name=f"phsw_proc{proc_number}_set_default_{pol_name}",
        ):
            for pin_idx in range(4):
                self.conn.set_phsw_status(
                    polarimeter=pol_name,
                    phsw_index=pin_idx,
                    status=PhswPinMode.NOMINAL_SWITCHING,
                )

    # Procedure 1
    def run_proc1(self):
        calibr = CalibrationTables()
        turnon_proc = TurnOnOffProcedure(
            waittime_s=1.0,
            turnon=True,
            stable_acquisition_time_s=600,
            bias_file_name=self.bias_file_name,
        )
        turnoff_proc = TurnOnOffProcedure(
            waittime_s=1.0,
            turnon=False,
            bias_file_name=self.bias_file_name,
        )
        for cur_board, pol_idx, pol_name in polarimeter_iterator(args.board):
            # turnon pol
            with StripTag(
                conn=self.command_emitter, name=f"phsw_proc1_turnon_pol_{pol_name}"
            ):
                turnon_proc.set_board_horn_polarimeter(
                    new_board=cur_board,
                    new_horn=pol_name,
                    new_pol=None,
                )
                turnon_proc.run()

                self.command_emitter.command_list += turnon_proc.get_command_list()
                turnon_proc.clear_command_list()

            self._stable_acquisition(pol_name, "1111", proc_number=1)

            # cuves

            test_num, unit_test_data = load_unit_level_test(
                self.pol_unittest_associations,
                pol_name,
                no_unit_level_tests=self.no_unit_level_tests,
            )

            if self.no_unit_level_tests:
                self.conn.log(
                    f"The ph/sw test #1 for polarimeter {pol_name} is *not* based on unit-level tests"
                )
            else:
                assert unit_test_data is not None

                self.conn.log(
                    f"The ph/sw test #1 for polarimeter {pol_name} is based on unit test #{test_num}"
                )

            if self.reverse_test:
                self._reverse(
                    calibr, cur_board, pol_name, unit_test_data, proc_number=1
                )

            if self.forward_test:
                self._forward(
                    calibr, cur_board, pol_name, unit_test_data, proc_number=1
                )

            self._restore_phsw_state(pol_name, proc_number=1)

            # turnoff pol
            with StripTag(
                conn=self.command_emitter, name=f"phsw_proc1_turnoff_pol_{pol_name}"
            ):
                turnoff_proc.set_board_horn_polarimeter(
                    new_board=cur_board,
                    new_horn=pol_name,
                    new_pol=None,
                )
                turnoff_proc.run()
                self.command_emitter.command_list += turnoff_proc.get_command_list()
                turnoff_proc.clear_command_list()

    # Procedure 2
    def run_proc2(self):
        calibr = CalibrationTables()

        if self.turn_on:
            turnon_proc = TurnOnOffProcedure(
                waittime_s=1.0,
                turnon=True,
                bias_file_name=self.bias_file_name,
            )
            with StripTag(conn=self.command_emitter, name="phsw_proc2_turnon_pol"):
                for cur_board, pol_idx, pol_name in polarimeter_iterator(args.board):

                    # turnon pol
                    turnon_proc.set_board_horn_polarimeter(
                        new_board=cur_board,
                        new_horn=pol_name,
                        new_pol=None,
                    )
                    turnon_proc.run()
                    self.command_emitter.command_list += turnon_proc.get_command_list()
                    turnon_proc.clear_command_list()

                self.conn.wait(seconds=self.pre_acquisition_time_s)

        for cur_board, pol_idx, pol_name in polarimeter_iterator(args.board):
            self._stable_acquisition(pol_name, "1111", proc_number=2)

            wait_with_tag(
                conn=self.command_emitter,
                seconds=self.pre_acquisition_time_s,
                name=f"acquisition_unsw0101_pol{pol_name}",
            )

            # curves
            test_num, unit_test_data = load_unit_level_test(
                self.pol_unittest_associations,
                pol_name,
                no_unit_level_tests=self.no_unit_level_tests,
            )

            if self.no_unit_level_tests:
                self.conn.log(
                    f"The ph/sw test #2 for polarimeter {pol_name} is *not* based on unit-level tests"
                )
            else:
                assert unit_test_data is not None

                self.conn.log(
                    f"The ph/sw test #2 for polarimeter {pol_name} is based on unit test #{test_num}"
                )

            if self.reverse_test:
                self._reverse(
                    calibr, cur_board, pol_name, unit_test_data, proc_number=2
                )

            if self.forward_test:
                self._forward(
                    calibr, cur_board, pol_name, unit_test_data, proc_number=2
                )

            self._restore_phsw_state(pol_name, proc_number=1)


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
        default=None,
        dest="pre_acquisition_time_s",
        type=float,
        help=f"""Before starting the test, the procedure acquires data
        in stable conditions for some time. With this switch you can
        either change the duration of the acquisition (the default is
        {DEFAULT_PRE_ACQUISITION1_TIME_S} s for procedure 1, and
        {DEFAULT_PRE_ACQUISITION2_TIME_S} s for procedure 2), or
        switch it off entirely by passing 0.""",
    )

    parser.add_argument(
        "--turn-on",
        default=False,
        action="store_true",
        help="""Include at the beginning of the procedure the sequence
        that turns on the polarimeters. (Valid only for procedure #2.)""",
    )

    parser.add_argument(
        "--no-unit-level-tests",
        "-n",
        default=False,
        action="store_true",
        help="""Do not download unit-level tests to determine the sequence of
        currents and voltages, but use a synthetic, pre-defined sequence of
        voltages and currents.""",
    )

    parser.add_argument(
        "bias_file_name",
        type=str,
        help="Excel file containing the turnon biases (either warm or cryo)",
    )

    parser.add_argument(
        "procedure",
        type=int,
        help="Procedure to generate, either 1 or 2",
    )

    parser.add_argument(
        "board",
        type=str,
        nargs="?",
        default=STRIP_BOARD_NAMES,
        help="turn on one or more boards",
    )

    args = parser.parse_args()

    if args.pre_acquisition_time_s is None:
        if args.procedure == 1:
            args.pre_acquisition_time_s = DEFAULT_PRE_ACQUISITION1_TIME_S
        elif args.procedure == 2:
            args.pre_acquisition_time_s = DEFAULT_PRE_ACQUISITION2_TIME_S

    # For the moment we do not provide a command-line switch for this
    args.__setattr__("forward_test", True)

    log.basicConfig(
        level=log.INFO,
        format="%(message)s",
        handlers=[RichHandler()],
    )

    proc = PSProcedure(
        pre_acquisition_time_s=args.pre_acquisition_time_s,
        reverse_test=args.reverse_test,
        forward_test=args.forward_test,
        turn_on=args.turn_on,
        no_unit_level_tests=args.no_unit_level_tests,
        bias_file_name=args.bias_file_name,
    )

    if args.procedure == 1:
        proc.run_proc1()
    elif args.procedure == 2:
        proc.run_proc2()
    else:
        print(f"Invalid procedure number {args.procedure}, it must be either 1 or 2.")
        sys.exit(1)

    if args.output_filename:
        log.info(f'Writing the procedure to file "{args.output_filename}"')

    proc.output_json(args.output_filename)
