# -*- encoding: utf-8 -*-

from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
from copy import copy
import logging as log

log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")
from pathlib import Path
import pickle
from typing import Dict, List, Tuple, Union

from astropy.time import Time
import json
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from sigfig import round as sigfig_round
import xarray as xr

from striptease import (
    DataStorage,
    parse_polarimeters,
    polarimeter_iterator,
    Tag,
)
from striptease.tuning import read_excel, Scanner2D

DEFAULT_POLARIMETERS = [polarimeter for _, _, polarimeter in polarimeter_iterator()]

THRESHOLD = 524287.0


def round(*args):
    return sigfig_round(*args, cutoff=29, separation="brackets", output_type=str)


def load_idrains_and_offsets(polarimeters, lnas, excel_file):
    """Assumes a Grid or IrregularGrid 2D scanner."""
    scanners = read_excel(excel_file, lnas)
    idrains = {}
    offsets = {}
    for polarimeter in polarimeters:
        idrains[polarimeter] = {}
        offsets[polarimeter] = {}
        for lna in lnas:
            idrains[polarimeter][lna] = {}
            offsets[polarimeter][lna] = {}
            scanner = scanners[polarimeter][lna]
            if not isinstance(scanner, Scanner2D):
                raise RuntimeError(
                    f"Scanners in Excel file {excel_file} must be instances of Scanner2D."
                )
            idrains[polarimeter][lna] = [int(scanner.x)]
            offsets[polarimeter][lna] = [copy(scanner.y)]
            while scanner.next() is True:
                # Scan the first row: save all offsets
                if int(scanner.x) == idrains[polarimeter][lna][0]:
                    offsets[polarimeter][lna].append(copy(scanner.y))
                # Scan subsequent rows: save all remaining idrains
                elif not int(scanner.x) in idrains[polarimeter][lna]:
                    idrains[polarimeter][lna].append(int(scanner.x))
            idrains[polarimeter][lna] = np.array(idrains[polarimeter][lna], dtype=int)
            offsets[polarimeter][lna] = np.array(offsets[polarimeter][lna], dtype=int)

    return idrains, offsets


def data_in_range(data: Tuple[Time, np.ndarray], tag: Tag) -> Tuple[Time, np.ndarray]:
    times, values = data
    index_start, index_end = np.searchsorted(times.value, [tag.mjd_start, tag.mjd_end])
    return (times[index_start:index_end], values[index_start:index_end])


def load_data(
    ds: DataStorage,
    mjd_range: Union[
        Tuple[float, float],
        Tuple[Time, Time],
        Tuple[str, str],
        Tag,
    ],
    polarimeter: str,
    detectors: Union[str, List[str], Tuple[str]] = ["Q1", "Q2", "U1", "U2"],
    delta=0.0,
) -> Dict[str, Dict[str, Tuple[Time, np.ndarray]]]:
    if len(detectors) == 1:
        detectors = detectors[0]
    pwr = ds.load_sci(
        # mjd_range=(mjd_range.mjd_start - delta, mjd_range.mjd_end - delta), # QUESTION: is it needed to subtract delta?
        mjd_range=mjd_range,
        polarimeter=polarimeter,
        data_type="PWR",
        detector=detectors,
    )
    dem = ds.load_sci(
        # mjd_range=(mjd_range.mjd_start - delta, mjd_range.mjd_end - delta), # QUESTION: is it needed to subtract delta?
        mjd_range=mjd_range,
        polarimeter=polarimeter,
        data_type="DEM",
        detector=detectors,
    )
    if isinstance(detectors, str):
        pwr = (
            Time(pwr[0].value + delta, format="mjd"),
            pwr[1].astype([(f"PWR{detectors}", pwr[1].dtype)]),
        )
        dem = (
            Time(dem[0].value + delta, format="mjd"),
            dem[1].astype([(f"DEM{detectors}", dem[1].dtype)]),
        )
    else:
        pwr = (Time(pwr[0].value + delta, format="mjd"), pwr[1])
        dem = (Time(dem[0].value + delta, format="mjd"), dem[1])

    return {"PWR": pwr, "DEM": dem}


