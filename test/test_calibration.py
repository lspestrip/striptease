# -*- encoding: utf-8 -*-

from calibration import CalibrationTables
from web.rest.errors import InputLogin


def test_calibration():
    try:
        cal_tables = CalibrationTables()
    except InputLogin:
        # We're probably running on Travis, so just forget about it
        return

    assert cal_tables.physical_units_to_adu("R0", "idrain", "HA1", 1000) == 180
    # W3 belongs to the R board
    assert cal_tables.physical_units_to_adu("W3", "vdrain", "HA1", 156) == 256
