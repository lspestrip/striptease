# -*- encoding: utf-8 -*-

from abc import ABC, abstractmethod
from copy import copy
from enum import IntEnum
import functools
from typing import Callable, Dict, List, Union

import numpy as np

from calibration import CalibrationTables
from striptease.procedures import StripProcedure
from striptease.stripconn import StripTag, wait_with_tag
from striptease.utilities import CLOSED_LOOP_MODE, OPEN_LOOP_MODE, STRIP_BOARD_NAMES, PhswPinMode, \
                                 get_polarimeter_board, polarimeter_iterator
from .scanners import Scanner1D, Scanner2D
from turnon import SetupBoard, TurnOnOffProcedure

DEFAULT_ACQUISITION_TIME_S = 5
DEFAULT_WAIT_TIME_S = 1

class StripState(IntEnum):
    OFF = 0         # All required boards are turned off
    DEFAULT = 1     # All required boards are turned on with default biases
    ZERO_BIAS = 2   # All required boards are turned on with zero biases
    ON = 3          # All required boards are turned on with unspecified biases

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

class TuningProcedure(StripProcedure, ABC):
    def __init__(self, start_state: StripState, end_state: StripState, turnon_zero_bias: bool, tag_comment: str,
                 test_name: str,
                 test_polarimeters: List[str] = [polarimeter for _, _, polarimeter in polarimeter_iterator()],
                 turnon_polarimeters: Union[List[str], None] = None,
                 bias_file_name: str = "data/default_biases_warm.xlsx",
                 stable_acquisition_time = DEFAULT_ACQUISITION_TIME_S,
                 turnon_acqisition_time = DEFAULT_WAIT_TIME_S,
                 turnon_wait_time = DEFAULT_WAIT_TIME_S,
                 message = "",
                 hk_scan_boards=STRIP_BOARD_NAMES,
                 open_loop=False):
        super(TuningProcedure, self).__init__()

        self.test_name = test_name
        self.test_polarimeters = list(dict.fromkeys(test_polarimeters)) # Remove duplicate polarimeters keeping order
        if (turnon_polarimeters):
            self.turnon_polarimeters = list(dict.fromkeys(turnon_polarimeters + test_polarimeters)) # Remove duplicate polarimeters keeping order
        else:
            self.turnon_polarimeters = list(dict.fromkeys(test_polarimeters))   # Remove duplicate polarimeters keeping order

        self.bias_file_name = bias_file_name
        self.stable_acquisition_time = stable_acquisition_time 
        self.turnon_acqisition_time = turnon_acqisition_time 
        self.turnon_wait_time = turnon_wait_time 
        self.hk_scan_boards = hk_scan_boards
        self.message = message

        self.start_state = start_state
        self.end_state = end_state
        self.open_loop = open_loop

        self._test_boards = set(map(get_polarimeter_board, self.test_polarimeters))
        self._setup_boards = {}      # A dictionary of SetupBoard objects (one for each board), used to reset LNA biases to default values during the procedure
        for board in self._test_boards:
            self._setup_boards[board] = SetupBoard(config=self.conf, post_command=self.command_emitter,
                board_name=board, bias_file_name=self.bias_file_name)

        self._calibr = CalibrationTables()

        # Decorate self.run function (we cannot use the @ syntax since we wish to decorate all run functions in child classes)
        self.run = self._run_with_turnonoff(self.run, turnon_zero_bias, tag_comment)

    @abstractmethod
    def run(self):
        ...

    def _run_with_turnonoff(self, run: Callable, turnon_zero_bias: bool, tag_comment: str):
        @functools.wraps(run)
        def wrapper():
            with StripTag(conn=self.conn, name=f"{self.test_name}", comment=tag_comment):
                if self.message != "":
                    self.conn.log(message=self.message, level="INFO")
                if self.start_state == StripState.OFF:
                    with StripTag(conn=self.conn, name=f"{self.test_name}_TURNON_POLARIMETERS",
                                  comment=f"Turnon polarimeters {self.turnon_polarimeters}."):
                        self._turnon(zero_bias=turnon_zero_bias)

                run()

                if self.end_state == StripState.OFF:
                    # Turn off all polarimeters
                    with StripTag(conn=self.conn, name=f"{self.test_name}_TURNOFF", comment="Turn off polarimeters."):
                        self._turnoff()
            
        return wrapper

    def _reset_lna(self, lna: str):
        """Reset the idrain, vgate and the offsets of the LNA to the default value for each polarimeter.
        
        Args:
        - `lna` (`str`): the LNA to reset."""
        for polarimeter in self.test_polarimeters:
            with StripTag(conn=self.command_emitter, name=f"{self.test_name}_RESET_LNA_{lna}_{polarimeter}",
                          comment=f"Reset LNA {lna}: polarimeter {polarimeter}."):
                setup_board = self._setup_boards[get_polarimeter_board(polarimeter)]
                setup_board.setup_VD(polarimeter, lna)
                if self.open_loop:
                    setup_board.setup_VG(polarimeter, lna)
                else:
                    setup_board.setup_ID(polarimeter, lna)
                self._reset_offset(polarimeter)

    def _reset_leg(self, leg: str):
        for lna in map(lambda x: leg + x, ("1", "2", "3")):
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
 
    def _reset_offset(self, polarimeter: str):
        setup_board = self._setup_boards[get_polarimeter_board(polarimeter)]
        default_offsets = np.array([
            setup_board.ib.get_biases(module_name=polarimeter, param_hk=f"DET{detector_idx}_OFFSET")
            for detector_idx in range(0, 4)
        ])
        self._set_offset(polarimeter, default_offsets)

    def _test(self, func: Callable, tag: str, comment: str):
        step = 0
        test_polarimeters = copy(self.test_polarimeters)
        while test_polarimeters != []:
            next_test_polarimeters = []
            with StripTag(conn=self.command_emitter, name=f"{tag}_{step}",
                          comment=f"{comment}: step {step}"):
                for polarimeter in test_polarimeters:
                    scanner = func(self, polarimeter, step)
                    if scanner.next() == True:    # The scan is not over for this polarimeter: add it to the next test list
                        next_test_polarimeters.append(polarimeter)
                self.conn.set_hk_scan(boards = self.hk_scan_boards) # QUESTION: dynamic hk_scan boards or not?
                wait_with_tag(conn=self.conn, seconds=self.stable_acquisition_time,
                              name=f"{tag}_{step}_ACQ",
                              comment=f"{comment}: step {step}, stable acquisition")
            test_polarimeters = next_test_polarimeters
            step += 1

    def _zero_bias(self, leg: str):
        """Set vdrain/idrain and phase switch biases to zero for all LNAs on all polarimeters on the specified leg.
        
        Args:
        - `leg` (`str`): the leg to set to zero bias. Can be "HA" or "HB"."""
        for polarimeter in self.test_polarimeters:
            with StripTag(conn=self.command_emitter, name=f"{self.test_name}_ZERO_BIAS_LEG_{leg}_{polarimeter}",
                          comment=f"Set leg {leg} to zero bias: polarimeter {polarimeter}."):
                for lna in leg + "1", leg + "2", leg + "3":
                    self.conn.set_vd(polarimeter, lna, value_adu=0)
                    if not self.open_loop:
                        self.conn.set_id(polarimeter, lna, value_adu=0)
                for phsw_index in self._get_phsw_from_leg(leg):
                    self.conn.set_phsw_status(polarimeter, phsw_index, PhswPinMode.STILL_NO_SIGNAL)

    def _turnon(self, zero_bias: bool):
        """Turn on all the polarimeters specified in self.polarimeters"""
        self._turnonoff(turnon=True, zero_bias=zero_bias)

    def _turnoff(self):
        """Turn off all polarimeters."""
        self._turnonoff(turnon=False)

    def _turnonoff(self, turnon: bool, zero_bias: bool = False):
        """Turn on or off all polarimeters.
        
        Args:
        - `turnon` (`bool`): True if turnon, False if turnoff."""

        turnonoff_proc = TurnOnOffProcedure(waittime_s=self.turnon_wait_time,
                                            stable_acquisition_time_s=self.turnon_acqisition_time,
                                            turnon=turnon, bias_file_name=self.bias_file_name, zero_bias=zero_bias)
        for polarimeter in self.turnon_polarimeters:
            turnonoff_proc.set_board_horn_polarimeter(new_board=get_polarimeter_board(polarimeter), new_horn=polarimeter, new_pol=None)
            turnonoff_proc.run()
            self.command_emitter.command_list += turnonoff_proc.get_command_list()
            turnonoff_proc.clear_command_list()
            if turnon:  # BUG: this is not run if staer state is not off
                if self.open_loop:
                    self.conn.set_pol_mode(polarimeter, OPEN_LOOP_MODE)
                else:
                    self.conn.set_pol_mode(polarimeter, CLOSED_LOOP_MODE)

