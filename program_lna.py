#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from abc import ABC, abstractmethod
from ast import literal_eval
from copy import copy
from datetime import datetime
import logging as log
from typing import Dict, List, Union

import numpy as np
import pandas as pd

from calibration import CalibrationTables
from striptease import StripTag
from striptease.procedures import StripProcedure
from striptease.stripconn import wait_with_tag
from striptease.utilities import CLOSED_LOOP_MODE, STRIP_BOARD_NAMES, PhswPinMode, get_polarimeter_board, polarimeter_iterator
from turnon import SetupBoard, TurnOnOffProcedure

DEFAULT_TEST_NAME = "PRETUNE"
DEFAULT_BIAS_FILENAME = "data/default_biases_warm.xlsx"
DEFAULT_TUNING_FILENAME = "data/pretuning.xlsx"
DEFAULT_ACQUISITION_TIME_S = 5
DEFAULT_WAIT_TIME_S = 1
DEFAULT_POLARIMETERS = [polarimeter for _, _, polarimeter in polarimeter_iterator()]

class Scanner2D(ABC):
    """Abstract base class representing a scanning strategy to explore a 2D plane.
    
    Args:
    -`x_label`/`y_label` (`str`): the names of the x, y variables, to be used in the plot."""

    def __init__(self, x_label: str = "x", y_label: str = "y"):
        self.x_label = x_label
        self.y_label = y_label

    @abstractmethod
    def next(self) -> bool:
        """Return True if there is still a parameter pair to be tested, and set self.x and self.y accordingly.
        Return False otherwise."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset the scanner by setting `self.x` and `self.y` to the initial values."""
        ...

    def plot(self):
        """Show a plot of the scanning strategy."""
        from matplotlib import pyplot as plt
        import numpy as np
        res = []
        while self.next() == True:
            res.append((self.x, self.y))

        res = np.asarray(res)
        plt.plot(res[:, 0], res[:, 1], "-o")
        plt.xlabel(self.x_label)
        plt.ylabel(self.y_label)
        plt.show()
        self.reset()

class GridScanner(Scanner2D):
    """A scanner that explores parameters on a grid from down to up and from left to right

    Args:
    - `x_start`/`y_start` (`float | np.ndarray`): the starting parameters
    - `x_stop`/`y_stop` (`float | np.ndarray`): the parameters at which the grid ends
    - `x_nsteps`/`y_nsteps` (`int`): the number of steps
    - `x_label`/`y_label` (`str`): the names of the x, y variables, to be used in the plot."""
    def __init__(self, x_start: Union[float, np.ndarray], x_stop: Union[float, np.ndarray], x_nsteps: int,
                 y_start: Union[float, np.ndarray], y_stop: Union[float, np.ndarray], y_nsteps: int,
                 x_label: str = "x", y_label: str = "y"):
        super(GridScanner, self).__init__(x_label, y_label)
        self.x_start = x_start
        self.x_stop = x_stop
        self.x_nsteps = x_nsteps
        self.delta_x = (x_stop - x_start) / x_nsteps
        self.y_start = y_start
        self.y_stop = y_stop
        self.y_nsteps = y_nsteps
        self.delta_y = (y_stop - y_start) / y_nsteps

        self.x = copy(x_start)
        self.y = copy(y_start)

        self.first_call = True
        self.x_current_step = 0
        self.y_current_step = 0

    def next(self) -> bool:
        if self.first_call:
            self.first_call = False
            return True

        if self.y_current_step == self.y_nsteps: # Last row in the column
            if self.x_current_step == self.x_nsteps:   # Last column in the grid
                return False
            else:                                       # Not last column in the grid
                self.x += self.delta_x
                self.x_current_step += 1
                self.y = copy(self.y_start)
                self.y_current_step = 0
                return True
        else:                                           # Not last row in the column
            self.y += self.delta_y
            self.y_current_step += 1
            return True
 
    def reset(self) -> None:
        self.x = copy(self.x_start)
        self.y = copy(self.y_start)
        self.first_call = True

        self.x_current_step = 0
        self.y_current_step = 0

