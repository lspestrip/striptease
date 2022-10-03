#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging as log
from pathlib import Path
from typing import Dict, List, Union
from collections import namedtuple
from abc import ABC, abstractmethod
from striptease import StripTag
from striptease.stripconn import wait_with_tag
from striptease.utilities import CLOSED_LOOP_MODE, get_polarimeter_board, polarimeter_iterator
from striptease.procedures import StripProcedure
from calibration import CalibrationTables
from turnon import SetupBoard, TurnOnOffProcedure

OneLNAConfig = namedtuple("OneLNAConfig", "offset_start offset_stop offset_nsteps idrain_start idrain_stop idrain_nsteps")
LNAConfig = namedtuple("LNAConfig", "ha1 ha2 ha3 hb1 hb2 hb3")

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

class GridScannerOneLNA(Scanner2D):
    """A scanner that explores parameters on a grid from down to up and from left to right

    Args:
    - `x_start`/`y_start` (`float`): the starting parameters
    - `x_stop`/`y_stop` (`float`): the parameters at which the grid ends
    - `x_nsteps`/`y_nsteps` (`int`): the number of steps
    -`x_label`/`y_label` (`str`): the names of the x, y variables, to be used in the plot."""
    def __init__(self, x_start: float, x_stop: float, x_nsteps: int,
                 y_start: float, y_stop: float, y_nsteps: int,
                 x_label: str = "x", y_label: str = "y"):
        super(GridScannerOneLNA, self).__init__(x_label, y_label)
        self.x_start = x_start
        self.x_stop = x_stop
        self.x_nsteps = x_nsteps
        self.delta_x = (x_stop - x_start) / x_nsteps
        self.y_start = y_start
        self.y_stop = y_stop
        self.y_nsteps = y_nsteps
        self.delta_y = (y_stop - y_start) / y_nsteps

        self.x = x_start
        self.y = y_start

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
                self.y = self.y_start
                self.y_current_step = 0
                return True
        else:                                           # Not last row in the column
            self.y += self.delta_y
            self.y_current_step += 1
            return True
 
    def reset(self) -> None:
        self.x = self.x_start
        self.y = self.y_start
        self.first_call = True

        self.x_current_step = 0
        self.y_current_step = 0

class RasterScannerOneLNA(Scanner2D):
    """A scanner that explores parameters on a grid \"boustrophedically\",
    from down to up and viceversa alternating at every column.

    Args:
    - `x_start`/`y_start` (`float`): the starting parameters
    - `x_stop`/`y_stop` (`float`): the parameters at which the grid ends
    - `x_nsteps`/`y_nsteps` (`int`): the number of steps
    """

    def __init__(self, x_start: float, x_stop: float, x_nsteps: int,
                 y_start: float, y_stop: float, y_nsteps: int,
                 x_label: str = "x", y_label: str = "y"):
        super(RasterScannerOneLNA, self).__init__(x_label, y_label)
        self.x_start = x_start
        self.x_stop = x_stop
        self.x_nsteps = x_nsteps
        self.delta_x = (x_stop - x_start) / x_nsteps
        self.y_start = y_start
        self.y_stop = y_stop
        self.y_nsteps = y_nsteps
        self.delta_y = (y_stop - y_start) / y_nsteps

        self.x = x_start
        self.y = y_start

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
        self.x = self.x_start
        self.y = self.y_start
        self.first_call = True

        self.x_current_step = 0
        self.y_current_step = 0
        self.y_direction = +1

