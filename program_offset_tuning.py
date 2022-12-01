#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from typing import List

from striptease.utilities import STRIP_BOARD_NAMES, get_polarimeter_board, \
                                 normalize_polarimeter_name, polarimeter_iterator

DEFAULT_TEST_NAME = "DET_OFFS_TUNE"
DEFAULT_BIAS_FILENAME = "data/default_biases_warm.xlsx"
DEFAULT_TUNING_FILENAME = "data/pretuning.xlsx"
DEFAULT_ACQUISITION_TIME_S = 5
DEFAULT_WAIT_TIME_S = 1
DEFAULT_POLARIMETERS = [polarimeter for _, _, polarimeter in polarimeter_iterator()]

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

if __name__ == "__main__":
    from argparse import ArgumentParser, RawDescriptionHelpFormatter
    from datetime import datetime
    import logging as log
    import subprocess
    import sys

    from tuning.procedures import OffsetTuningProcedure, parse_state
    from tuning.scanners import read_excel

    parser = ArgumentParser(
        description="Produce a command sequence to test the detector offsets on one or more polarimeters",
        formatter_class=RawDescriptionHelpFormatter,
        epilog="""

Usage examples:

    # Test all polarimeters using the biases in data/pretuning.xlsx and
    # data/default_biases_warm.xlsx, naming the test "TUNE1"
    python3 program_offset_tuning.py --test-name TUNE1

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

    message = f"Here begins the {args.test_name} procedure to test detector offsets, " \
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

    proc = OffsetTuningProcedure(test_name=args.test_name, scanners=test_scanners, test_polarimeters=args.test_polarimeters,
        turnon_polarimeters=args.turnon_polarimeters, bias_file_name=args.bias_file_name,
        stable_acquisition_time=args.stable_acquisition_time, turnon_acqisition_time=args.turnon_acquisition_time,
        turnon_wait_time=args.turnon_wait_time, message=message, hk_scan_boards=args.hk_scan_boards,
        open_loop=args.open_loop, start_state=args.start_state, end_state=args.end_state)
    proc.run()
    proc.output_json(args.output_filename)