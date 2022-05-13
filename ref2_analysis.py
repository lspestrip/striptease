#!/usr/bin/env python3 -*- encoding: utf-8 -*-

# Purpose of the code:
#
# 1. Consider only data acquired for *one* polarimeter during the ref2
#    test
#
# 2. Check all the tags signaling a stab le acquisitions
#
# 3. Create one folder per tag containing:
#
#    -   Correlation matrix between polarimeters (using 120 s of data)
#
#    -   A report containing some statistics about the signal


import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import logging
from rich.logging import RichHandler
import sys
from astropy.time import Time
from mako.template import Template
from pathlib import Path
from striptease import DataStorage, Tag, polarimeter_iterator
import numpy as np
import numpy
from datetime import datetime
from calibration import CalibrationTables
from typing import Any, Dict, List, Tuple


def get_ref_acquisition_tags(
    ds: DataStorage, time_start: "str", time_end: "str", pol_name: "str", n_ref="str"
) -> List[Tag]:
    "Given a time range, return all the tags signaling a ref2 stable acquisition"

    mjd_range = (time_start, time_end)
    tags = ds.get_tags(mjd_range)

    return [
        x
        for x in tags
        if f"ref{n_ref}_acquisition" in x.name and x.name.endswith(pol_name)
    ]


# TODO: this function is too heavy to run, but I have run out of ideas…
def analyzed_data(ds: DataStorage, time: tuple, pol_name: str) -> Dict[str, Any]:
    result = {}
    for data_type in ("DEM", "PWR"):
        for ch in ("Q1", "Q2", "U1", "U2"):
            _, value = ds.load_sci(
                mjd_range=time,
                polarimeter=pol_name,
                data_type=data_type,
                detector=ch,
            )

            pari = np.array(value[::2], dtype=numpy.int64)
            dispari = np.array(value[1::2], dtype=numpy.int64)
            if len(pari) != len(dispari):
                pari = pari[0:-1:1]
            sottratti = pari + dispari

            result[f"{data_type}{ch}_mean"] = round(float(np.mean(sottratti)), 2)
            result[f"{data_type}{ch}_median"] = int(np.median(sottratti))
            result[f"{data_type}{ch}_std"] = round(float(np.std(sottratti)), 2)
            result[f"{data_type}{ch}_25percentile"] = int(np.percentile(sottratti, 25))
            result[f"{data_type}{ch}_75percentile"] = int(np.percentile(sottratti, 75))

    for i in range(0, 6):
        for parameter in (
            f"ID{i}_HK",
            f"ID{i}_SET",
            f"VD{i}_HK",
            f"VD{i}_SET",
            f"VG{i}_HK",
            f"VG{i}_SET",
        ):
            _, value = ds.load_hk(
                mjd_range=time, group="BIAS", subgroup=f"POL_{pol_name}", par=parameter
            )
            if "SET" in parameter:
                cal = CalibrationTables()
                if "ID" in parameter:
                    value = cal.adu_to_physical_units(
                        polarimeter=pol_name, hk="idrain", component=i, value=value
                    )
                if "VD" in parameter:
                    value = cal.adu_to_physical_units(
                        polarimeter=pol_name, hk="vdrain", component=i, value=value
                    )
                if "VG" in parameter:
                    value = cal.adu_to_physical_units(
                        polarimeter=pol_name, hk="vgate", component=i, value=value
                    )
            result[f"{parameter}_mean"] = round(float(np.mean(value)), 2)
            result[f"{parameter}_median"] = int(np.median(value))
            result[f"{parameter}_std"] = round(float(np.std(value)), 2)
            result[f"{parameter}_25percentile"] = int(np.percentile(value, 25))
            result[f"{parameter}_75percentile"] = int(np.percentile(value, 75))

    for i in range(0, 4):
        for parameter in (f"IPIN{i}_SET", f"VPIN{i}_SET", f"PIN{i}_CON"):
            _, value = ds.load_hk(
                mjd_range=time, group="BIAS", subgroup=f"POL_{pol_name}", par=parameter
            )
            if "SET" in parameter:
                cal = CalibrationTables()
                if "IPIN" in parameter:
                    value = cal.adu_to_physical_units(
                        polarimeter=pol_name, hk="iphsw", component=i, value=value
                    )
                if "VPIN" in parameter:
                    value = cal.adu_to_physical_units(
                        polarimeter=pol_name, hk="vphsw", component=i, value=value
                    )
            result[f"{parameter}_mean"] = round(float(np.mean(value)), 2)
            result[f"{parameter}_median"] = int(np.median(value))
            result[f"{parameter}_std"] = round(float(np.std(value)), 2)
            result[f"{parameter}_25percentile"] = int(np.percentile(value, 25))
            result[f"{parameter}_75percentile"] = int(np.percentile(value, 75))
    return result


