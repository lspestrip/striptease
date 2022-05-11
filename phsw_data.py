#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
from datetime import datetime

from striptease import DataStorage
from striptease import Tag
import sys
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import logging
from rich.logging import RichHandler
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


# This function creates a list of the tags that need to be analyzed.
# questa funzione crea una lista dei tags che voglio analizzare, il nome è diverso per le due procedure
# come condizione ho dovuto inserire due opzioni perchè i tag nei test di francesco hanno nomi diversi
def analyze_hk(ds: DataStorage, tag_list: List, pol_name: str, pin: int) -> List[Dict]:
    lista_json = []  # Type: List[Dict[str, Any]]
    for i in range(len(tag_list) - 1):
        result = {}  # Type: Dict[str, Any]
        _, voltages = ds.load_hk(
            mjd_range=(tag_list[i].mjd_start, tag_list[i + 1].mjd_start),
            group="BIAS",
            subgroup=f"POL_{pol_name}",
            par=f"Vpin{pin}_HK",
        )
        _, currents = ds.load_hk(
            mjd_range=(tag_list[i].mjd_start, tag_list[i + 1].mjd_start),
            group="BIAS",
            subgroup=f"POL_{pol_name}",
            par=f"Ipin{pin}_HK",
        )
        result["tag"] = tag_list[i].name
        result["timeRange"] = [tag_list[i].mjd_start, tag_list[i + 1].mjd_start]
        result["V"] = float(np.median(voltages) / 1e3)
        result["I"] = float(np.median(currents) / 1e6)
        lista_json.append(result)
    return lista_json


# questa funzione per ogni tag restituisce un dizionario con le info importanti per file JSON
def main():
    logging.basicConfig(
        level="INFO", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
    )
    if len(sys.argv) != 7:
        print(
            f"usage: {sys.argv[0]} storage_path start_time end_time pol_name pins output_dir"
        )
        sys.exit(1)

    storage_path = sys.argv[1]
    start_time = sys.argv[2]
    end_time = sys.argv[3]
    pol_name = sys.argv[4]
    pins = sys.argv[5]
    output_dir = Path(sys.argv[6])
    output_dir.mkdir(exist_ok=True, parents=True)

    logging.info(f"Load data from {storage_path}")
    ds = DataStorage(storage_path)

    data = {
        "polarimeter": pol_name,
        "analysis_date": str(datetime.now()),
        "cryogenic": "false",
        "curves": {},
    }

    pins = [int(x) for x in pins.split(",")]
    for pin in pins:
        my_tags = tags_curve(ds, (start_time, end_time), pol_name, pin)
        logging.info(f"Pin{pin}: {len(my_tags)} tags")
        my_result = analyze_hk(ds, my_tags, pol_name, pin)
        data["curves"][f"pin{pin}"] = my_result

    logging.info("Creating file JSON")
    with open(output_dir / f"phsw_curve_{pol_name}.json", "wt") as outf:
        json.dump(data, outf)


if __name__ == "__main__":
    main()