class RasterScanner(Scanner2D):
    """A scanner that explores parameters on a grid \"boustrophedically\",
    from down to up and viceversa alternating at every column.

    Args:
    - `x_start`/`y_start` (`float | np.ndarray`): the starting parameters
    - `x_stop`/`y_stop` (`float | np.ndarray`): the parameters at which the grid ends
    - `x_nsteps`/`y_nsteps` (`int`): the number of steps
    """

    def __init__(self, x_start: Union[float, np.ndarray], x_stop: Union[float, np.ndarray], x_nsteps: int,
                 y_start: Union[float, np.ndarray], y_stop: Union[float, np.ndarray], y_nsteps: int,
                 x_label: str = "x", y_label: str = "y"):
        super(RasterScanner, self).__init__(x_label, y_label)
        self.x_start = x_start
        self.x_stop = x_stop
        self.x_nsteps = x_nsteps
        self.delta_x = (x_stop - x_start) / x_nsteps
        self.y_start = y_start
        self.y_stop = y_stop
        self.y_nsteps = y_nsteps
        self.delta_y = (y_stop - y_start) / y_nsteps

        self.x = copy(x_start)
        self.y = copy(y_start)

        self.first_call = True
        self.x_current_step = 0
        self.y_current_step = 0
        self.y_direction = +1

    def next(self) -> bool:
        if self.first_call:
            self.first_call = False
            return True

        if self.y_current_step == self.y_nsteps: # Last row in the column
            if self.x_current_step == self.x_nsteps:   # Last column in the grid
                return False
            else:                                       # Not last column in the grid
                self.x += self.delta_x
                self.x_current_step += 1
                self.y_direction *= -1                  # Invert the direction of the y scan
                self.y_current_step = 0
                return True
        else:                                           # Not last row in the column
            self.y += self.y_direction * self.delta_y
            self.y_current_step += 1
            return True
 
    def reset(self) -> None:
        self.x = copy(self.x_start)
        self.y = copy(self.y_start)
        self.first_call = True

        self.x_current_step = 0
        self.y_current_step = 0
        self.y_direction = +1

class SpiralScanner(Scanner2D):
    """A scanner that explores parameters on a grid "spirally",
    starting from a center and expanding step by step.

    Args:
    - `x_start`/`y_start` (`float | np.ndarray`): the starting parameters
    - `x_step`/`y_step` (`float | np.ndarray`): the distance between two steps
    - `n_arms` (`int`): the number of spiral arms to explore
    """
    def __init__(self, x_start: Union[float, np.ndarray], x_step: Union[float, np.ndarray],
                 y_start: Union[float, np.ndarray], y_step: Union[float, np.ndarray], n_arms: int,
                 x_label: str = "x", y_label: str = "y"):
        super(SpiralScanner, self).__init__(x_label, y_label)
        self.x_start = x_start
        self.x_step = x_step
        self.y_start = y_start
        self.y_step = y_step
        self.idrain = x_start
        self.x = copy(x_start)
        self.y = copy(y_start)

        self.n_arm = 1
        self.n_arms = n_arms
        self.step = 1
        self.steps = 1
        self.first_call = True

    def next(self) -> bool:
        if self.first_call:
            self.first_call = False
            return True

        if self.n_arm > self.n_arms:    # End of the spiral
            return False

        # match-case would be useful (python 3.10)
        if self.n_arm % 4 == 1:
            self.y += self.y_step   # Up
        elif self.n_arm % 4 == 2:
            self.x += self.x_step # Right
        elif self.n_arm % 4 == 3:
            self.y -= self.y_step   # Down
        elif self.n_arm % 4 == 0:
            self.x -= self.x_step # Left
        
        self.step += 1
        if self.step > self.steps:     # End of the arm
            self.step = 1
            self.n_arm += 1
            if self.n_arm % 2 == 1:
                self.steps += 1

        return True
 
    def reset(self) -> None:
        self.x = copy(self.x_start)
        self.y = copy(self.y_start)
        self.first_call = True

        self.n_arm = 1
        self.step = 1
        self.steps = 1