def main():
    if len(sys.argv) != 6:
        print(
            f"Usage: {sys.argv[0]} storage_path start_time end_time polarimeter output_dir"
        )
        sys.exit(1)

    logging.basicConfig(
        level="INFO", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
    )

    storage_path = sys.argv[1]
    start_time = sys.argv[2]
    end_time = sys.argv[3]
    pol_name = sys.argv[4]
    directory = Path(sys.argv[5]) / pol_name

    directory.mkdir(exist_ok=True, parents=True)
    ds = DataStorage(storage_path)
    logging.info(f'Loading data from "{storage_path}"')

    num_ref = "2"
    tags = get_ref_acquisition_tags(ds, start_time, end_time, pol_name, num_ref)

    logging.info(f"Going to analyze {len(tags)} tags")
    for t in range(len(tags)):
        start = (
            Time(tags[t].mjd_start, format="mjd")
            .to_datetime()
            .strftime("%Y-%m-%d %H:%M:%S")
        )
        end = (
            Time(tags[t].mjd_end, format="mjd")
            .to_datetime()
            .strftime("%Y-%m-%d %H:%M:%S")
        )
        r = (
            (start, end),
            'Analysis of the data taken when polarimeter {} was being tested (tag "{}")'.format(
                pol_name, tags[t].name
            ),
        )
        logging.info(f'Analyzing tag "{tags[t].name}"')
        logging.info(
            f"Considering the interval {r[0][0]} – {r[0][1]} for these polarimeters:"
        )
        output_dir = directory / tags[t].name
        output_dir.mkdir(exist_ok=True, parents=True)

        result_report = (
            []
        )  # type: List[Tuple[Any,Any,List[Tuple[str, Dict[str, Any]]]]] #TEMPO[POL[STATISTICHE]]
        cur_result_report = []  # type: List[Tuple[str, Dict[str, Any]]]
        result_jason = {}  # type: Dict[str, Dict[str, Dict[str, Any]]]
        cur_result_jason = {}  # type: Dict[str, Any]

        for pol in polarimeter_iterator():
            logging.info(f"polarimeter {pol}")
            cur_result_report.append((pol, analyzed_data(ds, r[0], pol)))
            cur_result_jason[pol] = analyzed_data(ds, r[0], pol)

        result_report.append((r[0], r[1], cur_result_report))
        result_jason[f"{r[0]}, {r[1]}"] = cur_result_jason

        with open(
            output_dir / f"data_analysis_ref{num_ref}_{pol_name}.json", "wt"
        ) as outf:
            json.dump(result_jason, outf)

        template = Template(filename="templates/ref2_report_2022_04_27.txt")
        with open(output_dir / f"report_ref{num_ref}_{pol_name}.md", "wt") as outf:
            print(
                template.render(
                    analysis_results=result_report,
                    analysis_date=str(datetime.now()),
                    data_storage_path=storage_path,
                    ref=num_ref,
                ),
                file=outf,
            )

        high_corr = {}
        for data_type in ("DEM", "PWR"):
            for ch in ("Q1", "Q2", "U1", "U2"):
                logging.info(
                    f'calculating the correlation matrix for "{data_type}{ch}"'
                )
                sottratti = {}
                for _, _, pol in polarimeter_iterator():
                    logging.info(f'Processing polarimeter "{pol}"')
                    try:
                        _, dem = ds.load_sci(
                            mjd_range=r[0],
                            polarimeter=pol,
                            data_type=data_type,
                            detector=ch,
                        )
                        pari = np.array(dem[::2], dtype=numpy.int64)
                        dispari = np.array(dem[1::2], dtype=numpy.int64)
                        if len(pari) != len(dispari):
                            pari = pari[0:-1:1]
                        sottratti[pol] = pari + dispari
                    except Exception as exc:
                        logging.error(
                            f'Error while processing polarimeter "{pol}": {exc}'
                        )

                try:
                    dati_df = pd.DataFrame(
                        {
                            "R0": sottratti["R0"],
                            "R1": sottratti["R1"],
                            "R2": sottratti["R2"],
                            "R3": sottratti["R3"],
                            "R4": sottratti["R4"],
                            "R5": sottratti["R5"],
                            "R6": sottratti["R6"],
                            "B0": sottratti["B0"],
                            "B1": sottratti["B1"],
                            "B2": sottratti["B2"],
                            "B3": sottratti["B3"],
                            "B4": sottratti["B4"],
                            "B5": sottratti["B5"],
                            "B6": sottratti["B6"],
                            "V0": sottratti["V0"],
                            "V1": sottratti["V1"],
                            "V2": sottratti["V2"],
                            "V3": sottratti["V3"],
                            "V4": sottratti["V4"],
                            "V5": sottratti["V5"],
                            "V6": sottratti["V6"],
                            "G0": sottratti["G0"],
                            "G1": sottratti["G1"],
                            "G2": sottratti["G2"],
                            "G3": sottratti["G3"],
                            "G4": sottratti["G4"],
                            "G5": sottratti["G5"],
                            "G6": sottratti["G6"],
                            "Y0": sottratti["Y0"],
                            "Y1": sottratti["Y1"],
                            "Y2": sottratti["Y2"],
                            "Y3": sottratti["Y3"],
                            "Y4": sottratti["Y4"],
                            "Y5": sottratti["Y5"],
                            "Y6": sottratti["Y6"],
                            "O0": sottratti["O0"],
                            "O1": sottratti["O1"],
                            "O2": sottratti["O2"],
                            "O3": sottratti["O3"],
                            "O4": sottratti["O4"],
                            "O5": sottratti["O5"],
                            "O6": sottratti["O6"],
                            "I0": sottratti["I0"],
                            "I1": sottratti["I1"],
                            "I2": sottratti["I2"],
                            "I3": sottratti["I3"],
                            "I4": sottratti["I4"],
                            "I5": sottratti["I5"],
                            "I6": sottratti["I6"],
                            "W1": sottratti["W1"],
                            "W2": sottratti["W2"],
                            "W3": sottratti["W3"],
                            "W4": sottratti["W4"],
                            "W5": sottratti["W5"],
                            "W6": sottratti["W6"],
                        }
                    )
                    corr_df = abs(dati_df.corr(method="pearson"))
                    plt.figure(figsize=(60, 35))
                    plt.title(f"from {r[0][0]} to {r[0][1]}", fontsize=40)
                    np.fill_diagonal(corr_df.values, np.NaN)
                    sns.heatmap(corr_df, annot=True, vmin=0, vmax=0.40)
                    logging.info(
                        f'creating correlation matrix from {r[0][0]} to {r[0][1]} for "{data_type}{ch}"'
                    )
                    graphic_file_name = output_dir / f"{data_type}{ch}.png"
                    plt.savefig(
                        graphic_file_name, bbox_inches="tight"
                    )  # per ridurre il margine bianco
                    plt.close("all")

                    cor = []
                    for _, _, pol1 in polarimeter_iterator():
                        for _, _, pol2 in polarimeter_iterator():
                            if (corr_df[pol1][pol2]) > 0.10 and (pol1 != pol2):
                                cor.append(
                                    (
                                        pol1,
                                        pol2,
                                        round(corr_df[pol1][pol2] * 100, 3),
                                    )
                                )

                    high_corr[f"{data_type}{ch}"] = cor
                except Exception as exc:
                    logging.error(
                        f'unable to create correlation matrix for "{data_type}{ch}": {exc}'
                    )

        template = Template(filename="templates/ref2_report_2022_05_11.txt")
        with open(output_dir / "report_corr.md", "wt") as outf:
            print(
                template.render(
                    corr=high_corr,
                    analysis_date=str(datetime.now()),
                    data_storage_path=storage_path,
                    start=r[0][0],
                    end=r[0][1],
                ),
                file=outf,
            )


if __name__ == "__main__":
    main()