class LNAPretuningProcedure(TuningProcedure):
    """A procedure that sets idrain and offset for polarimeters one LNA at a time, with only one leg active.

    Args:
    - `test_name` (`str`): the name of the test, used in tags
    - `scanners` (`Dict[str, ScannerOneLNA]`): a dictionary that associates to each LNA the scanner to use
    - `polarimeters` (`List[str]`): a list with the names of the polarimeters to turn on and test. Default to all polarimeters.
    """
    def __init__(self, test_name: str, scanners: Dict[str, Union[Scanner1D, Scanner2D]],
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
        super(LNAPretuningProcedure, self).__init__(
            start_state=start_state, end_state=end_state, turnon_zero_bias=False,
            tag_comment=f"{test_name} test: scan idrain and detector offset on polarimeters {test_polarimeters}, "
                        f"with {turnon_polarimeters} turned on.",
            test_name=test_name, test_polarimeters=test_polarimeters, turnon_polarimeters=turnon_polarimeters, bias_file_name=bias_file_name,
            stable_acquisition_time=stable_acquisition_time, turnon_acqisition_time=turnon_acqisition_time, turnon_wait_time=turnon_wait_time,
            message=message, hk_scan_boards=hk_scan_boards, open_loop=open_loop)
        self.scanners = scanners
        self.phsw_status = phsw_status
 
    def run(self):
        with StripTag(conn=self.conn, name=f"{self.test_name}_SETUP_LEG_HA",
                      comment="Set leg HA to default and HB to zero bias if needed."):
            with StripTag(conn=self.conn, name=f"{self.test_name}_RESET_LEG_HA",
                          comment=f"Turnon polarimeters {self.turnon_polarimeters}."):
                self._reset_phsw(leg="HA")
                if self.start_state != StripState.OFF and self.start_state != StripState.DEFAULT:
                    self._reset_leg(leg="HA")
            if self.start_state != StripState.ZERO_BIAS:
                with StripTag(conn=self.conn, name=f"{self.test_name}_ZERO_BIAS_LEG_HB",
                              comment="Set leg HB to zero bias."):
                    self._zero_bias(leg="HB")

            self.conn.set_hk_scan(boards = self.hk_scan_boards)
            wait_with_tag(conn=self.conn, seconds=self.stable_acquisition_time,
                          name=f"{self.test_name}_SETUP_LEG_HA_ACQ",
                          comment="Turnon leg HA: stable acquisition.")

        # Scan the leg A
        with StripTag(conn=self.conn, name=f"{self.test_name}_TEST_LEG_HA", comment="Run test on leg HA."):
            self._test_leg(leg="HA")

        # Reset the B leg biases and set A legs to zero bias
        with StripTag(conn=self.conn, name=f"{self.test_name}_SETUP_LEG_HB",
                      comment="Reset leg HB and set leg HA to zero bias."):
            with StripTag(conn=self.conn, name=f"{self.test_name}_RESET_LEG_HB",
                        comment="Reset leg HB to default biases."):
                self._reset_phsw(leg="HB")
                self._reset_leg(leg="HB")
            with StripTag(conn=self.conn, name=f"{self.test_name}_ZERO_BIAS_LEG_HA",
                          comment="Set leg HA to zero bias."):
                self._zero_bias(leg="HA")

            self.conn.set_hk_scan(boards = self.hk_scan_boards)
            wait_with_tag(conn=self.conn, seconds=self.stable_acquisition_time,
                          name=f"{self.test_name}_SETUP_LEG_HB_ACQ",
                          comment="Turnon leg HB: stable acquisition.")

        # Scan the leg B
        with StripTag(conn=self.conn, name=f"{self.test_name}_TEST_LEG_HB", comment="Run test on leg HB."):
            self._test_leg(leg="HB")

        if self.end_state == StripState.ZERO_BIAS:
            # Set leg B to zero bias
            with StripTag(conn=self.conn, name=f"{self.test_name}_ZERO_BIAS_LEG_HB",
                          comment="Set leg HB to zero bias."):
                self._zero_bias(leg="HB")

        if self.end_state == StripState.DEFAULT:
            with StripTag(conn=self.conn, name=f"{self.test_name}_RESET_LEG_HA",
                        comment="Reset leg HA to default biases."):
                self._reset_phsw(leg="HA")
                self._reset_leg(leg="HA")
            
    def _test_leg(self, leg: str):
        """Run the test on the specified leg on all polarimeters, from LNA 1 to 3.
        
        Args:
        - `leg` (`str`): the leg to run the test on. Can be "HA" or "HB"."""
        for lna in (f"{leg}{i}" for i in range(1, 4)):
            # Test LNA
            with StripTag(conn=self.conn, name=f"{self.test_name}_TEST_LNA_{lna}"):
                if self.open_loop:
                    func = lambda self, polarimeter, step: self._test_open_loop(polarimeter, step, lna)
                else:
                    func = lambda self, polarimeter, step: self._test_closed_loop(polarimeter, step, lna)
                self._test(func=func, tag=f"{self.test_name}_TEST_LNA_{lna}", comment=f"Test LNA {lna}")
            # Reset LNA
            with StripTag(conn=self.conn, name=f"{self.test_name}_RESET_LNA_{lna}",
                          comment=f"Reset LNA {lna} to default biases."):
                self._reset_lna(lna)
 
    def _test_closed_loop(self, polarimeter, step, lna: str) -> Scanner2D:
        """Test one LNA on all polarimeters changing idrain and offset according to a scanning strategy.
    
        Args:
        - `lna` (`str`): the LNA to test.
        """

        scanner = self.scanners[polarimeter][lna]
        idrain = int(scanner.x)
        idrain_step = scanner.index[0]
        offset = scanner.y.astype(int)
        offset_step = scanner.index[1]
        with StripTag(conn=self.command_emitter,
                      name=f"{self.test_name}_TEST_LNA_{lna}_{step}_{polarimeter}_{idrain_step}_{offset_step}",
                      comment=f"Test LNA {lna}: step {step}, polarimeter {polarimeter}:"
                              f"idrain={idrain}, offset={offset}."):
            idrain_adu = self._calibr.physical_units_to_adu(
                polarimeter=polarimeter, hk="idrain",
                component=lna, value=idrain)
            self.conn.set_id(polarimeter, lna, idrain_adu)
            self._set_offset(polarimeter, offset)
        return scanner

    def _test_open_loop(self, polarimeter, step, lna: str) -> Scanner2D:
        """Test one LNA on all polarimeters changing vgate and offset according to a scanning strategy.
    
        Args:
        - `lna` (`str`): the LNA to test.
        """

        scanner = self.scanners[polarimeter][lna]
        vgate = int(scanner.x)
        vgate_step = scanner.index[0]
        offset = scanner.y.astype(int)
        offset_step = scanner.index[1]
        with StripTag(conn=self.command_emitter,
                      name=f"{self.test_name}_TEST_LNA_{lna}_{step}_{polarimeter}_{vgate_step}_{offset_step}",
                      comment=f"Test LNA {lna}: step {step}, polarimeter {polarimeter}:"
                              f"vgate={vgate}, offset={offset}."):
            vgate_adu = self._calibr.physical_units_to_adu(
                polarimeter=polarimeter, hk="vgate",
                component=lna, value=vgate)
            self.conn.set_vg(polarimeter, lna, vgate_adu)
            self._set_offset(polarimeter, offset)
        return scanner

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

class OffsetTuningProcedure(TuningProcedure):
    def __init__(self, test_name: str, scanners: Dict[str, Union[Scanner1D, Scanner2D]],
                 test_polarimeters: List[str] = [polarimeter for _, _, polarimeter in polarimeter_iterator()],
                 turnon_polarimeters: Union[List[str], None] = None,
                 bias_file_name: str = "data/default_biases_warm.xlsx",
                 stable_acquisition_time = DEFAULT_ACQUISITION_TIME_S,
                 turnon_acqisition_time = DEFAULT_WAIT_TIME_S,
                 turnon_wait_time = DEFAULT_WAIT_TIME_S,
                 message = "",
                 hk_scan_boards=STRIP_BOARD_NAMES,
                 open_loop=False,
                 start_state=StripState.OFF,
                 end_state=StripState.ZERO_BIAS):
        super(OffsetTuningProcedure, self).__init__(
            start_state=start_state, end_state=end_state, turnon_zero_bias=True,
            tag_comment=f"{test_name} test: scan idrain and detector offset on polarimeters {test_polarimeters}, "
                        f"with {turnon_polarimeters} turned on.",
            test_name=test_name, test_polarimeters=test_polarimeters, turnon_polarimeters=turnon_polarimeters, bias_file_name=bias_file_name,
            stable_acquisition_time=stable_acquisition_time, turnon_acqisition_time=turnon_acqisition_time, turnon_wait_time=turnon_wait_time,
            message=message, hk_scan_boards=hk_scan_boards, open_loop=open_loop)
        self.scanners = scanners

    def run(self):
        if self.start_state != StripState.OFF and self.start_state != StripState.ZERO_BIAS:
            # Set legs to zero bias
            with StripTag(conn=self.conn, name=f"{self.test_name}_ZERO_BIAS_LEG_HA",
                          comment="Set leg HA to zero bias."):
                self._zero_bias(leg="HA")
            with StripTag(conn=self.conn, name=f"{self.test_name}_ZERO_BIAS_LEG_HB",
                          comment="Set leg HB to zero bias."):
                self._zero_bias(leg="HB")

        # Perform a detector offset test
        with StripTag(conn=self.conn, name=f"{self.test_name}_TEST_DET_OFFS",
                      comment="Perform a detector offset test."):
            self._test(func=lambda self, polarimeter, step: self._test_offset(polarimeter, step),
                       tag=f"{self.test_name}_TEST_DET_OFFS", comment="Test detector offset")

        if self.end_state == StripState.ZERO_BIAS:
            for polarimeter in self.test_polarimeters:
                self._set_offset(polarimeter, np.array([0, 0, 0, 0]))

        if self.end_state == StripState.DEFAULT:
            # Set legs to default bias
            with StripTag(conn=self.conn, name=f"{self.test_name}_RESET_LEG_HA",
                          comment="Set leg HA to default bias."):
                self._reset_leg(leg="HA")
            with StripTag(conn=self.conn, name=f"{self.test_name}_RESET_LEG_HB",
                          comment="Set leg HB to default bias."):
                self._reset_leg(leg="HB")

    def _test_offset(self, polarimeter, step) -> Scanner1D:
        scanner = self.scanners[polarimeter]["Offset"]
        offset = scanner.x.astype(int)
        with StripTag(conn=self.command_emitter,
                      name=f"{self.test_name}_TEST_DET_OFFS_{step}_{polarimeter}",
                      comment=f"Test detector offset: step {step}, polarimeter {polarimeter}, "
                              f"offset={offset}"):
            self._set_offset(polarimeter, offset)
        return scanner