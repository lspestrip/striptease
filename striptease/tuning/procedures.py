# -*- encoding: utf-8 -*-

from __future__ import annotations
from abc import ABC, abstractmethod
from copy import copy
from enum import IntEnum
import functools
from typing import Callable, Dict, List, Optional, Tuple, Union

from calibration import CalibrationTables
from striptease.procedures import StripProcedure
from striptease.stripconn import StripTag, wait_with_tag
from striptease.utilities import (
    STRIP_BOARD_NAMES,
    PhswPinMode,
    get_polarimeter_board,
    polarimeter_iterator,
)
from .scanners import Scanner1D, Scanner2D
from turnon import SetupBoard, TurnOnOffProcedure

DEFAULT_ACQUISITION_TIME_S = 5
DEFAULT_WAIT_TIME_S = 1


class StripState(IntEnum):
    """An enum that represents the current state of Strip."""

    OFF = 0  # All required boards are turned off
    DEFAULT = 1  # All required boards are turned on with default biases
    ZERO_BIAS = 2  # All required boards are turned on with zero biases
    ON = 3  # All required boards are turned on with unspecified biases


def parse_state(state: str) -> StripState:
    """Return a StripState corresponding to the input string.

    Args:

    - `state` (`str`): one of "on", "off", "zero-bias", "default."."""
    if state == "on":
        return StripState.ON
    elif state == "off":
        return StripState.OFF
    elif state == "zero-bias":
        return StripState.ZERO_BIAS
    elif state == "default":
        return StripState.DEFAULT
    raise ValueError(
        f'state must be one of "on", "off", "zero-bias", "default". Got {state} instead.'
    )


