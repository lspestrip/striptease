#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from striptease import (
    PhswPinMode,
    StripTag,
    wait_with_tag,
)
from turnon import SetupBoard


def set_0_bias(self, polname):
    with StripTag(conn=self.command_emitter, name=f"ref_set_0B_pol_{polname}"):

        for cur_lna in ("HA3", "HA2", "HA1", "HB3", "HB2", "HB1"):
            adu = self.calib.physical_units_to_adu(
                polarimeter=polname,
                hk="vdrain",
                component=cur_lna,
                value=0,
            )
            self.conn.set_vd(polname, cur_lna, value_adu=adu)

        self.conn.set_pol_mode(polarimeter=polname, mode=5)


def proc_1(self, polname, cur_board):
    # set to zero bias
    set_0_bias(self, polname)
    self.conn.set_hk_scan(boards=cur_board, allboards=False, time_ms=500)
    wait_with_tag(conn=self.conn, seconds=120, name=f"ref_acquisition_0B_pol{polname}")

    self.conn.log(message="ref_set pol state to unsw 1010")
    # set pol state to unsw 1010 (STATO 1)
    with StripTag(conn=self.command_emitter, name=f"ref_set_pol_state{polname}"):
        for h, s in enumerate(
            [
                PhswPinMode.STILL_NO_SIGNAL,
                PhswPinMode.STILL_SIGNAL,
                PhswPinMode.STILL_NO_SIGNAL,
                PhswPinMode.STILL_SIGNAL,
            ]
        ):
            self.conn.set_phsw_status(polarimeter=polname, phsw_index=h, status=s)

    self.conn.set_hk_scan(boards=cur_board, allboards=False, time_ms=500)

    # imposto un wait per l'acquisizione
    wait_with_tag(
        conn=self.conn, seconds=120, name=f"ref_acquisition_STATE1_pol{polname}"
    )

    # set pol to default bias
    board_setup = SetupBoard(
        config=self.conf, post_command=self.command_emitter, board_name=cur_board
    )

    self.conn.log(message="ref_set pol state to default bias")
    for lna in ("HA3", "HA2", "HA1", "HB3", "HB2", "HB1"):
        board_setup.setup_VD(polname, lna, step=1.0)
        board_setup.setup_VG(polname, lna, step=1.0)

    self.conn.set_hk_scan(boards=cur_board, allboards=False, time_ms=500)

    wait_with_tag(conn=self.conn, seconds=120, name=f"ref_acquisition_pol{polname}")

    self.conn.log(message="ref_set pol state to unsw 0101")
    # set pol to unsw 0101 (STATO 2)
    with StripTag(conn=self.command_emitter, name=f"ref_set_pol_state{polname}"):
        for h, s in enumerate(
            [
                PhswPinMode.STILL_SIGNAL,
                PhswPinMode.STILL_NO_SIGNAL,
                PhswPinMode.STILL_SIGNAL,
                PhswPinMode.STILL_NO_SIGNAL,
            ]
        ):
            self.conn.set_phsw_status(polarimeter=polname, phsw_index=h, status=s)

    self.conn.set_hk_scan(boards=cur_board, allboards=False, time_ms=200)

    wait_with_tag(
        conn=self.conn, seconds=120, name=f"ref_acquisition_STATE2_pol{polname}"
    )

    self.conn.log(message="ref_set phsw state to default bias")
    # set phsw modulation to default bias
    for h in range(4):
        with StripTag(conn=self.command_emitter, name=f"ref_set_pol_state{polname}"):
            self.conn.set_phsw_status(
                polarimeter=polname,
                phsw_index=h,
                status=PhswPinMode.DEFAULT_STATE,
            )

    self.conn.set_hk_scan(boards=cur_board, allboards=False, time_ms=500)

    wait_with_tag(conn=self.conn, seconds=120, name=f"ref_acquisition_pol{polname}")

    self.conn.log(message="ref_set phsw state to antidefault bias")
    # set phsw modulation to antidefault bias
    with StripTag(conn=self.command_emitter, name=f"ref_set_pol_state{polname}"):
        for h, s in enumerate(
            [
                PhswPinMode.SLOW_SWITCHING_FORWARD,
                PhswPinMode.SLOW_SWITCHING_REVERSE,
                PhswPinMode.FAST_SWITCHING_FORWARD,
                PhswPinMode.FAST_SWITCHING_REVERSE,
            ]
        ):
            self.conn.set_phsw_status(polarimeter=polname, phsw_index=h, status=s)

    self.conn.set_hk_scan(boards=cur_board, allboards=False, time_ms=500)

    wait_with_tag(conn=self.conn, seconds=120, name=f"ref_acquisition_pol{polname}")