class LNATestProcedure(StripProcedure):
    """A procedure that sets idrain and offset for polarimeters one LNA at a time, with only one leg active.

    Args:
    - `test_name` (`str`): the name of the test, used in tags
    - `scanners` (`Dict[str, ScannerOneLNA]`): a dictionary that associates to each LNA the scanner to use
    - `polarimeters` (`List[str]`): a list with the names of the polarimeters to turn on and test. Default to all polarimeters.
    """
    def __init__(self, test_name: str, scanners: Dict[str, Scanner2D],
                 test_polarimeters: List[str] = [polarimeter for _, _, polarimeter in polarimeter_iterator()],
                 turnon_polarimeters: Union[List[str], None] = None,
                 bias_file_name: str = "data/default_biases_warm.xlsx",
                 stable_acquisition_time = DEFAULT_ACQUISITION_TIME_S,
                 turnon_acqisition_time = DEFAULT_WAIT_TIME_S,
                 turnon_wait_time = DEFAULT_WAIT_TIME_S,
                 message = "",
                 hk_scan_boards=STRIP_BOARD_NAMES,
                 phsw_status="77"):
        super(LNATestProcedure, self).__init__()
        self.test_name = test_name
        self.scanners = scanners
        self.test_polarimeters = list(dict.fromkeys(test_polarimeters)) # Remove duplicate polarimeters keeping order
        if (turnon_polarimeters):
            self.turnon_polarimeters = list(dict.fromkeys(turnon_polarimeters + test_polarimeters)) # Remove duplicate polarimeters keeping order
        else:
            self.turnon_polarimeters = list(dict.fromkeys(test_polarimeters))   # Remove duplicate polarimeters keeping order

        self.bias_file_name = bias_file_name
        self.stable_acquisition_time = stable_acquisition_time 
        self.turnon_acqisition_time = turnon_acqisition_time 
        self.turnon_wait_time = turnon_wait_time 
        self.message = message
        self.hk_scan_boards = hk_scan_boards
        self.phsw_status = phsw_status

        self._test_boards = set(map(get_polarimeter_board, self.test_polarimeters))
        self._setup_boards = {}      # A dictionary of SetupBoard objects (one for each board), used to reset LNA biases to default values during the procedure
        for board in self._test_boards:
            self._setup_boards[board] = SetupBoard(config=self.conf, post_command=self.command_emitter,
                board_name=board, bias_file_name=self.bias_file_name)

        self._calibr = CalibrationTables()

    def run(self):
        with StripTag(conn=self.conn, name=f"{self.test_name}",
                      comment=f"{self.test_name} test: scan idrain and detector offset on polarimeters "
                              f"{self.test_polarimeters}, with {self.turnon_polarimeters} turned on."):
            self.conn.log(message=self.message, level="INFO")
            # Turn on all polarimeters and set all the B legs to zero bias
            with StripTag(conn=self.conn, name=f"{self.test_name}_TURNON_LEG_HA",
                          comment="Turnon polarimeters and set leg HB to zero bias."):
                with StripTag(conn=self.conn, name=f"{self.test_name}_TURNON_POLARIMETERS",
                              comment=f"Turnon polarimeters {self.turnon_polarimeters}."):
                    self._turnon()
                with StripTag(conn=self.conn, name=f"{self.test_name}_SET_PHSW_LEG_HA",
                              comment=f"Turnon polarimeters {self.turnon_polarimeters}."):
                    self._reset_phsw(leg="HA")
                with StripTag(conn=self.conn, name=f"{self.test_name}_ZERO_BIAS_LEG_HB",
                              comment="Set leg HB to zero bias."):
                    self._zero_bias(leg="HB")
        
            # Scan the leg A
            with StripTag(conn=self.conn, name=f"{self.test_name}_TEST_LEG_HA", comment="Run test on leg HA."):
                self._test_leg(leg="HA")

            # Reset the B leg biases and set A legs to zero bias
            with StripTag(conn=self.conn, name=f"{self.test_name}_TURNON_LEG_HB",
                          comment="Reset leg HB and set leg HA to zero bias."):
                with StripTag(conn=self.conn, name=f"{self.test_name}_RESET_LEG_HB",
                            comment="Reset leg HB to default biases."):
                    for lna in "HB1", "HB2", "HB3":
                        self._reset_lna(lna)
                    self._reset_phsw(leg="HB")
                with StripTag(conn=self.conn, name=f"{self.test_name}_ZERO_BIAS_LEG_HA",
                              comment="Set leg HA to zero bias."):
                    self._zero_bias(leg="HA")

            # Scan the leg B
            with StripTag(conn=self.conn, name=f"{self.test_name}_TEST_LEG_HB", comment="Run test on leg HB."):
                self._test_leg(leg="HB")

            # Turn off all polarimeters
            with StripTag(conn=self.conn, name=f"{self.test_name}_TURNOFF", comment="Turn off polarimeters."):
                self._turnoff()

    def _test_leg(self, leg: str):
        """Run the test on the specified leg on all polarimeters, from LNA 1 to 3.
        
        Args:
        - `leg` (`str`): the leg to run the test on. Can be "HA" or "HB"."""
        for lna in (f"{leg}{i}" for i in range(1, 4)):
            with StripTag(conn=self.conn, name=f"{self.test_name}_TEST_LNA_{lna}"):
                self._test_lna(lna)

    def _test_lna(self, lna: str):
        """Test one LNA on all polarimeters changing idrain and offset according to a scanning strategy.
    
        Args:
        - `lna` (`str`): the LNA to test.
        """
        
        # Test LNA using scanner
        end = False
        i = 0
        while not end:
            with StripTag(conn=self.command_emitter, name=f"{self.test_name}_TEST_LNA_{lna}_{i}",
                          comment=f"Test LNA {lna}: step {i}."):
                for polarimeter in self.test_polarimeters:
                    scanner = scanners[polarimeter][lna]
                    if scanner.next() == False:    # Exit when the first scanner reaches an end
                        end = True
                    idrain = int(scanner.x)
                    offset = scanner.y.astype(int)
                    with StripTag(conn=self.command_emitter,
                                  name=f"{self.test_name}_TEST_LNA_{lna}_{i}_{polarimeter}",
                                  comment=f"Test LNA {lna}: step {i}, polarimeter {polarimeter}:"
                                          f"idrain={idrain}, offset={offset}."):
                        idrain_adu = self._calibr.physical_units_to_adu(
                            polarimeter=polarimeter, hk="idrain",
                            component=lna, value=idrain)
                        self.conn.set_id(polarimeter, lna, idrain_adu)
                        self._set_offset(polarimeter, offset)
                self.conn.set_hk_scan(boards = self.hk_scan_boards)
                wait_with_tag(conn=self.conn, seconds=self.stable_acquisition_time,
                              name=f"{self.test_name}_TEST_LNA_{lna}_{i}_ACQ",
                              comment=f"Test LNA {lna}: step {i}, stable acquisition")
            i += 1

        # Reset LNA
        with StripTag(conn=self.conn, name=f"{self.test_name}_RESET_LNA_{lna}",
                      comment=f"Reset LNA {lna} to default biases."):
            self._reset_lna(lna)

    def _set_offset(self, polarimeter: str, offset: np.ndarray):
        """Set the offset for all detectors on the specified polarimeter.
        
        Args:
        - `polarimeter` (`str`): the polarimeter to set the offset on.
        - `offset` (`np.ndarray`): an array containing the four values for the offsets (one for each detector).
            Must be between 0 and 4096."""

        # Get the REST API URL
        url = self.conf.get_rest_base() + "/slo"

        # Prepare the REST API command
        cmd = {}
        cmd["board"] = get_polarimeter_board(polarimeter)
        cmd["type"] = "BIAS"
        cmd["method"] = "SET"
        cmd["timeout"] = 500
        cmd["pol"] = polarimeter
        cmd["type"] = "DAQ"
        
        # Post a SET command for each detector (0, 1, 2, 3)
        for detector_idx in range(0, 4):
            cmd["base_addr"] = f"DET{detector_idx}_OFFS"
            cmd["data"] = [int(offset[detector_idx])]
            self.conn.post_command(url, cmd)

    def _reset_lna(self, lna: str):
        """Reset the idrain and the offsets of the LNA to the default value for each polarimeter.
        
        Args:
        - `lna` (`str`): the LNA to reset."""
        for polarimeter in self.test_polarimeters:
            with StripTag(conn=self.command_emitter, name=f"{self.test_name}_RESET_LNA_{lna}_{polarimeter}",
                          comment=f"Reset LNA {lna}: polarimeter {polarimeter}."):
                setup_board = self._setup_boards[get_polarimeter_board(polarimeter)]
                setup_board.setup_ID(polarimeter, lna)
                default_offsets = np.array([
                    setup_board.ib.get_biases(module_name=polarimeter, param_hk=f"DET{detector_idx}_OFFSET")
                    for detector_idx in range(0, 4)
                ])
                self._set_offset(polarimeter, default_offsets)

    def _get_phsw_from_leg(self, leg: str):
        if leg == "HA":
            return (0, 1)
        elif leg == "HB":
            return (2, 3)

    def _reset_phsw(self, leg: str):
        for polarimeter in self.test_polarimeters:
            with StripTag(conn=self.command_emitter, name=f"{self.test_name}_RESET_PHSW_{leg}_{polarimeter}",
                          comment=f"Reset phase switch on leg {leg}: polarimeter {polarimeter}."):
                phase_switches = self._get_phsw_from_leg(leg)
                if self.phsw_status == "77":
                    for phsw_index in phase_switches:
                        self.conn.set_phsw_status(polarimeter, phsw_index, PhswPinMode.NOMINAL_SWITCHING)
                elif self.phsw_status == "56":
                    self.conn.set_phsw_status(polarimeter, phase_switches[0], PhswPinMode.STILL_SIGNAL)
                    self.conn.set_phsw_status(polarimeter, phase_switches[1], PhswPinMode.STILL_NO_SIGNAL)
                elif self.phsw_status == "65":
                    self.conn.set_phsw_status(polarimeter, phase_switches[0], PhswPinMode.STILL_NO_SIGNAL)
                    self.conn.set_phsw_status(polarimeter, phase_switches[1], PhswPinMode.STILL_SIGNAL)

    def _zero_bias(self, leg: str):
        """Set vdrain and phase switch biases to zero for all LNAs on all polarimeters on the specified leg.
        
        Args:
        - `leg` (`str`): the leg to set to zero bias. Can be "HA" or "HB"."""
        for polarimeter in self.test_polarimeters:
            with StripTag(conn=self.command_emitter, name=f"{self.test_name}_ZERO_BIAS_LEG_{leg}_{polarimeter}",
                          comment=f"Set leg {leg} to zero bias: polarimeter {polarimeter}."):
                # QUESTION: Set vdrain to zero? YES!
                #for lna in leg + "1", leg + "2", leg + "3":
                #    self.conn.set_vd(polarimeter, lna, value_adu=0)
                for phsw_index in self._get_phsw_from_leg(leg):
                    self.conn.set_phsw_status(polarimeter, phsw_index, PhswPinMode.STILL_NO_SIGNAL)

    def _turnon(self):
        """Turn on all the polarimeters specified in self.polarimeters"""
        self._turnonoff(turnon=True)

    def _turnoff(self):
        """Turn off all polarimeters."""
        self._turnonoff(turnon=False)

    def _turnonoff(self, turnon: bool):
        """Turn on or off all polarimeters.
        
        Args:
        - `turnon` (`bool`): True if turnon, False if turnoff."""

        turnonoff_proc = TurnOnOffProcedure(waittime_s=self.turnon_wait_time,
                                            stable_acquisition_time_s=self.turnon_acqisition_time,
                                            turnon=turnon, bias_file_name=self.bias_file_name)
        for polarimeter in self.turnon_polarimeters:
            turnonoff_proc.set_board_horn_polarimeter(new_board=get_polarimeter_board(polarimeter), new_horn=polarimeter, new_pol=None)
            turnonoff_proc.run()
            self.command_emitter.command_list += turnonoff_proc.get_command_list()
            turnonoff_proc.clear_command_list()
            if turnon:
                self.conn.set_pol_mode(polarimeter, CLOSED_LOOP_MODE)   # QUESTION: is this in the right place?