class TuningProcedure(StripProcedure, ABC):
    """An abstract class representing a tuning procedure. It decorates the run method of child classes adding a turnon and turnoff procedure,
    if required by the start and end states.

    Args:

    - `start_state`(`StripState`): the state before the procedure is run.

    - `end_state` (`StripState`): the state to leave Strip after the procedure.

    - `turnon_zero_bias` (`bool`): True if the turnon procedure is to be run with zero bias flag.

    - `tag_comment` (`str`): the comment of the tag surrounding the procedure

    - `test_name`: `str`: the name of the test.

    - `test_polarimeters` (`List[str]`): the polarimeters to test.

    - `turnon_polarimeters` (`Union[List[str], None]`): the polarimeters to turnon.

    - `bias_file_name` (`str`): the file containing the default biases.

    - `stable_acquisition_time` (`int`): the time in seconds to do stable acquisition.

    - `turnon_acqisition_time` (`int`): the time in seconds to do acquisition during turnon.

    - `turnon_wait_time` (`int`): the time in seconds to wait during turnon.

    - `message` (`str`): the log message for the procedure (if empty, no log command is added to the json).

    - `hk_scan_boards` (`List[str]`): the boards to scan housekeeping on.

    - `open_loop` (`bool`): True if the procedure is run in open loop mode.
    """

    def __init__(
        self,
        start_state: StripState,
        end_state: StripState,
        turnon_zero_bias: bool,
        tag_comment: str,
        test_name: str,
        test_polarimeters: List[str] = [
            polarimeter for _, _, polarimeter in polarimeter_iterator()
        ],
        turnon_polarimeters: Union[List[str], None] = None,
        bias_file_name: str = "data/default_biases_warm.xlsx",
        stable_acquisition_time=DEFAULT_ACQUISITION_TIME_S,
        turnon_acqisition_time=DEFAULT_WAIT_TIME_S,
        turnon_wait_time=DEFAULT_WAIT_TIME_S,
        message="",
        hk_scan_boards=STRIP_BOARD_NAMES,
        open_loop=False,
        command_emitter=None,
    ):
        super(TuningProcedure, self).__init__()

        self.test_name = test_name
        self.test_polarimeters = list(
            dict.fromkeys(test_polarimeters)
        )  # Remove duplicate polarimeters keeping order
        if turnon_polarimeters:
            self.turnon_polarimeters = list(
                dict.fromkeys(turnon_polarimeters + test_polarimeters)
            )  # Remove duplicate polarimeters keeping order
        else:
            self.turnon_polarimeters = list(
                dict.fromkeys(test_polarimeters)
            )  # Remove duplicate polarimeters keeping order

        self.bias_file_name = bias_file_name
        self.stable_acquisition_time = stable_acquisition_time
        self.turnon_acqisition_time = turnon_acqisition_time
        self.turnon_wait_time = turnon_wait_time
        self.hk_scan_boards = hk_scan_boards
        self.message = message

        self.start_state = start_state
        self.end_state = end_state
        self.open_loop = open_loop

        if command_emitter is not None:
            self.command_emitter = command_emitter

        self._test_boards = set(map(get_polarimeter_board, self.test_polarimeters))
        self._setup_boards = (
            {}
        )  # A dictionary of SetupBoard objects (one for each board), used to reset LNA biases to default values during the procedure
        for board in self._test_boards:
            self._setup_boards[board] = SetupBoard(
                config=self.conf,
                post_command=self.command_emitter,
                board_name=board,
                bias_file_name=self.bias_file_name,
            )

        self._calibr = CalibrationTables()

        # Decorate self.run function (we cannot use the @ syntax since we wish to decorate all run functions in child classes)
        self.run = self._run_with_turnonoff(self.run, turnon_zero_bias, tag_comment)

    @abstractmethod
    def run(self):
        ...

    def _run_with_turnonoff(
        self, run: Callable, turnon_zero_bias: bool, tag_comment: str
    ):
        """Decorate run methods adding a turnon and turnoff procedure if self.start_state and self.end_state are off.

        Args:

        - `run` (`Callable`): the procedure method to decorate (the run method of child classes).

        - `turnon_zero_bias` (`bool`): `True` if the turnon procedure needs to set polarimeters to zero bias, `False` otherwise.

        - `tag_comment` (`str`): the comment for the tag surrounding the whole procedure."""

        @functools.wraps(run)
        def wrapper():
            with StripTag(
                conn=self.conn, name=f"{self.test_name}", comment=tag_comment
            ):
                if self.message != "":
                    self.conn.log(message=self.message, level="INFO")
                if self.start_state == StripState.OFF:
                    # Turn on the boards
                    with StripTag(
                        conn=self.conn,
                        name=f"{self.test_name}_TURNON_POLARIMETERS",
                        comment=f"Turnon polarimeters {self.turnon_polarimeters}.",
                    ):
                        self._turnon(zero_bias=turnon_zero_bias)

                run()  # Run the procedure defined by child classes

                if self.end_state == StripState.OFF:
                    # Turn off the boards
                    with StripTag(
                        conn=self.conn,
                        name=f"{self.test_name}_TURNOFF",
                        comment="Turn off polarimeters.",
                    ):
                        self._turnoff()

        return wrapper  # Return the decorated function

    def _reset_lna(self, lna: str):
        """Reset the vdrain and idrain or vgate of the required LNA and the offsets to the default value for each polarimeter.

        Args:

        - `lna` (`str`): the LNA to reset."""
        for polarimeter in self.test_polarimeters:
            with StripTag(
                conn=self.command_emitter,
                name=f"{self.test_name}_RESET_LNA_{lna}_{polarimeter}",
                comment=f"Reset LNA {lna}: polarimeter {polarimeter}.",
            ):
                setup_board = self._setup_boards[get_polarimeter_board(polarimeter)]
                setup_board.setup_VD(polarimeter, lna)
                if self.open_loop:
                    setup_board.setup_VG(polarimeter, lna)
                else:
                    setup_board.setup_ID(polarimeter, lna)
                self._reset_offset(polarimeter)

    def _reset_leg(self, leg: str):
        """Reset all the LNAs in a leg, and the offsets, for each polarimeter.

        Args:

        - `leg` (`str`): the leg to reset. Can be "HA" or "HB"."""
        for lna in map(lambda x: leg + x, ("1", "2", "3")):
            self._reset_lna(lna)

    def _reset_offset(self, polarimeter: str):
        """Reset offsets of the polarimeter to default values.

        Args:

        - `polarimeter` (`str`): the polarimeter to reset."""
        setup_board = self._setup_boards[get_polarimeter_board(polarimeter)]
        default_offsets = [
            setup_board.ib.get_biases(
                module_name=polarimeter, param_hk=f"DET{detector_idx}_OFFSET"
            )
            for detector_idx in range(0, 4)
        ]
        self.conn.set_offsets(polarimeter, default_offsets)

    def _test(
        self,
        func: Callable[[TuningProcedure, str, int], Union[Scanner1D, Scanner2D]],
        tag: str,
        comment: str,
    ):
        """Run the test described by the func argument on each of the polarimeters to test.

        Args:

        - `func` (`Callable`): the test to run. Args: self, polarimeter (to run the test on), step. Returns a scanner with the state of the test.

        - `tag` (`str`): the tag to surround the test steps with.

        - `comment` (`str`): the comment for the tag."""
        step = 0
        test_polarimeters = copy(self.test_polarimeters)
        while test_polarimeters != []:
            next_test_polarimeters = []
            with StripTag(
                conn=self.command_emitter,
                name=f"{tag}_{step}",
                comment=f"{comment}: step {step}",
            ):
                for polarimeter in test_polarimeters:
                    scanner = func(self, polarimeter, step)
                    if (
                        scanner.next() is True
                    ):  # The scan is not over for this polarimeter: add it to the next test list
                        next_test_polarimeters.append(polarimeter)
                self.conn.set_hk_scan(
                    boards=self.hk_scan_boards
                )  # QUESTION: dynamic hk_scan boards or not?
                wait_with_tag(
                    conn=self.conn,
                    seconds=self.stable_acquisition_time,
                    name=f"{tag}_{step}_ACQ",
                    comment=f"{comment}: step {step}, stable acquisition",
                )
            test_polarimeters = next_test_polarimeters
            step += 1

    def _get_phsw_from_leg(self, leg: str) -> Tuple[int, int]:
        """Return a tuple with the phsw indexes on the leg.

        Args:

        - `leg` (`str`): the leg of the phase switches (can be "HA" or "HB")."""
        if leg == "HA":
            return (0, 1)
        elif leg == "HB":
            return (2, 3)
        raise (ValueError(f'leg must be one of "HA" or "HB". Got {leg} instead.'))

    def _zero_bias(self, leg: str):
        """Set vgate (and idrain if in closed loop) for all LNAs and phase switch biases to zero on all polarimeters on the specified leg.

        Args:

        - `leg` (`str`): the leg to set to zero bias. Can be "HA" or "HB"."""
        for polarimeter in self.test_polarimeters:
            with StripTag(
                conn=self.command_emitter,
                name=f"{self.test_name}_ZERO_BIAS_LEG_{leg}_{polarimeter}",
                comment=f"Set leg {leg} to zero bias: polarimeter {polarimeter}.",
            ):
                for lna in leg + "1", leg + "2", leg + "3":
                    self.conn.set_vd(polarimeter, lna, value_adu=0)
                    if not self.open_loop:
                        self.conn.set_id(polarimeter, lna, value_adu=0)
                for phsw_index in self._get_phsw_from_leg(leg):
                    self.conn.set_phsw_status(
                        polarimeter, phsw_index, PhswPinMode.STILL_NO_SIGNAL
                    )

    def _turnon(self, zero_bias: bool):
        """Turn on all the polarimeters specified in self.polarimeters.

        Args:

        - `zero_bias` (`bool`): True if the turnon is to be done with zero bias, False if with default values."""
        self._turnonoff(turnon=True, zero_bias=zero_bias)

    def _turnoff(self):
        """Turn off all polarimeters."""
        self._turnonoff(turnon=False)

    def _turnonoff(self, turnon: bool, zero_bias: bool = False):
        """Turn on or off all polarimeters.

        Args:

        - `turnon` (`bool`): True if turnon, False if turnoff.

        - `zero_bias` (`bool`): True if the turnon is to be done with zero bias, False if with default values. Not used in turnoff."""

        turnonoff_proc = TurnOnOffProcedure(
            waittime_s=self.turnon_wait_time,
            stable_acquisition_time_s=self.turnon_acqisition_time,
            turnon=turnon,
            bias_file_name=self.bias_file_name,
            zero_bias=zero_bias,
            closed_loop=not self.open_loop,
        )
        for polarimeter in self.turnon_polarimeters:
            turnonoff_proc.set_board_horn_polarimeter(
                new_board=get_polarimeter_board(polarimeter),
                new_horn=polarimeter,
                new_pol=None,
            )
            turnonoff_proc.run()
            self.command_emitter.command_list += turnonoff_proc.get_command_list()
            turnonoff_proc.clear_command_list()