def load_tags(
    ds: DataStorage,
    mjd_range: Union[
        Tuple[float, float],
        Tuple[Time, Time],
        Tuple[str, str],
        Tag,
    ],
    test_name: str,
    polarimeters: Union[List[str], Tuple[str]] = ["Q1", "Q2", "U1", "U2"],
    lnas=["HA1", "HA2", "HA3", "HB1", "HB2", "HB3"],
):
    # All tags in the time range
    tags_all = [x for x in ds.get_tags(mjd_range)]

    # All tags in the time range belonging to the test
    tags_test = [tag for tag in tags_all if tag.name.startswith(test_name)]

    # The tags that contain the tests for each LNA
    tags_test_lna = {
        lna: [
            tag
            for tag in tags_test
            if tag.name.startswith(f"{test_name}_{lna}")
            or tag.name.startswith(f"{test_name}_LNA_{lna}")
            or tag.name.startswith(f"{test_name}_LNA_TEST_{lna}")
            or tag.name.startswith(f"{test_name}_LNA_TEST_LNA_{lna}")
        ]
        for lna in lnas
    }

    # Fix mjd_end = -1. problem
    for lna in lnas:
        if tags_test_lna[lna][0].mjd_end < 0.0:
            tag_reset = next(
                tag
                for tag in tags_all
                if tag.name == f"{test_name}_LNA_RESET_LNA_{lna}"
            )
            tags_test_lna[lna][0].mjd_end = tag_reset.mjd_start

    # The tags about setting the offset for each polarimeter
    tags_pol = {
        lna: {
            polarimeter: [
                tag
                for tag in tags_test_lna[lna]
                if tag.name.find(f"_{polarimeter}_") != -1
            ]
            for polarimeter in polarimeters
        }
        for lna in ("HA1", "HA2", "HA3", "HB1", "HB2", "HB3")
    }

    # The tags with stable acquisition after setting offsets
    tags_acq = {
        lna: [tag for tag in tags_test_lna[lna] if tag.name.endswith("_ACQ")]
        for lna in ("HA1", "HA2", "HA3", "HB1", "HB2", "HB3")
    }

    # The tags with each whole setting + acquisition step
    tags_global = {
        lna: [
            tag
            for tag in tags_test_lna[lna]
            if not tag.name.endswith("_ACQ")
            and all(
                [
                    tag.name.find(polarimeter) == -1
                    for polarimeter in DEFAULT_POLARIMETERS
                ]
            )
        ]
        for lna in ("HA1", "HA2", "HA3", "HB1", "HB2", "HB3")
    }

    return tags_all, tags_test, tags_test_lna, tags_pol, tags_acq, tags_global


def plot_timeline(
    data: Dict,
    mjd_range: Tag,
    tags_global: List[Tag],
    polarimeter: str,
    detectors: Union[List[str], Tuple[str]],
):
    fig, ax = plt.subplots(1, 2, figsize=(15, 8))
    # fig, ax = plt.subplots(1, 2)
    fig.suptitle(f"{polarimeter}")

    for data_type, subplot in ("PWR", 0), ("DEM", 1):
        plot_data = data_in_range(data[polarimeter][data_type], mjd_range)
        for detector in detectors:
            channel = f"{data_type}{detector}"
            ax[subplot].plot(
                plot_data[0].value, plot_data[1][channel], ",", label=channel
            )
        for tag in tags_global:
            ax[subplot].axvline(tag.mjd_end, linewidth=0.05, color="k")
        ax[subplot].legend(loc="upper right")
        ax[subplot].set_title(data_type)

    fig.tight_layout()
    return fig, ax


def sigma_method(data):
    even = data[::2]
    odd = data[1::2]
    if len(even) != len(odd):
        even = even[:-1]
    return np.std(odd - even) / np.sqrt(2)


