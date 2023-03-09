# -*- encoding: utf-8 -*-

from copy import copy
import logging as log

log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")
from typing import Dict, List, Tuple, Union
from pathlib import Path
import pickle


from astropy.time import Time
from matplotlib import pyplot as plt
import numpy as np

from striptease import (
    DataStorage,
    get_lna_num,
    parse_polarimeters,
    polarimeter_iterator,
    Tag,
)
from striptease.tuning import read_excel

DEFAULT_POLARIMETERS = [polarimeter for _, _, polarimeter in polarimeter_iterator()]


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


def load_hk(
    ds: DataStorage,
    mjd_range: Tuple[str],
    polarimeter: str,
    lna: str,
    detectors: Union[str, List[str], Tuple[str]] = ["Q1", "Q2", "U1", "U2"],
    delta=0.0,
) -> Dict[str, Dict[str, Tuple[Time, np.ndarray]]]:
    if len(detectors) == 1:
        detectors = detectors[0]

    lna_num = get_lna_num(lna)

    idrain = ds.load_hk(
        mjd_range=(mjd_range.mjd_start - delta, mjd_range.mjd_end - delta),
        group="BIAS",
        subgroup=f"POL_{polarimeter}",
        par=f"ID{lna_num}_HK",
    )
    vgate = ds.load_hk(
        mjd_range=(mjd_range.mjd_start - delta, mjd_range.mjd_end - delta),
        group="BIAS",
        subgroup=f"POL_{polarimeter}",
        par=f"VG{lna_num}_HK",
    )
    vdrain = ds.load_hk(
        mjd_range=(mjd_range.mjd_start - delta, mjd_range.mjd_end - delta),
        group="BIAS",
        subgroup=f"POL_{polarimeter}",
        par=f"VD{lna_num}_HK",
    )

    idrain = (Time(idrain[0].value + delta, format="mjd"), idrain[1])
    vgate = (Time(vgate[0].value + delta, format="mjd"), vgate[1])
    vdrain = (Time(vdrain[0].value + delta, format="mjd"), vdrain[1])

    return {"idrain": idrain, "vgate": vgate, "vdrain": vdrain}


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

    # The tags that contain the tests for each LNA
    tags_test_lna = {
        lna: [
            tag
            for tag in tags_test
            if tag.name.startswith(f"{test_name}_{lna}")
            or tag.name.startswith(f"{test_name}_LNA_{lna}")
            or tag.name.startswith(f"{test_name}_TEST_{lna}")
            or tag.name.startswith(f"{test_name}_TEST_LNA_{lna}")
        ]
        for lna in ("HA1", "HA2", "HA3", "HB1", "HB2", "HB3")
    }

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
            and not any(map(tag.name.find, polarimeters))
        ]
        for lna in ("HA1", "HA2", "HA3", "HB1", "HB2", "HB3")
    }

    return tags_all, tags_test, tags_test_lna, tags_pol, tags_acq, tags_global


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
        dest="polarimeters",
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
        default="data/pretuning_closed_loop_fixed_offset_warm.xlsx",
        help="The file containing the scanning strategy.",
    )

    args = parser.parse_args()

    ds = DataStorage(args.ds_path)
    polarimeters = parse_polarimeters(args.polarimeters)
    lnas = ["HA1", "HA2", "HA3", "HB1", "HB2", "HB3"]
    detectors = ["Q1", "Q2", "U1", "U2"]
    mjd_range = (args.mjd_start, args.mjd_end)
    output_dir = Path(args.output_dir)
    pickle_filename = output_dir / "transconductance_data"
    img_types = ["pdf", "svg", "png"]

    tags_all, tags_test, tags_test_lna, tags_pol, tags_acq, tags_global = load_tags(
        ds, mjd_range, test_name=args.test_name, polarimeters=polarimeters
    )

    store_to_pickle = False
    if store_to_pickle:
        log.log(log.INFO, "Storing in pickle")
        for polarimeter in polarimeters:
            for lna in lnas:
                with open(f"{pickle_filename}_{polarimeter}_{lna}.pkl", "wb") as f:
                    log.log(log.INFO, f"Storing in pickle: {polarimeter} {lna}")
                    tag = tags_test_lna[lna][0]
                    pickle.dump(
                        load_hk(ds, tag, polarimeter, lna, detectors, args.delta), f
                    )
        return

    idrains, offsets = load_idrains_and_offsets(
        polarimeters, lnas, excel_file=args.tuning_file
    )

    analyze = True
    if analyze:
        transconductance_json = {}
        for polarimeter in polarimeters:
            log.info(f"Analyzing polarimeter {polarimeter}")
            transconductance_json[polarimeter] = {}
            for lna in lnas:
                log.info(f"Analyzing polarimeter {polarimeter}: LNA {lna}")
                with open(f"{pickle_filename}_{polarimeter}_{lna}.pkl", "rb") as f:
                    log.info(f"Loading data: {polarimeter} {lna}")
                    data = pickle.load(f)
                transconductance_json[polarimeter][lna] = {
                    "raw": {hk: data[hk][1] for hk in ("idrain", "vgate", "vdrain")},
                    "analyzed": {
                        hk: {"mean": [], "median": [], "std": [], "nsamples": []}
                        for hk in ("idrain", "vgate", "vdrain")
                    },
                }
                for idrain_idx in range(len(idrains[polarimeter][lna])):
                    for hk in "idrain", "vgate", "vdrain":
                        hk_data = []
                        for offset_idx in range(len(offsets[polarimeter][lna])):
                            tag = tags_acq[lna][idrain_idx * len(offsets) + offset_idx]
                            hk_data += data_in_range(data[hk], tag)[1].tolist()
                        transconductance_json[polarimeter][lna]["analyzed"][hk][
                            "mean"
                        ].append(np.mean(hk_data))
                        transconductance_json[polarimeter][lna]["analyzed"][hk][
                            "median"
                        ].append(np.median(hk_data))
                        transconductance_json[polarimeter][lna]["analyzed"][hk][
                            "std"
                        ].append(np.std(hk_data))
                        transconductance_json[polarimeter][lna]["analyzed"][hk][
                            "nsamples"
                        ].append(len(hk_data))

        # with open(f"{args.output_dir}/{args.json_output}", "w") as f:
        # json.dump(transconductance_json, f, indent=5)

    # else:
    # transconductance_json = json.load(f"{args.output_dir}/{args.json_output}")

    # Convert to np array
    data = {}
    for polarimeter in polarimeters:
        data[polarimeter] = {}
        for lna in lnas:
            data[polarimeter][lna] = {}
            data[polarimeter][lna]["raw"] = {
                hk: np.array(transconductance_json[polarimeter][lna]["raw"][hk])
                for hk in ("idrain", "vgate", "vdrain")
            }
            data[polarimeter][lna]["analyzed"] = {
                hk: {
                    value: np.array(
                        transconductance_json[polarimeter][lna]["analyzed"][hk][value]
                    )
                    for value in ("mean", "median", "std", "nsamples")
                }
                for hk in ("idrain", "vgate", "vdrain")
            }

    for polarimeter in polarimeters:
        for lna in lnas:
            current_data = data[polarimeter][lna]
            log.info(f"Generating plot: raw {polarimeter} {lna}")
            plt.plot(current_data["raw"]["vgate"], current_data["raw"]["idrain"], ".")
            plt.xlabel("vgate")
            plt.ylabel("idrain")
            plt.title(f"Raw {polarimeter} {lna}")
            for img_type in img_types:
                plt.savefig(output_dir / f"{polarimeter}_{lna}_raw.{img_type}")
            plt.close()
            log.info(f"Generating plot: mean {polarimeter} {lna}")
            plt.plot(
                current_data["analyzed"]["vgate"]["mean"],
                current_data["analyzed"]["idrain"]["mean"],
                ".",
            )
            plt.xlabel("vgate")
            plt.ylabel("idrain")
            plt.title(f"Mean {polarimeter} {lna}")
            for img_type in img_types:
                plt.savefig(output_dir / f"{polarimeter}_{lna}_mean.{img_type}")
            plt.close()
            log.info(f"Generating plot: median {polarimeter} {lna}")
            plt.plot(
                current_data["analyzed"]["vgate"]["median"],
                current_data["analyzed"]["idrain"]["median"],
                ".",
            )
            plt.xlabel("vgate")
            plt.ylabel("idrain")
            plt.title(f"Median {polarimeter} {lna}")
            for img_type in img_types:
                plt.savefig(output_dir / f"{polarimeter}_{lna}_median.{img_type}")
            plt.close()


if __name__ == "__main__":
    main()
