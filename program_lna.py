#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging as log
from pathlib import Path
from typing import Tuple
from abc import ABC, abstractmethod
from striptease import StripTag
from striptease.stripconn import wait_with_tag
from striptease.utilities import CLOSED_LOOP_MODE, get_polarimeter_board
from striptease.procedures import StripProcedure
from calibration import CalibrationTables
from turnon import TurnOnOffProcedure

#   |_|_|_|_|_|_|_|_
# v |_|_|_|_|_|_|_|_
# g |_|_|_|_|_|_|_|_
# a |_|_|_|_|_|_|_|_
# t |_|_|_|_|_|_|_|_
# e |_|_|_|_|_|_|_|_
#   |_|_|_|_|_|_|_|_
#      i d r a i n

class ScannerOneLNA(ABC):
    """Abstract base class representing a scanning strategy to explore the idrain-vgate parameter space for one LNA """

    def __init__(self):
        pass

    @abstractmethod
    def next(self) -> bool:
        """Return True if there is still a parameter pair to be tested, and set self.idrain and self.vgate accordingly.
        Return False otherwise."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset the scanner by setting `self.idrain` and `self.vgate` to the initial values."""
        pass

    def plot(self):
        """Show a plot of the scanning strategy."""
        from matplotlib import pyplot as plt
        import numpy as np
        res = []
        while self.next() == True:
            #print(idrain, vgate)
            res.append((self.idrain, self.vgate))

        res = np.asarray(res)
        plt.plot(res[:, 0], res[:, 1], "-o")
        plt.xlabel("idrain")
        plt.ylabel("vgate")
        plt.show()
        self.reset()

class RasterScannerOneLNA(ScannerOneLNA):
    """A scanner that explores parameters on a grid \"boustrophedically\",
    from left to right and viceversa alternating at every line.

    Args:
    - `idrain_min`/`vgate_min` (`float`): the starting parameters
    - `n_idrain_steps`/`n_vgate_steps` (`int`): the number of steps to explore for each bias
    - `idrain_step`/`vgate_step` (`float`): the distance between two steps
    """

    def __init__(self, idrain_min: float, n_idrain_steps: int, idrain_step: float,
                 vgate_min: float, n_vgate_steps: int, vgate_step: float):
        self.idrain_min = idrain_min
        self.n_idrain_steps = n_idrain_steps
        self.idrain_step = idrain_step
        self.vgate_min = vgate_min
        self.n_vgate_steps = n_vgate_steps
        self.vgate_step = vgate_step

        self.idrain = idrain_min
        self.vgate = vgate_min

        self.first_call = True
        self.n_idrain_step = 0
        self.n_vgate_step = 0
        self.idrain_direction = +1

    def next(self) -> bool:
        if self.first_call:
            self.first_call = False
            return True

        if self.n_idrain_step == self.n_idrain_steps:   # Last column in the row
            if self.n_vgate_step == self.n_vgate_steps: # Last row in the grid
                return False
            else:                                       # Not last row in the grid
                self.vgate += self.vgate_step
                self.n_vgate_step += 1
                self.idrain_direction *= -1             # Invert the direction of the idrain scan
                self.n_idrain_step = 0
                return True
        else:                                           # Not last column in the row
            self.idrain += self.idrain_direction * self.idrain_step
            self.n_idrain_step += 1
            return True
 
    def reset(self) -> None:
        self.idrain = self.idrain_min
        self.vgate = self.vgate_min
        self.first_call = True

        self.n_idrain_step = 0
        self.n_vgate_step = 0
        self.idrain_direction = +1

