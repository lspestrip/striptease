#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# 2023-05-10 (based on version of 2021-12-03)
# 2023-06-13 (last modification)

import numpy as np
from typing import List, Tuple, Dict, Union
from astropy.time import Time, TimeDelta
from matplotlib import pyplot as plt

from striptease import DataStorage, Tag
import striptease as st
from rich.progress import track
from rich.logging import RichHandler
from pathlib import Path
from mako.template import Template

import logging
import pickle as pkl
import time
import sys
import os


def find_waittime_tests(
    ds: DataStorage,
    date_range: Union[Tuple[float, float], Tuple[str, str], Tag, Tuple[Time, Time]],
    tag_main: str = "WAITTIME",
    tag_exclude: Union[List[str], str] = "VERIFICATION_TURNON",
) -> List[Tag]:
    """
    This function obtains the number of tests associated with
    the waittime procedure during the given time interval.
    """
    tags_in = ds.get_tags(date_range)
    tags0 = [tt for tt in tags_in if tag_main in tt.name]

    if tag_exclude is not None and type(tag_exclude) == str:
        tags0 = [tt for tt in tags0 if tag_exclude not in tt.name]
    elif tag_exclude is not None and type(tag_exclude) == List:
        for cc in tag_exclude:
            tags0 = [tt for tt in tags0 if cc not in tt.name]
    tags_out = tags0.copy()

    for ii, tt in enumerate(tags0):
        date_str = (Time(tt.mjd_start, format="mjd"), Time(tt.mjd_end, format="mjd"))
        idcase = str(date_str[0].fits).split(".")[0]
        polna = str(tt.name).split(tag_main + "_")[1]

    #
    ncc = len(tags_out)
    log.info(f"Found {ncc} tests between: {date_range}")
    idx_case = 0
    tt = tags_out[idx_case]
    date_str = (Time(tt.mjd_start, format="mjd"), Time(tt.mjd_end, format="mjd"))
    idcase = str(date_str[0].fits).split(".")[0]
    polna = str(tt.name).split(tag_main + "_")[1]
    log.info(f"Analysing Case {idx_case}: {idcase} ({polna})")
    # f"from {date_str[0].fits.replace('T', ' ')} to {date_str[1].fits.replace('T', ' ')}")
    log.info(f"\t{tt}")
    #
    return tags_out


