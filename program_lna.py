#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from typing import Dict, List, Union

import numpy as np
from striptease.procedures import StripProcedure

from striptease.utilities import STRIP_BOARD_NAMES, get_polarimeter_board, \
                                 normalize_polarimeter_name, polarimeter_iterator
from tuning import scanners
from tuning.scanners import Scanner1D, Scanner2D
from tuning.procedures import LNAPretuningProcedure, OffsetTuningProcedure, StripState

DEFAULT_TEST_NAME = "PRETUNE"
DEFAULT_BIAS_FILENAME = "data/default_biases_warm.xlsx"
DEFAULT_TUNING_FILENAME = "data/pretuning.xlsx"
DEFAULT_ACQUISITION_TIME_S = 5
DEFAULT_WAIT_TIME_S = 1
DEFAULT_POLARIMETERS = [polarimeter for _, _, polarimeter in polarimeter_iterator()]

class LNAOffsetProcedure(StripProcedure):
    def __init__(self, test_name: str, scanners: Dict[str, Scanner2D],
                 test_polarimeters: List[str] = [polarimeter for _, _, polarimeter in polarimeter_iterator()],
                 turnon_polarimeters: Union[List[str], None] = None,
                 bias_file_name: str = "data/default_biases_warm.xlsx",
                 stable_acquisition_time = DEFAULT_ACQUISITION_TIME_S,
                 turnon_acqisition_time = DEFAULT_WAIT_TIME_S,
                 turnon_wait_time = DEFAULT_WAIT_TIME_S,
                 message = "",
                 hk_scan_boards=STRIP_BOARD_NAMES,
                 phsw_status="77",
                 open_loop=False,
                 start_state=StripState.OFF,
                 end_state=StripState.ZERO_BIAS):
        super().__init__()
        self.lna_pretuning_procedure = LNAPretuningProcedure(
            start_state=start_state, end_state=StripState.ZERO_BIAS,
            test_name=test_name, test_polarimeters=test_polarimeters, turnon_polarimeters=turnon_polarimeters, bias_file_name=bias_file_name,
            stable_acquisition_time=stable_acquisition_time, turnon_acqisition_time=turnon_acqisition_time, turnon_wait_time=turnon_wait_time,
            message=message, hk_scan_boards=hk_scan_boards, open_loop=open_loop, scanners=scanners, phsw_status=phsw_status)
        self.lna_pretuning_procedure.conn = self.conn
        self.offset_tuning_procedure = OffsetTuningProcedure(
            start_state=StripState.ZERO_BIAS, end_state=end_state,
            test_name=test_name, test_polarimeters=test_polarimeters, turnon_polarimeters=turnon_polarimeters, bias_file_name=bias_file_name,
            stable_acquisition_time=stable_acquisition_time, turnon_acqisition_time=turnon_acqisition_time, turnon_wait_time=turnon_wait_time,
            message="", hk_scan_boards=hk_scan_boards, open_loop=open_loop, scanners=scanners)
        self.offset_tuning_procedure.conn = self.conn

    def run(self):
        self.lna_pretuning_procedure.run()
        self.offset_tuning_procedure.run()

def read_cell(excel_file, polarimeter: str, test: str, mode: str) -> Union[Scanner2D, Scanner1D]:
    from ast import literal_eval

    row = excel_file[polarimeter]
    if test != "Offset":
        test += mode
    scanner_class = getattr(scanners, row[(test, "Scanner")])
    arguments_str = row[(test, "Arguments")]
    arguments = list(map(literal_eval, arguments_str.split(";")))
    for i in range(len(arguments)):
        if isinstance(arguments[i], list):
            arguments[i] = np.asarray(arguments[i], dtype=float)
    if test == "Offset":
        return scanner_class(*arguments, label="offset")
    else:
        return scanner_class(*arguments, x_label="idrain", y_label="offset")

