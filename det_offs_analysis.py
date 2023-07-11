# -*- encoding: utf-8 -*-

from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
from copy import copy
import logging as log

log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")
from pathlib import Path
import pickle
import sys
from typing import Dict, List, Tuple, Union

from astropy.time import Time
import json
from matplotlib import pyplot as plt
import numpy as np
from sigfig import round as sigfig_round
import xarray as xr

from striptease import (
    DataStorage,
    parse_polarimeters,
    polarimeter_iterator,
    Tag,
)
from striptease.tuning import read_excel

DEFAULT_POLARIMETERS = [polarimeter for _, _, polarimeter in polarimeter_iterator()]
SATURATION_VALUE = 524287.0


def round(*args):
    return sigfig_round(*args, cutoff=29, separation="brackets", output_type=str)


def load_offsets(polarimeters, excel_file):
    scanners = read_excel(excel_file, ["Offset"])
    offsets = {}
    for polarimeter in polarimeters:
        scanner = scanners[polarimeter]["Offset"]
        offsets[polarimeter] = [copy(scanner.x)]
        while scanner.next() is True:
            offsets[polarimeter].append(copy(scanner.x))
        offsets[polarimeter] = np.array(offsets[polarimeter], dtype="int")
    return offsets


def data_in_range(data: Tuple[Time, np.ndarray], tag: Tag) -> Tuple[Time, np.ndarray]:
    times, values = data
    index_start, index_end = np.searchsorted(times.value, [tag.mjd_start, tag.mjd_end])
    return (times[index_start:index_end], values[index_start:index_end])


def load_data(
    ds: DataStorage,
    mjd_range: Tuple[str],
    polarimeter: str,
    detectors: Union[str, List[str], Tuple[str]] = ["Q1", "Q2", "U1", "U2"],
    delta=0.0,
) -> Dict[str, Dict[str, Tuple[Time, np.ndarray]]]:
    if len(detectors) == 1:
        detectors = detectors[0]
    pwr = ds.load_sci(
        mjd_range=mjd_range,
        polarimeter=polarimeter,
        data_type="PWR",
        detector=detectors,
    )
    dem = ds.load_sci(
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
    mjd_range: Tuple[str],
    test_name: str,
    polarimeters: Union[List[str], Tuple[str]],
):
    # All tags in the time range
    tags_all = [x for x in ds.get_tags(mjd_range)]

    # All tags in the time range belonging to the test
    tags_test = [tag for tag in tags_all if tag.name.startswith(test_name)]

    # The tag that contains the whole test
    tag_whole_test = tags_test[0]

    # The tags about setting the offset for each polarimeter
    tags_pol = {
        polarimeter: [tag for tag in tags_test if tag.name.endswith(f"_{polarimeter}")]
        for polarimeter in polarimeters
    }

    # The tags with stable acquisition after setting offsets
    tags_acq = [
        tag
        for tag in tags_test
        if tag.name.endswith("_ACQ")
        and not tag.name.endswith("_PRE_ACQ")
        and not tag.name.endswith("_POST_ACQ")
    ]

    # The tags with each whole setting + acquisition step
    tags_global = [
        tag
        for tag in tags_test[1:]
        if not tag.name.endswith("_ACQ")
        and not any(map(tag.name.endswith, polarimeters))
    ]

    return tags_all, tags_test, tag_whole_test, tags_pol, tags_acq, tags_global


def plot_timeline(
    data: Dict,
    mjd_range: Tag,
    tags_global: List[Tag],
    polarimeter: str,
    detectors: Union[List[str], Tuple[str]],
    data_type: str,
):
    fig, ax = plt.subplots()
    fig.suptitle(f"{polarimeter}")

    plot_data = data_in_range(data[polarimeter][data_type], mjd_range)
    for detector in detectors:
        channel = f"{data_type}{detector}"
        ax.plot(plot_data[0].value, plot_data[1][channel], ",", label=channel)
    for tag in tags_global:
        ax.axvline(tag.mjd_end, linewidth=0.1, color="k")
    ax.legend(loc="upper right")
    # ax.set_title(data_type)
    ax.set_xlabel("$t$ [mjd]")
    ax.set_ylabel(f"{data_type} [adu]")

    fig.tight_layout()
    return fig, ax


def sigma_method(data):
    even = data[::2]
    odd = data[1::2]
    if len(even) != len(odd):
        even = even[:-1]
    return np.std(odd - even) / np.sqrt(2)


