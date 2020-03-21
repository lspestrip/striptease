# -*- encoding: utf-8 -*-

from calibration import CalibrationTables


def test_calibration():
    cal_tables = CalibrationTables()
    assert cal_tables.physical_units_to_adu("R0", "idrain", "HA1", 1000) == 180
    # W3 belongs to the R board
    assert cal_tables.physical_units_to_adu("W3", "vdrain", "HA1", 156) == 256