def analyze_test(
    data: Dict,
    tags_acq: List[Tag],
    detectors: List[str],
    idrains: List[int],
    offsets: List[int],
):
    def analyze_type(data):
        return np.mean(data), np.std(data), sigma_method(data), len(data)

    analysis = {
        data_type: {
            detector: {
                value: [[None] * len(offsets) for _ in range(len(idrains))]
                for value in ("mean", "std", "sigma", "nsamples")
            }
            for detector in detectors
        }
        for data_type in ("PWR", "DEM", "PWR_SUM", "DEM_DIFF")
    }

    i = 0
    for idrain in range(len(idrains)):
        for offset in range(len(offsets)):
            tag_acq = tags_acq[i]
            pwr = data_in_range(data["PWR"], tag_acq)[1]
            dem = data_in_range(data["DEM"], tag_acq)[1]

            for detector in detectors:
                pwr_det = pwr[f"PWR{detector}"]
                (
                    analysis["PWR"][detector]["mean"][idrain][offset],
                    analysis["PWR"][detector]["std"][idrain][offset],
                    analysis["PWR"][detector]["sigma"][idrain][offset],
                    analysis["PWR"][detector]["nsamples"][idrain][offset],
                ) = analyze_type(pwr_det)

                dem_det = dem[f"DEM{detector}"]
                (
                    analysis["DEM"][detector]["mean"][idrain][offset],
                    analysis["DEM"][detector]["std"][idrain][offset],
                    analysis["DEM"][detector]["sigma"][idrain][offset],
                    analysis["DEM"][detector]["nsamples"][idrain][offset],
                ) = analyze_type(dem_det)

                pwr_even = pwr_det[::2]
                pwr_odd = pwr_det[1::2]
                if len(pwr_even) != len(pwr_odd):
                    pwr_even = pwr_even[:-1]
                (
                    analysis["PWR_SUM"][detector]["mean"][idrain][offset],
                    analysis["PWR_SUM"][detector]["std"][idrain][offset],
                    analysis["PWR_SUM"][detector]["sigma"][idrain][offset],
                    analysis["PWR_SUM"][detector]["nsamples"][idrain][offset],
                ) = analyze_type((pwr_even + pwr_odd) / 2)

                dem_even = dem_det[::2]
                dem_odd = dem_det[1::2]
                if len(dem_even) != len(dem_odd):
                    dem_even = dem_even[:-1]
                (
                    analysis["DEM_DIFF"][detector]["mean"][idrain][offset],
                    analysis["DEM_DIFF"][detector]["std"][idrain][offset],
                    analysis["DEM_DIFF"][detector]["sigma"][idrain][offset],
                    analysis["DEM_DIFF"][detector]["nsamples"][idrain][offset],
                ) = analyze_type(np.abs(dem_even - dem_odd) / 2)

            i = i + 1
    return analysis


def plot_analysed_data(det_offs_analysis, polarimeter: str, offsets, detectors):
    fig, ax = plt.subplots(4, 2, figsize=(15, 30))
    fig.suptitle(f"{polarimeter}")

    offsets = offsets[polarimeter][:, 0]

    for (i, j, value) in (
        (0, 0, "PWR"),
        (0, 1, "DEM"),
        (1, 0, "PWR_SUM"),
        (1, 1, "DEM_DIFF"),
    ):
        for detector in detectors:
            mean = np.array(
                [
                    det_offs_analysis[polarimeter][offset][value][detector]["mean"]
                    for offset in offsets
                ]
            )
            std = np.array(
                [
                    det_offs_analysis[polarimeter][offset][value][detector]["std"]
                    for offset in offsets
                ]
            )
            ax[i, j].errorbar(
                offsets, mean, yerr=std, marker=".", ls="none", label=detector
            )
            ax[i + 2, j].plot(offsets, std, marker=".", ls="none")
        ax[i, j].set_title(f"{value} mean")
        ax[i + 2, j].set_title(f"{value} std")

    fig.tight_layout()
    plt.tight_layout()
    return ax, fig


def fit_function(offset, angular_coefficient, saturation_offset):
    #          { threshold                                                          for offset <= saturation_offset
    # idrain = {
    #          { threshold - angular_coefficient * (offset - saturation_offset)     for offset > saturation_offset
    return np.where(
        offset <= saturation_offset,
        THRESHOLD,
        THRESHOLD - angular_coefficient * (offset - saturation_offset),
    )


