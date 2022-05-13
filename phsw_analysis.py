#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from datetime import datetime
import logging
from rich.logging import RichHandler
import sys
import numpy as np
from pathlib import Path
from typing import List, Any, Dict
from mako.template import Template
import math
import json

import matplotlib
import matplotlib.pylab as plt

matplotlib.use("Agg")

# Range of currents to consider when doing the linear fit
SLOPE_FIT_MIN_CURRENT_A = 0.0004
SLOPE_FIT_MAX_CURRENT_A = 0.00095


def create_list_of_iv_curves(data: Dict, pin: int) -> list:
    result = []  # Type: Dict[str, Any]
    for cur_data in data["curves"][f"pin{pin}"]:
        coppia = {"V": cur_data["V"], "I": cur_data["I"]}
        result.append(coppia)
    return result


def decimate(
    results: List[Dict[str, Any]],
    min: float = SLOPE_FIT_MIN_CURRENT_A,
    max: float = SLOPE_FIT_MAX_CURRENT_A,
) -> list:
    retta = [x for x in results if min <= x["I"] <= max]
    return retta


def compute_slope(data: list) -> list:
    Vretta = []
    Iretta = []
    for i in data:
        Vretta.append(i["V"])
        Iretta.append(i["I"])
    m, b = np.polyfit(Vretta, Iretta, 1)
    return [m, b]


def funz_err(lim1: float, lim2: float):
    media = (lim1 + lim2) / 2
    err = (abs(lim1 - lim2) / media) * 100
    return round(err, 4)


def devst(datiRetta: list, intercetta: float, slope: float) -> float:
    somma = 0
    for dato in datiRetta:
        Vteo = (dato["I"] - intercetta) / slope
        delta2 = pow((Vteo - dato["V"]), 2)
        somma += delta2
    devst = math.sqrt(somma / len(datiRetta))
    return devst