def load_waittime_polan_analysis(
    ds_in: DataStorage, tag_in: Tag, tag_main: str = "WAITTIME"
) -> Dict:
    """
    This function provides the order pair of time for each explored wait time and voltage condition.
    """
    # Reading basic information about of the test
    polna = str(tag_in.name).split(tag_main + "_")[1]
    pol_name, lna_name = polna.split("_")

    t0 = str(Time(tag_in.mjd_start, format="mjd").fits).split(".")[0]
    idcase = tag_in.name + f"_{t0}"
    results = {
        "idcase": idcase,
        "polna": polna,
        "pol_name": pol_name,
        "lna_name": lna_name,
        "time_start": t0,
    }

    # -->Selection Tags with procedure results
    tag_second = polna + "_WT"
    tag_third = "_VD_"
    tags = ds_in.get_tags(tag_in)
    tags = [tt for tt in tags if tag_second in tt.name]
    #
    tids = np.array([tt.name.split(tag_second)[1].split("_") for tt in tags])
    arr_wtime, arr_case, arr_sets = (
        np.unique(tids[:, 0]),
        np.unique(tids[:, 3]),
        np.unique(tids[:, 2]),
    )
    nwt, ncase = len(arr_wtime), len(arr_case)

    arr_volt = np.zeros(len(arr_case))
    for tt in tags:
        if "_SET_VD_" in tt.name:
            cc = int(tt.name.split("_SET_VD_")[1])
            vvolt = tt.start_comment.split(tag_third)[1].split("mV")[0]
            arr_volt[cc] = vvolt
    log.info(
        f"Waittime [sec] ({nwt}): {arr_wtime}\nVoltages [mV]  ({ncase}): {arr_volt}"
    )
    # log.info(f"Voltages [mV]  ({ncase}): {arr_volt}")
    results[f"{arr_sets[1]}_in"] = arr_wtime.astype(float)
    results[f"{arr_sets[0]}_in"] = arr_volt.astype(float)

    # -->Defining the date ranges of each configuration
    dtype_dranges = [("t_start", "float"), ("t_end", "float")]
    results.update(
        {
            f"{arr_sets[0]}_date_range": np.zeros([nwt, ncase], dtype_dranges),
            f"{arr_sets[1]}_date_range": np.zeros([nwt, ncase], dtype_dranges),
            f"{arr_sets[0]+arr_sets[1]}_date_range": np.zeros(
                [nwt, ncase], dtype_dranges
            ),
            "GAP_date_range": np.zeros([nwt, ncase], dtype_dranges),
        }
    )
    idx_wt = {}
    for ii, ww in enumerate(arr_wtime):
        idx_wt[str(ww)] = ii

    for tt in tags:
        idtt = tt.name.split(tag_second)[1].split("_")
        vtime = (tt.mjd_start, tt.mjd_end)
        results[f"{idtt[2]}_date_range"][idx_wt[idtt[0]], int(idtt[3])] = vtime

    set_joint = arr_sets[0] + arr_sets[1]
    results[f"{set_joint}_date_range"]["t_start"] = results[
        f"{arr_sets[0]}_date_range"
    ]["t_start"]
    results[f"{set_joint}_date_range"]["t_end"] = results[f"{arr_sets[1]}_date_range"][
        "t_end"
    ]
    set_gap = "GAP"
    results[f"{set_gap}_date_range"]["t_start"] = results[f"{arr_sets[0]}_date_range"][
        "t_end"
    ]
    results[f"{set_gap}_date_range"]["t_end"] = results[f"{arr_sets[1]}_date_range"][
        "t_start"
    ]

    arr_sets = np.append(arr_sets, [set_joint, set_gap])
    results["sets"] = arr_sets

    # -->
    set_measure = arr_sets.copy()
    dtype_results = [
        ("count", "<f4"),
        ("DrainV", "<f4"),
        ("t_DrainV", "<f4"),
        ("WaitTime", "<f4"),
        ("t_start", "<f4"),
        ("t_end", "<f4"),
        ("WaitTime_in", "<f4"),
        ("DrainV_in", "<f4"),
    ]

    for sm in set_measure:
        res0 = np.zeros([nwt, ncase], dtype_results)
        # log.info(f"\n####### Data set: {sm}")
        for ii, wt in enumerate(arr_wtime):
            log.info(
                f"Configuration: set {sm} for waitTime {wt}sec ({ii+1}/{nwt}). Analyzing {ncase} cases of voltages:"
            )
            for jj, vv in track(enumerate(arr_volt), description="Progress..."):
                vrange = tuple(results[f"{sm}_date_range"][ii, jj])

                deltat = TimeDelta(vrange[1] - vrange[0], scale="tai", format="jd").sec

                # log.info(f"\nSET: {sm} ({wt}sec, {vv}mV). mjd_range: {vrange} ('{pol_name}','{lna_name}','VD')")
                cc, vd, t_vd = get_polna_statistic(
                    ds_in, vrange, pol_name, lna_name, parin="VD"
                )
                res0[ii, jj] = (cc, vd, t_vd, deltat, vrange[0], vrange[1], wt, vv)
                # log.info(f'  Yield: {res0[ii,jj]}\n')
        results[sm] = res0
    return results