class SpiralScannerOneLNA(Scanner2D):
    """A scanner that explores parameters on a grid "spirally",
    starting from a center and expanding step by step.

    Args:
    - `x_start`/`y_start` (`float`): the starting parameters
    - `x_step`/`y_step` (`float`): the distance between two steps
    - `n_arms` (`int`): the number of spiral arms to explore
    """
    def __init__(self, x_start: float, x_step: float,
                 y_start: float, y_step: float, n_arms: int,
                 x_label: str = "x", y_label: str = "y"):
        super(SpiralScannerOneLNA, self).__init__(x_label, y_label)
        self.x_start = x_start
        self.x_step = x_step
        self.y_start = y_start
        self.y_step = y_step
        self.idrain = x_start
        self.x = x_start
        self.y = y_start

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
        self.idrain = self.x_start
        self.y = self.y_start
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
    def __init__(self, test_name: str, scanners: Dict[str, Scanner2D], polarimeters: List[str] = [polarimeter for _, _, polarimeter in polarimeter_iterator()]):
        super(LNATestProcedure, self).__init__()
        self.test_name = test_name
        self.scanners = scanners
        self.polarimeters = polarimeters

        self._bias_file_name = Path(__file__).parent / "data" / "default_biases_warm.xlsx"
        self._setup_boards = {}      # A dictionary of SetupBoard objects (one for each board), used to reset LNA biases to default values during the procedure
        for board in set(map(get_polarimeter_board, polarimeters)):
            self._setup_boards[board] = SetupBoard(config=self.conf, post_command=self.command_emitter,
                board_name=board, bias_file_name=self._bias_file_name)

    def run(self):
        with StripTag(conn=self.conn, name=f"{self.test_name}"):
            # Turn on all polarimeters and set all the B legs to zero bias
            with StripTag(conn=self.conn, name=f"{self.test_name}_TURNON_LEG_HA"):
                with StripTag(conn=self.conn, name=f"{self.test_name}_TURNON_POLARIMETERS"):
                    self._turnon()
                with StripTag(conn=self.conn, name=f"{self.test_name}_ZERO_BIAS_LEG_HB"):
                    self._zero_bias(leg="HB")
        
            # Scan the leg A
            with StripTag(conn=self.conn, name=f"{self.test_name}_TEST_LEG_HA"):
                self._test_leg(leg="HA")

            # Reset the B leg biases and set A legs to zero bias
            with StripTag(conn=self.conn, name=f"{self.test_name}_TURNON_LEG_HB"):
                with StripTag(conn=self.conn, name=f"{self.test_name}_RESET_LEG_HB"):
                    for lna in "HB1", "HB2", "HB3":
                        self._reset_lna(lna)
                with StripTag(conn=self.conn, name=f"{self.test_name}_ZERO_BIAS_LEG_HA"):
                    self._zero_bias(leg="HA")

            # Scan the leg B
            with StripTag(conn=self.conn, name=f"{self.test_name}_TEST_LEG_HB"):
                self._test_leg(leg="HB")

            # Turn off all polarimeters
            with StripTag(conn=self.conn, name=f"{self.test_name}_TURNOFF"):
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
        scanner = self.scanners[lna]
        while scanner.next() == True:
            idrain = int(scanner.x)
            offset = int(scanner.y)
            with StripTag(conn=self.command_emitter, name=f"IDRAIN_{idrain}_OFFSET_{offset}", comment="Comment"):
                for polarimeter in self.polarimeters:
                    with StripTag(conn=self.command_emitter, name=f"{polarimeter}", comment=f"Comment"):
                        self.conn.set_id(polarimeter, lna, idrain)
                        self._set_offset(polarimeter, offset)
                wait_with_tag(conn=self.conn, seconds=5., name=f"STABLE_ACQUISITION")

        # Reset LNA
        with StripTag(conn=self.conn, name=f"{self.test_name}_RESET_LNA_{lna}"):
            self._reset_lna(lna)

    def _set_offset(self, polarimeter: str, offset: Union[List[int], int]):
        """Set the offset for all detectors on the specified polarimeter.
        
        Args:
        - `polarimeter` (`str`): the polarimeter to set the offset on.
        - `offset` (`List[int] | int`): a list containing the four values for the offsets (one for each detector),
            or a single value if it is equal for all detectors (must be between 0 and 4096)."""

        # If the offset is the same for each detector, make it into a 4 repeated element list
        if not isinstance(offset, list):
            offset = [offset] * 4

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
        for detector_idx in range(0, 4):    # QUESTION: are the fields adjacent? Is the for cycle needed?
            cmd["base_addr"] = f"DET{detector_idx}_OFFS"
            cmd["data"] = [offset[detector_idx]]
            self.conn.post_command(url, cmd)

    def _reset_lna(self, lna: str):
        """Reset the idrain and the offsets of the LNA to the default value for each polarimeter.
        
        Args:
        - `lna` (`str`): the LNA to reset."""
        for polarimeter in self.polarimeters:
            with StripTag(conn=self.command_emitter, name=f"{polarimeter}", comment=f"Comment"):
                setup_board = self._setup_boards[get_polarimeter_board(polarimeter)]
                setup_board.setup_ID(polarimeter, lna)
                default_offsets = [
                    setup_board .ib.get_biases(module_name=polarimeter, param_hk=f"DET{detector_idx}_OFFSET")
                    for detector_idx in range(0, 4)
                ]
                self._set_offset(polarimeter, default_offsets)


    def _zero_bias(self, leg: str):
        """Set vdrain and phase switch biases to zero for all LNAs on all polarimeters on the specified leg.
        
        Args:
        - `leg` (`str`): the leg to set to zero bias. Can be "HA" or "HB"."""
        for polarimeter in self.polarimeters:
            with StripTag(conn=self.command_emitter, name=f"{polarimeter}", comment=f"Comment"):
                for lna in leg + "1", leg + "2", leg + "3":
                    self.conn.set_vd(polarimeter, lna, value_adu=0)
                if leg == "HA":
                    phase_switches = (0, 1)
                elif leg == "HB":
                    phase_switches = (2, 3)
                for phsw_index in phase_switches:
                    self.conn.set_phsw_bias(polarimeter, phsw_index, vpin_adu=0, ipin_adu=0)

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

        turnonoff_proc = TurnOnOffProcedure(waittime_s=1.0, stable_acquisition_time_s=1.0,
            turnon=turnon, bias_file_name=self._bias_file_name)
        for polarimeter in self.polarimeters:
            turnonoff_proc.set_board_horn_polarimeter(new_board=get_polarimeter_board(polarimeter), new_horn=polarimeter, new_pol=None)
            turnonoff_proc.run_turnon(stable_acquisition_time_s=1.0)
            if turnon:
                self.conn.set_pol_mode(polarimeter, CLOSED_LOOP_MODE)   # QUESTION: is this in the right place?

        self.command_emitter.command_list += turnonoff_proc.get_command_list()
        turnonoff_proc.clear_command_list()