def main():
    logging.basicConfig(
        level="INFO", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
    )
    if len(sys.argv) != 7:
        print(
            f"Usage: {sys.argv[0]} storage_path_proc1 storage_path_proc2 storage_path_ult storage_path_buchi_1 storage_path_buchi_2 pol_name pins output_dir"
        )
        sys.exit(1)

    storage_path_1 = sys.argv[1]
    storage_path_2 = sys.argv[2]
    storage_path_ult = sys.argv[3]
    storage_path_buchi_1 = sys.argv[4]
    storage_path_buchi_2 = sys.argv[5]
    pol_name = sys.argv[6]
    pins = sys.argv[7]
    output_dir = Path(sys.argv[8])
    output_dir.mkdir(exist_ok=True, parents=True)
    (output_dir / "analysis").mkdir(exist_ok=True)
    (output_dir / "ref1").mkdir(exist_ok=True)
    (output_dir / "ref2").mkdir(exist_ok=True)

    data_P1 = json.load(open(storage_path_1))  # dati della procedura 1
    data_P2 = json.load(open(storage_path_2))  # dati della procedura 2
    data_ULT = json.load(open(storage_path_ult))  # dati dei ULT
    buchi1 = json.load(
        open(storage_path_buchi_1)
    )  # informazioni sui buchi nella procedura 1
    buchi2 = json.load(
        open(storage_path_buchi_2)
    )  # informazioni sui buchi nella procedura 2

    vmin = {}
    vmax = {}
    slope = {}
    errori = {}
    puntiOut = {}

    pins = [int(x) for x in pins.split(",")]
    for pin in pins:
        proc1 = create_list_of_iv_curves(data_P1, pin)
        ULT = create_list_of_iv_curves(data_ULT, pin)
        proc2 = create_list_of_iv_curves(data_P2, pin)

        plt.clf()
        logging.info(f"Graph pin{pin} P1 e ULT")
        for i in proc1:
            g_proc1 = plt.scatter(i["V"], i["I"], c="red", s=5, label="Proc1")
        for j in ULT:
            g_procULT = plt.scatter(j["V"], j["I"], c="blue", s=5, label="ProcULT")
        plt.xlabel("Voltage [V]")
        plt.ylabel("Current [A]")
        plt.legend(handles=[g_proc1, g_procULT], loc="upper left", title="Legenda")
        plt.title(f"VI curve for {pol_name}, pin {pin}")
        plt_file_name = output_dir / f"{pol_name}_pin{pin}_plt_P1eULT.pdf"
        plt.savefig(plt_file_name, bbox_inches="tight")

        plt.clf()
        logging.info(f"Graph pin{pin} P1 e P2")
        for i in proc1:
            g_proc1 = plt.scatter(i["V"], i["I"], c="red", s=5, label="Proc1")
        for j in proc2:
            g_proc2 = plt.scatter(j["V"], j["I"], c="blue", s=5, label="Proc2")
        plt.xlabel("Voltage [V]")
        plt.ylabel("Current [A]")
        plt.legend(handles=[g_proc1, g_proc2], loc="upper left", title="Legenda")
        plt.title(f"Curve VI - {pol_name} - pin{pin}")
        plt_file_name = output_dir / f"{pol_name}_pin{pin}_plt_P1eP2.pdf"
        plt.savefig(plt_file_name, bbox_inches="tight")

        logging.info(f"Start analysis on pin{pin}")

        vmin[f"Pin{pin}"] = {}
        vmax[f"Pin{pin}"] = {}
        slope[f"Pin{pin}"] = {}
        errori[f"Pin{pin}"] = {}
        puntiOut[f"Pin{pin}"] = {}

        procedure = [proc1, ULT, proc2]
        for res in procedure:
            line_data = decimate(res)
            vmin[f"Pin{pin}"][f"{procedure.index(res)}"] = line_data[0]["V"]
            vmax[f"Pin{pin}"][f"{procedure.index(res)}"] = line_data[-1]["V"]
            sl = compute_slope(line_data)[0]
            slope[f"Pin{pin}"][f"{procedure.index(res)}"] = round(sl, 5)
            intercetta = compute_slope(line_data)[1]
            sigma = devst(line_data, intercetta, sl)
            puntiOut[f"Pin{pin}"][f"{procedure.index(res)}"] = []
            for mydato in line_data:
                Vteo = (mydato["I"] - intercetta) / sl
                if abs(Vteo - mydato["V"]) > 3 * sigma:
                    puntiOut[f"Pin{pin}"][f"{procedure.index(res)}"].append(
                        {"V": mydato["V"], "I": mydato["I"]}
                    )

        errori[f"Pin{pin}"]["P1-ULT"] = {}
        errori[f"Pin{pin}"]["P1-P2"] = {}
        errori[f"Pin{pin}"]["P1-ULT"]["Min"] = funz_err(
            vmin[f"Pin{pin}"]["0"], vmin[f"Pin{pin}"]["1"]
        )
        errori[f"Pin{pin}"]["P1-ULT"]["Max"] = funz_err(
            vmax[f"Pin{pin}"]["0"], vmax[f"Pin{pin}"]["1"]
        )
        errori[f"Pin{pin}"]["P1-P2"]["Min"] = funz_err(
            vmin[f"Pin{pin}"]["0"], vmin[f"Pin{pin}"]["2"]
        )
        errori[f"Pin{pin}"]["P1-P2"]["Max"] = funz_err(
            vmax[f"Pin{pin}"]["0"], vmax[f"Pin{pin}"]["2"]
        )

    logging.info("Creating report")
    template = Template(filename=Path("templates") / "phsw_report.txt")
    with open(output_dir / "phsw_report.md", "wt") as outf:
        print(
            template.render(
                analysis_date=str(datetime.now()),
                polarimeter=pol_name,
                data_storage_path_1=storage_path_1,
                data_storage_path_U=storage_path_ult,
                data_storage_path_2=storage_path_2,
                command_line=" ".join(sys.argv),
                pin_list=pins,
                vmin=vmin,
                vmax=vmax,
                slope=slope,
                errori=errori,
                puntiOut=puntiOut,
                gaps1=buchi1,
                gaps2=buchi2,
                output_dir=output_dir,
            ),
            file=outf,
        )


if __name__ == "__main__":
    main()
