# -*- encoding: utf-8 -*-

from copy import copy
import logging as log

log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")
import pickle
from typing import Dict, List, Tuple, Union

from astropy.time import Time
import json
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from striptease import (
    DataStorage,
    parse_polarimeters,
    polarimeter_iterator,
    Tag,
)
from striptease.tuning import read_excel

DEFAULT_POLARIMETERS = [polarimeter for _, _, polarimeter in polarimeter_iterator()]

THRESHOLD = 524287.0


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


def sigma_method(data):
    even = data[::2]
    odd = data[1::2]
    if len(even) != len(odd):
        even = even[:-1]
    return np.std(odd - even) / np.sqrt(2)


def analyze_test(data, polarimeter, tags_acq, detectors, idrains, offsets):
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
            pwr = data_in_range(data[polarimeter]["PWR"], tag_acq)[1]
            dem = data_in_range(data[polarimeter]["DEM"], tag_acq)[1]

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


def saturates(data, threshold=THRESHOLD):
    return data >= threshold


def do_analysis(lna_analysis):
    # lna_analysis.sel(
    # data_type="PWR_SUM", value="mean", polarimeter="R0", detector="Q1", lna="HA1"
    # ).isel(idrain=slice(1, None)).plot(x="offset", hue="idrain")
    # plt.show()
    # lna_analysis.sel(
    # data_type="PWR_SUM", value="mean", polarimeter="R0", lna="HA1", detector="Q1"
    # ).isel(idrain=slice(1, None)).plot.pcolormesh(x="idrain", y="offset", cmap="Greys")#hue="detector", marker=".")
    plt.show()
    lna_analysis.sel(
        data_type="PWR_SUM",
        value="std",
        polarimeter="R0",
        lna="HA1",
        detector="Q1",
        offset=2500,
    ).isel(idrain=slice(1, None)).plot()
    plt.show()
    print(
        lna_analysis.sel(lna="HA1").isel(idrain=slice(1, None)).coords["idrain"].values
    )
    plt.errorbar(
        lna_analysis.sel(lna="HA1").isel(idrain=slice(1, None)).coords["idrain"],
        lna_analysis.sel(
            data_type="PWR_SUM",
            value="mean",
            polarimeter="R0",
            lna="HA1",
            detector="Q1",
            offset=2500,
        ).isel(idrain=slice(1, None)),
        lna_analysis.sel(
            data_type="PWR_SUM",
            value="std",
            polarimeter="R0",
            lna="HA1",
            detector="Q1",
            offset=2500,
        ).isel(idrain=slice(1, None)),
    )
    plt.show()

    return
    lna_analysis.sel(
        data_type="PWR_SUM", value="mean", polarimeter="R0", lna="HA1", offset=2200
    ).isel(idrain=slice(1, -1)).plot(x="idrain", hue="detector", marker=".")
    plt.title("")
    plt.legend(["Q1", "Q2", "U1", "U2"])
    plt.ylabel("$I$ [adu]")
    plt.tight_layout()
    plt.savefig("../tesi/images/my-work/lna_fit_idrain_good.pdf")
    plt.close()

    lna_analysis.sel(
        data_type="PWR_SUM", value="mean", polarimeter="R0", lna="HB3", offset=2140
    ).isel(idrain=slice(1, -1)).plot(x="idrain", hue="detector", marker=".")
    plt.title("")
    plt.legend(["Q1", "Q2", "U1", "U2"])
    plt.ylabel("$I$ [adu]")
    plt.tight_layout()
    plt.savefig("../tesi/images/my-work/lna_fit_idrain_bad.pdf")
    plt.close()

    return

    # Fit I(idrain)
    for polarimeter in "R0", "R4", "R5", "R6":
        for lna in "HA1", "HA2", "HA3", "HB1", "HB2", "HB3":
            print(polarimeter, lna)
            for offset in lna_analysis.coords["offset"].values:
                lna_analysis.sel(
                    data_type="PWR_SUM",
                    value="mean",
                    polarimeter=polarimeter,
                    lna=lna,
                    offset=offset,
                ).isel(idrain=slice(1, -1)).plot(x="idrain", hue="detector", marker=".")
                # ).isel(idrain=slice(1, -1)).plot(x="idrain",  marker=".")
                # ).plot(x="idrain", hue="offset", marker=".")
                plt.title(f"{polarimeter} {lna} {offset}")
                plt.savefig(f"../reports/plots-lna/{polarimeter}_{lna}_{offset}.png")
                plt.close()
    return

    # Look for combinations that do not saturate
    # print("Look for combinations that do not saturate")
    # x = np.argwhere(np.logical_not(saturates(lna_analysis["R0"]["HA1"]["PWR"]["Q1"]["mean"])))
    # for idrain, offset in x:
    # print(idrains["R0"]["HA1"][idrain], offsets["R0"]["HA1"][offset])

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

    id4000 = lna_analysis.sel(
        lna="HA1", data_type="DEM_DIFF", detector="Q1", idrain=6000
    )
    id4000.sel(value="sigma").plot(hue="polarimeter")
    id4000.sel(value="std").plot(hue="polarimeter")
    plt.show()
    (id4000.sel(value="sigma") / id4000.sel(value="std")).plot(hue="polarimeter")
    plt.show()
    # return

    # pwr = lna_analysis.sel(polarimeter="R0", lna="HA1", data_type="PWR", value="mean", detector="Q1")#.isel(idrain=slice(1, -1))
    # polarimeters = pwr.coords["polarimeter"].values
    # data_types = pwr.coords["data_types"].values
    # detectors = pwr.coords["detectors"].values
    # values = pwr.coords["polarimeter"].values
    # idrains = pwr.coords["idrain"].values
    # idrains = pwr.coords["idrain"]
    # lnas = pwr.coords["lna"]
    # offsets = pwr.coords["offset"]
    # print(idrains)

    # print(np.concatenate((np.array(range(-1000, 100, 100)), np.array(idrains))))
    # coords = [(lna, idrain) for lna in lnas for idrain in np.concatenate((np.array(range(-1000, 0, 100)), np.array(idrains)))]
    # idx = pd.MultiIndex.from_tuples(coords, names=("lna", "idrain"))

    # pre_saturated = xr.DataArray(
    # data=THRESHOLD,
    # coords=[
    # ("polarimeter", polarimeters),
    # ("lna_idrain", idx),
    # ("idrain", np.concatenate((np.array(range(-1000, 0, 100)), np.array(idrains)))),
    # ("data_type", data_types),
    # ("detector", detectors),
    # ("value", values),
    # ("offset", (2500))
    # ]
    # )

    # new = xr.concat((pre_saturated, pwr), dim="idrain")
    # pwr.plot(x="idrain", hue="offset", ls="-", marker=".")
    # plt.show()
    # new.plot(x="idrain", hue="offset", ls="-", marker=".")
    # plt.show()
    # pwr.plot(x="idrain", hue="offset", ls="", marker=".")
    # fit = pwr.curvefit("idrain", lambda x, m, q: m*x + q, p0={"m": -3.5, "q": 400000})
    # fit = pwr.curvefit("idrain", fit_function)
    # m = fit["curvefit_coefficients"].sel(param="angular_coefficient")
    # q = fit["curvefit_coefficients"].sel(param="saturation_offset")
    # print(m, q)

    # lna_analysis.sel(polarimeter="R0", lna="HA1", data_type="PWR_SUM", value="mean", detector="Q1", idrain=2000).plot()
    # plt.show()

    # Fit I(offs)
    pwr_fit_offset = lna_analysis.sel(
        data_type=["PWR", "PWR_SUM"], value="mean"
    ).curvefit("offset", fit_function)
    print(pwr_fit_offset)

    for lna in "HA1", "HA2", "HA3", "HB1", "HB2", "HB3":
        print(
            pwr_fit_offset["curvefit_coefficients"]
            .sel(
                param="angular_coefficient",
                polarimeter="R0",
                data_type="PWR_SUM",
                lna=lna,
            )
            .isel(idrain=slice(1, -1))
            .mean(dim="idrain")
        )
        print(
            pwr_fit_offset["curvefit_coefficients"]
            .sel(
                param="angular_coefficient",
                polarimeter="R0",
                data_type="PWR_SUM",
                lna=lna,
            )
            .isel(idrain=slice(1, -1))
            .std(dim="idrain")
        )

    # print(pwr_fit_offset["curvefit_coefficients"].sel(param="angular_coefficient", polarimeter="R0", data_type="PWR_SUM").isel(lna_idrain=(slice(-1), slice(1, -1))).mean(dim="lna_idrain"))
    # print(pwr_fit_offset["curvefit_coefficients"].sel(param="angular_coefficient", polarimeter="R0", data_type="PWR_SUM").isel(lna_idrain=(slice(-1), slice(1, -1))).std(dim="lna_idrain"))

    for lna in "HA1", "HA2", "HA3", "HB1", "HB2", "HB3":
        pwr_fit_offset["curvefit_coefficients"].sel(
            param="angular_coefficient",
            polarimeter="R0",
            detector="Q1",
            data_type="PWR_SUM",
            lna=lna,
        ).isel(idrain=slice(1, -1)).plot.hist(histtype="stepfilled", label=lna)
    plt.xlabel("Angular coefficient")
    plt.title("")
    plt.legend()
    plt.savefig("offs_angular_coefficient_R0_Q1.pdf")
    plt.show()

    for lna in "HA1", "HA2", "HA3", "HB1", "HB2", "HB3":
        pwr_fit_offset["curvefit_coefficients"].sel(
            param="saturation_offset",
            polarimeter="R0",
            detector="Q1",
            data_type="PWR_SUM",
            lna=lna,
        ).isel(idrain=slice(1, -1)).plot.line(x="idrain", label=lna, marker=".")
    plt.ylabel("Saturation offset")
    plt.title("")
    plt.legend()
    plt.savefig("offs_saturation_R0_Q1.pdf")
    plt.show()

    # plt.show()
    # print(idrains[0])
    # plt.plot(idrains, xr.apply_ufunc(
    # fit_function, idrains, m, q
    # ))
    # plt.show()
    # plt.plot(idrains, pwr - xr.apply_ufunc(
    # fit_function, idrains, m, q
    # ))
    # plt.show()

    # print(fit["curvefit_coefficients"].sel(param="angular_coefficient"))
    # fit["curvefit_coefficients"].sel(param="angular_coefficient").plot(ls="", marker=".")
    # plt.show()
    # return

    # Fit I(idrain)
    lna_analysis.sel(
        data_type="PWR_SUM", value="mean", polarimeter="R0", lna="HB1", detector="Q1"
    ).isel(idrain=slice(1, -1)).plot(x="idrain", hue="offset", marker=".")
    # ).plot(x="idrain", hue="offset", marker=".")
    plt.show()

    # print(lna_analysis.sel(
    # data_type="PWR_SUM", value="mean", polarimeter="R0", lna="HA1", detector="Q1"
    # ).isel(idrain=slice(1, -1)).curvefit("idrain", fit_function)["curvefit_coefficients"].sel(offset=2200))
    # ).curvefit("idrain", fit_function)["curvefit_coefficients"].sel(offset=2200))

    for lna in "HA1", "HA2", "HA3", "HB1", "HB2", "HB3":
        print(lna)
        pwr_fit_idrain = (
            lna_analysis.sel(
                data_type="PWR_SUM", polarimeter="R0", value="mean", lna=lna
            )
            .isel(offset=slice(1, -1))
            .curvefit("idrain", fit_function)
        )
        # ).curvefit("idrain", fit_function)
        print(pwr_fit_idrain)