class LNAPretuningProcedure(TuningProcedure):
    """A procedure that sets idrain and offset for polarimeters one LNA at a time, with only one leg active.

    Args:

    - `test_name` (`str`): the name of the test, used in tags

    - `scanners` (`Dict[str, ScannerOneLNA]`): a dictionary that associates to each LNA the scanner to use

    - `test_polarimeters` (`List[str]`): the polarimeters to test.

    - `turnon_polarimeters` (`Union[List[str], None]`): the polarimeters to turnon.

    - `bias_file_name` (`str`): the file containing the default biases.

    - `stable_acquisition_time` (`int`): the time in seconds to do stable acquisition.

    - `turnon_acqisition_time` (`int`): the time in seconds to do acquisition during turnon.

    - `turnon_wait_time` (`int`): the time in seconds to wait during turnon.

    - `message` (`str`): the log message for the procedure (if empty, no log command is added to the json).

    - `hk_scan_boards` (`List[str]`): the boards to scan housekeeping on.

    - `phsw_status` (`str`): the status of the phase switches (can be "77", "56" or "65").

    - `open_loop` (`bool`): True if the procedure is run in open loop mode.

    - `start_state`(`StripState`): the state before the procedure is run.

    - `end_state` (`StripState`): the state to leave Strip after the procedure.
    """

    def __init__(
        self,
        test_name: str,
        scanners: Dict[str, Dict[str, Union[Scanner1D, Scanner2D]]],
        test_polarimeters: List[str] = [
            polarimeter for _, _, polarimeter in polarimeter_iterator()
        ],
        turnon_polarimeters: Union[List[str], None] = None,
        bias_file_name: str = "data/default_biases_warm.xlsx",
        stable_acquisition_time=DEFAULT_ACQUISITION_TIME_S,
        turnon_acqisition_time=DEFAULT_WAIT_TIME_S,
        turnon_wait_time=DEFAULT_WAIT_TIME_S,
        message="",
        hk_scan_boards=STRIP_BOARD_NAMES,
        phsw_status="77",
        open_loop=False,
        start_state=StripState.OFF,
        end_state=StripState.ZERO_BIAS,
        command_emitter=None,
    ):
        super(LNAPretuningProcedure, self).__init__(
            start_state=start_state,
            end_state=end_state,
            turnon_zero_bias=False,
            tag_comment=f"{test_name} test: scan idrain and detector offset on polarimeters {test_polarimeters}, "
            f"with {turnon_polarimeters} turned on.",
            test_name=test_name,
            test_polarimeters=test_polarimeters,
            turnon_polarimeters=turnon_polarimeters,
            bias_file_name=bias_file_name,
            stable_acquisition_time=stable_acquisition_time,
            turnon_acqisition_time=turnon_acqisition_time,
            turnon_wait_time=turnon_wait_time,
            message=message,
            hk_scan_boards=hk_scan_boards,
            open_loop=open_loop,
            command_emitter=command_emitter,
        )
        self.scanners = scanners
        self.phsw_status = phsw_status

        if open_loop:
            self._previous_vgate: Dict[str, Optional[int]] = {
                polarimeter: None for polarimeter in test_polarimeters
            }
        else:
            self._previous_idrain: Dict[str, Optional[int]] = {
                polarimeter: None for polarimeter in test_polarimeters
            }
        self._previous_offset = {polarimeter: None for polarimeter in test_polarimeters}

    def run(self):
        with StripTag(
            conn=self.conn,
            name=f"{self.test_name}_SETUP_LEG_HA",
            comment="Set leg HA to default and HB to zero bias if needed.",
        ):
            with StripTag(
                conn=self.conn,
                name=f"{self.test_name}_RESET_LEG_HA",
                comment=f"Turnon polarimeters {self.turnon_polarimeters}.",
            ):
                self._reset_phsw(leg="HA")
                if (
                    self.start_state != StripState.OFF
                    and self.start_state != StripState.DEFAULT
                ):
                    self._reset_leg(leg="HA")
            if self.start_state != StripState.ZERO_BIAS:
                with StripTag(
                    conn=self.conn,
                    name=f"{self.test_name}_ZERO_BIAS_LEG_HB",
                    comment="Set leg HB to zero bias.",
                ):
                    self._zero_bias(leg="HB")

            self.conn.set_hk_scan(boards=self.hk_scan_boards)
            wait_with_tag(
                conn=self.conn,
                seconds=self.stable_acquisition_time,
                name=f"{self.test_name}_SETUP_LEG_HA_ACQ",
                comment="Turnon leg HA: stable acquisition.",
            )

        # Scan the leg A
        with StripTag(
            conn=self.conn,
            name=f"{self.test_name}_TEST_LEG_HA",
            comment="Run test on leg HA.",
        ):
            self._test_leg(leg="HA")

        # Reset the B leg biases and set A legs to zero bias
        with StripTag(
            conn=self.conn,
            name=f"{self.test_name}_SETUP_LEG_HB",
            comment="Reset leg HB and set leg HA to zero bias.",
        ):
            with StripTag(
                conn=self.conn,
                name=f"{self.test_name}_RESET_LEG_HB",
                comment="Reset leg HB to default biases.",
            ):
                self._reset_phsw(leg="HB")
                self._reset_leg(leg="HB")
            with StripTag(
                conn=self.conn,
                name=f"{self.test_name}_ZERO_BIAS_LEG_HA",
                comment="Set leg HA to zero bias.",
            ):
                self._zero_bias(leg="HA")

            self.conn.set_hk_scan(boards=self.hk_scan_boards)
            wait_with_tag(
                conn=self.conn,
                seconds=self.stable_acquisition_time,
                name=f"{self.test_name}_SETUP_LEG_HB_ACQ",
                comment="Turnon leg HB: stable acquisition.",
            )

        # Scan the leg B
        with StripTag(
            conn=self.conn,
            name=f"{self.test_name}_TEST_LEG_HB",
            comment="Run test on leg HB.",
        ):
            self._test_leg(leg="HB")

        if self.end_state == StripState.ZERO_BIAS:
            # Set leg B to zero bias
            with StripTag(
                conn=self.conn,
                name=f"{self.test_name}_ZERO_BIAS_LEG_HB",
                comment="Set leg HB to zero bias.",
            ):
                self._zero_bias(leg="HB")

        if self.end_state == StripState.DEFAULT:
            with StripTag(
                conn=self.conn,
                name=f"{self.test_name}_RESET_LEG_HA",
                comment="Reset leg HA to default biases.",
            ):
                self._reset_phsw(leg="HA")
                self._reset_leg(leg="HA")

    def _test_leg(self, leg: str):
        """Run the test on the specified leg on all polarimeters, from LNA 1 to 3.

        Args:

        - `leg` (`str`): the leg to run the test on. Can be "HA" or "HB"."""
        for lna in (f"{leg}{i}" for i in range(1, 4)):
            # Test LNA
            with StripTag(conn=self.conn, name=f"{self.test_name}_TEST_{lna}"):
                if self.open_loop:

                    def func(self: LNAPretuningProcedure, polarimeter: str, step: int):
                        return self._test_open_loop(polarimeter, step, lna)

                else:

                    def func(self: LNAPretuningProcedure, polarimeter: str, step: int):
                        return self._test_closed_loop(polarimeter, step, lna)

                self._test(
                    func=func,
                    tag=f"{self.test_name}_TEST_LNA_{lna}",
                    comment=f"Test LNA {lna}",
                )
            # Reset LNA
            with StripTag(
                conn=self.conn,
                name=f"{self.test_name}_RESET_LNA_{lna}",
                comment=f"Reset LNA {lna} to default biases.",
            ):
                self._reset_lna(lna)

    def _test_closed_loop(self, polarimeter: str, step: int, lna: str) -> Scanner2D:
        """Test one LNA on all polarimeters changing idrain and offset according to a scanning strategy.

        Args:

        - `polarimeter` (`str`): the polarimeter to test.

        - `step` (`int`): the current step of the test.

        - `lna` (`str`): the LNA to test.
        """

        scanner = self.scanners[polarimeter][lna]
        assert isinstance(scanner, Scanner2D)
        idrain = int(scanner.x)
        idrain_step = scanner.index[0]
        offset = scanner.y.astype(int)
        offset_step = scanner.index[1]
        with StripTag(
            conn=self.command_emitter,
            name=f"{self.test_name}_TEST_{lna}_{step}_{polarimeter}_{idrain_step}_{offset_step}",
            comment=f"Test LNA {lna}: step {step}, polarimeter {polarimeter}:"
            f"idrain={idrain}, offset={offset}.",
        ):
            if idrain != self._previous_idrain[polarimeter]:
                idrain_adu = self._calibr.physical_units_to_adu(
                    polarimeter=polarimeter, hk="idrain", component=lna, value=idrain
                )
                self.conn.set_id(polarimeter, lna, idrain_adu)
                self._previous_idrain[polarimeter] = idrain
            if any(offset != self._previous_offset[polarimeter]):
                self.conn.set_offsets(polarimeter, offset)
                self._previous_offset[polarimeter] = offset
        return scanner

    def _test_open_loop(self, polarimeter, step, lna: str) -> Scanner2D:
        """Test one LNA on all polarimeters changing vgate and offset according to a scanning strategy.

        Args:

        - `polarimeter` (`str`): the polarimeter to test.

        - `step` (`int`): the current step of the test.

        - `lna` (`str`): the LNA to test.
        """

        scanner = self.scanners[polarimeter][lna]
        assert isinstance(scanner, Scanner2D)
        vgate = int(scanner.x)
        vgate_step = scanner.index[0]
        offset = scanner.y.astype(int)
        offset_step = scanner.index[1]
        with StripTag(
            conn=self.command_emitter,
            name=f"{self.test_name}_TEST_{lna}_{step}_{polarimeter}_{vgate_step}_{offset_step}",
            comment=f"Test LNA {lna}: step {step}, polarimeter {polarimeter}:"
            f"vgate={vgate}, offset={offset}.",
        ):
            if vgate != self._previous_vgate[polarimeter]:
                vgate_adu = self._calibr.physical_units_to_adu(
                    polarimeter=polarimeter, hk="vgate", component=lna, value=vgate
                )
                self.conn.set_vg(polarimeter, lna, vgate_adu)
                self._previous_vgate[polarimeter] = vgate
            if any(offset != self._previous_offset[polarimeter]):
                self.conn.set_offsets(polarimeter, offset)
                self._previous_offset[polarimeter] = offset
        return scanner

    def _reset_phsw(self, leg: str):
        """Reset phase switches of all tested polarimeters on the requested leg according to self.phsw_status.

        Args:

        - `leg` (`str`): the leg of the phase switches to reset (can be "HA" or "HB")."""
        for polarimeter in self.test_polarimeters:
            with StripTag(
                conn=self.command_emitter,
                name=f"{self.test_name}_RESET_PHSW_{leg}_{polarimeter}",
                comment=f"Reset phase switch on leg {leg}: polarimeter {polarimeter}.",
            ):
                phase_switches = self._get_phsw_from_leg(leg)
                if self.phsw_status == "77":
                    for phsw_index in phase_switches:
                        self.conn.set_phsw_status(
                            polarimeter, phsw_index, PhswPinMode.NOMINAL_SWITCHING
                        )
                elif self.phsw_status == "56":
                    self.conn.set_phsw_status(
                        polarimeter, phase_switches[0], PhswPinMode.STILL_SIGNAL
                    )
                    self.conn.set_phsw_status(
                        polarimeter, phase_switches[1], PhswPinMode.STILL_NO_SIGNAL
                    )
                elif self.phsw_status == "65":
                    self.conn.set_phsw_status(
                        polarimeter, phase_switches[0], PhswPinMode.STILL_NO_SIGNAL
                    )
                    self.conn.set_phsw_status(
                        polarimeter, phase_switches[1], PhswPinMode.STILL_SIGNAL
                    )