def fit_offsets(lna_analysis: xr.DataArray):
    fit = lna_analysis.sel(data_type=["PWR", "PWR_SUM"], value="mean").curvefit(
        "offset", fit_function
    )

    # print(fit["curvefit_coefficients"].sel(data_type="PWR", detector="Q1", lna="HA1"))
    # print(fit["curvefit_coefficients"].sel(data_type="PWR", detector="Q1", lna="HA2"))

    pwr_chi = (
        (
            (
                lna_analysis.sel(data_type=["PWR", "PWR_SUM"], value="mean")
                - xr.apply_ufunc(
                    fit_function,
                    lna_analysis.coords["offset"],
                    fit["curvefit_coefficients"].sel(
                        param="angular_coefficient", data_type=["PWR", "PWR_SUM"]
                    ),
                    fit["curvefit_coefficients"].sel(
                        param="saturation_offset", data_type=["PWR", "PWR_SUM"]
                    ),
                )
            )
            / lna_analysis.sel(data_type=["PWR", "PWR_SUM"], value="std")
        )
        ** 2
    ).sum(dim="offset")
    pwr_chi_reduced = pwr_chi / (len(lna_analysis.coords["offset"]) - 2)
    pwr_chi_sigma = np.sqrt(2 * pwr_chi) / (len(lna_analysis.coords["offset"]) - 2)

    print("Sigmas:")
    lna_analysis.sel(data_type="PWR", value="std")
    print("Chi square:")
    print(pwr_chi_reduced.sel(data_type="PWR"))
    print("Chi square sigma:")
    print(pwr_chi_sigma.sel(data_type="PWR"))

    # lna_analysis.sel(polarimeter="R0", data_type="PWR_SUM", value="mean", detector="Q1").plot(x="offset", hue= "idrain", marker=".", linestyle="")
    # for lna in lna_analysis.coords["lna"].values:
    # for idrain in lna_analysis.coords["idrain"].values:
    #    plt.plot(
    #        x=lna_analysis.coords["offset"].values,
    #        y=xr.apply_ufunc(
    #            fit_function,
    #            lna_analysis.coords["offset"].values,
    #            fit["curvefit_coefficients"].sel(param="angular_coefficient", polarimeter="R0", data_type="PWR", lna=lna, idrain=idrain, detector="Q1"),
    #            fit["curvefit_coefficients"].sel(param="saturation_offset", polarimeter="R0", data_type="PWR", lna=lna, idrain=idrain, detector="Q1")
    #        ),
    #        output_core_dims=("idrain"),
    #        vectorize=True
    #    )
    # plt.plot(
    # lna_analysis.coords["offset"].values,
    # fit_function(
    # lna_analysis.coords["offset"].values,
    # fit["curvefit_coefficients"].sel(param="angular_coefficient", polarimeter="R0", data_type="PWR_SUM", lna=lna, idrain=idrain, detector="Q1").values,
    # fit["curvefit_coefficients"].sel(param="saturation_offset", polarimeter="R0", data_type="PWR_SUM", lna=lna, idrain=idrain, detector="Q1").values
    # )
    # ),
    # plt.legend('', frameon=False)
    # plt.show()

    # for lna in "HA1", "HA2", "HA3":
    # print(fit["curvefit_coefficients"].sel(param="angular_coefficient", polarimeter="R0", data_type="PWR").reset_index("lna_idrain"))
    # plot = fit["curvefit_coefficients"].sel(param="angular_coefficient", polarimeter="R0", data_type="PWR_SUM").plot(x="idrain", hue="lna", col="detector", col_wrap=2, marker=".", sharex=False, sharey=False)
    plot = (
        fit["curvefit_coefficients"]
        .sel(param="angular_coefficient", polarimeter="R0", data_type="PWR")
        .reset_index("lna_idrain")
        .plot(
            x="idrain",
            col="detector",
            hue="lna",
            col_wrap=2,
            marker=".",
            linestyle="",
            sharex=False,
            sharey=False,
        )
    )
    plot.set_ylabels("angular coefficient")
    plt.show()
    plot = (
        fit["curvefit_coefficients"]
        .sel(param="saturation_offset", polarimeter="R0", data_type="PWR")
        .plot(
            x="idrain",
            hue="lna",
            col="detector",
            col_wrap=2,
            marker=".",
            linestyle="",
            sharex=False,
            sharey=False,
        )
    )
    plot.set_ylabels("saturation offset")
    plt.show()

    np.abs(
        lna_analysis.sel(
            polarimeter="R0",
            data_type="DEM",
            value="mean",
            detector="Q1",
            lna="HA1",
            idrain=2000,
        )
    ).plot(x="offset", marker=".", linestyle="")
    plt.show()


