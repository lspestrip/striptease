#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import logging as log
from pathlib import Path
import requests
from typing import Dict, List, Union
from urllib.parse import urljoin

import numpy as np

from calibration import CalibrationTables
from striptease import (
    STRIP_BOARD_NAMES,
    BOARD_TO_W_BAND_POL,
    StripTag,
    normalize_polarimeter_name,
)
from striptease import InstrumentBiases, BiasConfiguration, DataFile
from striptease.procedures import StripProcedure
from program_turnon import TurnOnOffProcedure

# Used to look for tags in HDF5 files
DEFAULT_TAG_TEMPLATE = "OPEN_LOOP_TEST_ACQUISITION_{polarimeter}"


def instrument_biases_to_dict(
    polarimeters: List[str], biases: InstrumentBiases
) -> Dict[str, BiasConfiguration]:
    biases_per_pol = {}
    for cur_pol in polarimeters:
        biases_per_pol[cur_pol] = biases.get_biases(module_name=cur_pol)

    return biases_per_pol


def retrieve_biases_from_hdf5(
    polarimeters: List[str],
    test_name: str,
    filename: Union[str, Path],
    tag_template: str,
    calibr: CalibrationTables,
) -> Dict[str, BiasConfiguration]:

    log.info(f"Retrieving biases from file {filename}")
    result = {}
    with DataFile(filename) as inpf:
        for cur_pol in polarimeters:
            tagname = tag_template.format(test_name=test_name, polarimeter=cur_pol)
            tag = [x for x in inpf.tags if x.name == tagname]
            if len(tag) == 0:
                raise RuntimeError(f'no "{tagname}" tag found in file {filename}')
            if len(tag) > 1:
                raise RuntimeError(
                    f'{len(tag)} tags with name "{tagname}" found in file {filename}'
                )

            tag = tag[0]
            cur_pol_fullname = f"POL_{cur_pol}"
            result[cur_pol] = inpf.get_average_biases(
                polarimeter=cur_pol, time_range=(), calibration_tables=calibr
            )

    return result


def retrieve_biases_from_url(
    polarimeter_name: str, url: str,
) -> Dict[str, BiasConfiguration]:

    if (not url.endswith("json")) and not (url.endswith("json/")):
        url = urljoin(url, "json")

    log.info(f"Retrieving biases from URL {url}")

    response = requests.get(url)
    biases = response.json()["hemt_biases"]
    biases_per_pol = {
        polarimeter_name: BiasConfiguration(
            vd0=biases["drain_voltage_ha1_V"] * 1e3,
            vd1=biases["drain_voltage_hb1_V"] * 1e3,
            vd2=biases["drain_voltage_ha2_V"] * 1e3,
            vd3=biases["drain_voltage_hb2_V"] * 1e3,
            vd4=biases["drain_voltage_ha3_V"] * 1e3,
            vd5=biases["drain_voltage_hb3_V"] * 1e3,
            vg0=biases["gate_voltage_ha1_mV"],
            vg1=biases["gate_voltage_hb1_mV"],
            vg2=biases["gate_voltage_ha2_mV"],
            vg3=biases["gate_voltage_hb2_mV"],
            vg4=biases["gate_voltage_ha3_mV"],
            vg5=biases["gate_voltage_hb3_mV"],
            vg4a=0.0,
            vg5a=0.0,
            vpin0=None,
            vpin1=None,
            vpin2=None,
            vpin3=None,
            ipin0=None,
            ipin1=None,
            ipin2=None,
            ipin3=None,
            id0=biases["drain_current_ha1_mA"] * 1e3,
            id1=biases["drain_current_hb1_mA"] * 1e3,
            id2=biases["drain_current_ha2_mA"] * 1e3,
            id3=biases["drain_current_hb2_mA"] * 1e3,
            id4=biases["drain_current_ha3_mA"] * 1e3,
            id5=biases["drain_current_hb3_mA"] * 1e3,
        ),
    }
    return biases_per_pol