def read_excel(filename: str, dummy_polarimeter: bool = False, open_loop: bool = False) -> Dict[str, Dict[str, Scanner2D]]:
    import pandas as pd

    excel_file = pd.read_excel(filename, header=(0, 1), index_col=0).to_dict(orient="index")
    scanners = {}
    if open_loop:
        mode = " open loop"
    else:
        mode = " closed loop"
    for polarimeter in set(excel_file) - {"DUMMY"}: # Iterate over all polarimeters except the DUMMY one
        scanners[polarimeter] = {}
        for test in "HA1", "HA2", "HA3", "HB1", "HB2", "HB3", "Offset":
            if dummy_polarimeter:
                scanners[polarimeter][test] = read_cell(excel_file, "DUMMY", test, mode)
            else:
                scanners[polarimeter][test] = read_cell(excel_file, polarimeter, test, mode)
    return scanners

def parse_polarimeters(polarimeters: List[str]) -> List[str]:
    """Parse a list of polarimeters, boards, "Q" (all Q polarimeters), "W" (all W polarimeters)
    and (e.g.) "OQ", "OW" (all Q or W polarimeters in board O), and return a list of polarimeter names."""
    if polarimeters == []:
        return []
    if polarimeters[0] == "all":
        return DEFAULT_POLARIMETERS

    parsed_polarimeters = []
    for item in polarimeters:
        try:
            if normalize_polarimeter_name(item) in map(normalize_polarimeter_name, DEFAULT_POLARIMETERS):
                parsed_polarimeters.append(item)
                continue
        except KeyError:
            pass
        if item in STRIP_BOARD_NAMES:
            parsed_polarimeters += [polarimeter
                for _, _, polarimeter in polarimeter_iterator(boards=[item])]
        elif item == "Q":
            parsed_polarimeters += [polarimeter
                for _, _, polarimeter in polarimeter_iterator(include_w_band=False)]
        elif item == "W":
            parsed_polarimeters += [polarimeter
                for _, _, polarimeter in polarimeter_iterator(include_q_band=False)]
        elif item[1] == "Q":
            parsed_polarimeters += [polarimeter
                for _, _, polarimeter in polarimeter_iterator(boards=[item[0]], include_w_band=False)]
        elif item[1] == "W":
            parsed_polarimeters += [polarimeter
                for _, _, polarimeter in polarimeter_iterator(boards=[item[0]], include_q_band=False)]
    return list(dict.fromkeys(parsed_polarimeters)) # Remove duplicate polarimeters

def parse_state(state: str) -> StripState:
        assert ["on", "off", "zero-bias", "default"].count(state) > 0
        if state == "on":
            return StripState.ON
        elif state == "off":
            return StripState.OFF
        elif state == "zero-bias":
            return StripState.ZERO_BIAS
        elif state == "default":
            return StripState.DEFAULT