def read_cell(excel_file, polarimeter: str, lna: str) -> Scanner2D:
    row = excel_file[polarimeter]
    scanner_class = globals()[row[(lna, "Scanner")]]
    arguments_str = row[(lna, "Arguments")]
    arguments = list(map(literal_eval, arguments_str.split(";")))
    for i in range(len(arguments)):
        if isinstance(arguments[i], list):
            arguments[i] = np.asarray(arguments[i], dtype=float)
    return scanner_class(*arguments, x_label="idrain", y_label="offset")

def read_excel(filename: str, dummy_polarimeter: bool = False) -> Dict[str, Dict[str, Scanner2D]]:
    excel_file = pd.read_excel(filename, header=(0, 1), index_col=0).to_dict(orient="index")
    scanners = {}
    for polarimeter in set(excel_file) - {"DUMMY"}: # Iterate over all polarimeterx except the DUMMY one
        scanners[polarimeter] = {}
        for lna in "HA1", "HA2", "HA3", "HB1", "HB2", "HB3":
            if dummy_polarimeter:
                scanners[polarimeter][lna] = read_cell(excel_file, "DUMMY", lna)
            else:
                scanners[polarimeter][lna] = read_cell(excel_file, polarimeter, lna)
    return scanners

if __name__ == "__main__":
    from argparse import ArgumentParser, RawDescriptionHelpFormatter

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
    parser.add_argument(
        "--output", "-o",
        metavar="FILENAME",
        type=str,
        dest="output_filename",
        default="",
        help="Name of the file where to write the output (in JSON format). "
        "If not provided, the output will be sent to stdout.",
    )
    parser.add_argument(
        "--test-polarimeters",
        metavar="POLARIMETER",
        type=str,
        nargs="+",
        default=DEFAULT_POLARIMETERS,
        help="Name of the polarimeters/module to test. Valid names "
            'are "G4", "W3", etc. Can be "all" (which is the default).',
    )
    parser.add_argument(
        "--turnon-polarimeters",
        metavar="POLARIMETER",
        type=str,
        nargs="+",
        default=[],
        help="Name of the polarimeters/module to turn on. Valid names "
            'are "G4", "W3", etc. Can be "all", and by default it is equal '
            "to test-polarimeters.",
    )
    parser.add_argument(
        "--test-name",
        metavar="STRING",
        type=str,
        dest="test_name",
        default=DEFAULT_TEST_NAME,
        help="The name of the test, to be put at the beginning of each tag. "
            f'The default is "{DEFAULT_TEST_NAME}".'
    )
    parser.add_argument(
        "--bias-file-name",
        metavar="FILENAME",
        type=str,
        dest="bias_file_name",
        default=DEFAULT_BIAS_FILENAME,
        help="Excel file containing the biases to be used when turning on the polarimeters. "
            f'The default is "{DEFAULT_BIAS_FILENAME}"'
    )
    parser.add_argument(
        "--hk-scan-boards",
        metavar="BOARD",
        dest="hk_scan_boards",
        default=["test"],
        type=str,
        nargs="+",
        help="The list of boards to scan housekeeping on before stable acquisition. "
             'Can be "test" for boards under testing (the default), '
             '"turnon" for turned-on ones, "all", "none" or a list of boards.'
    )
    parser.add_argument(
        "--phsw-status",
        type=str,
        dest="phsw_status",
        default="77",
        help="Status of turned-on phase switch pins. Can be 77 (the default), 56 or 65."
    )
    parser.add_argument(
        "--stable-acquisition-time",
        metavar="SECONDS",
        default=DEFAULT_ACQUISITION_TIME_S,
        type=int,
        dest="stable_acquisition_time",
        help="Number of seconds to measure after the polarimeter biases have been "
            f"set up (default: {DEFAULT_ACQUISITION_TIME_S}s)"
    )
    parser.add_argument(
        "--turnon-acquisition-time",
        metavar="SECONDS",
        default=DEFAULT_WAIT_TIME_S,
        type=int,
        dest="turnon_acquisition_time",
        help="Number of seconds to measure after the polarimeters have been "
            f"turned on (default: {DEFAULT_WAIT_TIME_S}s)"
    )
    parser.add_argument(
        "--turnon-wait-time",
        metavar="SECONDS",
        default=DEFAULT_WAIT_TIME_S,
        type=int,
        dest="turnon_wait_time",
        help="Number of seconds to wait between turnon commands "
            f"set up (default: {DEFAULT_WAIT_TIME_S}s)"
    )
    parser.add_argument(
        "--tuning-file",
        metavar="FILENAME",
        type=str,
        dest="tuning_filename",
        default=DEFAULT_TUNING_FILENAME,
        help="Run the test using the scanners contained in an Excel file. "
            f'The default is "{DEFAULT_TUNING_FILENAME}".'
    )
    parser.add_argument(
        "--bias-from-dummy-polarimeter",
        action="store_true",
        dest="dummy_polarimeter",
        help="Test all polarimeters using the scanning strategy of the DUMMY one."
    )

    args = parser.parse_args()
    log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    assert(args.phsw_status == "77" or args.phsw_status == "56" or args.phsw_status == "65")

    scanners = read_excel(args.tuning_filename, args.dummy_polarimeter)

    if args.test_polarimeters[0] == "all":
        args.test_polarimeters = DEFAULT_POLARIMETERS
    if args.turnon_polarimeters != [] and args.turnon_polarimeters[0] == "all":
        args.turnon_polarimeters = DEFAULT_POLARIMETERS
    args.turnon_polarimeters = list(dict.fromkeys(args.turnon_polarimeters + args.test_polarimeters)) # Make sure that all tested polarimeters are also turned on

    if args.hk_scan_boards == [] or args.hk_scan_boards[0] == "none":
        args.hk_scan_boards = []
    elif args.hk_scan_boards[0] == "all":
        args.hk_scan_boards = STRIP_BOARD_NAMES
    elif args.hk_scan_boards[0] == "test":
        args.hk_scan_boards = list(set(map(get_polarimeter_board, args.test_polarimeters)))
    elif args.hk_scan_boards[0] == "turnon":
        args.hk_scan_boards = list(set(map(get_polarimeter_board, args.turnon_polarimeters)))

    message = f"Here begins the {args.test_name} procedure to test LNA biases, " \
              f"generated on {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}.\n" \
              f"Tested polarimeters: {args.test_polarimeters}.\n"\
              f"Turned-on polarimeters: {args.turnon_polarimeters}.\n"\
              f"Housekeeping scanned on boards: {args.hk_scan_boards}.\n"\
              f"Bias file: {args.bias_file_name}.\n"\
              f"Tuning file: {args.tuning_filename}.\n"\
              f"Dummy polarimeter: {args.dummy_polarimeter}.\n"\
              f"Stable acquisition time: {args.stable_acquisition_time}s.\n"\
              f"Turnon wait time: {args.turnon_wait_time}s.\n"\
              f"Turnon acquisition time: {args.turnon_acquisition_time}s."

    proc = LNATestProcedure(test_name=args.test_name, scanners=scanners, test_polarimeters=args.test_polarimeters,
        turnon_polarimeters=args.turnon_polarimeters, bias_file_name=args.bias_file_name,
        stable_acquisition_time=args.stable_acquisition_time, turnon_acqisition_time=args.turnon_acquisition_time,
        turnon_wait_time=args.turnon_wait_time, message=message, hk_scan_boards=args.hk_scan_boards, phsw_status=args.phsw_status)
    proc.run()
    proc.output_json(args.output_filename)