class OpenClosedLoopProcedure(StripProcedure):
    def __init__(self, args):
        super(OpenClosedLoopProcedure, self).__init__()
        self.args = args
        self.calibr = CalibrationTables()

        # This is used when the user specifies the switch --print-biases
        self.used_biases = []

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

    def _run_test(
        self,
        test_name,
        polarimeters,
        biases_per_pol: Dict[str, BiasConfiguration],
        sequence,
    ):
        # This method is used internally to implement both the
        # open-loop and closed-loop tests

        for cur_pol in polarimeters:
            cur_biases = biases_per_pol[cur_pol]._asdict()
            self.used_biases.append(
                {
                    "polarimeter": cur_pol,
                    "test_name": test_name,
                    "calibrated_biases": {
                        key: val for (key, val) in cur_biases.items() if val
                    },
                }
            )

            bias_repr = ", ".join(
                [f"{key}={val:.1f}" for (key, val) in cur_biases.items() if val]
            )
            with StripTag(
                conn=self.command_emitter,
                name=f"{test_name}_TEST_SETUP_{cur_pol}",
                comment=f"(calibrated) biases are: {bias_repr}",
            ):
                for component, param, key in sequence:
                    params = {
                        "polarimeter": cur_pol,
                        "lna": component,
                        "value_adu": self.calibr.physical_units_to_adu(
                            polarimeter=cur_pol,
                            hk=key,
                            component=component,
                            value=cur_biases[param],
                        ),
                    }

                    if key == "vdrain":
                        self.conn.set_vd(**params)
                    elif key == "idrain":
                        self.conn.set_id(**params)
                    elif key == "vgate":
                        self.conn.set_vg(**params)

            with StripTag(
                conn=self.command_emitter,
                name=f"{test_name}_TEST_ACQUISITION_{cur_pol}",
                comment=f"Stable acquisition",
            ):
                self.conn.wait(seconds=80)

    def run_open_loop_test(
        self, polarimeters, biases_per_pol: Dict[str, BiasConfiguration]
    ):
        self._run_test(
            test_name="OPEN_LOOP",
            polarimeters=polarimeters,
            biases_per_pol=biases_per_pol,
            sequence=[
                ("H0", "vd0", "vdrain"),
                ("H1", "vd1", "vdrain"),
                ("H2", "vd2", "vdrain"),
                ("H3", "vd3", "vdrain"),
                ("H4", "vd4", "vdrain"),
                ("H5", "vd5", "vdrain"),
                ("H0", "vg0", "vgate"),
                ("H1", "vg1", "vgate"),
                ("H2", "vg2", "vgate"),
                ("H3", "vg3", "vgate"),
                ("H4", "vg4", "vgate"),
                ("H4A", "vg4a", "vgate"),
                ("H5A", "vg5a", "vgate"),
            ],
        )

    def run_closed_loop_test(
        self, polarimeters, biases_per_pol: Dict[str, BiasConfiguration]
    ):
        self._run_test(
            test_name="CLOSED_LOOP",
            polarimeters=polarimeters,
            biases_per_pol=biases_per_pol,
            sequence=[
                ("H0", "id0", "idrain"),
                ("H1", "id1", "idrain"),
                ("H2", "id2", "idrain"),
                ("H3", "id3", "idrain"),
                ("H4", "id4", "idrain"),
                ("H5", "id5", "idrain"),
                ("H0", "vg0", "vgate"),
                ("H1", "vg1", "vgate"),
                ("H2", "vg2", "vgate"),
                ("H3", "vg3", "vgate"),
                ("H4", "vg4", "vgate"),
                ("H4A", "vg4a", "vgate"),
                ("H5A", "vg5a", "vgate"),
            ],
        )

    def read_biases_per_pol(self, filename, test_name):
        if str(filename).startswith("http"):
            assert len(self.args.polarimeters) == 1
            biases_per_pol = retrieve_biases_from_url(
                polarimeter_name=self.args.polarimeters[0], url=str(filename),
            )
        else:
            if filename.suffix == ".h5":
                biases_per_pol = retrieve_biases_from_hdf5(
                    polarimeters=self.args.polarimeters,
                    test_name=test_name,
                    filename=filename,
                    tag_template=self.args.tag_template,
                    calibr=self.calibr,
                )
            else:
                biases_per_pol = instrument_biases_to_dict(
                    polarimeters=self.args.polarimeters,
                    biases=InstrumentBiases(filename),
                )

        return biases_per_pol

    def run(self):
        calibr = CalibrationTables()

        # Open loop test
        if self.args.open_loop_filename:
            biases_per_pol = self.read_biases_per_pol(
                self.args.open_loop_filename, "OPEN_LOOP"
            )
            self.run_open_loop_test(self.args.polarimeters, biases_per_pol)

        # Closed loop test
        if self.args.closed_loop_filename:
            biases_per_pol = self.read_biases_per_pol(
                self.args.open_loop_filename, "CLOSED_LOOP"
            )
            self.run_closed_loop_test(self.args.polarimeters, biases)

    def output_biases(self):
        print(json.dumps(self.used_biases, indent=4))


