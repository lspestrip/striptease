#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging as log
from pathlib import Path

log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter

import xarray as xr
from matplotlib import pyplot as plt
import numpy as np
from scipy import signal

from striptease import polarimeter_iterator

DEFAULT_POLARIMETERS = [polarimeter for _, _, polarimeter in polarimeter_iterator()]


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Calculate y-factor",
        formatter_class=RawDescriptionHelpFormatter,
        epilog=""" """,
    )
    parser.add_argument(
        "file1",
        type=str,
        help="The file containing the first set of data.",
    )
    parser.add_argument(
        "temperature1",
        type=float,
        help="The temperature of the first set of data.",
    )
    parser.add_argument(
        "file_offset_1",
        type=str,
        help="The file containing the first offset test data.",
    )
    parser.add_argument(
        "file2",
        type=str,
        help="The file containing the second set of data.",
    )
    parser.add_argument(
        "temperature2",
        type=float,
        help="The temperature of the second set of data.",
    )
    parser.add_argument(
        "file_offset_2",
        type=str,
        help="The file containing the second offset test data.",
    )
    parser.add_argument(
        "--polarimeter",
        metavar="POLARIMETER",
        type=str,
        default="",
        help="Name of the polarimeter/module to test. It is used only to set plot titles and file names, "
        "therefore it can also be set to a string that does not represent a polarimeter. Empty by default.",
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
        "--no-save-plots",
        action="store_false",
        dest="save_plots",
        help="Don't store plots to files.",
    )
    parser.add_argument(
        "--show-plots",
        action="store_true",
        dest="show_plots",
        help="Show plots at runtime.",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    lnas = ["HA1", "HA2", "HA3", "HB1", "HB2", "HB3"]
    detectors = ["Q1", "Q2", "U1", "U2"]
    polarimeter = args.polarimeter
    output_dir = Path(args.output_dir)
    output_file = output_dir / f"y_factor_{polarimeter}.nc"
    save_plots = args.save_plots
    show_plots = args.show_plots

    def savefig(fig, filename: str, lna: str):
        img_types = ["pdf", "png", "svg"]
        for img_type in img_types:
            path = output_dir / f"{filename}_{polarimeter}_{lna}.{img_type}"
            fig.savefig(path)

    log.info(f"Loading file {args.file1}.")
    data1 = xr.open_dataarray(args.file1).set_index(lna_idrain=["lna", "idrain"])
    temperature1 = args.temperature1

    log.info(f"Loading file {args.file_offset_1}.")
    data_offset_1 = xr.open_dataarray(args.file_offset_1)

    log.info(f"Loading file {args.file2}.")
    data2 = xr.open_dataarray(args.file2).set_index(lna_idrain=["lna", "idrain"])
    temperature2 = args.temperature2

    log.info(f"Loading file {args.file_offset_2}.")
    data_offset_2 = xr.open_dataarray(args.file_offset_2)

    v_t1 = data1.sel(data_type="PWR_SUM", value="mean", drop=True)
    v_t2 = data2.sel(data_type="PWR_SUM", value="mean", drop=True)
    v_offs_1 = data_offset_1.sel(data_type="PWR_SUM", value="mean", drop=True)
    v_offs_2 = data_offset_2.sel(data_type="PWR_SUM", value="mean", drop=True)

    v1 = v_t1 - v_offs_1
    v2 = v_t2 - v_offs_2

    m = (v2 - v1) / (temperature2 - temperature1)
    q = v1 - m * temperature1
    temperature_noise = q / m

    ds = xr.Dataset(
        data_vars=dict(
            v_t1=v_t1,
            v_t2=v_t2,
            v_offs_1=v_offs_1,
            v_offs_2=v_offs_2,
            v_1=v1,
            v_2=v2,
            m=m,
            q=q,
            temperature_noise=temperature_noise,
        )
    )
    log.info(f"Storing results into file {output_file}.")
    ds.reset_index("lna_idrain").to_netcdf(output_file)

    ax_idx = {"U1": (0, 0), "U2": (0, 1), "Q1": (1, 0), "Q2": (1, 1)}
    offset = temperature_noise.coords["offset"].values[
        -1
    ]  # choose the last offset to avoid saturation
    for lna in lnas:
        log.info(f"Generating plots: {lna}.")
        # Plot signal - offset
        fig, ax = plt.subplots(2, 2)
        for detector in detectors:
            v1_cur = v1.sel(detector=detector, lna=lna, offset=offset)
            v2_cur = v2.sel(detector=detector, lna=lna, offset=offset)

            v1_cur.plot(
                marker=".", label=f"T = {temperature1}K", ax=ax[ax_idx[detector]]
            )
            v2_cur.plot(
                marker=".", label=f"T = {temperature2}K", ax=ax[ax_idx[detector]]
            )

            ax[ax_idx[detector]].set_title(detector)
            ax[ax_idx[detector]].set_xlabel("$i_\\mathrm{drain}$ [$\\mu$A]")
            ax[ax_idx[detector]].set_ylabel("$v - v_\\mathrm{off}$ [ADU]")

        fig.legend([f"{temperature1}K", f"{temperature2}K"])
        fig.suptitle(f"{polarimeter} {lna} (offset={offset})")
        plt.tight_layout()
        if save_plots:
            savefig(plt, "v-v_off", lna)
        if show_plots:
            plt.show()
        plt.close()

        # Plot signal
        fig, ax = plt.subplots(2, 2)
        for detector in detectors:
            v_t1_cur = v_t1.sel(detector=detector, lna=lna, offset=offset)
            v_t2_cur = v_t2.sel(detector=detector, lna=lna, offset=offset)

            v_t1_cur.plot(
                marker=".", label=f"T = {temperature1}K", ax=ax[ax_idx[detector]]
            )
            v_t2_cur.plot(
                marker=".", label=f"T = {temperature2}K", ax=ax[ax_idx[detector]]
            )

            ax[ax_idx[detector]].set_title(detector)
            ax[ax_idx[detector]].set_xlabel("$i_\\mathrm{drain}$ [$\\mu$A]")
            ax[ax_idx[detector]].set_ylabel("$v$ [ADU]")

        fig.legend([f"{temperature1}K", f"{temperature2}K"])
        fig.suptitle(f"{polarimeter} {lna} (offset={offset})")
        plt.tight_layout()
        if save_plots:
            savefig(plt, "v", lna)
        if show_plots:
            plt.show()
        plt.close()

        # Plot T_noise
        temperature_noise_cur = temperature_noise.sel(lna=lna, offset=offset)
        temperature_noise_cur.plot(hue="detector", marker=".")
        plt.xlabel("$i_\\mathrm{drain}$ [$\\mu$A]")
        plt.ylabel("$T_\\mathrm{noise}$ [K]")
        plt.title(f"{polarimeter} {lna} (offset={offset})")
        plt.tight_layout()
        if save_plots:
            savefig(plt, "T_noise", lna)
        if show_plots:
            plt.show()
        plt.close()

        # Plot smoothed T_noise
        w = np.ones(3)
        idrains = temperature_noise_cur.coords["idrain"]

        fig_smooth, ax_smooth = plt.subplots()
        fig_full, ax_full = plt.subplots()
        for detector in detectors:
            temperature_noise_detector = temperature_noise_cur.sel(detector=detector)
            temperature_noise_smooth = np.convolve(
                w / w.sum(), temperature_noise_detector, mode="valid"
            )
            smooth_minima = signal.argrelmin(temperature_noise_smooth)[0]

            ax_smooth.plot(
                idrains[1:-1], temperature_noise_smooth, marker=".", label=detector
            )
            for minimum in smooth_minima:
                ax_smooth.plot(
                    idrains[minimum + 1], temperature_noise_smooth[minimum], "k+"
                )

            ax_full.plot(idrains, temperature_noise_detector, ".", label=detector)
            ax_full.plot(
                idrains[1:-1],
                temperature_noise_smooth,
                color=ax_full.lines[-1].get_color(),
                alpha=0.5,
            )
            for minimum in smooth_minima:
                ax_full.plot(
                    idrains[minimum + 1], temperature_noise_smooth[minimum], "k+"
                )

        ax_smooth.legend()
        ax_smooth.set_xlabel("$i_\\mathrm{drain}$ [$\\mu$A]")
        ax_smooth.set_ylabel("Smoothed $T_\\mathrm{noise}$ [K]")
        fig_smooth.suptitle(f"{polarimeter} {lna} (offset={offset})")
        fig_smooth.tight_layout()
        if save_plots:
            savefig(fig_smooth, "smooth_T_noise", lna)

        ax_full.legend()
        ax_full.set_xlabel("$i_\\mathrm{drain}$ [$\\mu$A]")
        ax_full.set_ylabel("$T_\\mathrm{noise}$ [K] with smoothing")
        fig_full.suptitle(f"{polarimeter} {lna} (offset={offset})")
        fig_full.tight_layout()
        if save_plots:
            savefig(fig_full, "full_T_noise", lna)

        if show_plots:
            plt.show()
        plt.close(fig_smooth)
        plt.close(fig_full)


if __name__ == "__main__":
    main()
