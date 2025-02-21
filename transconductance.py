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
                elif int(scanner.x) not in idrains[polarimeter][lna]:
                    idrains[polarimeter][lna].append(int(scanner.x))
            idrains[polarimeter][lna] = np.array(idrains[polarimeter][lna], dtype=int)
            offsets[polarimeter][lna] = np.array(offsets[polarimeter][lna], dtype=int)

    return idrains, offsets


def data_in_range(data: Tuple[Time, np.ndarray], tag: Tag) -> Tuple[Time, np.ndarray]:
    times, values = data
    index_start, index_end = np.searchsorted(times.value, [tag.mjd_start, tag.mjd_end])
    return (times[index_start:index_end], values[index_start:index_end])


def sigma_method(data):
    even = data[::2]
    odd = data[1::2]
    if len(even) != len(odd):
        even = even[:-1]
    return np.std(odd - even) / np.sqrt(2)


def analyze_data(data, polarimeter, tags_acq, detectors, idrains, offsets):
    def analyze_type(data):
        return np.mean(data), np.std(data), sigma_method(data), len(data)

    analysis = {
        data_type: {
            detector: {
                value: [None] * len(idrains)
                for value in ("mean", "std", "sigma", "nsamples")
            }
            for detector in detectors
        }
        for data_type in ("PWR", "DEM", "PWR_SUM", "DEM_DIFF")
    }

    i = 0
    for idrain in range(len(idrains)):
        # tag_acq = tags_acq[i]
        pwr = np.concatenate(
            [
                data_in_range(data[polarimeter]["PWR"], tags_acq[j])[1]
                for j in range(i, i + len(offsets))
            ]
        )
        dem = np.concatenate(
            [
                data_in_range(data[polarimeter]["DEM"], tags_acq[j])[1]
                for j in range(i, i + len(offsets))
            ]
        )
        i = i + len(offsets)

        for detector in detectors:
            pwr_det = pwr[f"PWR{detector}"]
            (
                analysis["PWR"][detector]["mean"][idrain],
                analysis["PWR"][detector]["std"][idrain],
                analysis["PWR"][detector]["sigma"][idrain],
                analysis["PWR"][detector]["nsamples"][idrain],
            ) = analyze_type(pwr_det)

            dem_det = dem[f"DEM{detector}"]
            (
                analysis["DEM"][detector]["mean"][idrain],
                analysis["DEM"][detector]["std"][idrain],
                analysis["DEM"][detector]["sigma"][idrain],
                analysis["DEM"][detector]["nsamples"][idrain],
            ) = analyze_type(dem_det)

            pwr_even = pwr_det[::2]
            pwr_odd = pwr_det[1::2]
            if len(pwr_even) != len(pwr_odd):
                pwr_even = pwr_even[:-1]
            (
                analysis["PWR_SUM"][detector]["mean"][idrain],
                analysis["PWR_SUM"][detector]["std"][idrain],
                analysis["PWR_SUM"][detector]["sigma"][idrain],
                analysis["PWR_SUM"][detector]["nsamples"][idrain],
            ) = analyze_type((pwr_even + pwr_odd) / 2)

            dem_even = dem_det[::2]
            dem_odd = dem_det[1::2]
            if len(dem_even) != len(dem_odd):
                dem_even = dem_even[:-1]
            (
                analysis["DEM_DIFF"][detector]["mean"][idrain],
                analysis["DEM_DIFF"][detector]["std"][idrain],
                analysis["DEM_DIFF"][detector]["sigma"][idrain],
                analysis["DEM_DIFF"][detector]["nsamples"][idrain],
            ) = analyze_type(np.abs(dem_even - dem_odd) / 2)

    return analysis


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
        mjd_range=(mjd_range.mjd_start - delta, mjd_range.mjd_end - delta),
        polarimeter=polarimeter,
        data_type="PWR",
        detector=detectors,
    )
    dem = ds.load_sci(
        mjd_range=(mjd_range.mjd_start - delta, mjd_range.mjd_end - delta),
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

    # The tags that contain the tests for each LNA
    tags_test_lna = {
        lna: [
            tag
            for tag in tags_test
            if tag.name.startswith(f"{test_name}_{lna}")
            or tag.name.startswith(f"{test_name}_LNA_{lna}")
            or tag.name.startswith(f"{test_name}_TEST_{lna}")
            or tag.name.startswith(f"{test_name}_TEST_LNA_{lna}")
            or tag.name.startswith(f"{test_name}_LNA_TEST_{lna}")
            or tag.name.startswith(f"{test_name}_LNA_TEST_LNA_{lna}")
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

    # import pdb; pdb.set_trace()
    store_to_pickle = False
    if store_to_pickle:
        log.log(log.INFO, "Storing in pickle")
        for polarimeter in polarimeters:
            for lna in lnas:
                with open(f"{pickle_filename}_{polarimeter}_{lna}.pkl", "wb") as f:
                    log.log(log.INFO, f"Storing in pickle: {polarimeter} {lna}")
                    tag = tags_test_lna[lna][0]
                    pickle.dump(
                        {
                            "hk": load_hk(
                                ds, tag, polarimeter, lna, detectors, args.delta
                            ),
                            "sci": load_data(
                                ds, tag, polarimeter, detectors, args.delta
                            ),
                        },
                        f,
                    )

    idrains, offsets = load_idrains_and_offsets(
        polarimeters, lnas, excel_file=args.tuning_file
    )

    analyze = False
    hks = ("idrain", "vgate", "vdrain")
    if analyze:
        transconductance_json = {}
        for polarimeter in polarimeters:
            log.info(f"Analyzing polarimeter {polarimeter}")
            transconductance_json[polarimeter] = {"hk": {}, "sci": {}}
            for lna in lnas:
                log.info(f"Analyzing polarimeter {polarimeter}: LNA {lna}")
                with open(f"{pickle_filename}_{polarimeter}_{lna}.pkl", "rb") as f:
                    log.info(f"Loading data: {polarimeter} {lna}")
                    pickle_data = pickle.load(f)
                    hk_data_pickle = pickle_data["hk"]
                    sci_data_pickle = {polarimeter: pickle_data["sci"]}
                transconductance_json[polarimeter]["hk"][lna] = {
                    "raw": {hk: [] for hk in hks},
                    "analyzed": {
                        hk: {"mean": [], "median": [], "std": [], "nsamples": []}
                        for hk in hks
                    },
                }
                transconductance_json[polarimeter]["sci"][lna] = analyze_data(
                    sci_data_pickle,
                    polarimeter,
                    tags_acq[lna],
                    detectors,
                    idrains[polarimeter][lna],
                    offsets[polarimeter][lna],
                )

                for idrain_idx in range(len(idrains[polarimeter][lna])):
                    hk_data = {hk: [] for hk in hks}
                    for offset_idx in range(len(offsets[polarimeter][lna])):
                        tag = tags_acq[lna][idrain_idx * len(offsets) + offset_idx]
                        for hk in hks:
                            hk_data[hk] += data_in_range(hk_data_pickle[hk], tag)[
                                1
                            ].tolist()
                    for hk in hks:
                        transconductance_json[polarimeter]["hk"][lna]["raw"][
                            hk
                        ] += hk_data[hk]

                        transconductance_json[polarimeter]["hk"][lna]["analyzed"][hk][
                            "mean"
                        ].append(np.mean(hk_data[hk]))
                        transconductance_json[polarimeter]["hk"][lna]["analyzed"][hk][
                            "median"
                        ].append(np.median(hk_data[hk]))
                        transconductance_json[polarimeter]["hk"][lna]["analyzed"][hk][
                            "std"
                        ].append(np.std(hk_data[hk]))
                        transconductance_json[polarimeter]["hk"][lna]["analyzed"][hk][
                            "nsamples"
                        ].append(len(hk_data[hk]))

        import json

        with open(f"{args.output_dir}/{args.json_output}", "w") as f:
            json.dump(transconductance_json, f, indent=2)

    else:
        import json

        with open(f"{args.output_dir}/{args.json_output}", "r") as f:
            transconductance_json = json.load(f)

    # Convert to np array
    hk_data = {}
    sci_data = {}
    for polarimeter in polarimeters:
        hk_data[polarimeter] = {}
        sci_data[polarimeter] = {}
        for lna in lnas:
            hk_data[polarimeter][lna] = {
                "raw": {
                    hk: np.array(
                        transconductance_json[polarimeter]["hk"][lna]["raw"][hk]
                    )
                    for hk in ("idrain", "vgate", "vdrain")
                },
                "analyzed": {
                    hk: {
                        value: np.array(
                            transconductance_json[polarimeter]["hk"][lna]["analyzed"][
                                hk
                            ][value]
                        )
                        for value in ("mean", "median", "std", "nsamples")
                    }
                    for hk in ("idrain", "vgate", "vdrain")
                },
            }

            sci_data[polarimeter][lna] = {
                data_type: {
                    detector: {
                        value: np.array(
                            transconductance_json[polarimeter]["sci"][lna][data_type][
                                detector
                            ][value]
                        )
                        for value in ("mean", "std", "sigma", "nsamples")
                    }
                    for detector in detectors
                }
                for data_type in ("PWR", "DEM", "PWR_SUM", "DEM_DIFF")
            }

    # coords = [(lna, idrain) for lna in lnas for idrain in np.concatenate((np.array([0]), np.array(idrains["R0"][lna])))]
    # idx = pd.MultiIndex.from_tuples(coords, names=("lna", "idrain"))

    # hk_data = xr.DataArray(
    # data=np.nan,
    # coords=[
    # ("polarimeter", polarimeters),
    # ("lna", lnas),
    # ("lna_idrain", idx),
    # ("data_type", data_types),
    # ("detector", detectors),
    # ("value", values),
    # ("idrain", all_idrains),
    # ("offset", all_offsets)
    # ]
    # )

    # print(hk_data["R0"]["HA1"]["analyzed"]["idrain"]["median"])
    # print()
    # print(sci_data["R0"]["HA1"]["PWR_SUM"]["Q1"]["mean"])
    # print()
    # print(hk_data["R0"]["HA1"]["analyzed"]["vgate"]["median"])
    for polarimeter in polarimeters:
        for lna in lnas:
            plt.errorbar(
                hk_data[polarimeter][lna]["analyzed"]["idrain"]["median"],
                hk_data[polarimeter][lna]["analyzed"]["vgate"]["mean"],
                hk_data[polarimeter][lna]["analyzed"]["vgate"]["std"],
            )
            plt.title(f"{polarimeter} {lna}")
            plt.xlabel("idrain [$\\mu$A]")
            plt.ylabel("vgate [V]")
            plt.tight_layout()
            plt.show()
        # plt.scatter(hk_data[polarimeter]["HB2"]["analyzed"]["idrain"]["median"], hk_data[polarimeter]["HB2"]["analyzed"]["vgate"]["mean"], c=sci_data[polarimeter]["HB2"]["PWR_SUM"]["Q2"]["mean"])
        # plt.show()
        for lna in lnas:
            plt.plot(
                hk_data[polarimeter][lna]["analyzed"]["vgate"]["mean"],
                hk_data[polarimeter][lna]["analyzed"]["vgate"]["std"],
                ".-",
                label=lna,
            )
        plt.title(f"{polarimeter}")
        plt.xlabel("idrain [$\\mu$A]")
        plt.ylabel("$\\sigma$ vgate [V]")
        plt.legend()
        plt.tight_layout()
        plt.show()

    return
    for polarimeter in polarimeters:
        for lna in lnas:
            current_data = hk_data[polarimeter][lna]
            log.info(f"Generating plot: raw {polarimeter} {lna}")
            plt.plot(current_data["raw"]["vgate"], current_data["raw"]["idrain"], ".-")
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
                ".-",
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
                ".-",
            )
            plt.xlabel("vgate")
            plt.ylabel("idrain")
            plt.title(f"Median {polarimeter} {lna}")
            for img_type in img_types:
                plt.savefig(output_dir / f"{polarimeter}_{lna}_median.{img_type}")
            plt.close()


if __name__ == "__main__":
    main()