def saturates(data: xr.DataArray, threshold=THRESHOLD):
    return data >= threshold


def analyze(lna_analysis: xr.DataArray, polarimeter: str, output_dir: Path):
    img_types = ["png", "pdf", "svg"]
    lnas = ["HA1", "HA2", "HA3", "HB1", "HB2", "HB3"]
    detectors = ["Q1", "Q2", "U1", "U2"]

    # Fit I(offs)
    pwr_fit_offset = lna_analysis.sel(data_type="PWR_SUM", value="mean").curvefit(
        "offset", fit_function
    )

    mean = {}
    std = {}
    for lna in lnas:
        mean[lna] = (
            pwr_fit_offset["curvefit_coefficients"]
            .sel(param="angular_coefficient", lna=lna)
            .mean(dim="idrain")
        )
        std[lna] = (
            pwr_fit_offset["curvefit_coefficients"]
            .sel(param="angular_coefficient", lna=lna)
            .std(dim="idrain")
        )

    x = np.argwhere(
        np.array(
            np.logical_not(
                saturates(lna_analysis.sel(value="mean", data_type="PWR_SUM")).any(
                    dim=("lna_idrain")
                )
            )
        )
    )
    old_detector = None
    min_non_sat_offs = {detector: "/" for detector in detectors}
    for y in x:
        detector = (lna_analysis.coords["detector"][y[0]].values.item(),)
        if detector == old_detector:
            continue
        old_detector = detector
        offset = (lna_analysis.coords["offset"][y[1]].values.item(),)
        min_non_sat_offs[detector[0]] = offset[0]

    for lna in lnas:
        for detector in detectors:
            plt.errorbar(
                lna_analysis.sel(lna=lna).coords["idrain"],
                lna_analysis.sel(
                    data_type="PWR_SUM",
                    value="mean",
                    lna=lna,
                    detector=detector,
                    offset=2400,
                ),
                lna_analysis.sel(
                    data_type="PWR_SUM",
                    value="std",
                    lna=lna,
                    detector="Q1",
                    offset=2400,
                ),
                fmt=".-",
                label=detector,
            )
            plt.title(f"{polarimeter} {lna}")
            plt.xlabel("idrain [$\\mu$A]")
            plt.ylabel("$I$ [adu]")
            plt.legend()
            plt.tight_layout()
        for img_type in img_types:
            plt.savefig(output_dir / f"id_s_{polarimeter}_{lna}.{img_type}")
        plt.close()
        pwr_fit_offset["curvefit_coefficients"].sel(
            param="saturation_offset", lna=lna
        ).plot(x="idrain", hue="detector", marker=".")
        plt.title(f"{polarimeter} {lna}")
        plt.xlabel("idrain [$\\mu$A]")
        plt.ylabel("Saturation offset")
        plt.legend(detectors)
        plt.tight_layout()
        for img_type in img_types:
            plt.savefig(output_dir / f"sat_off_{polarimeter}_{lna}.{img_type}")
        plt.close()

    with open(output_dir / f"table_{polarimeter}", "w") as f:
        row = f"{polarimeter}"
        for lna in lnas:
            row += f" & Ang. coeff. {lna}"
            for detector in detectors:
                mean_angular_coefficient = (
                    mean[lna].sel(detector=detector).values.item()
                )
                std_angular_coefficient = std[lna].sel(detector=detector).values.item()

                row += f" & {round(mean_angular_coefficient, std_angular_coefficient) if std_angular_coefficient!=np.inf else sigfig_round(mean_angular_coefficient, decimals=2)}"
            row += " \\\\\n"

        for lna in lnas:
            row += f" & Idrain min {lna}"
            for detector in detectors:
                inversion_idrain = int(
                    lna_analysis.sel(
                        data_type="PWR_SUM",
                        value="mean",
                        lna=lna,
                        detector=detector,
                        offset=2400,
                    ).idxmin(dim="idrain")
                )
                row += f" & {inversion_idrain}"
            row += " \\\\\n"
        row += " & Non sat. off. "
        for detector in detectors:
            row += f" & {min_non_sat_offs[detector]}"
        row += " \\\\\n\\hline\n"
        f.write(row)

    return

    # Look for idrains that don't saturate for all offsets
    print("Look for idrains that don't saturate for all offsets")
    x = np.argwhere(
        np.array(
            np.logical_not(
                saturates(
                    lna_analysis.sel(value="mean", data_type=["PWR", "PWR_SUM"])
                ).any(dim=("data_type", "detector", "offset"))
            )
        )
    )
    for y in x:
        print(
            lna_analysis.coords["polarimeter"][y[0]].values,
            lna_analysis.coords["lna_idrain"][y[1]].values,
        )

    print("Look for offsets that don't saturate for all idrains")
    x = np.argwhere(
        np.array(
            np.logical_not(
                saturates(
                    lna_analysis.sel(value="mean", data_type=["PWR", "PWR_SUM"])
                ).any(dim=("lna_idrain", "data_type", "detector"))
            )
        )
    )
    for y in x:
        print(
            lna_analysis.coords["polarimeter"][y[0]].values,
            lna_analysis.coords["offset"][y[1]].values,
        )

    # zero = lna_analysis.sel(polarimeter="R0", lna="HA1", data_type="PWR_SUM", detector="Q1", idrain=0)
    # zero.sel(value="sigma").plot()
    # zero.sel(value="std").plot()
    # plt.show()
    # (zero.sel(value="sigma") / zero.sel(value="std")).plot()
    # plt.show()

    x = np.argwhere(
        np.array(
            np.logical_not(
                saturates(
                    lna_analysis.sel(value="mean", data_type=["PWR", "PWR_SUM"])
                ).any(dim=("lna_idrain", "data_type", "detector"))
            )
        )
    )


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Analyze data produced in the pretuning lna idrain and offset test",
        formatter_class=RawDescriptionHelpFormatter,
        epilog=""" """,
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILENAME",
        type=str,
        dest="json_output",
        default="",
        help="Name of the file where to write the analyzed data output (in JSON format). "
        "If not provided, the output will be sent to stdout.",
    )
    parser.add_argument(
        "--no-report",
        action="store_false",
        dest="report",
        help="Don't generate a report.",
    )
    parser.add_argument(
        "--report-output",
        metavar="FILENAME",
        type=str,
        dest="report_output",
        default="report.md",
        help="The file to write the report to (default: report.md).",
    )
    parser.add_argument(
        "--template",
        metavar="FILENAME",
        type=str,
        dest="template",
        default="templates/det_offs_analysis.txt",
        help="The report template (default templates/lna_analysis.txt).",
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIRECTORY",
        type=str,
        dest="output_dir",
        default="../reports",
        help="All output filenames are relative to this directory, where also plots are saved.",
    )
    parser.add_argument(
        "--data-storage",
        metavar="DIRECTORY",
        type=str,
        dest="ds_path",
        default="../HDF5",
        help="The directory containing the HDF5 database (default: ../HDF5).",
    )
    parser.add_argument(
        "--mjd-start",
        metavar="TIME",
        type=str,
        dest="mjd_start",
        help="The beginning of the test (can be a MJD value or a YYYY-MM-DD hh:mm:ss string).",
    )
    parser.add_argument(
        "--mjd-end",
        metavar="TIME",
        type=str,
        dest="mjd_end",
        help="The end of the test (can be a MJD value or a YYYY-MM-DD hh:mm:ss string).",
    )
    parser.add_argument(
        "--polarimeters",
        metavar="POLARIMETER",
        type=str,
        nargs="+",
        default=DEFAULT_POLARIMETERS,
        help="Name of the polarimeters/module to test. Valid names "
        'are "G4", "W3", "O" (meaning all polarimeters in board O), "OQ" (meaning all Q polarimeters '
        'in board Q), "OW" (meaning the W polarimeter on board O), "Q" (meaning all Q polarimeters) or "W" '
        '(meaning all W polarimeters). Can be "all" (which is the default).',
    )
    parser.add_argument(
        "--delta",
        metavar="DELTA",
        type=float,
        dest="delta",
        default=0.0,
        help="The time difference between the tags and the scientific data (in days). Default: 0.",
    )
    parser.add_argument(
        "--test-name",
        metavar="NAME",
        type=str,
        dest="test_name",
        default="PT_LNA_TEST",
        help="The name of the test, at the beginning of tags.",
    )
    parser.add_argument(
        "--tuning-file",
        metavar="FILENAME",
        type=str,
        dest="tuning_file",
        default="data/pretuning_closed_loop_warm.xlsx",
        help="The file containing the scanning strategy.",
    )
    parser.add_argument(
        "--start-point",
        choices=("none", "pickle", "json", "netcdf"),
        dest="start_point",
        default="none",
        help='The file from which the analysis shall start: "none" means starting from the raw HDF5 database. '
        '"pickle" starts from a pickle containing the data. "json" starts from a json containing analyzed data. '
        '"netcdf" starts from a structured xarray containing analyzed data.',
    )

    return parser.parse_args()