def get_polna_statistic(
    ds: DataStorage,
    date_range: Union[Tuple[float, float], Tuple[str, str], Tag, Tuple[Time, Time]],
    pol_name: str,
    lna_name: str,
    parin: str = "VD",
    statistic="last",
) -> Tuple:
    """ """
    # date_range = tuple(date_range)
    subgroup = f"POL_{pol_name}"
    lna_pin = st.get_lna_num(lna_name)
    par_str = f"{parin}{lna_pin}_HK"

    # log.info(f"\tLoading HK ({type(date_range)}, {date_range}, '{subgroup}', '{lna_name}', '{par_str}')") #This took around 9 sec by one case
    vtime, vparam = ds.load_hk(
        mjd_range=date_range, group="BIAS", subgroup=subgroup, par=par_str
    )
    # log.info(f'\t--> Time: {vtime} ## Params: {vparam}')

    if vtime is None:
        result = (0, np.nan, np.nan)
    elif len(vtime) == 1:
        result = (1, vparam[0], vtime[0].value)
    elif len(vtime) > 1:
        result = (len(vtime), vparam[-1], vtime[-1].value)
    else:
        result = (0, np.nan, np.nan)
    return result


def plotting_countmap(metaData, idout=None, path_dir: Path = Path("./")):
    #
    md = metaData.copy()
    #
    idcase = md.get("idcase", "")
    pp, ll = md["pol_name"], md["lna_name"]
    vsets = md["sets"]
    
    # Countmap
    # plt.figure(figsize=(18 / 2.54, 10 / 2.54),layout='tight')
    plt.figure(figsize=(18 / 2.54, 10 / 2.54))
    plt.subplots_adjust(wspace=0.4, hspace=0.4)

    cur0 = md[f"{vsets[0]}_in"]
    xmin, xmax = np.nanmin(cur0), np.nanmax(cur0)
    xdelta = (xmax - xmin) / len(np.unique(cur0)) * 0.5
    cur0 = md[f"{vsets[1]}_in"]
    ymin, ymax = np.nanmin(cur0), np.nanmax(cur0)
    ydelta = (ymax - ymin) / len(np.unique(cur0)) * 0.5
    vextent = [xmin - xdelta, xmax + xdelta, ymin - ydelta, ymax + ydelta]

    for jj, kk in enumerate(vsets[0:3]):
        log.info(f"\tSubplot {jj} ({kk})")
        curAll = md[kk]
        print(curAll["count"],"\n") #log.info(curAll["count"],"\n")

        plt.subplot(1, 3, jj + 1)
        plt.title(f"{pp} {ll} (set {kk})", {"fontsize": 10})

        if jj == 0:
            plt.xlabel(f"{vsets[0]} [mV]")
            plt.ylabel("Time [sec]")
        else:
            plt.xlabel(f"{vsets[0]} [mV]")

        plt.imshow(
            curAll["count"],
            vmin=-0.5,
            vmax=8.5,
            cmap="Set1",
            extent=vextent,
            aspect="auto",
            origin="lower",
        )
        if jj == 2:
            cbar = plt.colorbar(pad=0.02, fraction=0.15)
            cbar.set_label("#", labelpad=-20, y=-0.02, rotation=0, fontsize=10)
    if idout is None:
        idout = idcase
    plt.savefig(path_dir / f"Fig_{idout}_countMap.png", dpi=300)


