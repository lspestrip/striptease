import os.path
from web.rest.base import Connection
from config import Config
from copy import deepcopy
from collections import namedtuple
from datetime import datetime
from striptease import StripTag
import logging as log
import re
import time
import csv
import sys
import pandas as pd
from pprint import pprint
from striptease.biases import InstrumentBiases, BoardCalibration
from striptease.procedures import StripProcedure

CalibrationCurve = namedtuple(
    "CalibrationCurve", ["slope", "intercept", "mul", "div", "add",]
)


def get_step(v, cal, step):
    val = v * step * cal.slope + cal.intercept
    if val < 0:
        val = 0
    return int(val + 0.5)


def get_polarimeter_index(pol_name):
    "Return the progressive number of the polarimeter within the board (1…8)"

    if pol_name[0] == "W":
        return 8
    else:
        return int(pol_name[1]) + 1


def get_lna_num(name):
    """Return the number of an LNA, in the range 0…5

    Valid values for `name` can be:
    - The official name, e.g., HA1
    - The UniMIB convention, e.g., H0
    - The JPL convention, e.g., Q1
    - An integer number, which will be returned identically
    """

    if type(name) is int:
        # Assume that the index refers to the proper firmware register
        return name
    elif (len(name) == 3) and (name[0:2] in ["HA", "HB"]):
        # Official names
        d = {
            "HA1": 0,
            "HA2": 2,
            "HA3": 4,
            "HB1": 1,
            "HB2": 3,
            "HB3": 5,
        }
        return d[name]
    elif (len(name) == 2) and (name[0] == "H"):
        # UniMiB
        d = {
            "H0": 0,
            "H1": 1,
            "H2": 2,
            "H3": 3,
            "H4": 4,
            "H5": 5,
        }
        return d[name]
    elif (len(name) == 2) and (name[0] == "Q"):
        # JPL
        d = {
            "Q1": 0,
            "Q2": 1,
            "Q3": 2,
            "Q4": 3,
            "Q5": 4,
            "Q6": 5,
        }
        return d[name]
    else:
        raise ValueError(f"Invalid amplifier name '{name}'")


def read_board_xlsx(path):
    log.debug(f"Reading Excel file {path}")
    board = {}
    cal = pd.read_excel(path, header=None, sheet_name=None)
    for p in cal:
        d = {}
        pol = cal[p].transpose()
        line_count = 0
        current_item = pd.np.nan
        current_fit = pd.np.nan
        current_chan = pd.np.nan
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
                if d.get(current_item) is None:
                    d[current_item] = {}
                if d[current_item].get(current_fit) is None:
                    d[current_item][current_fit] = {}
                d[current_item][current_fit][row[2]] = CalibrationCurve(
                    slope=float(row[3]),
                    intercept=float(row[4]),
                    mul=int(row[5]),
                    div=int(row[6]),
                    add=int(row[7]),
                )
            line_count += 1
        board[p] = d
    return board