if __name__ == "__main__":
    config = LNAConfig(
        ha1=OneLNAConfig(
            offset_start=0, offset_stop=4096, offset_nsteps=5,
            idrain_start=2000, idrain_stop=7000, idrain_nsteps=5
        ),
        ha2=OneLNAConfig(
            offset_start=0, offset_stop=4096, offset_nsteps=5,
            idrain_start=3000, idrain_stop=13000, idrain_nsteps=5
        ),
        ha3=OneLNAConfig(
            offset_start=0, offset_stop=4096, offset_nsteps=5,
            idrain_start=5000, idrain_stop=21000, idrain_nsteps=5
        ),
        hb1=OneLNAConfig(
            offset_start=0, offset_stop=4096, offset_nsteps=5,
            idrain_start=2000, idrain_stop=7000, idrain_nsteps=5
        ),
        hb2=OneLNAConfig(
            offset_start=0, offset_stop=4096, offset_nsteps=5,
            idrain_start=3000, idrain_stop=13000, idrain_nsteps=5
        ),
        hb3=OneLNAConfig(
            offset_start=0, offset_stop=4096, offset_nsteps=5,
            idrain_start=5000, idrain_stop=21000, idrain_nsteps=5
        )
    )

    scanners = {}
    for lna in "HA1", "HA2", "HA3", "HB1", "HB2", "HB3":
        lna_config = getattr(config, lna.lower())
        scanners[lna] = GridScannerOneLNA(
            x_start=lna_config.idrain_start, x_stop=lna_config.idrain_stop, x_nsteps=lna_config.idrain_nsteps, x_label="idrain",
            y_start=lna_config.offset_start, y_stop=lna_config.offset_stop, y_nsteps=lna_config.offset_nsteps, y_label="offset"
        )

    #scanners["HA1"].plot()
    proc = LNATestProcedure(test_name="PRETUNING", scanners=scanners, polarimeters=["O1", "R2"])
    proc.run()
    proc.output_json()