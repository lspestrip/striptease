#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from striptease import DataStorage
from striptease import Tag
import matplotlib.pylab as plt
from astropy.time import Time
import logging
from rich.logging import RichHandler
import sys
import numpy as np
from pathlib import Path
from typing import List, Any, Tuple
import json


def tags_curve(
    ds: DataStorage, data_range: Tuple[str, str], pol_name: str, pin: int
) -> List[Tag]:
    tags = ds.get_tags(data_range)
    return [
        x
        for x in tags
        if (f"set_i_{pol_name}" in x.name or f"Set I {pol_name}" in x.name)
        and f"pin{pin}" in x.name
    ]


def range_buco(tempi: list) -> List[Any]:
    lista_buchi = []
    t1 = np.array(tempi[:-1])
    t2 = np.array(tempi[1:])
    for i in range(len(t1)):
        if (t2[i] - t1[i]) > 0.0002:
            t1[i].format = "iso"
            t2[i].format = "iso"
            lista_buchi.append(
                [
                    t1[i].strftime("%Y-%m-%d %H:%M:%S"),
                    t2[i].strftime("%Y-%m-%d %H:%M:%S"),
                    round((t2[i] - t1[i]).to("s").value, 3),
                ]
            )
    return lista_buchi


def main():
    logging.basicConfig(
        level="INFO", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
    )
    if len(sys.argv) != 7:
        print(
            f"Usage: {sys.argv[0]} storage_path start_time end_time pol_name pins output_dir"
        )
        sys.exit(1)

    storage_path = sys.argv[1]
    start_time = sys.argv[2]
    end_time = sys.argv[3]
    pol_name = sys.argv[4]
    pins = sys.argv[5]
    output_dir = Path(sys.argv[6])
    output_dir.mkdir(exist_ok=True, parents=True)

    ds = DataStorage(storage_path)
    buchi = {}
    info = (
        {}
    )  # dizionario in cui sono salvate medie e devst di correnti di drain e dato sci

    pins = [int(x) for x in pins.split(",")]
    for pin in pins:
        logging.info(f"Analisi pin {pin}")
        fig, axs = plt.subplots(4, figsize=(7, 8))
        fig.subplots_adjust(hspace=0.4)
        fig.suptitle(f"Analisi pin{pin}")
        for i in range(4):
            axs[i].clear()
        my_tags = tags_curve(ds, (start_time, end_time), pol_name, pin)
        buchi[f"Pin{pin}"] = {}

        logging.info(f"Analizzo V e I del pin {pin}")
        tempi_Vpin = []
        for i in range(len(my_tags) - 1):
            times, valueV = ds.load_hk(
                (my_tags[i].mjd_start, my_tags[i + 1].mjd_start),
                "BIAS",
                f"POL_{pol_name}",
                f"Vpin{pin}_HK",
            )
            _, valueI = ds.load_hk(
                (my_tags[i].mjd_start, my_tags[i + 1].mjd_start),
                "BIAS",
                f"POL_{pol_name}",
                f"Ipin{pin}_HK",
            )
            tempo = Time(np.median(times.value), format="mjd")
            tempi_Vpin.append(tempo)
            V = float(np.median(valueV) / 1000)
            I = float(np.median(valueI) / 1000000)
            axs[0].scatter((tempo - tempi_Vpin[0]).to("s"), V, c="red", s=5)
            axs[1].scatter((tempo - tempi_Vpin[0]).to("s"), I, c="red", s=5)
        axs[0].set_xlabel("Tempi [s]")
        axs[0].set_ylabel("V pin [V]")
        axs[1].set_xlabel("Tempi [s]")
        axs[1].set_ylabel("I pin [A]")
        buchi[f"Pin{pin}"]["Vpin"] = range_buco(tempi_Vpin)

        logging.info(f"Analizzo I drain del pin {pin}")
        color_cycle = ["red", "orange", "yellow", "green", "blue", "pink"]
        info[f"Pin{pin}"] = {}
        for num in range(6):
            tempi_ID = []
            correnti = []
            for i in range(len(my_tags) - 1):
                times, valueID = ds.load_hk(
                    (my_tags[i].mjd_start, my_tags[i + 1].mjd_start),
                    "BIAS",
                    f"POL_{pol_name}",
                    f"ID{num}_HK",
                )
                tempo = Time(np.median(times.value), format="mjd")
                tempi_ID.append(tempo)
                ID = float(np.median(valueID) / 1000000)
                correnti.append(ID)
                axs[2].scatter(
                    (tempo - tempi_ID[0]).to("s"), ID, color=color_cycle[num], s=5
                )
            media = np.mean(correnti)
            sigma = np.std(correnti)
            info[f"Pin{pin}"][f"ID{num}"] = {"Media": media, "Sigma": sigma}
            buchi[f"Pin{pin}"][f"ID{num}"] = range_buco(tempi_ID)
        axs[2].set_xlabel("Tempi [s]")
        axs[2].set_ylabel("I drain [A]")

        logging.info(f"Analizzo dato scientifico del pin {pin}")
        for data in [
            "DEM"
        ]:  # ho lasciato i due cicli anche se ora non li uso, così è comodo considerare anche le altre uscite del dato scientifico
            for detect in ["Q1"]:
                tempi_SCI = []
                values = []
                for i in range(len(my_tags) - 1):
                    times, value = ds.load_sci(
                        (my_tags[i].mjd_start, my_tags[i + 1].mjd_start),
                        polarimeter=f"{pol_name}",
                        data_type=f"{data}",
                        detector=f"{detect}",
                    )
                    timesBuchi = [Time(x.value, format="mjd") for x in times]
                    tempi_SCI += timesBuchi
                    values += list(value)
                    axs[3].scatter(
                        (times - tempi_SCI[0]).to("s").value, value, c="blue", s=5
                    )
                buchi[f"Pin{pin}"][f"{data}{detect}"] = range_buco(tempi_SCI)
                media = np.mean(values)
                sigma = np.std(values)
                info[f"Pin{pin}"][f"{data}{detect}"] = {"Media": media, "Sigma": sigma}
        axs[3].set_xlabel("Tempi [s]")
        axs[3].set_ylabel("Dato Sci [ADU]")

        logging.info("Salvo il grafico")
        plt_file_name = output_dir / f"{pol_name}_pin{pin}_CT.pdf"
        plt.savefig(plt_file_name, bbox_inches="tight")

        logging.info("Creating file JSON")
        with open(output_dir / f"buchi_{pol_name}.json", "wt") as outf:
            json.dump(buchi, outf)
        with open(output_dir / f"info_{pol_name}.json", "wt") as outf:
            json.dump(info, outf)


if __name__ == "__main__":
    main()