if __name__ == "__main__":
    from argparse import ArgumentParser, RawDescriptionHelpFormatter

    parser = ArgumentParser(
        description="Produce a command sequence to turn on one or more polarimeters",
        formatter_class=RawDescriptionHelpFormatter,
        epilog="""

Usage examples:

    # Test the open-loop mode for polarimeter Y6, reading the biases
    # from an Excel file. For an example, see 
    # "{data_file_path}"
    python3 program_open_closed_loop.py \\
        --open-loop=biases.xlsx \\
        Y6 > my_test.json

    # Read the biases for a closed-loop test from the Unit Test database,
    # containing the results of the tests done in Bicocca
    python3 program_open_closed_loop.py \\
        --open-loop=https://striptest.fisica.unimi.it/unittests/tests/500/ \\
        B6 > my_test.json

    # Read the biases from a HDF5 file, considering the average value of
    # the housekeeping parameters only in the tags corresponding to the
    # polarimeter. (By default, it searches for tags referring to open-loop
    # tests, as this is the most common situation.)
    python3 program_open_closed_loop.py --closed-loop=./open_loop_test.h5 \\
        Y0 G1 > my_test.json

    # The same as above, but do not assume that the names of the tags are
    # those used for open-loop tests
    python3 program_open_closed_loop.py \\
        --closed-loop=./closed_loop_test.h5 \\
        --tag-template="CLOSED_LOOP_TEST_ACQUISITION_{{polarimeter}}" \\
        Y0 G1 > my_test.json

    # The --print-biases switch is handy if you want to check what are
    # the biases that are going to be used for a test
    python3 program_open_closed_loop.py \\
        --open-loop=https://striptest.fisica.unimi.it/unittests/tests/500/ \\
        --print-biases \\
        B6
""".format(
            data_file_path=(
                Path(__file__).parent / "data" / "default_biases_warm.xlsx"
            ).absolute(),
        ),
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
        "polarimeters",
        metavar="POLARIMETER",
        type=str,
        nargs="+",
        help="Name of the polarimeters/module to turn on. Valid names "
        'are "G4", "W3", etc.',
    )
    parser.add_argument(
        "--tag-template",
        metavar="STRING",
        type=str,
        dest="tag_template",
        default=DEFAULT_TAG_TEMPLATE,
        help=f"Template string to be used when looking for tags in HDF5 files "
        "(default: {DEFAULT_TAG_TEMPLATE}). You can use the placeholders "
        "'{test_name}' and '{polarimeter}' instead of the strings "
        "'OPEN_LOOP'/'CLOSED_LOOP' and the polarimeter name (uppercase).",
    )
    parser.add_argument(
        "--open-loop",
        metavar="FILENAME",
        type=str,
        dest="open_loop_filename",
        default=None,
        help="Run the test in open-loop mode. You must specify a Excel/CSV file "
        "containing the biases to be used for the voltages.",
    )
    parser.add_argument(
        "--closed-loop",
        metavar="FILENAME",
        type=str,
        dest="closed_loop_filename",
        default=None,
        help="Run the test using a closed-loop mode. You can either specify a "
        "Excel/HDF5 file containing the biases to be used for the currents, or a URL "
        "to a unit test file. For HDF5 files, you might want to use --tag-template "
        "to specify the kind of tag you are looking for (the default is ok for "
        "HDF5 files produced by running this open/closed loop test script).",
    )
    parser.add_argument(
        "--print-biases",
        action="store_true",
        default=False,
        dest="print_biases",
        help="Instead of producing a JSON file containing the sequence of commands, "
        "write a JSON containing the calibrated values of the biases to be set "
        "during the test. This is always printed to 'stdout', regardless of the "
        "--output flag, and it's useful for debugging.",
    )

    args = parser.parse_args()

    if args.open_loop_filename and not args.open_loop_filename.startswith("http"):
        args.open_loop_filename = Path(args.open_loop_filename)

    if args.closed_loop_filename and not args.closed_loop_filename.startswith("http"):
        args.closed_loop_filename = Path(args.closed_loop_filename)

    log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    proc = OpenClosedLoopProcedure(args)
    proc.run()

    if args.print_biases:
        proc.output_biases()
    else:
        proc.output_json(args.output_filename)