def plotting_checks_params(
    metaData,
    idout=None,
    plot_case: Union[str, Dict] = "WT",
    path_dir: Path = Path("./"),
):
    """
    This function provides a figure comparing the input and recovered values
    of each configuration. The two options are:
        *) The input and measured wait time during the set: waittime. Option: plot_case='WT'
        *) The input and measured voltage value during the set: waittime. Option: plot_case='VD'
    """
    #
    md = metaData.copy()
    #
    idcase = md.get("idcase", "")
    pp, ll = md["pol_name"], md["lna_name"]
    vsets = md["sets"]
    #
    # log.info(f"\n## Plots to check input and measured params: {md['polna']}")

    # Plot case
    if plot_case == "WT":
        pcase = {
            "set": "WT",
            "column": "WaitTime",
            "label": "sec",
            "idoutput": "waittime",
        }
    elif plot_case == "VD":
        pcase = {"set": "WT", "column": "DrainV", "label": "mV", "idoutput": "voltage"}
    elif type(plot_case) is Dict:
        pcase = plot_case.copy()
    else:
        sys.exit(1)

    plt.figure(figsize=(18 / 2.54, 10 / 2.54))  # ,layout='tight')
    plt.subplots_adjust(wspace=0.4, hspace=0.4)

    cur0 = md[f"{vsets[0]}_in"]
    xmin, xmax = np.nanmin(cur0), np.nanmax(cur0)
    xdelta = (xmax - xmin) / len(np.unique(cur0)) * 0.5
    cur0 = md[f"{vsets[1]}_in"]
    ymin, ymax = np.nanmin(cur0), np.nanmax(cur0)
    ydelta = (ymax - ymin) / len(np.unique(cur0)) * 0.5
    vextent = [xmin - xdelta, xmax + xdelta, ymin - ydelta, ymax + ydelta]

    kk0 = pcase["set"]
    curAll = {
        "input": md[kk0][pcase["column"] + "_in"],
        "get": md[kk0][pcase["column"]],
    }
    curAll["$\\Delta$"] = curAll["get"] - curAll["input"]
    vmin, vmax = curAll["input"].min(), 0.8 * curAll["get"].max()

    jj = 1
    for kk, cur in curAll.items():
        plt.subplot(1, 3, jj)
        plt.title(f"{pp} {ll} (set {kk0}, {kk})", {"fontsize": 10})
        plt.xlabel(f"{vsets[0]} [mV]")

        if kk == "input":
            plt.ylabel("Time [sec]")
        elif kk == "$\\Delta$":
            vmin = cur.min()
            vmax = np.median(cur) + 2 * cur.std()

        plt.imshow(
            cur,
            vmin=vmin,
            vmax=vmax,
            cmap="jet",
            extent=vextent,
            aspect="auto",
            origin="lower",
        )

        if kk != "input":
            cbar = plt.colorbar(pad=0.02, fraction=0.15)
            cbar.ax.tick_params(labelsize=8)
            cbar.set_label(
                pcase["label"], labelpad=-20, y=-0.02, rotation=0, fontsize=10
            )
        jj += 1

    if idout is None:
        idout = idcase
    plt.savefig(path_dir / f"Fig_{idout}_{pcase['idoutput']}Map.png", dpi=300)


def plotting_settingTime(metaData, idout=None, path_dir: Path = Path("./")):
    #
    md = metaData.copy()
    #
    idcase = md.get("idcase", "")
    pp, ll = md["pol_name"], md["lna_name"]
    vsets = md["sets"]
    #
    # log.info(f"\n## Plotting the setting time of each data set: {md['polna']}")

    # time
    plt.figure(figsize=(2 * 12 / 2.54, 10 / 2.54))  # ,layout='tight')
    plt.subplots_adjust(wspace=0.4, hspace=0.4)

    cur0 = md[f"{vsets[0]}_in"]
    xmin, xmax = np.nanmin(cur0), np.nanmax(cur0)
    xdelta = (xmax - xmin) / len(np.unique(cur0)) * 0.5
    cur0 = md[f"{vsets[1]}_in"]
    ymin, ymax = np.nanmin(cur0), np.nanmax(cur0)
    ydelta = (ymax - ymin) / len(np.unique(cur0)) * 0.5
    vextent = [xmin - xdelta, xmax + xdelta, ymin - ydelta, ymax + ydelta]

    for jj, kk in enumerate(vsets):
        curAll = md[kk]

        plt.subplot(1, 4, jj + 1)
        plt.title(f"{pp} {ll} (set {kk})", {"fontsize": 10})

        if jj == 0:
            plt.xlabel(f"{vsets[0]} [mV]")
            plt.ylabel("Time [sec]")
        else:
            plt.xlabel(f"{vsets[0]} [mV]")

        plt.imshow(
            curAll["WaitTime"],
            cmap="jet",
            extent=vextent,
            aspect="auto",
            origin="lower",
        )

        cbar = plt.colorbar(pad=0.02, fraction=0.15, format="%.1f")
        cbar.ax.tick_params(labelsize=7)
        cbar.set_label("sec", labelpad=-20, y=-0.02, rotation=0, fontsize=10)
    if idout is None:
        idout = idcase
    plt.savefig(path_dir / f"Fig_{idout}_settingTimeMap.png", dpi=300)


