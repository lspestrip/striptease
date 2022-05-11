#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
from datetime import datetime

import pandas
import striptease.unittests as u
import logging
from rich.logging import RichHandler
import sys
from pathlib import Path
import json


def select_test(storage_path: str, pol_name: str):
    data = pandas.read_excel(storage_path)
    logging.info("File aperto")
    num = data[data["RGB"] == f"{pol_name}"]["RT"].array[0]
    test = u.get_unit_test(num)
    return test


# questa funzione associa il polarimetro al suo ULT


def analyze_data(test: u.UnitTest, pin: str):
    result = []
    mydata = u.load_unit_test_data(test)
    mydataPin = mydata.components[f"PS{pin}"].curves["IFVF"]
    for value in mydataPin:
        single = {}
        single["V"] = float(value[0][1])
        single["I"] = float(value[0][0])
        result.append(single)
    return result


# questa funzione per tutti i tag restituisce un dizionario con le info importanti per file JSON


def main():
    logging.basicConfig(
        level="INFO", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
    )
    if len(sys.argv) != 4:
        print(
            f"Usage: {sys.argv[0]} curveVI_ULT.py storage_path_corrispondenze pol_name output_dir"
        )
        sys.exit(1)

    storage_path = sys.argv[1]
    pol_name = sys.argv[2]
    output_dir = Path(sys.argv[3])
    output_dir.mkdir(exist_ok=True, parents=True)
    test = select_test(storage_path, pol_name)

    data = {
        "polarimeter": pol_name,
        "analysis_date": str(datetime.now()),
        "cryogenic": "false",
        "operator": test.metadata["operators"],
        "curves": {},
    }

    conv_pin = {"A1": 0, "A2": 1, "B1": 2, "B2": 3}
    for pin in conv_pin:
        logging.info(f"Pin{pin}")
        pin_number = conv_pin[f"{pin}"]
        result = analyze_data(test, pin)
        data["curves"][f"pin{pin_number}"] = result

    with open(output_dir / f"results_{pol_name}.json", "wt") as outf:
        json.dump(data, outf)


if __name__ == "__main__":
    main()
