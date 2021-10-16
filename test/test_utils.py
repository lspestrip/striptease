# -*- encoding: utf-8 -*-

from striptease import normalize_polarimeter_name, get_polarimeter_index, get_lna_num


def test_normalize_polarimeter_name():
    assert normalize_polarimeter_name("R3") == "R3"
    assert normalize_polarimeter_name("O7") == "O7"
    assert normalize_polarimeter_name("W3") == "R7"


def test_get_polarimeter_index():
    assert get_polarimeter_index("R0") == 0
    assert get_polarimeter_index("O4") == 4
    assert get_polarimeter_index("W4") == 7


def test_get_lna_num():
    for lnaidx, lnaname in enumerate(["HA1", "HA2", "HA3", "HB3", "HB2", "HB1"]):
        assert get_lna_num(lnaname) == lnaidx

    for lnaidx, lnaname in enumerate(["H0", "H1", "H2", "H3", "H4", "H5"]):
        assert get_lna_num(lnaname) == lnaidx

    for lnaidx, lnaname in enumerate(["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]):
        assert get_lna_num(lnaname) == lnaidx

    for lnaidx, lnaname in enumerate(range(6)):
        assert get_lna_num(lnaname) == lnaidx