class checks_waitTime_analysis:
    def __init__(self, args):
        self.start_run = time.time()
        self.path_data = args.path_data
        self.date_range = (args.date_range[0:19], args.date_range[20:])
        self.ds = DataStorage(self.path_data, update_database=True)
        self.idout = args.idout
        self.cmmd_line = " ".join(argparse._sys.argv)
        #
        log.info("Analysis of wait time tests")
        log.info(f"Path: {self.path_data}\nRange: {self.date_range}")
        #
        if args.picklein:
            log.info(f"Reading the metaData from input file {args.picklein}")
            self.metaData = pkl.load(open(args.picklein, "rb"))
            self.idcase = self.metaData["idcase"] + "_" + self.idout
            self.filemetaData = args.picklein
        else:
            log.info("Getting the metaData")
            _ = self.querry_metaData()
            self.idcase = self.metaData["idcase"] + "_" + self.idout
            self.filemetaData = f"MetaData_{self.idcase}.pkl"
            self.savePickle(self.filemetaData)

        if args.output_dir == "dir_idcase":
            output_dir = Path(f"./{self.idcase}")
        else:
            output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
        self.output_dir = output_dir

        if args.report_template == "None":
            self.report_template = None
        else:
            self.report_template = args.report_template

    def savePickle(self, filename):
        """
        This function saves the dictionary (our metaData) in a file with
        pickle format
        """
        # outpath = self.output_dir / filename
        # with outpath.open('wb') as ff:
        #    pkl.dump(self.metaData,ff)
        ff = open(filename, "wb")
        pkl.dump(self.metaData, ff)
        ff.close()

    def querry_metaData(self) -> Dict:
        """
        This function performs the analysis of the wait time procedure.
        """
        tag_ini = find_waittime_tests(self.ds, self.date_range, tag_main="WAITTIME")
        metaData = load_waittime_polan_analysis(
            ds_in=self.ds, tag_in=tag_ini[0], tag_main="WAITTIME"
        )
        self.metaData = metaData
        return metaData

    def mkdir_report(self, reportTemplate_file: str = None):
        """
        This function generates a report with the main results based on
        the report template in ~/striptease/.
        """
        if reportTemplate_file is None:
            path_template = Path(__file__).parent / "templates"
            file_template = str(path_template / "reportTemplate_waitTime_analysis.txt")
        else:
            file_template = reportTemplate_file
            path_template = Path(file_template).parent
        log.info(f"Making the reports. The template used: {file_template}")

        temp = Template(filename=file_template)

        # Saving md
        file_report_md = f"report_{self.idcase}.md"
        with open(self.output_dir / file_report_md, "wt") as outf:
            print(
                temp.render(
                    polna=self.metaData["polna"],
                    date_range=self.date_range[0] + " " + self.date_range[1],
                    fileout=self.filemetaData,
                    metdat=self.metaData,
                    idout=self.idcase,
                    figname=self.figname,
                    cmmd_line=self.cmmd_line,
                ),
                file=outf,
            )

        # Saving pdf and html
        file_report_pdf = f"report_{self.idcase}.pdf"
        file_report_html = f"report_{self.idcase}.html"

        cmmd_pdf = f"pandoc -t pdf -o {self.output_dir/file_report_pdf} {self.output_dir/file_report_md}"
        cmmd_html = f"pandoc -t html5 -o  {self.output_dir/file_report_html} {self.output_dir/file_report_md}"

        os.system(cmmd_pdf)
        os.system(cmmd_html)
        #

    def run(self):
        # Ploting
        log.info("Plotting maps")
        log.info("Plotting the count map")
        plotting_countmap(self.metaData, idout=self.idcase, path_dir=self.output_dir)
        log.info("Plotting the check map of the wait time inputs")
        plotting_checks_params(
            self.metaData, idout=self.idcase, plot_case="WT", path_dir=self.output_dir
        )
        log.info("Plotting the check map of the voltage inputs")
        plotting_checks_params(
            self.metaData, idout=self.idcase, plot_case="VD", path_dir=self.output_dir
        )
        log.info("Plotting the check map of the setting times for each data set")
        plotting_settingTime(self.metaData, idout=self.idcase, path_dir=self.output_dir)
        self.figname = {
            "count": self.output_dir.absolute() / f"Fig_{self.idcase}_countMap.png",
            "waittime": self.output_dir.absolute()
            / f"Fig_{self.idcase}_waitTimeMap.png",
            "voltage": self.output_dir.absolute() / f"Fig_{self.idcase}_voltageMap.png",
            "settingtime": self.output_dir.absolute()
            / f"Fig_{self.idcase}_settingTimeMap.png",
        }

        # Saving report using template
        self.mkdir_report(reportTemplate_file=self.report_template)

        # Total time
        self.end_run = time.time()
        time_run_sec = np.around(self.end_run - self.start_run, 3)
        log.info(
            f"Time run (main routine): {time_run_sec} sec ({time_run_sec / 60:.3f} min)"
        )
        # END main program