def store_to_pickle(
    ds: DataStorage,
    tag: Tag,
    pickle_filename: str,
    polarimeter: str,
    delta: float,
    detectors: List[str],
):
    data = load_data(ds, tag, polarimeter, detectors, delta)
    with open(pickle_filename, "wb") as f:
        pickle.dump(data, f)
    return data


def to_xarray(
    lna_analysis_json: Dict,
    polarimeter: str,
    idrains: Dict,
    offsets: Dict,
    lnas: List[str],
    detectors: List[str],
):
    data_types = ["PWR", "DEM", "PWR_SUM", "DEM_DIFF"]
    values = ["mean", "std", "sigma", "nsamples"]
    all_offsets = np.sort(
        np.unique(
            np.concatenate(
                [
                    offsets[polarimeter][lna][:, detector]
                    for lna in lnas
                    for detector in range(len(detectors))
                ]
            )
        )
    )

    coords = [(lna, idrain) for lna in lnas for idrain in idrains[polarimeter][lna]]
    idx = pd.MultiIndex.from_tuples(coords, names=("lna", "idrain"))

    lna_analysis = xr.DataArray(
        data=np.nan,
        coords=[
            ("lna_idrain", idx),
            ("data_type", data_types),
            ("detector", detectors),
            ("value", values),
            ("offset", all_offsets),
        ],
    )

    for lna in lnas:
        log.info(f"Converting to xarray: {polarimeter} {lna}.")
        for data_type in data_types:
            for detector_idx in range(len(detectors)):
                for value in values:
                    for offset_idx in range(
                        len(offsets[polarimeter][lna][:, detector_idx])
                    ):
                        for idrain_idx in range(len(idrains[polarimeter][lna])):
                            lna_analysis.loc[
                                dict(
                                    lna=lna,
                                    data_type=data_type,
                                    detector=detectors[detector_idx],
                                    value=value,
                                    idrain=idrains[polarimeter][lna][idrain_idx],
                                    offset=offsets[polarimeter][lna][
                                        offset_idx, detector_idx
                                    ],
                                )
                            ] = lna_analysis_json[polarimeter][lna][data_type][
                                detectors[detector_idx]
                            ][
                                value
                            ][
                                idrain_idx
                            ][
                                offset_idx
                            ]

    return lna_analysis