class SetupBoard(object):
    def __init__(
        self,
        config,
        post_command,
        board_calibration=None,
        instrument_biases=None,
        board_name="R",
        pol_list=None,
    ):

        self.post_command = post_command
        self.conf = config
        self.board = board_name
        self.pols = pol_list

        if board_calibration:
            self.bc = board_calibration
        else:
            self.bc = None
            log.info(
                f"Looking for an appropriate board configuration, there are {len(self.conf.boards)} choices"
            )
            log.info(
                "The choices are: {0}".format(
                    ", ".join(['"{0}"'.format(x["name"]) for x in self.conf.boards])
                )
            )
            for cur_board in self.conf.boards:
                if cur_board["name"] == board_name:
                    id = cur_board["id"]
                    try:
                        filename = os.path.join(
                            os.path.dirname(__file__),
                            "..",
                            "data",
                            self.conf.get_board_bias_file(id),
                        )
                        log.info(
                            f'Using biases for board "{board_name}" from "{filename}"'
                        )
                        self.bc = read_board_xlsx(filename)
                        if self.pols is None:
                            self.pols = [
                                (x, i) for (i, x) in enumerate(cur_board["pols"])
                            ]
                        break
                    except Exception as exc:
                        log.warning(
                            f'No suitable bias file for board "{board_name}" found: {exc}'
                        )
                        if self.pols is None:
                            self.pols = [
                                "{0}{1}".format(board_name, x) for x in range(7)
                            ]

            if not self.bc:
                log.warning(f'Using default calibration for board "{board_name}"')
                self.bc = BoardCalibration()

        if instrument_biases is not None:
            self.ib = instrument_biases
        else:
            self.ib = InstrumentBiases()

    def board_setup(self):
        url = self.conf.get_rest_base() + "/slo"

        cmd = {}
        cmd["board"] = self.board
        cmd["pol"] = "BOARD"
        cmd["type"] = "BIAS"
        cmd["method"] = "SET"
        cmd["timeout"] = 500

        for (addr, datum) in [
            ("POL_RCL", [23295]),
            ("CAL_RCL", [23295]),
        ]:
            cmd["base_addr"] = addr
            cmd["data"] = datum

            if not self.post_command(url, cmd):
                log.warning(f"Unable to post command {addr}")
                return

    def enable_electronics(self, polarimeter, delay_sec=0.5, mode=5):
        url = self.conf.get_rest_base() + "/slo"

        cmd = {}
        cmd["board"] = self.board
        cmd["type"] = "BIAS"
        cmd["method"] = "SET"
        cmd["timeout"] = 500

        cmd["pol"] = polarimeter
        cmd["type"] = "BIAS"
        for c in [("POL_PWR", 1), ("DAC_REF", 1), ("POL_MODE", mode), ("CLK_REF", 0)]:
            cmd["base_addr"] = c[0]
            cmd["data"] = [c[1]]

            if not self.post_command(url, cmd):
                print(
                    f"WARNING: command {c[0]}={c[1]} gave an error",
                    file=sys.stderr,
                    flush=True,
                )
                break

        cmd["base_addr"] = "PRE_EN"
        cmd["type"] = "PREAMP"
        cmd["data"] = [1]

        if not self.post_command(url, cmd):
            return

    def enable_all_electronics(self, mode=5):
        for (p, _) in self.pols:
            self.polarimeter_on(polarimeter=p, mode=mode)

    def disable_electronics(self, polarimeter, delay_sec=0.5):
        url = self.conf.get_rest_base() + "/slo"

        cmd = {}
        cmd["board"] = self.board
        cmd["type"] = "BIAS"
        cmd["method"] = "SET"
        cmd["timeout"] = 500

        cmd["pol"] = polarimeter

        cmd["base_addr"] = "PRE_EN"
        cmd["type"] = "PREAMP"
        cmd["data"] = [0]

        if not self.post_command(url, cmd):
            return

        cmd["type"] = "BIAS"
        for c in [("POL_MODE", 0), ("DAC_REF", 0), ("POL_PWR", 0)]:
            cmd["base_addr"] = c[0]
            cmd["data"] = [c[1]]

            if not self.post_command(url, cmd):
                return

    def disable_all_electronics(self):
        for (p, _) in self.pols:
            self.polariemter_off(polarimeter=p)

    def turn_on_detector(self, polarimeter, detector_idx, bias=0, offset=0, gain=0):
        assert detector_idx in [0, 1, 2, 3]

        url = self.conf.get_rest_base() + "/slo"

        cmd = {}
        cmd["board"] = self.board
        cmd["type"] = "PREAMP"
        cmd["method"] = "SET"
        cmd["timeout"] = 500

        cmd["pol"] = polarimeter

        cmd["base_addr"] = f"DET{detector_idx}_BIAS"
        cmd["data"] = [bias]
        if not self.post_command(url, cmd):
            return

        cmd["base_addr"] = f"DET{detector_idx}_OFFS"
        cmd["data"] = [offset]
        # if not self.post_command(url, cmd):
        #    return

        cmd["base_addr"] = f"DET{detector_idx}_GAIN"
        cmd["data"] = [gain]
        # if not self.post_command(url, cmd):
        #    return

    def set_phsw_status(self, polarimeter, phsw_idx, status):
        assert phsw_idx in [0, 1, 2, 3]

        url = self.conf.get_rest_base() + "/slo"

        cmd = {}
        cmd["board"] = self.board
        cmd["type"] = "BIAS"
        cmd["method"] = "SET"
        cmd["timeout"] = 500

        cmd["pol"] = polarimeter

        cmd["base_addr"] = f"PIN{phsw_idx}_CON"
        cmd["data"] = [status]
        if not self.post_command(url, cmd):
            return

    def set_phsw_bias(self, polarimeter, index, vpin, ipin):
        url = self.conf.get_rest_base() + "/slo"

        cmd = {}
        cmd["board"] = self.board
        cmd["type"] = "BIAS"
        cmd["method"] = "SET"
        cmd["timeout"] = 500

        bc = self.ib.get_biases(module_name=polarimeter)
        calib = self.bc[f"Pol{get_polarimeter_index(polarimeter)}"]

        cmd["pol"] = polarimeter
        cmd["base_addr"] = f"VPIN{index}_SET"
        cmd["data"] = [get_step(vpin, calib["PIN DIODES"]["SET VOLTAGE"][index], 1.0)]

        if not self.post_command(url, cmd):
            return

        cmd["base_addr"] = f"IPIN{index}_SET"
        cmd["data"] = [get_step(ipin, calib["PIN DIODES"]["SET CURRENT"][index], 1.0)]

        if not self.post_command(url, cmd):
            return

    def setup_bias(
        self, polarimeter, index, bias_dict, param_name, excel_entry, step=1
    ):
        url = self.conf.get_rest_base() + "/slo"

        pol_index = get_polarimeter_index(polarimeter)
        bc = self.ib.get_biases(module_name=polarimeter)
        calib = self.bc[f"Pol{pol_index + 1}"]
        title1, title2 = excel_entry

        cmd = {
            "board": self.board,
            "type": "BIAS",
            "method": "SET",
            "timeout": 500,
            "pol": polarimeter,
            "base_addr": f"{param_name}{index}_SET",
            "data": [
                get_step(
                    bc.__getattribute__(bias_dict[index]),
                    calib[title1][title2][index],
                    step,
                )
            ],
        }

        if not self.post_command(url, cmd):
            return

    def setup_lna_bias(
        self, polarimeter, lna, bias_dict, param_name, excel_entry, step=1
    ):
        self.setup_bias(
            polarimeter=polarimeter,
            index=get_lna_num(lna),
            bias_dict=bias_dict,
            param_name=param_name,
            excel_entry=excel_entry,
            step=step,
        )

    def setup_VD(self, polarimeter, lna, step=1):
        vd = {
            0: "vd0",
            1: "vd1",
            2: "vd2",
            3: "vd3",
            4: "vd4",
            5: "vd5",
        }

        self.setup_lna_bias(
            polarimeter=polarimeter,
            lna=lna,
            bias_dict=vd,
            param_name="VD",
            excel_entry=("DRAIN", "SET VOLTAGE"),
            step=step,
        )

    def setup_VG(self, polarimeter, lna, step=1):
        vg = {
            0: "vg0",
            1: "vg1",
            2: "vg2",
            3: "vg3",
            4: "vg4",
            5: "vg5",
            "4A": "vg4a",
            "5A": "vg5a",
        }

        self.setup_lna_bias(
            polarimeter=polarimeter,
            lna=lna,
            bias_dict=vg,
            param_name="VG",
            excel_entry=("GATE", "SET VOLTAGE"),
            step=step,
        )

    def setup_ID(self, polarimeter, lna, step=1):
        id = {
            0: "id0",
            1: "id1",
            2: "id2",
            3: "id3",
            4: "id4",
            5: "id5",
        }

        self.setup_lna_bias(
            polarimeter=polarimeter,
            lna=lna,
            bias_dict=id,
            param_name="ID",
            excel_entry=("DRAIN", "SET CURRENT"),
            step=step,
        )

    def setup_all_VDs(self, step=1):
        for pol, _ in self.pols:
            self.setup_VD(polarimeter=pol, step=step)

    def setup_all_VGs(self, step=1):
        for pol, _ in self.pols:
            self.setup_VG(polarimeter=pol, step=step)

    def setup_all_IDs(self, step=1):
        for pol, _ in self.pols:
            self.setup_ID(polarimeter=pol, step=step)

    def change_file(self):
        url = self.conf.get_rest_base() + "/command"

        cmd = {"command": "round_hdf5_files"}

        if not self.post_command(url, cmd):
            return

    def log(self, msg, level="INFO"):
        url = self.conf.get_rest_base() + "/log"
        cmd = {"level": level, "message": str(msg)}

        if not self.post_command(url, cmd):
            return