if __name__ == "__main__":
    from argparse import ArgumentParser, RawDescriptionHelpFormatter
    import argparse

    parser = ArgumentParser(
        description="Obtains and plots the time wait results for one test",
        formatter_class=RawDescriptionHelpFormatter,
        epilog="""
        Usage example:

        python proganalysis_waittime.py -pd /Users/clopez/lspe-strip-bologna/test_data/ -dr '2021-11-23 19:44:04 2021-11-23 20:38:47' -io test2023-06-13
 
        python proganalysis_waittime.py -pd /Users/clopez/lspe-strip-bologna/test_data/ -dr '2021-11-23 19:44:04 2021-11-23 20:38:47' -io test2023-06-13 -pkl MetaData_WAITTIME_V0_HA1_2021-11-23T19:44:04_test2023-06-13.pkl -od dir_idcase
        
        """,
    )

    parser.add_argument(
        "-pd",
        "--pathdata",
        metavar="FILENAME",
        type=str,
        dest="path_data",
        default="",
        help="Path of the local folder with data to be processed with DataStorage",
    )

    parser.add_argument(
        "-dr",
        "--daterange",
        metavar="FILENAME",
        type=str,
        dest="date_range",
        default="2021-11-23 19:44:04 2021-11-23 20:38:47",
        help="Dates range to be considered in the wait time analysis."
        "If not provided, we use '2021-11-23 19:44:04 2021-11-23 20:38:47'",
    )

    parser.add_argument(
        "-io",
        "--idout",
        metavar="FILENAME",
        type=str,
        dest="idout",
        default="",
        help="Extra identification name to write the output (file and figures).",
    )

    parser.add_argument(
        "-od",
        "--outputdir",
        metavar="FILENAME",
        type=str,
        dest="output_dir",
        default="./",
        help="Path with the output folder to save results and products" "",
    )

    parser.add_argument(
        "-pkl",
        "--pickle",
        metavar="FILENAME",
        type=str,
        dest="picklein",
        default="",
        help="Input file (pickle format) with the dictionary with the information" "",
    )

    parser.add_argument(
        "-rt",
        "--reporttemplate",
        metavar="FILENAME",
        type=str,
        dest="report_template",
        default="None",
        help="Input file with the report template of mako."
        "If not we use the 'reportTemplate_waitTime_analysis.txt' in ~/striptease/templates/",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()],
    )
    log = logging.getLogger("rich")

    proc = checks_waitTime_analysis(args=args)
    proc.run()