class SpiralScannerOneLNA(ScannerOneLNA):
    """A scanner that explores parameters on a grid "spirally",
    starting from a center and expanding step by step.

    Args:
    - `idrain_min`/`vgate_min` (`float`): the starting parameters
    - `idrain_step`/`vgate_step` (`float`): the distance between two steps
    - `n_arms` (`int`): the number of spiral arms to explore
    """
    def __init__(self, idrain_min: float, idrain_step: float,
                 vgate_min: float, vgate_step: float, n_arms: int):
        self.idrain_min = idrain_min
        self.idrain_step = idrain_step
        self.vgate_min = vgate_min
        self.vgate_step = vgate_step
        self.idrain = idrain_min
        self.vgate = vgate_min

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
            self.vgate += self.vgate_step   # Up
        elif self.n_arm % 4 == 2:
            self.idrain += self.idrain_step # Right
        elif self.n_arm % 4 == 3:
            self.vgate -= self.vgate_step   # Down
        elif self.n_arm % 4 == 0:
            self.idrain -= self.idrain_step # Left
        
        self.step += 1
        if self.step >= self.steps:     # End of the arm
            self.step = 1
            self.steps += 1
            self.n_arm += 1

        return True
 
    def reset(self) -> None:
        self.idrain = self.idrain_min
        self.vgate = self.vgate_min
        self.first_call = True

        self.n_arm = 1
        self.step = 1
        self.steps = 1

class OneLNATestProcedure(StripProcedure):
    """Procedure to test one LNA changing idrain and vgate according to a scanning strategy.
    
    Args:
    - `test_name` (`str`): the name of the test, used in tags
    - `scanner` (`ScannerOneLNA`): the scanner that provides the scanning strategy
    - `polarimeter` (`str`): the polarimeter to test
    - `lna` (`str`): the LNA to test
    """
    def __init__(self, test_name: str, scanner: ScannerOneLNA, polarimeter: str, lna: str):
        super(OneLNATestProcedure, self).__init__()
        self.test_name = test_name
        self.scanner = scanner
        self.polarimeter = polarimeter
        self.lna = lna
        self.board = get_polarimeter_board(self.polarimeter)
        self.bias_file_name = Path(__file__).parent / "data" / "default_biases_warm.xlsx"
        self.calibration = CalibrationTables()

    def run(self):
        turnon_proc = TurnOnOffProcedure(waittime_s=1.0, stable_acquisition_time_s=1.0,
                                         turnon=True, bias_file_name=self.bias_file_name)
        turnon_proc.set_board_horn_polarimeter(new_board=self.board, new_horn=self.polarimeter, new_pol=None)
        turnon_proc.run_turnon(stable_acquisition_time_s=1.0)
        self.command_emitter.command_list += turnon_proc.get_command_list()
        turnon_proc.clear_command_list()

        self.conn.set_pol_mode(self.polarimeter, CLOSED_LOOP_MODE)
        
        while scanner.next() == True:
            with StripTag(conn=self.command_emitter,
                          name=f"{self.test_name}_{self.polarimeter}_IDRAIN_{scanner.idrain:.2f}_VGATE_{scanner.vgate:.2f}",
                          comment=f"Comment"):
                idrain = self.calibration.physical_units_to_adu(self.polarimeter, "idrain", self.lna, scanner.idrain)
                self.conn.set_id(self.polarimeter, self.lna, idrain)
                vgate = self.calibration.physical_units_to_adu(self.polarimeter, "vgate", self.lna, scanner.vgate)
                self.conn.set_vd(self.polarimeter, self.lna, vgate)
                self.conn.wait(seconds=5 * 60.)

        wait_with_tag(conn=self.conn, seconds=1.,
                      name=f"{self.test_name}_{self.polarimeter}_END")


        turnoff_proc = TurnOnOffProcedure(waittime_s=1.0, stable_acquisition_time_s=1.0,
                                         turnon=False, bias_file_name=self.bias_file_name)
        turnoff_proc.set_board_horn_polarimeter(new_board=self.board, new_horn=self.polarimeter, new_pol=None)
        turnoff_proc.run()
        self.command_emitter.command_list += turnoff_proc.get_command_list()
        turnoff_proc.clear_command_list()

if __name__ == "__main__":
    #scanner = RasterScannerOneLNA(0., 10, 1., 0., 20, 1.)
    scanner = SpiralScannerOneLNA(0., 1., 0., 1., 20)
    scanner.plot()
    proc = OneLNATestProcedure("TEST", scanner, "I1", "HA1")
    proc.run()
    proc.output_json()