def main():
    # x = np.random.randn(100000)
    # print(sigma_method(x))
    # return

    from argparse import ArgumentParser, RawDescriptionHelpFormatter

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

    args = parser.parse_args()

    ds = DataStorage(args.ds_path)
    polarimeters = parse_polarimeters(args.polarimeters)
    detectors = ["Q1", "Q2", "U1", "U2"]
    lnas = ["HA1", "HA2", "HA3", "HB1", "HB2", "HB3"]
    mjd_range = (args.mjd_start, args.mjd_end)
    output_dir = args.output_dir

    store_to_pickle = False
    pickle_filename = f"{output_dir}/lna_analysis_data"

    log.info("Loading tags")

    tags_all, tags_test, tags_test_lna, tags_pol, tags_acq, tags_global = load_tags(
        ds, mjd_range, test_name=args.test_name, polarimeters=polarimeters
    )

    if store_to_pickle:
        log.log(log.INFO, "Storing in pickle")
        for polarimeter in polarimeters:
            for lna in lnas:
                with open(f"{pickle_filename}_{polarimeter}_{lna}.pkl", "wb") as f:
                    log.log(log.INFO, f"Storing in pickle: {polarimeter} {lna}")
                    # tag = copy(tags_test_lna[lna][0]),
                    tag = tags_test_lna[lna][0]
                    # Correct mjd_end=-1. problem
                    if lna == "HA1":
                        tag.mjd_end = tags_test_lna["HA2"][0].mjd_start
                    pickle.dump(
                        load_data(ds, tag, polarimeter, detectors, args.delta), f
                    )
        return

    idrains, offsets = load_idrains_and_offsets(
        polarimeters, lnas, excel_file=args.tuning_file
    )

    analyze = False
    if analyze:
        lna_analysis_json = {}
        for polarimeter in polarimeters:
            log.info(f"Analyzing polarimeter {polarimeter}")
            lna_analysis_json[polarimeter] = {}
            for lna in lnas:
                log.info(f"Analyzing polarimeter {polarimeter}: LNA {lna}")
                with open(f"{pickle_filename}_{polarimeter}_{lna}.pkl", "rb") as f:
                    log.info(f"Loading data: {polarimeter} {lna}")
                    data = {}
                    data[polarimeter] = pickle.load(f)
                    # for lna in lnas:

                    # fig, ax = plot_timeline(data, tag_whole_test, tags_global[lna], polarimeter, detectors)
                    # fig.savefig(f"lna_timeline_{polarimeter}_{lna}.pdf")

                    # plt.plot(data[polarimeter]["PWR"][0].value, data[polarimeter]["PWR"][1]["PWRQ1"], ".")
                    # plt.show()

                    log.info(f"Analyzing data: {polarimeter} {lna}")
                    lna_analysis_json[polarimeter][lna] = analyze_test(
                        data,
                        polarimeter,
                        tags_acq[lna],
                        detectors,
                        idrains[polarimeter][lna],
                        offsets[polarimeter][lna]
                        # ds, polarimeter, tags_acq[lna], detectors, idrains[polarimeter][lna], offsets[polarimeter][lna]
                    )
                    # i = 0
                    # for idrain in idrains_and_offsets[polarimeter][lna]:
                    # lna_analysis[polarimeter][lna][int(idrain)] = {}
                    # for i in range(idrains_and_offsets[polarimeter][lna][idrain].shape[0]):
                    # offset = int(idrains_and_offsets[polarimeter][lna][idrain][i, 0])
                    # lna_analysis[polarimeter][lna][idrain][offset] = analyze_test(
                    # data,
                    # polarimeter,
                    # tags_acq[lna][i],
                    # detectors
                    # )
                    # lna_analysis[polarimeter][lna][idrain][offset]["mjd_range"] = (
                    # tags_acq[lna][i].mjd_start, tags_acq[lna][i].mjd_end
                    # )
                    # i += 1
                    # if i == 3:
                    # return

                    # ax, fig = plot_analysed_data(det_offs_analysis, polarimeter, offsets, detectors)
                    # fig.savefig(f"analysis_{polarimeter}.pdf")

        lna_analysis_json["mjd_range"] = mjd_range
        with open(f"{output_dir}/{args.json_output}", "w") as f:
            json.dump(lna_analysis_json, f, indent=5)
    else:
        with open(f"{output_dir}/{args.json_output}", "r") as f:
            lna_analysis_json = json.load(f)

    with open(f"{output_dir}/det_offs_analysis.json", "r") as f:
        det_offs_analysis = json.load(f)

    data_types = ["PWR", "DEM", "PWR_SUM", "DEM_DIFF"]
    values = ["mean", "std", "sigma", "nsamples"]

    store_to_netcdf = False
    if store_to_netcdf:
        # all_idrains = np.sort(
        # np.unique(
        # np.concatenate(
        # [np.array([0])]
        # + [
        # idrains[polarimeter][lna]
        # for lna in lnas
        # for polarimeter in polarimeters
        # ]
        # )
        # )
        # )
        all_offsets = np.sort(
            np.unique(
                np.concatenate(
                    [
                        offsets[polarimeter][lna][:, detector]
                        for lna in lnas
                        for polarimeter in polarimeters
                        for detector in range(len(detectors))
                    ]
                )
            )
        )

        coords = [
            (lna, idrain)
            for lna in lnas
            for idrain in np.concatenate((np.array([0]), np.array(idrains["R0"][lna])))
        ]
        idx = pd.MultiIndex.from_tuples(coords, names=("lna", "idrain"))

        lna_analysis = xr.DataArray(
            data=np.nan,
            coords=[
                ("polarimeter", polarimeters),
                # ("lna", lnas),
                ("lna_idrain", idx),
                ("data_type", data_types),
                ("detector", detectors),
                ("value", values),
                # ("idrain", all_idrains),
                ("offset", all_offsets),
            ],
        )

        for polarimeter in polarimeters:
            log.log(log.INFO, f"Converting {polarimeter} to xarray.")
            for lna in lnas:
                log.log(log.INFO, f"Converting {polarimeter} {lna} to xarray.")
                for data_type in data_types:
                    log.log(
                        log.INFO,
                        f"Converting {polarimeter} {lna} {data_type} to xarray.",
                    )
                    for detector_idx in range(len(detectors)):
                        for value in values:
                            for offset_idx in range(
                                len(offsets[polarimeter][lna][:, detector_idx])
                            ):
                                for idrain_idx in range(len(idrains[polarimeter][lna])):
                                    lna_analysis.loc[
                                        dict(
                                            polarimeter=polarimeter,
                                            lna=lna,
                                            data_type=data_type,
                                            detector=detectors[detector_idx],
                                            value=value,
                                            idrain=idrains[polarimeter][lna][
                                                idrain_idx
                                            ],
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
                                lna_analysis.loc[
                                    dict(
                                        polarimeter=polarimeter,
                                        lna=lna,
                                        data_type=data_type,
                                        detector=detectors[detector_idx],
                                        value=value,
                                        idrain=0,
                                        offset=offsets[polarimeter][lna][
                                            offset_idx, detector_idx
                                        ],
                                    )
                                ] = det_offs_analysis[polarimeter][
                                    str(
                                        offsets[polarimeter][lna][
                                            offset_idx, detector_idx
                                        ]
                                    )
                                ][
                                    data_type
                                ][
                                    detectors[detector_idx]
                                ][
                                    value
                                ]

        lna_analysis.reset_index("lna_idrain").to_netcdf(
            f"{output_dir}/lna_analysis_xarray_multiindex.nc"
        )
    else:
        log.log(log.INFO, "Loading xarray.")
        lna_analysis = xr.open_dataarray(
            f"{output_dir}/lna_analysis_xarray_multiindex.nc"
        ).set_index(lna_idrain=["lna", "idrain"])

    do_analysis(lna_analysis)


if __name__ == "__main__":
    main()