def analyze_test(data, polarimeter, tag_acq, detectors):
    def analyze_type(data):
        return {
            "mean": np.mean(data),
            "std": np.std(data),
            "sigma": sigma_method(data),
            "nsamples": len(data),
        }

    analysis = {"PWR": {}, "DEM": {}, "PWR_SUM": {}, "DEM_DIFF": {}}

    pwr = data_in_range(data[polarimeter]["PWR"], tag_acq)[1]
    dem = data_in_range(data[polarimeter]["DEM"], tag_acq)[1]

    for detector in detectors:

        pwr_det = pwr[f"PWR{detector}"]
        analysis["PWR"][detector] = analyze_type(pwr[f"PWR{detector}"])

        dem_det = dem[f"DEM{detector}"]
        analysis["DEM"][detector] = analyze_type(np.abs(dem[f"DEM{detector}"]))

        pwr_even = pwr_det[::2]
        pwr_odd = pwr_det[1::2]
        if len(pwr_even) != len(pwr_odd):
            pwr_even = pwr_even[:-1]
        analysis["PWR_SUM"][detector] = analyze_type((pwr_even + pwr_odd) / 2)

        dem_even = dem_det[::2]
        dem_odd = dem_det[1::2]
        if len(dem_even) != len(dem_odd):
            dem_even = dem_even[:-1]
        analysis["DEM_DIFF"][detector] = analyze_type(np.abs(dem_even - dem_odd) / 2)

    return analysis


def plot_analysed_data(det_offs_analysis, polarimeter: str, data_type: str, fit=None):
    fig_mean, ax_mean = plt.subplots()
    fig_std, ax_std = plt.subplots()

    offsets = det_offs_analysis.coords["offset"]
    detectors = det_offs_analysis.coords["detector"]

    for detector in detectors:
        color = next(ax_mean._get_lines.prop_cycler)["color"]
        mean = det_offs_analysis.sel(
            polarimeter=polarimeter,
            data_type=data_type,
            value="mean",
            detector=detector,
        )
        std = det_offs_analysis.sel(
            polarimeter=polarimeter, data_type=data_type, value="std", detector=detector
        )
        ax_mean.errorbar(
            offsets, mean, yerr=std, marker=".", ls="none", color=color, label=None
        )
        ax_std.plot(
            offsets, std, marker=".", ls="none", color=color, label=detector.values
        )

        if fit:
            ax_mean.plot(
                offsets,
                xr.apply_ufunc(
                    fit_function,
                    det_offs_analysis.coords["offset"],
                    fit["curvefit_coefficients"].sel(
                        param="angular_coefficient",
                        data_type=data_type,
                        detector=detector,
                        polarimeter=polarimeter,
                    ),
                    fit["curvefit_coefficients"].sel(
                        param="saturation_offset",
                        data_type=data_type,
                        detector=detector,
                        polarimeter=polarimeter,
                    ),
                ),
                color=color,
                label=detector.values,
            )
    ax_mean.legend()
    if data_type == "PWR_SUM":
        data_type = "$I$"
    # ax_mean.set_title(f"{data_type} mean")
    ax_mean.set_title(f"{polarimeter}")
    ax_mean.set_xlabel("offset")
    ax_mean.set_ylabel(f"{data_type} [adu]")
    ax_std.legend()
    ax_std.set_title(f"{polarimeter}")
    ax_std.set_xlabel("offset")
    ax_std.set_ylabel(f"{data_type} std [adu]")

    fig_mean.tight_layout()
    fig_std.tight_layout()
    plt.tight_layout()
    return fig_mean, ax_mean, fig_std, ax_std


def fit_function(offset, angular_coefficient, saturation_offset):
    #          { max                                                          for offset <= saturation_offset
    # idrain = {
    #          { max - angular_coefficient * (offset - saturation_offset)     for offset > saturation_offset
    return np.where(
        offset <= saturation_offset,
        SATURATION_VALUE,
        SATURATION_VALUE - angular_coefficient * (offset - saturation_offset),
    )


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Analyze data produced in the pretuning detector offset test",
        formatter_class=RawDescriptionHelpFormatter,
        epilog=""" """,
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILENAME",
        type=str,
        dest="output_file",
        default=None,
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
        dest="report_file",
        default="report.md",
        help="The file to write the report to (default: report.md).",
    )
    parser.add_argument(
        "--template",
        metavar="FILENAME",
        type=str,
        dest="template",
        default="templates/det_offs_analysis.txt",
        help="The report template (default templates/det_offs_analysis.txt).",
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
        default="PT_OFFS_TEST_DET_OFF",
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
    detectors=["Q1", "Q2", "U1", "U2"],
):
    data = load_data(ds, tag, polarimeter, detectors, delta)
    with open(pickle_filename, "wb") as f:
        pickle.dump(data, f)
    return data