class OffsetTuningProcedure(TuningProcedure):
    """A procedure that sets offsets for polarimeters with everything at zero bias.

    Args:

    - `test_name` (`str`): the name of the test, used in tags

    - `scanners` (`Dict[str, ScannerOneLNA]`): a dictionary that associates to each LNA the scanner to use

    - `test_polarimeters` (`List[str]`): the polarimeters to test.

    - `turnon_polarimeters` (`Union[List[str], None]`): the polarimeters to turnon.

    - `bias_file_name` (`str`): the file containing the default biases.

    - `stable_acquisition_time` (`int`): the time in seconds to do stable acquisition.

    - `turnon_acqisition_time` (`int`): the time in seconds to do acquisition during turnon.

    - `turnon_wait_time` (`int`): the time in seconds to wait during turnon.

    - `message` (`str`): the log message for the procedure (if empty, no log command is added to the json).

    - `hk_scan_boards` (`List[str]`): the boards to scan housekeeping on.

    - `open_loop` (`bool`): True if the procedure is run in open loop mode.

    - `start_state`(`StripState`): the state before the procedure is run.

    - `end_state` (`StripState`): the state to leave Strip after the procedure.
    """

    def __init__(
        self,
        test_name: str,
        scanners: Dict[str, Dict[str, Union[Scanner1D, Scanner2D]]],
        test_polarimeters: List[str] = [
            polarimeter for _, _, polarimeter in polarimeter_iterator()
        ],
        turnon_polarimeters: Union[List[str], None] = None,
        bias_file_name: str = "data/default_biases_warm.xlsx",
        stable_acquisition_time=DEFAULT_ACQUISITION_TIME_S,
        turnon_acqisition_time=DEFAULT_WAIT_TIME_S,
        turnon_wait_time=DEFAULT_WAIT_TIME_S,
        message="",
        hk_scan_boards=STRIP_BOARD_NAMES,
        open_loop=False,
        start_state=StripState.OFF,
        end_state=StripState.ZERO_BIAS,
        command_emitter=None,
    ):
        super(OffsetTuningProcedure, self).__init__(
            start_state=start_state,
            end_state=end_state,
            turnon_zero_bias=True,
            tag_comment=f"{test_name} test: scan idrain and detector offset on polarimeters {test_polarimeters}, "
            f"with {turnon_polarimeters} turned on.",
            test_name=test_name,
            test_polarimeters=test_polarimeters,
            turnon_polarimeters=turnon_polarimeters,
            bias_file_name=bias_file_name,
            stable_acquisition_time=stable_acquisition_time,
            turnon_acqisition_time=turnon_acqisition_time,
            turnon_wait_time=turnon_wait_time,
            message=message,
            hk_scan_boards=hk_scan_boards,
            open_loop=open_loop,
            command_emitter=command_emitter,
        )
        self.scanners = scanners

    def run(self):
        if (
            self.start_state != StripState.OFF
            and self.start_state != StripState.ZERO_BIAS
        ):
            # Set legs to zero bias
            with StripTag(
                conn=self.conn,
                name=f"{self.test_name}_ZERO_BIAS_LEG_HA",
                comment="Set leg HA to zero bias.",
            ):
                self._zero_bias(leg="HA")
            with StripTag(
                conn=self.conn,
                name=f"{self.test_name}_ZERO_BIAS_LEG_HB",
                comment="Set leg HB to zero bias.",
            ):
                self._zero_bias(leg="HB")

        wait_with_tag(conn=self.conn, name=f"{self.test_name}_PRE_ACQ", seconds=120)
        # Perform a detector offset test
        with StripTag(
            conn=self.conn,
            name=f"{self.test_name}_TEST_DET_OFFS",
            comment="Perform a detector offset test.",
        ):

            def func(self: OffsetTuningProcedure, polarimeter: str, step: int):
                return self._test_offset(polarimeter, step)

            self._test(
                func=func,
                tag=f"{self.test_name}_TEST_DET_OFFS",
                comment="Test detector offset",
            )

        if self.end_state == StripState.ZERO_BIAS:
            with StripTag(
                conn=self.conn,
                name=f"{self.test_name}_ZERO_OFFS",
                comment="Set offsets to zero.",
            ):
                for polarimeter in self.test_polarimeters:
                    with StripTag(
                        conn=self.conn,
                        name=f"{self.test_name}_ZERO_OFFS_{polarimeter}",
                        comment=f"Set offsets to zero. Polarimeter {polarimeter}.",
                    ):
                        self.conn.set_offsets(polarimeter, [0, 0, 0, 0])

        if self.end_state == StripState.DEFAULT:
            # Set legs to default bias
            with StripTag(
                conn=self.conn,
                name=f"{self.test_name}_RESET_LEG_HA",
                comment="Set leg HA to default bias.",
            ):
                self._reset_leg(leg="HA")
            with StripTag(
                conn=self.conn,
                name=f"{self.test_name}_RESET_LEG_HB",
                comment="Set leg HB to default bias.",
            ):
                self._reset_leg(leg="HB")

        wait_with_tag(conn=self.conn, name=f"{self.test_name}_POST_ACQ", seconds=120)

    def _test_offset(self, polarimeter, step) -> Scanner1D:
        """Test offsets on all polarimeters changing them according to a scanning strategy.

        Args:

        - `polarimeter` (`str`): the polarimeter to test.

        - `step` (`int`): the current step of the test.
        """
        scanner = self.scanners[polarimeter]["Offset"]
        assert isinstance(scanner, Scanner1D)
        offset = scanner.x.astype(int)
        with StripTag(
            conn=self.command_emitter,
            name=f"{self.test_name}_TEST_DET_OFFS_{step}_{polarimeter}",
            comment=f"Test detector offset: step {step}, polarimeter {polarimeter}, "
            f"offset={offset}",
        ):
            self.conn.set_offsets(polarimeter, offset)
        return scanner
