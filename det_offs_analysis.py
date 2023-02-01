# -*- encoding: utf-8 -*-

from copy import copy
import sys
from typing import Dict, List, Tuple, Union

from astropy.time import Time
import json
from matplotlib import pyplot as plt
import numpy as np

from striptease import (
    DataStorage,
    parse_polarimeters,
    polarimeter_iterator,
    Tag,
)
from striptease.tuning import read_excel

DEFAULT_POLARIMETERS = [polarimeter for _, _, polarimeter in polarimeter_iterator()]


def load_offsets(polarimeters, excel_file):
    scanners = read_excel(excel_file, ["Offset"])
    offsets = {}
    for polarimeter in polarimeters:
        scanner = scanners[polarimeter]["Offset"]
        offsets[polarimeter] = [copy(scanner.x)]
        while scanner.next() is True:
            offsets[polarimeter].append(copy(scanner.x))
        offsets[polarimeter] = np.array(offsets[polarimeter])
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
    polarimeters: Union[List[str], Tuple[str]] = ["Q1", "Q2", "U1", "U2"],
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
    tags_acq = [tag for tag in tags_test if tag.name.endswith("_ACQ")]

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
            ax[subplot].axvline(tag.mjd_end, linewidth=0.1, color="k")
        ax[subplot].legend(loc="upper right")
        ax[subplot].set_title(data_type)

    fig.tight_layout()
    return fig, ax


def analyze_test(data, polarimeter, tag_acq, detectors):
    def analyze_type(data):
        return {"mean": np.mean(data), "std": np.std(data), "nsamples": len(data)}

    analysis = {"PWR": {}, "DEM": {}, "PWR_SUM": {}, "DEM_DIFF": {}}

    pwr = data_in_range(data[polarimeter]["PWR"], tag_acq)[1]
    dem = data_in_range(data[polarimeter]["DEM"], tag_acq)[1]

    for detector in detectors:

        pwr_det = pwr[f"PWR{detector}"]
        analysis["PWR"][detector] = analyze_type(pwr[f"PWR{detector}"])

        dem_det = dem[f"DEM{detector}"]
        analysis["DEM"][detector] = analyze_type(dem[f"DEM{detector}"])

        pwr_even = pwr_det[::2]
        pwr_odd = pwr_det[1::2]
        if len(pwr_even) != len(pwr_odd):
            pwr_even = pwr_even[:-1]
        analysis["PWR_SUM"][detector] = analyze_type(pwr_even + pwr_odd)

        dem_even = dem_det[::2]
        dem_odd = dem_det[1::2]
        if len(dem_even) != len(dem_odd):
            dem_even = dem_even[:-1]
        analysis["DEM_DIFF"][detector] = analyze_type(np.abs(dem_even - dem_odd))

    return analysis


def plot_analysed_data(det_offs_analysis, polarimeter: str, offsets, detectors):
    fig, ax = plt.subplots(4, 2, figsize=(15, 30))
    # fig, ax = plt.subplots(4, 2)
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


def main():
    from argparse import ArgumentParser, RawDescriptionHelpFormatter

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

    args = parser.parse_args()

    ds = DataStorage(args.ds_path)
    polarimeters = parse_polarimeters(args.polarimeters)
    detectors = ("Q1", "Q2", "U1", "U2")
    mjd_range = (args.mjd_start, args.mjd_end)

    data = {
        polarimeter: load_data(ds, mjd_range, polarimeter, detectors, args.delta)
        for polarimeter in polarimeters
    }

    tags_all, tags_test, tag_whole_test, tags_pol, tags_acq, tags_global = load_tags(
        ds, mjd_range, test_name=args.test_name, polarimeters=polarimeters
    )

    offsets = load_offsets(polarimeters, excel_file=args.tuning_file)

    det_offs_analysis = {
        "mjd_range": mjd_range,
        "argv": sys.argv,
        "analyzed_data": {
            polarimeter: {
                int(offsets[polarimeter][i, 0]): analyze_test(
                    data, polarimeter, tags_acq[i], detectors
                )
                for i in range(len(tags_acq))
            }
            for polarimeter in polarimeters
        },
    }

    with open(f"{args.output_dir}/{args.json_output}", "w") as f:
        json.dump(det_offs_analysis, f, indent=0)

    if args.report:
        for polarimeter in polarimeters:
            fig, ax = plot_timeline(
                data, tag_whole_test, tags_global, polarimeter, detectors
            )
            fig.savefig(f"{args.output_dir}/timeline_{polarimeter}.png")

        for polarimeter in polarimeters:
            ax, fig = plot_analysed_data(
                det_offs_analysis["analyzed_data"], polarimeter, offsets, detectors
            )
            fig.savefig(f"{args.output_dir}/analysis_{polarimeter}.pdf")

        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader(searchpath="./"),
            autoescape=select_autoescape(["html", "xml"]),
        )

        template = env.get_template(args.template)
        with open(f"{args.output_dir}/{args.report_output}", "w") as f:
            print(template.render(det_offs_analysis), file=f)


if __name__ == "__main__":
    main()