def main():
    args = parse_args()

    ds = DataStorage(args.ds_path)
    polarimeters = parse_polarimeters(args.polarimeters)
    detectors = ["Q1", "Q2", "U1", "U2"]
    lnas = ["HA1", "HA2", "HA3", "HB1", "HB2", "HB3"]
    mjd_range = (args.mjd_start, args.mjd_end)
    output_dir = Path(args.output_dir)
    start_point = args.start_point
    pickle_filename = f"{output_dir}/lna_analysis_data"

    log.info("Loading tags.")
    tags_all, tags_test, tags_test_lna, tags_pol, tags_acq, tags_global = load_tags(
        ds, mjd_range, test_name=args.test_name, polarimeters=polarimeters
    )

    # tag = tags_test_lna["HA1"][0]
    # polarimeter = "R0"
    # data = {}
    # data[polarimeter] = load_data(ds, tag, polarimeter, ["Q1"], args.delta)
    # fig, ax = plot_timeline(data, tag, tags_global["HA1"], polarimeter, ["Q1"])
    # fig.show()
    # input()
    # return

    data = {}
    if start_point == "none":
        log.info("Storing to pickle.")
        for polarimeter in polarimeters:
            log.info(f"Storing to pickle: {polarimeter}.")
            data[polarimeter] = {}
            for lna in lnas:
                tag = tags_test_lna[lna][0]
                data[polarimeter][lna] = {}
                log.info(f"Storing to pickle: {polarimeter} {lna}.")
                data[polarimeter][lna] = store_to_pickle(
                    ds,
                    tag,
                    f"{pickle_filename}_{polarimeter}_{lna}.pkl",
                    polarimeter,
                    args.delta,
                    detectors,
                )
    elif start_point == "pickle":
        log.info("Loading from pickle.")
        for polarimeter in polarimeters:
            log.info(f"Loading from pickle: {polarimeter}.")
            data[polarimeter] = {}
            for lna in lnas:
                log.info(f"Loading from pickle: {polarimeter} {lna}.")
                with open(f"{pickle_filename}_{polarimeter}_{lna}.pkl", "rb") as f:
                    data[polarimeter][lna] = pickle.load(f)

    log.info("Loading idrains and offsets.")
    idrains, offsets = load_idrains_and_offsets(
        polarimeters, lnas, excel_file=args.tuning_file
    )

    lna_analysis_json = {}
    if start_point == "none" or start_point == "pickle":
        log.info("Calculating values and storing to json.")
        for polarimeter in polarimeters:
            log.info(f"Calculating values: {polarimeter}.")
            lna_analysis_json[polarimeter] = {}
            for lna in lnas:
                log.info(f"Calculating values: {polarimeter} {lna}.")
                lna_analysis_json[polarimeter][lna] = analyze_test(
                    data[polarimeter][lna],
                    tags_acq[lna],
                    detectors,
                    idrains[polarimeter][lna],
                    offsets[polarimeter][lna],
                )

            lna_analysis_json[polarimeter]["mjd_range"] = mjd_range
            log.info(f"Storing to json: {polarimeter}.")
            with open(f"{output_dir}/{args.json_output}_{polarimeter}.json", "w") as f:
                json.dump(lna_analysis_json[polarimeter], f, indent=5)
    elif start_point == "json":
        log.info("Loading values from json.")
        for polarimeter in polarimeters:
            log.info(f"Loading values from json: {polarimeter}.")
            with open(f"{output_dir}/{args.json_output}_{polarimeter}.json", "r") as f:
                lna_analysis_json[polarimeter] = json.load(f)

    lna_analysis = {}
    if start_point == "none" or start_point == "pickle" or start_point == "json":
        log.info("Converting to xarray and storing to netcdf.")
        for polarimeter in polarimeters:
            log.info(f"Converting to xarray: {polarimeter}.")
            lna_analysis[polarimeter] = to_xarray(
                lna_analysis_json, polarimeter, idrains, offsets, lnas, detectors
            )
            log.info(f"Storing to netcdf: {polarimeter}.")
            lna_analysis[polarimeter].reset_index("lna_idrain").to_netcdf(
                f"{output_dir}/lna_analysis_{polarimeter}.nc"
            )
    elif start_point == "netcdf":
        log.info("Loading xarray from netcdf.")
        for polarimeter in polarimeters:
            log.info(f"Loading xarray from netcdf: {polarimeter}.")
            lna_analysis[polarimeter] = xr.open_dataarray(
                f"{output_dir}/lna_analysis_{polarimeter}.nc"
            ).set_index(lna_idrain=["lna", "idrain"])

    log.info("Analyzing data.")
    for polarimeter in polarimeters:
        log.info(f"Analyzing data: {polarimeter}.")
        analyze(lna_analysis[polarimeter], polarimeter, output_dir)


if __name__ == "__main__":
    main()
