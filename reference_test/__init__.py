#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from striptease import (
    PhswPinMode,
    StripTag,
    wait_with_tag,
)
from turnon import SetupBoard


def set_0_bias(procedure, polname, test_number):
    with StripTag(
        conn=procedure.command_emitter,
        name=f"ref{test_number}_set_pol{polname}_lna_zero_bias",
    ):

        for cur_lna in ("HA3", "HA2", "HA1", "HB3", "HB2", "HB1"):
            adu = procedure.calib.physical_units_to_adu(
                polarimeter=polname,
                hk="vdrain",
                component=cur_lna,
                value=0,
            )
            procedure.conn.set_vd(polname, cur_lna, value_adu=adu)

        procedure.conn.set_pol_mode(polarimeter=polname, mode=5)


def proc_1(procedure, polname, cur_board, test_number, wait_time_s=120):
    # set to zero bias
    set_0_bias(procedure, polname, test_number)
    procedure.conn.set_hk_scan(boards=cur_board, allboards=False, time_ms=500)
    wait_with_tag(
        conn=procedure.conn,
        seconds=wait_time_s,
        name=f"ref{test_number}_acquisition_pol{polname}_zero_bias",
    )

    procedure.conn.log(message="ref_set pol state to unsw 1010")
    # set pol state to unsw 1010 (STATO 1)
    with StripTag(
        conn=procedure.command_emitter,
        name=f"ref{test_number}_set_pol{polname}_phsw_unsw1010",
    ):
        for h, s in enumerate(
            [
                PhswPinMode.STILL_NO_SIGNAL,
                PhswPinMode.STILL_SIGNAL,
                PhswPinMode.STILL_NO_SIGNAL,
                PhswPinMode.STILL_SIGNAL,
            ]
        ):
            procedure.conn.set_phsw_status(polarimeter=polname, phsw_index=h, status=s)

    procedure.conn.set_hk_scan(boards=cur_board, allboards=False, time_ms=500)

    # imposto un wait per l'acquisizione
    wait_with_tag(
        conn=procedure.conn,
        seconds=wait_time_s,
        name=f"ref{test_number}_acquisition_pol{polname}_zero_bias_unsw1010",
    )

    # set pol to default bias
    board_setup = SetupBoard(
        config=procedure.conf,
        post_command=procedure.command_emitter,
        board_name=cur_board,
    )

    procedure.conn.log(message="ref_set pol state to default bias")

    with StripTag(
        conn=procedure.command_emitter,
        name=f"ref{test_number}_set_pol{polname}_lna_nominal",
    ):
        for lna in ("HA3", "HA2", "HA1", "HB3", "HB2", "HB1"):
            board_setup.setup_VD(polname, lna, step=1.0)
            board_setup.setup_VG(polname, lna, step=1.0)

    procedure.conn.set_hk_scan(boards=cur_board, allboards=False, time_ms=500)

    wait_with_tag(
        conn=procedure.conn,
        seconds=wait_time_s,
        name=f"ref{test_number}_acquisition_pol{polname}_unsw1010",
    )

    procedure.conn.log(message="ref_set pol state to unsw 0101")
    # set pol to unsw 0101 (STATO 2)
    with StripTag(
        conn=procedure.command_emitter,
        name=f"ref{test_number}_set_pol{polname}_phsw_unsw0101",
    ):
        for h, s in enumerate(
            [
                PhswPinMode.STILL_SIGNAL,
                PhswPinMode.STILL_NO_SIGNAL,
                PhswPinMode.STILL_SIGNAL,
                PhswPinMode.STILL_NO_SIGNAL,
            ]
        ):
            procedure.conn.set_phsw_status(polarimeter=polname, phsw_index=h, status=s)

    procedure.conn.set_hk_scan(boards=cur_board, allboards=False, time_ms=200)

    wait_with_tag(
        conn=procedure.conn,
        seconds=wait_time_s,
        name=f"ref{test_number}_acquisition_pol{polname}_unsw0101",
    )

    procedure.conn.log(message="ref_set phsw state to default bias")
    # set phsw modulation to default bias
    with StripTag(
        conn=procedure.command_emitter,
        name=f"ref{test_number}_set_pol{polname}_phsw_default",
    ):
        for h in range(4):
            procedure.conn.set_phsw_status(
                polarimeter=polname,
                phsw_index=h,
                status=PhswPinMode.DEFAULT_STATE,
            )

    procedure.conn.set_hk_scan(boards=cur_board, allboards=False, time_ms=500)

    wait_with_tag(
        conn=procedure.conn,
        seconds=wait_time_s,
        name=f"ref{test_number}_acquisition_pol{polname}_default",
    )

    procedure.conn.log(message="ref_set phsw state to antidefault bias")
    # set phsw modulation to antidefault bias
    with StripTag(
        conn=procedure.command_emitter,
        name=f"ref{test_number}_set_pol{polname}_phsw_default_inv",
    ):
        for h, s in enumerate(
            [
                PhswPinMode.SLOW_SWITCHING_FORWARD,
                PhswPinMode.SLOW_SWITCHING_REVERSE,
                PhswPinMode.FAST_SWITCHING_FORWARD,
                PhswPinMode.FAST_SWITCHING_REVERSE,
            ]
        ):
            procedure.conn.set_phsw_status(polarimeter=polname, phsw_index=h, status=s)

    procedure.conn.set_hk_scan(boards=cur_board, allboards=False, time_ms=500)

    wait_with_tag(
        conn=procedure.conn,
        seconds=wait_time_s,
        name=f"ref{test_number}_acquisition_pol{polname}_default_inv",
    )
