# calibration/__init__.py --- class handling the conversion from ADU to phisical units and viceversa
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it

from collections import namedtuple
import logging as log
from pathlib import Path

import pandas as pd
import numpy as np

from config import Config
from striptease import (
    StripConnection,
    normalize_polarimeter_name,
    get_polarimeter_index,
    get_lna_num,
)

__all__ = [
    "CalibrationCurve",
    "physical_units_to_adu",
    "adu_to_physical_units",
    "CalibrationTables",
]

#: Linear calibration curve (from physical units to ADU) for an
#: housekeeping parameter.
#:
#: .. py:attribute:: slope
#:
#:    Floating-point value for the slope of the calibration curve
#:
#: .. py:attribute:: intercept
#:
#:    Floating-point value for the additive offset of the calibration curve
#:
#: .. py:attribute:: mul
#:
#:    Integer numerator of the slope of the calibration curve
#:
#: .. py:attribute:: div
#:
#:    Integer denominator of the slope of the calibration curve
#:
#: .. py:attribute:: add
#:
#:    Integer value for the additive offset of the calibration curve
#:
CalibrationCurve = namedtuple(
    "CalibrationCurve", ["slope", "intercept", "mul", "div", "add"]
)


def physical_units_to_adu(
    physical_value, calibration_curve: CalibrationCurve, step=1.0
):
    """Convert physical units to an ADU value, using a linear interpolation

    See also :meth:`.adu_to_physical_units`.

    Args:

        physical_value (float): the value to be converted; the measurement units
            depend on the kind of calibration curve used

        calibration_curve (CalibrationCurve): the calibration curve to use for
            the conversion from physical units to ADUs

        step (float): if provided, the physical value will be multiplied by
            this factor before the conversion. The default value is 1.0.

    Return:

        The physical value converted to ADU units, expressed as a
        positive integer number.

    """

    adu = physical_value * step * calibration_curve.slope + calibration_curve.intercept
    if adu < 0:
        adu = 0
    return int(adu + 0.5)


def adu_to_physical_units(adu_value, calibration_curve: CalibrationCurve):
    """Convert physical units to an ADU value, using a linear interpolation

    See also :meth:`.physical_units_to_adu`.

    Args:

        adu_value (int): the value to be converted

        calibration_curve (CalibrationCurve): the calibration curve to use for
            the conversion from physical units to ADUs

    Return:

        The physical value corresponding to the ADUs in `adu_value`.
        The measurement unit used in the result depends on the kind of
        calibration curve provided in `calibration_curve`.

    """
    return (adu_value - calibration_curve.intercept) / calibration_curve.slope


def read_board_xlsx(path):
    log.debug(f"Reading Excel file {path}")
    board = []
    excel_file_data = pd.read_excel(path, header=None, sheet_name=None)
    for cur_sheet in excel_file_data:
        cur_sheet_dict = {}
        pol = excel_file_data[cur_sheet].transpose()
        line_count = 0
        current_item = np.nan
        current_fit = np.nan
        current_chan = np.nan
        for r in pol:
            row = pol[r]
            if line_count <= 1:
                line_count += 1
                continue
            elif type(row[0]) == str and row[0].strip() == "ITEM":
                line_count += 1
                continue
            else:
                if type(row[0]) == str:
                    current_item = row[0].replace("\n", " ")
                if type(row[1]) == str:
                    current_fit = row[1].replace("\n", " ")
                if cur_sheet_dict.get(current_item) is None:
                    cur_sheet_dict[current_item] = {}
                if cur_sheet_dict[current_item].get(current_fit) is None:
                    cur_sheet_dict[current_item][current_fit] = {}
                cur_sheet_dict[current_item][current_fit][row[2]] = CalibrationCurve(
                    slope=float(row[3]),
                    intercept=float(row[4]),
                    mul=int(row[5]),
                    div=int(row[6]),
                    add=int(row[7]),
                )
            line_count += 1
        board.append(cur_sheet_dict)
    return board


