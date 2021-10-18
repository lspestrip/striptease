# -*- encoding: utf-8 -*-

from striptease import (
    normalize_polarimeter_name,
    get_polarimeter_index,
    get_lna_num,
    polarimeter_iterator,
)


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


def test_iterate_polarimeters():
    pol_list = [
        x
        for x in polarimeter_iterator(
            boards="I", include_q_band=True, include_w_band=True
        )
    ]

    assert len(pol_list) == 7
    assert pol_list[0] == ("I", 0, "I0")
    assert pol_list[1] == ("I", 1, "I1")
    assert pol_list[2] == ("I", 2, "I2")
    assert pol_list[3] == ("I", 3, "I3")
    assert pol_list[4] == ("I", 4, "I4")
    assert pol_list[5] == ("I", 5, "I5")
    assert pol_list[6] == ("I", 6, "I6")

    pol_list = [
        x
        for x in polarimeter_iterator(
            boards="V", include_q_band=True, include_w_band=False
        )
    ]

    assert len(pol_list) == 7
    assert pol_list[0] == ("V", 0, "V0")
    assert pol_list[1] == ("V", 1, "V1")
    assert pol_list[2] == ("V", 2, "V2")
    assert pol_list[3] == ("V", 3, "V3")
    assert pol_list[4] == ("V", 4, "V4")
    assert pol_list[5] == ("V", 5, "V5")
    assert pol_list[6] == ("V", 6, "V6")

    pol_list = [
        x
        for x in polarimeter_iterator(
            boards="V", include_q_band=True, include_w_band=True
        )
    ]

    assert len(pol_list) == 8
    assert pol_list[0] == ("V", 0, "V0")
    assert pol_list[1] == ("V", 1, "V1")
    assert pol_list[2] == ("V", 2, "V2")
    assert pol_list[3] == ("V", 3, "V3")
    assert pol_list[4] == ("V", 4, "V4")
    assert pol_list[5] == ("V", 5, "V5")
    assert pol_list[6] == ("V", 6, "V6")
    assert pol_list[7] == ("V", 7, "W4")

    pol_list = [
        x
        for x in polarimeter_iterator(
            boards="V", include_q_band=False, include_w_band=True
        )
    ]

    assert len(pol_list) == 1
    assert pol_list[0] == ("V", 7, "W4")

    pol_list = [
        x for x in polarimeter_iterator(include_q_band=True, include_w_band=False)
    ]
    assert len(pol_list) == 49

    pol_list = [
        x for x in polarimeter_iterator(include_q_band=True, include_w_band=True)
    ]
    assert len(pol_list) == 55

    pol_list = [
        x for x in polarimeter_iterator(include_q_band=False, include_w_band=False)
    ]
    assert len(pol_list) == 0

    pol_list = [
        x for x in polarimeter_iterator(include_q_band=False, include_w_band=True)
    ]
    assert len(pol_list) == 6