def biases_to_str(biases):
    return "Biases: " + ",".join(
        [
            str(biases.vd0),
            str(biases.vd1),
            str(biases.vd2),
            str(biases.vd3),
            str(biases.vd4),
            str(biases.vd5),
            str(biases.vg0),
            str(biases.vg1),
            str(biases.vg2),
            str(biases.vg3),
            str(biases.vg4),
            str(biases.vg5),
            str(biases.vg4a),
            str(biases.vg5a),
            str(biases.vpin0),
            str(biases.vpin1),
            str(biases.vpin2),
            str(biases.vpin3),
            str(biases.ipin0),
            str(biases.ipin1),
            str(biases.ipin2),
            str(biases.ipin3),
            str(biases.id0),
            str(biases.id1),
            str(biases.id2),
            str(biases.id3),
            str(biases.id4),
            str(biases.id5),
        ]
    )


class TurnOnOffProcedure(StripProcedure):
    def __init__(self, waittime_s=5, turnon=True):
        super(TurnOnOffProcedure, self).__init__()
        self.board = None
        self.horn = None
        self.polarimeter = None
        self.waittime_s = waittime_s
        self.turnon = turnon

    def set_board_horn_polarimeter(self, new_board, new_horn, new_pol=None):
        self.board = new_board
        self.horn = new_horn
        self.polarimeter = new_pol

    def run(self):
        "Depending on `self.turnon`, execute a turn-on or turn-off procedure for `self.horn`."
        if self.turnon:
            self.run_turnon()
        else:
            self.run_turnoff()

    def run_turnon(self, turn_on_board=True, stable_acquisition_time_s=120):
        """Execute a turn-on procedure for the horn specified in `self.horn`.
        
        Optional parameters:
        
        - turn_on_board: if True, turn on the board. Set it to false if you are sure the
            board has already been turned on (default: True).

        - stable_acquisition_time_s: if nonzero, wait for the specified amount of
            seconds once the polarimeter has been fully turned on.                         
        """

        assert self.horn
        board_setup = SetupBoard(
            config=self.conf, board_name=self.board, post_command=self.command_emitter
        )

        current_time = datetime.now().strftime("%A %Y-%m-%d %H:%M:%S (%Z)")
        board_setup.log(
            f"Here begins the turnon procedure for polarimeter {self.horn}, "
            + f"created on {current_time} using program_turnon.py"
        )
        board_setup.log(f"We are using the setup for board {self.board}")
        if self.polarimeter:
            board_setup.log(
                f"This procedure assumes that horn {self.horn} is connected to polarimeter {self.polarimeter}"
            )

        # 1
        if turn_on_board:
            with StripTag(
                conn=self.command_emitter,
                name="BOARD_TURN_ON",
                comment=f"Turning on board for {self.horn}",
            ):
                board_setup.log("Going to set up the board…")
                board_setup.board_setup()
                board_setup.log("Board has been set up")

        # 2
        with StripTag(
            conn=self.command_emitter,
            name=f"ELECTRONICS_ENABLE_{self.horn}",
            comment=f"Enabling electronics for {self.horn}",
        ):
            board_setup.log(f"Enabling electronics for {self.horn}…")
            board_setup.enable_electronics(polarimeter=self.horn)
            board_setup.log("The electronics has been enabled")

        # 3
        for idx in (0, 1, 2, 3):
            with StripTag(
                conn=self.command_emitter,
                name=f"DETECTOR_TURN_ON_{self.horn}_{idx}",
                comment=f"Turning on detector {idx} in {self.horn}",
            ):
                board_setup.turn_on_detector(self.horn, idx)

        # 4
        if self.polarimeter:
            biases = self.biases.get_biases(polarimeter_name=self.polarimeter)
            board_setup.log(f"{self.polarimeter}: {biases_to_str(biases)}")
        else:
            biases = self.biases.get_biases(module_name=self.horn)
            board_setup.log(f"{self.horn}: {biases_to_str(biases)}")

        for (index, vpin, ipin) in zip(
            range(4),
            [biases.vpin0, biases.vpin1, biases.vpin2, biases.vpin3],
            [biases.ipin0, biases.ipin1, biases.ipin2, biases.ipin3],
        ):
            try:
                with StripTag(
                    conn=self.command_emitter,
                    name=f"PHSW_BIAS_{self.horn}_{index}",
                    comment=f"Setting biases for PH/SW {index} in {self.horn}",
                ):
                    board_setup.set_phsw_bias(self.horn, index, vpin, ipin)
            except:
                log.warning(f"Unable to set bias for detector #{index}")

        # 5
        for idx in (0, 1, 2, 3):
            with StripTag(
                conn=self.command_emitter,
                name=f"PHSW_STATUS_{self.horn}_{idx}",
                comment=f"Setting status for PH/SW {idx} in {self.horn}",
            ):
                board_setup.set_phsw_status(self.horn, idx, status=7)

        # 6
        for lna in ("HA3", "HA2", "HA1", "HB3", "HB2", "HB1"):
            for step_idx, cur_step in enumerate([0.0, 0.5, 1.0]):
                with StripTag(
                    conn=self.command_emitter,
                    name=f"VD_SET_{self.horn}_{lna}",
                    comment=f"Setting drain voltages for LNA {lna} in {self.horn}",
                ):
                    board_setup.setup_VD(self.horn, lna, step=cur_step)

                    if step_idx == 0:
                        board_setup.setup_VG(self.horn, lna, step=1.0)

                    if False and cur_step == 1.0:
                        # In mode 5, the following command should be useless…
                        board_setup.setup_ID(self.horn, lna, step=1.0)

                if self.waittime_s > 0:
                    with StripTag(
                        conn=self.command_emitter,
                        name=f"VD_SET_{self.horn}_{lna}_ACQUISITION",
                        comment=f"Acquiring some data after VD_SET_{lna}",
                    ):
                        self.wait(seconds=self.waittime_s)

        if stable_acquisition_time_s > 0:
            board_setup.log(
                f"Horn {self.horn} has been turned on, stable acquisition for {stable_acquisition_time_s} s begins here"
            )
            with StripTag(
                conn=self.command_emitter, name=f"STABLE_ACQUISITION_{self.horn}"
            ):
                self.wait(seconds=stable_acquisition_time_s)
            board_setup.log(f"End of stable acquisition for horn {self.horn}")
        else:
            board_setup.log(f"Horn {self.horn} has been turned on")

    def run_turnoff(self):
        "Execute a turn-off procedure for the horn specified in `self.horn`."

        assert self.horn
        board_setup = SetupBoard(
            config=self.conf, board_name=self.board, post_command=self.command_emitter
        )

        current_time = datetime.now().strftime("%A %Y-%m-%d %H:%M:%S (%Z)")
        board_setup.log(
            f"Here begins the turnoff procedure for polarimeter {self.horn}, "
            + f"created on {current_time} using program_turnon.py"
        )
        board_setup.log(f"We are using the setup for board {self.board}")
        if self.polarimeter:
            board_setup.log(
                f"This procedure assumes that horn {self.horn} is connected to polarimeter {self.polarimeter}"
            )

        # 1
        with StripTag(
            conn=self.command_emitter,
            name="BOARD_TURN_OFF",
            comment=f"Turning off board for {self.horn}",
        ):
            board_setup.log("Going to set up the board…")
            board_setup.board_setup()
            board_setup.log("Board has been set up")

        # 6
        for lna in reversed(["HA3", "HA2", "HA1", "HB3", "HB2", "HB1"]):
            for step_idx, cur_step in enumerate(reversed([0.0, 0.5, 1.0])):
                with StripTag(
                    conn=self.command_emitter,
                    name="VD_SET",
                    comment=f"Setting drain voltages for LNA {lna} in {self.horn}",
                ):
                    board_setup.setup_VD(self.horn, lna, step=cur_step)

                    if step_idx == 0:
                        board_setup.setup_VG(self.horn, lna, step=1.0)

                    if False and cur_step == 1.0:
                        # In mode 5, the following command should be useless…
                        board_setup.setup_ID(self.horn, lna, step=1.0)

                if self.waittime_s > 0:
                    self.wait(seconds=self.waittime_s)

        # 2
        with StripTag(
            conn=self.command_emitter,
            name="ELECTRONICS_DISABLE",
            comment=f"Enabling electronics for {self.horn}",
        ):
            board_setup.log(f"Disabling electronics for {self.horn}…")
            board_setup.disable_electronics(polarimeter=self.horn)
            board_setup.log("The electronics has been disabled")

        board_setup.log(f"Turnoff procedure for {self.horn} completed")


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("usage: python ", sys.argv[0], "MODULE_ID")
        sys.exit(-1)

    board_calibration = read_board_xlsx(sys.argv[1])

    con = Connection()
    con.login()

    sb = SetupBoard(con, board_calibration)

    sb.board_on()
    sb.pols_on()

    sb.setup_VD(0)
    sb.setup_VG(1)
    sb.setup_VPIN(1)
    sb.setup_IPIN(1)

    sb.pols_off()