def pol_name_to_dict_key(name: str):
    board_name = name[0]
    idx = int(name[1])

    return (board_name, idx)


class CalibrationTables(object):
    """Calibration tables used to convert HK ADUs into physical units and back

    This class loads the calibration tables for housekeeping parameters from
    a set of Excel files.

    You can pass a :class:`striptease.Config` class to this class. Not
    doing so is equivalent to the following code::

        from calibration import CalibrationTables
        from config import Config
        from striptease import StripConnection

        with StripConnection() as conn:
            conf = Config()
            conf.load(conn)

        cal_tables = CalibrationTables(conf)

    """

    def __init__(self, config=None):

        if not config:
            with StripConnection() as conn:
                config = Config()
                config.load(conn)

        self.conf = config

        # Each of these dictionaries associates a key in the form
        # (BOARD, POL_IDX) (like "R", 0) with a list of
        # CalibrationCurve objects
        self.calibration_curves = {
            "vdrain": {},
            "idrain": {},
            "vgate": {},
            "vphsw": {},
            "iphsw": {},
        }

        base_path = Path(__file__).parent.parent / "data"
        for cur_board in self.conf.boards:
            board_name = cur_board["name"]
            board_id = cur_board["id"]
            filename = base_path / self.conf.get_board_bias_file(board_id)
            try:
                board_conf = read_board_xlsx(filename)
            except Exception as exc:
                log.warning(
                    f"No suitable bias file for board {board_name} found: {exc}"
                )
                continue

            for polidx, pol in enumerate(board_conf):
                key = f"{board_name.upper()}{polidx}"
                self.calibration_curves["vdrain"][key] = pol["DRAIN"]["SET VOLTAGE"]
                self.calibration_curves["idrain"][key] = pol["DRAIN"]["SET CURRENT"]
                self.calibration_curves["vgate"][key] = pol["GATE"]["SET VOLTAGE"]
                self.calibration_curves["vphsw"][key] = pol["PIN DIODES"]["SET VOLTAGE"]
                self.calibration_curves["iphsw"][key] = pol["PIN DIODES"]["SET CURRENT"]

    def get_calibration_curve(self, polarimeter, hk, component):
        """Return a :class:`CalibrationCurve` object for an housekeeping parameter

        Args:

            polarimeter (str): the name of the polarimeter, e.g., `I4` or `W3`

            hk (str): one of the following strings:

                - ``vdrain``: drain voltage

                - ``idrain``: drain current

                - ``vgate``: gate voltage

                - ``vphsw``: voltage pin for a phase switch

                - ``iphsw``: current pin for a phase switch

            component (str): name of the component within the
                polarimeter. For LNAs, you can use whatever string
                works with :meth:`striptease.get_lna_num`. For phase
                switches, you must pass an integer number in the range
                0…3.

        Return:

            A :class:`.CalibrationCurve` object.

        """

        hk_key = hk.lower()
        polarimeter_id = normalize_polarimeter_name(polarimeter)
        if hk_key in ("vdrain", "idrain", "vgate"):
            component_id = get_lna_num(component)
        else:
            component_id = component

        return self.calibration_curves[hk_key][polarimeter_id][component_id]

    def adu_to_physical_units(self, polarimeter, hk, component, value):
        """Convert ADUs into physical units for an housekeeping parameter.

        The meaning of the parameters `polarimeter`, `hk`, and
        `component` is the same as in :meth:`.get_calibration_curve`.

        """
        calibration_curve = self.get_calibration_curve(polarimeter, hk, component)
        return adu_to_physical_units(value, calibration_curve=calibration_curve)

    def physical_units_to_adu(self, polarimeter, hk, component, value):
        """Convert physical units into ADUs for an housekeeping parameter.

        The meaning of the parameters `polarimeter`, `hk`, and
        `component` is the same as in :meth:`.get_calibration_curve`.

        """
        calibration_curve = self.get_calibration_curve(polarimeter, hk, component)
        return physical_units_to_adu(value, calibration_curve=calibration_curve)