def to_xarray(det_offs_analysis_json, polarimeter, offsets, detectors):
    data_types = ["PWR", "DEM", "PWR_SUM", "DEM_DIFF"]
    values = ["mean", "std", "nsamples"]

    all_offsets = np.sort(
        np.unique(
            np.concatenate(
                [
                    offsets[polarimeter][:, detector]
                    for detector in range(len(detectors))
                ]
            )
        )
    )
    det_offs_analysis = xr.DataArray(
        data=np.nan,
        coords=[
            ("data_type", data_types),
            ("detector", detectors),
            ("value", values),
            ("offset", all_offsets),
        ],
    )

    for data_type in data_types:
        for detector_idx in range(len(detectors)):
            detector = detectors[detector_idx]
            for value in values:
                for offset in offsets[polarimeter][:, detector_idx]:
                    det_offs_analysis.loc[
                        dict(
                            data_type=data_type,
                            detector=detector,
                            value=value,
                            offset=int(offset),
                        )
                    ] = det_offs_analysis_json[polarimeter][str(offset)][data_type][
                        detector
                    ][
                        value
                    ]

    return det_offs_analysis


def main():
    args = parse_args()

    img_types = ["pdf", "svg", "png"]
    output_dir = Path(args.output_dir)
    output_file = (
        (output_dir / args.output_file).resolve() if args.output_file else None
    )
    report_file = (output_dir / args.report_file).resolve()
    template_file = args.template
    ds_path = Path(args.ds_path)
    ds = DataStorage(ds_path)
    tuning_file = Path(args.tuning_file)
    mjd_range = (args.mjd_start, args.mjd_end)
    polarimeters = parse_polarimeters(args.polarimeters)
    detectors = ["Q1", "Q2", "U1", "U2"]
    pickle_filename = f"{output_dir}/det_offs_analysis_data"
    start_point = args.start_point

    log.info("Loading tags.")
    tags_all, tags_test, tag_whole_test, tags_pol, tags_acq, tags_global = load_tags(
        ds, mjd_range, test_name=args.test_name, polarimeters=polarimeters
    )

    data = {}
    if start_point == "none":
        log.info("Storing to pickle.")
        for polarimeter in polarimeters:
            log.info(f"Storing to pickle: {polarimeter}.")
            data[polarimeter] = store_to_pickle(
                ds,
                tag_whole_test,
                f"{pickle_filename}_{polarimeter}.pkl",
                polarimeter,
                args.delta,
                detectors,
            )
    elif start_point == "pickle":
        log.info("Loading from pickle.")
        for polarimeter in polarimeters:
            with open(f"{pickle_filename}_{polarimeter}.pkl", "rb") as f:
                log.info(f"Loading from pickle: {polarimeter}.")
                data[polarimeter] = pickle.load(f)

    log.info("Loading offsets.")
    offsets = load_offsets(polarimeters, excel_file=tuning_file)

    det_offs_analysis_json = {}
    if start_point == "none" or start_point == "pickle":
        log.info("Calculating values and storing to json")
        for polarimeter in polarimeters:
            log.info(f"Calculating values: {polarimeter}.")
            det_offs_analysis_json[polarimeter] = {
                str(offsets[polarimeter][i, 0]): analyze_test(
                    data, polarimeter, tags_acq[i], detectors
                )
                for i in range(len(tags_acq))
            }
            log.info(f"Storing to json: {polarimeter}.")
            with open(f"{output_file}_{polarimeter}.json", "w") as f:
                json.dump(det_offs_analysis_json[polarimeter], f, indent=0)
    elif start_point == "json":
        log.info("Loading values from json.")
        for polarimeter in polarimeters:
            log.info(f"Loading values from json: {polarimeter}.")
            with open(f"{output_file}_{polarimeter}.json", "r") as f:
                det_offs_analysis_json[polarimeter] = json.load(f)

    det_offs_analysis = {}
    if start_point == "none" or start_point == "pickle" or start_point == "json":
        log.info("Converting to xarray and storing to netcdf.")
        for polarimeter in polarimeters:
            log.info(f"Converting to xarray: {polarimeter}.")
            det_offs_analysis[polarimeter] = to_xarray(
                det_offs_analysis_json, polarimeter, offsets, detectors
            )
            log.info(f"Storing to netcdf: {polarimeter}.")
            det_offs_analysis[polarimeter].to_netcdf(
                f"{output_dir}/det_offs_analysis_{polarimeter}.nc"
            )
    elif start_point == "netcdf":
        log.info("Loading xarray from netcdf.")
        for polarimeter in polarimeters:
            log.info(f"Loading xarray from netcdf: {polarimeter}.")
            det_offs_analysis[polarimeter] = xr.open_dataarray(
                f"{output_dir}/det_offs_analysis_{polarimeter}.nc"
            )

    return

    pwr_fit = det_offs_analysis.sel(
        data_type="PWR_SUM", value="mean", polarimeter=polarimeters[0]
    ).plot(x="offset", hue="detector")
    # plt.savefig("plot.png")
    # return
    log.info("Fitting PWR and PWR_SUM data.")
    pwr_fit = det_offs_analysis.sel(
        data_type=["PWR", "PWR_SUM"], value="mean"
    ).curvefit("offset", fit_function)

    # print(pwr_fit.sel(data_type="PWR_SUM", polarimeter="R0", detector="Q1"))
    # print(pwr_fit.sel(data_type="PWR_SUM", polarimeter="R0", detector="Q1"))

    pwr_chi = (
        (
            (
                det_offs_analysis.sel(data_type=["PWR", "PWR_SUM"], value="mean")
                - xr.apply_ufunc(
                    fit_function,
                    det_offs_analysis.coords["offset"],
                    pwr_fit["curvefit_coefficients"].sel(
                        param="angular_coefficient", data_type=["PWR", "PWR_SUM"]
                    ),
                    pwr_fit["curvefit_coefficients"].sel(
                        param="saturation_offset", data_type=["PWR", "PWR_SUM"]
                    ),
                )
            )
            / det_offs_analysis.sel(data_type=["PWR", "PWR_SUM"], value="std")
        )
        ** 2
    ).sum(dim="offset")
    pwr_chi_reduced = pwr_chi / (len(det_offs_analysis.coords["offset"]) - 2)
    pwr_chi_sigma = np.sqrt(2 * pwr_chi) / (len(det_offs_analysis.coords["offset"]) - 2)

    # det_offs_analysis.sel(polarimeter="R0", data_type="PWR", value="mean").plot(x="offset", hue="detector", ls="", marker=".")
    # plt.show()

    # (
    # det_offs_analysis.sel(data_type=["PWR", "PWR_SUM"], value="mean")
    # - xr.apply_ufunc(
    # fit_function,
    # det_offs_analysis.coords["offset"],
    # pwr_fit["curvefit_coefficients"].sel(
    # param="angular_coefficient", data_type=["PWR", "PWR_SUM"]
    # ),
    # pwr_fit["curvefit_coefficients"].sel(
    # param="saturation_offset", data_type=["PWR", "PWR_SUM"]
    # ),
    # )
    # ).sel(data_type="PWR_SUM", detector="U1").plot(
    # x="offset", hue="polarimeter", marker="."
    # )
    # plt.xlabel("Offset")
    # plt.ylabel("$I$ (measured - fit)")
    # plt.title("")
    # plt.savefig(f"residuals_U1.{img_type}")
    # plt.show()
    # plt.close()
    # (
    # det_offs_analysis.sel(data_type=["PWR", "PWR_SUM"], value="mean")
    # - xr.apply_ufunc(
    # fit_function,
    # det_offs_analysis.coords["offset"],
    # pwr_fit["curvefit_coefficients"].sel(
    # param="angular_coefficient", data_type=["PWR", "PWR_SUM"]
    # ),
    # pwr_fit["curvefit_coefficients"].sel(
    # param="saturation_offset", data_type=["PWR", "PWR_SUM"]
    # ),
    # )
    # ).sel(data_type="PWR_SUM", detector="U2").plot(
    # x="offset", hue="polarimeter", marker="."
    # )
    # plt.show()
    # plt.close()

    if args.report:
        report_data = {
            "mjd_range": mjd_range,
            "argv": sys.argv,
            "data_file": output_file,
            "polarimeters": {
                polarimeter: {
                    "timeline": {},
                    "fit": {},
                }
                for polarimeter in polarimeters
            },
        }

        for polarimeter in polarimeters:
            for data_type in "PWR", "DEM":
                for img_type in img_types:
                    timeline_plot = (
                        output_dir / f"timeline_{polarimeter}_{data_type}.{img_type}"
                    )

                    report_data["polarimeters"][polarimeter]["timeline"][
                        data_type
                    ] = timeline_plot

                    fig, ax = plot_timeline(
                        data,
                        tag_whole_test,
                        tags_global,
                        polarimeter,
                        detectors,
                        data_type,
                    )
                    fig.savefig(timeline_plot)
                    plt.close()

            for data_type in "PWR", "DEM", "PWR_SUM", "DEM_DIFF":
                for img_type in img_types:
                    fit_mean_plot = (
                        output_dir / f"fit_{polarimeter}_{data_type}_mean.{img_type}"
                    )
                    fit_std_plot = (
                        output_dir / f"fit_{polarimeter}_{data_type}_std.{img_type}"
                    )

                    report_data["polarimeters"][polarimeter]["fit"][data_type] = {
                        "mean_plot": fit_mean_plot,
                        "std_plot": fit_std_plot,
                    }

                    if data_type == "PWR" or data_type == "PWR_SUM":
                        fig_mean, ax_mean, fig_std, ax_std = plot_analysed_data(
                            det_offs_analysis, polarimeter, data_type, pwr_fit
                        )
                    else:
                        fig_mean, ax_mean, fig_std, ax_std = plot_analysed_data(
                            det_offs_analysis, polarimeter, data_type
                        )
                    fig_mean.savefig(fit_mean_plot)
                    fig_std.savefig(fit_std_plot)
                    plt.close()

            for data_type in "PWR", "PWR_SUM":
                report_data["polarimeters"][polarimeter]["fit"][data_type]["fit"] = {
                    detector: {
                        "parameters": pwr_fit["curvefit_coefficients"]
                        .sel(
                            polarimeter=polarimeter,
                            data_type=data_type,
                            detector=detector,
                        )
                        .values,
                        "covariance": pwr_fit["curvefit_covariance"]
                        .sel(
                            polarimeter=polarimeter,
                            data_type=data_type,
                            detector=detector,
                        )
                        .values,
                        "chi": pwr_chi_reduced.sel(
                            polarimeter=polarimeter,
                            data_type=data_type,
                            detector=detector,
                        ).values.item(),
                        "chi_sigma": pwr_chi_sigma.sel(
                            polarimeter=polarimeter,
                            data_type=data_type,
                            detector=detector,
                        ).values.item(),
                    }
                    for detector in detectors
                }

        log.info("Generating Latex table.")
        for polarimeter in polarimeters:
            with open(output_dir / f"table_{polarimeter}", "w") as f:
                row = f"{polarimeter}"
                for detector in detectors:
                    fit = pwr_fit["curvefit_coefficients"].sel(
                        polarimeter=polarimeter, data_type="PWR_SUM", detector=detector
                    )
                    angular_coefficient = fit.sel(
                        param="angular_coefficient"
                    ).values.item()
                    saturation_offset = fit.sel(param="saturation_offset").values.item()
                    cov_matrix = pwr_fit["curvefit_covariance"].sel(
                        polarimeter=polarimeter, data_type="PWR_SUM", detector=detector
                    )
                    sigma_angular_coefficient = cov_matrix.isel(
                        cov_i=0, cov_j=0
                    ).values.item()
                    sigma_saturation_offset = cov_matrix.isel(
                        cov_i=1, cov_j=1
                    ).values.item()
                    covariance = cov_matrix.isel(cov_i=0, cov_j=1).values.item()
                    print(pwr_chi_reduced)
                    chi = (
                        pwr_chi_reduced.sel(
                            # polarimeter=polarimeter,
                            data_type=data_type,
                            detector=detector,
                        ).values[0],
                    )
                    sigma_chi = (
                        pwr_chi_sigma.sel(
                            # polarimeter=polarimeter,
                            data_type=data_type,
                            detector=detector,
                        ).values[0],
                    )
                    print(angular_coefficient, sigma_angular_coefficient)
                    row += (
                        f" & {detector} & {round(angular_coefficient, sigma_angular_coefficient) if sigma_angular_coefficient!=np.inf else sigfig_round(angular_coefficient, decimals=2)} & "
                        f"{round(saturation_offset, sigma_saturation_offset)} & {sigfig_round(covariance, covariance, cutoff=29, sep=tuple)[0]} & "
                        f"{round(chi[0], sigma_chi[0])} \\\\\n"
                    )
                row += "\\hline\n"
                f.write(row)
        log.info("Generating report.")
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader(searchpath="./"),
            autoescape=select_autoescape(["html", "xml"]),
        )

        template = env.get_template(template_file)
        with open(report_file, "w") as f:
            print(template.render(report_data), file=f)


if __name__ == "__main__":
    main()