if __name__ == "__main__":
    from argparse import ArgumentParser, RawDescriptionHelpFormatter
    from datetime import datetime
    import logging as log
    import subprocess
    import sys

    parser = ArgumentParser(
        description="Produce a command sequence to test the LNAs on one or more polarimeters",
        formatter_class=RawDescriptionHelpFormatter,
        epilog="""

Usage examples:

    # Test all polarimeters using the biases in data/pretuning.xlsx and
    # data/default_biases_warm.xlsx, naming the test "TUNE1"
    python3 program_lna.py --test-name TUNE1

    # Turn on and test polarimeters O1 and O2, using default biases from
    # file biases.xlsx
    python3 program_lna.py \\
        --test-polarimeters O1 O2 \\
        --bias-file-name biases.xlsx

    # Test polarimeters O1 and O2 turning on also polarimeters O3 and O4,
    # using the scanning strategy in file scan.xlsx and writing the output
    # on file proc.json
    python3 program_lna.py \\
        --test-polarimeters O1 O2 \\
        --turnon-polarimeters O3 O4 \\
        --tuning-file scan.xlsx \\
        --output proc.json

    # Test polarimeters O1 and O2 turning on all polarimeters,
    # using the scanning strategy defined for the DUMMY polarimeter.
    python3 program_lna.py \\
        --test-polarimeters O1 O2 \\
        --turnon-polarimeters all \\
        --bias-from-dummy-polarimeter
""")
    parser.add_argument("--output", "-o",
        metavar="FILENAME",
        type=str,
        dest="output_filename",
        default="",
        help="Name of the file where to write the output (in JSON format). "
        "If not provided, the output will be sent to stdout.",
    )
    parser.add_argument("--test-polarimeters",
        metavar="POLARIMETER",
        type=str,
        nargs="+",
        default=DEFAULT_POLARIMETERS,
        help="Name of the polarimeters/module to test. Valid names "
            'are "G4", "W3", "O" (meaning all polarimeters in board O), "OQ" (meaning all Q polarimeters '
            'in board Q), "OW" (meaning the W polarimeter on board O), "Q" (meaning all Q polarimeters) or "W" '
            '(meaning all W polarimeters). Can be "all" (which is the default).',
    )
    parser.add_argument("--turnon-polarimeters",
        metavar="POLARIMETER",
        type=str,
        nargs="+",
        default=[],
        help="Name of the polarimeters/module to turn on. Valid names "
            'are the same of test-polarimeters. Can be "all", and by default it is equal '
            "to test-polarimeters.",
    )
    parser.add_argument("--test-name",
        metavar="STRING",
        type=str,
        dest="test_name",
        default=DEFAULT_TEST_NAME,
        help="The name of the test, to be put at the beginning of each tag. "
            f'The default is "{DEFAULT_TEST_NAME}".'
    )
    parser.add_argument("--bias-file-name",
        metavar="FILENAME",
        type=str,
        dest="bias_file_name",
        default=DEFAULT_BIAS_FILENAME,
        help="Excel file containing the biases to be used when turning on the polarimeters. "
            f'The default is "{DEFAULT_BIAS_FILENAME}"'
    )
    parser.add_argument("--hk-scan-boards",
        metavar="BOARD",
        dest="hk_scan_boards",
        default=["test"],
        type=str,
        nargs="+",
        help="The list of boards to scan housekeeping on before stable acquisition. "
             'Can be "test" for boards under testing (the default), '
             '"turnon" for turned-on ones, "all", "none" or a list of boards.'
    )
    parser.add_argument("--phsw-status",
        type=str,
        dest="phsw_status",
        default="77",
        help="Status of turned-on phase switch pins. Can be 77 (the default), 56 or 65."
    )
    parser.add_argument("--stable-acquisition-time",
        metavar="SECONDS",
        default=DEFAULT_ACQUISITION_TIME_S,
        type=int,
        dest="stable_acquisition_time",
        help="Number of seconds to measure after the polarimeter biases have been "
            f"set up (default: {DEFAULT_ACQUISITION_TIME_S}s)"
    )
    parser.add_argument("--turnon-acquisition-time",
        metavar="SECONDS",
        default=DEFAULT_WAIT_TIME_S,
        type=int,
        dest="turnon_acquisition_time",
        help="Number of seconds to measure after the polarimeters have been "
            f"turned on (default: {DEFAULT_WAIT_TIME_S}s)"
    )
    parser.add_argument("--turnon-wait-time",
        metavar="SECONDS",
        default=DEFAULT_WAIT_TIME_S,
        type=int,
        dest="turnon_wait_time",
        help="Number of seconds to wait between turnon commands "
            f"set up (default: {DEFAULT_WAIT_TIME_S}s)"
    )
    parser.add_argument("--tuning-file",
        metavar="FILENAME",
        type=str,
        dest="tuning_filename",
        default=DEFAULT_TUNING_FILENAME,
        help="Run the test using the scanners contained in an Excel file. "
            f'The default is "{DEFAULT_TUNING_FILENAME}".'
    )
    parser.add_argument("--bias-from-dummy-polarimeter",
        action="store_true",
        dest="dummy_polarimeter",
        help="Test all polarimeters using the scanning strategy of the DUMMY one."
    )
    parser.add_argument("--start-state",
        metavar="STATE",
        type=str,
        dest="start_state",
        default="off",
        help='The state Strip is in before the procedure starts (can be "on" if it is turned on with any bias, ' \
              '"off" if it is turned off, "zero-bias" if it is on with id, vg, vd, phsw and offset to zero, ' \
              '"default" if it is turned on with all biases to the default values (as per bias-file-name). The default is "off".'
    )
    parser.add_argument("--end-state",
        metavar="STATE",
        type=str,
        dest="end_state",
        default="zero-bias",
        help='The state to leave Strip in after the procedure ends (can be "on" meaning turned on with any bias, ' \
              '"off" meaning turned off, "zero-bias" meaning turned on with id, vg, vd, phsw and offset to zero, ' \
              '"default" meaning turned on with all biases to the default values (as per bias-file-name). ' \
              'The default is "zero-bias".'  
    )
    parser.add_argument("--open-loop",
        action="store_true",
        dest="open_loop",
        help="Run open loop test (instead of the default closed loop)."
    )

    args = parser.parse_args()
    log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    assert(args.phsw_status == "77" or args.phsw_status == "56" or args.phsw_status == "65")

    test_scanners = read_excel(args.tuning_filename, args.dummy_polarimeter, args.open_loop)

    args.test_polarimeters = parse_polarimeters(args.test_polarimeters)
    args.turnon_polarimeters = parse_polarimeters(args.turnon_polarimeters)
    args.turnon_polarimeters = list(dict.fromkeys(args.turnon_polarimeters + args.test_polarimeters)) # Make sure that all tested polarimeters are also turned on

    if args.hk_scan_boards == [] or args.hk_scan_boards[0] == "none":
        args.hk_scan_boards = []
    elif args.hk_scan_boards[0] == "all":
        args.hk_scan_boards = STRIP_BOARD_NAMES
    elif args.hk_scan_boards[0] == "test":
        args.hk_scan_boards = list(set(map(get_polarimeter_board, args.test_polarimeters)))
    elif args.hk_scan_boards[0] == "turnon":
        args.hk_scan_boards = list(set(map(get_polarimeter_board, args.turnon_polarimeters)))

 
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.rstrip("\n")
    status = subprocess.run(["git", "status", "--untracked-files=no", "--porcelain"], capture_output=True, text=True).stdout
    if status == "":
        status = "No change.\n"
    else:
        status = "\n" + status
        status = '\t'.join(status.splitlines(True))

    message = f"Here begins the {args.test_name} procedure to test LNA biases, " \
              f"generated on {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}.\n" \
              f"Argv: {sys.argv}.\n" \
              f"Git commit: {commit}.\n" \
              f"Git status: {status}" \
              f"Tested polarimeters: {args.test_polarimeters}.\n"\
              f"Turned-on polarimeters: {args.turnon_polarimeters}.\n"\
              f"Housekeeping scanned on boards: {args.hk_scan_boards}.\n"\
              f"Bias file: {args.bias_file_name}.\n"\
              f"Tuning file: {args.tuning_filename}.\n"\
              f"Dummy polarimeter: {args.dummy_polarimeter}.\n"\
              f"Stable acquisition time: {args.stable_acquisition_time}s.\n"\
              f"Turnon wait time: {args.turnon_wait_time}s.\n"\
              f"Turnon acquisition time: {args.turnon_acquisition_time}s.\n"\
              f"Start state: {args.start_state}.\n"\
              f"End state: {args.end_state}."\

    args.start_state = parse_state(args.start_state)
    args.end_state = parse_state(args.end_state)

    proc = LNAOffsetProcedure(test_name=args.test_name, scanners=test_scanners, test_polarimeters=args.test_polarimeters,
        turnon_polarimeters=args.turnon_polarimeters, bias_file_name=args.bias_file_name,
        stable_acquisition_time=args.stable_acquisition_time, turnon_acqisition_time=args.turnon_acquisition_time,
        turnon_wait_time=args.turnon_wait_time, message=message, hk_scan_boards=args.hk_scan_boards, phsw_status=args.phsw_status,
        open_loop=args.open_loop, start_state=args.start_state, end_state=args.end_state)
    proc.run()
    proc.output_json(args.output_filename)