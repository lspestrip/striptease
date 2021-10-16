#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import striptease as st
from striptease.hdf5files import DataFile
from matplotlib import pyplot as plt
import h5py
import numpy as np
import pickle as pkl

import warnings
import logging as log

# Util functions
def get_string_from_tag(tags_arr, idtags, relational_op="start", idx_str=1):
    """
    This function finds tags which start/contain a particular
    iditenfication string (idtags).

    Params:
    -------

    Return:
    -------

    """
    out = []
    for tt in tags_arr["tag"].astype(str):
        if relational_op == "in":
            if idtags in tt:
                pol = tt.split(idtags)[idx_str]
                out.append(pol)
        elif relational_op == "start":
            if tt.startswith(idtags):
                pol = tt.split(idtags)[idx_str]
                out.append(pol)
        elif relational_op == "end":
            if tt.endswith(idtags):
                pol = tt.split(idtags)[idx_str]
                out.append(pol)
    return out


def get_time_tag_start(tags_arr, idtags):
    """
    This function provides the time for which tags start with
    a particular iditenfication string (idtags).

    Params:
    -------

    Return:
    -------

    """
    out = []
    for ii, tt in enumerate(tags_arr["tag"].astype(str)):
        if tt.startswith(idtags):
            out.append(
                [tags_arr["mjd_start"][ii], tags_arr["mjd_end"][ii], tags_arr["id"][ii]]
            )
    return out


def get_info_tag_start(tags_arr, idtags):
    """
    This function provides the information (idx, times and comments)
    for which tags start with a particular iditenfication string
    (idtags).

    Params:
    -------

    Return:
    -------

    """
    out = []
    for ii, tt in enumerate(tags_arr["tag"].astype(str)):
        if tt.startswith(idtags):
            pol = tt.split(idtags)[1]
            out.append(
                [
                    tags_arr["id"][ii],
                    tags_arr["mjd_start"][ii],
                    tags_arr["mjd_end"][ii],
                    tags_arr["start_comment"][ii],
                    tags_arr["end_comment"][ii],
                ]
            )
    return out


def get_time_tag_in(tags_arr, idtags):
    """
    This function provides the time for which tags contain a
    particular iditenfication string (idtags).

    Params:
    -------

    Return:
    -------

    """
    out = []
    for ii, tt in enumerate(tags_arr["tag"].astype(str)):
        if idtags in tt:
            pol = tt.split(idtags)[1]
            out.append([tags_arr["mjd_start"][ii], tags_arr["mjd_end"][ii]])
    return out


def get_info_tag_in(tags_arr, idtags):
    """
    This function provides the information (idx, times and comments)
    for which tags contain a particular iditenfication string
    (idtags).

    Params:
    -------

    Return:
    -------

    """
    out = []
    for ii, tt in enumerate(tags_arr["tag"].astype(str)):
        if idtags in tt:
            pol = tt.split(idtags)[1]
            out.append(
                [
                    tags_arr["id"][ii],
                    tags_arr["mjd_start"][ii],
                    tags_arr["mjd_end"][ii],
                    tags_arr["start_comment"][ii],
                    tags_arr["end_comment"][ii],
                ]
            )
    return out


def get_selection_time(datfile, param, t0, t1=None):
    """
    This function obtains the selected points, time and param
    values in a time range defined between t0 and [t1].

    Params:
    -------
    datfile:

    param: string with the group (BIAS or DAQ), subgroup
    (BOARD_X or POL_XY) and parameter name.
            *) ['BIAS','POL_V0','VD1_HK']
            *) ['BIAS POL_V0 VD1_HK']

    Return:
    -------


    """
    if type(param) is str:
        param = param.split(" ")
    if len(param) != 3:
        raise ValueError(f"Invalid param name {param}")

    tt, vpar = datfile.load_hk(param[0], param[1], param[2])
    #
    if t1 is None:
        selcut = tt.value >= t0
    else:
        selcut = (tt.value >= t0) * (tt.value <= t1)
    #
    if selcut.sum() == 0:
        return selcut, np.nan, np.nan
    else:
        return selcut, tt[selcut], vpar[selcut]


def get_selection_param(datfile, param, t0, t1=None):
    """
    This function provides the information of one point (time,
    param value) from selected points in a time range defined
    between t0 and [t1].

    Params:
    -------
    datfile:

    param: string with the group (BIAS or DAQ), subgroup
    (BOARD_X or POL_XY) and parameter name.
            *) ['BIAS','POL_V0','VD1_HK']
            *) ['BIAS POL_V0 VD1_HK']

    Return:
    -------


    """
    selcut, tt, vv = get_selection_time(datfile, param, t0, t1=t1)
    #
    ncount = np.size(tt)
    #
    if ncount == 0:
        tpar, vpar = np.nan, np.nan
    elif ncount == 1:
        tpar, vpar = tt, vv
    else:
        tpar, vpar = tt[-1], vv[-1]
    #
    dictOut = {"count": ncount, "param": param, "time_par": tt, "value_par": vv}
    return tpar, vpar, dictOut


def load_one_curve_polna(datfile, tags_arr, pol, lna, tag_ref="SET_VGVD_"):
    """
    This function obtains the ID, VG and VD for one LNA
    (in one polarimeter).

    Params:
    -------

    Return:
    -------

    """
    lna_num = st.get_lna_num(lna)
    idcur_in = f"{pol}_{lna}_{tag_ref}"

    tagcur_all = get_string_from_tag(tags_arr, idcur_in, relational_op="in")
    #
    vg_idx = np.unique(np.array([cc.split("_")[0] for cc in tagcur_all]).astype(int))
    vd_idx = np.unique(np.array([cc.split("_")[1] for cc in tagcur_all]).astype(int))

    curAll = np.zeros(
        [np.max(vg_idx) + 1, np.max(vd_idx) + 1],
        [("DrainI", "<f4"), ("GateV", "<f4"), ("DrainV", "<f4")],
    )
    curInfo = np.zeros(
        [np.max(vg_idx) + 1, np.max(vd_idx) + 1],
        [("count", "<f4"), ("t_start", "<f4"), ("t_end", "<f4")],
    )

    param_vg = f"BIAS POL_{pol} VG{lna_num}_HK"
    param_vd = f"BIAS POL_{pol} VD{lna_num}_HK"
    param_id = f"BIAS POL_{pol} ID{lna_num}_HK"

    print(f"Case: {idcur_in}")
    print(f"reading: {param_vg}, {param_vd}, {param_id}\n")
    # print(f"\n\t tagcur_all: {tagcur_all}")
    # print(f"\n\t vg_idx: {vg_idx}\n\t vd_idx: {vd_idx}")
    for cc in tagcur_all:
        idx_vg = int(cc.split("_")[0])
        idx_vd = int(cc.split("_")[1])
        t0, t1 = get_time_tag_in(tags_arr, idcur_in + cc)[0]

        tvg, vvg, dictVG = get_selection_param(datfile, param_vg, t0, t1)
        tvd, vvd, dictVD = get_selection_param(datfile, param_vd, t0, t1)
        tid, vid, dictID = get_selection_param(datfile, param_id, t0, t1)

        nc_vg, nc_vd, nc_id = dictVG["count"], dictVD["count"], dictID["count"]
        if nc_vg != nc_vd or nc_vd != nc_id:
            valid = f"\n\t{pol}_{lna} for {cc} (nVg,nVD,nID):{nc_vg},{nc_vd},{nc_id}"
            raise warnings.warn(f"VG, VD and ID counts are different {valid}")

        curAll[idx_vg, idx_vd] = vid, vvg, vvd
        curInfo[idx_vg, idx_vd] = nc_id, t0, t1
    return curAll, curInfo


class IVcurve_analysis:
    def __init__(self, args, picklein=None):
        if args.filename:
            self.file = args.filename
        else:
            raise ValueError(f"Input file is needed")
        self.data = h5py.File(self.file, "r")
        self.dfile = DataFile(self.file)
        #
        if args.picklein:
            print(f"\n\t--> Loading self.allivcurves from {args.picklein}\n")
            self.allivcurves = pkl.load(open(args.picklein, "rb"))
        else:
            print("\n\t--> Getting self.allivcurves \n")
            _ = self.query_ivcurves(silent=True)
        #
        self.idout = args.idout

    def savePickle(self, filename, all=False):
        """
        This function saves, in a pickle file, the dictionary with
        the IV curves.

        --Note: This function saves self.allivcurves.

        --Parameters
        filename : string file name.
        """
        ff = open(filename, "wb")
        if all is True:
            pkl.dump(self.allivcurves, ff)
        else:
            pkl.dump(self.allivcurves, ff)
        ff.close()

    def query_ivcurves(self, silent=True):
        """
        This function provides the IV curve and information analysis for
        one file in STRIP format .h5

        Params:
        -------

        Return:
        -------

        """
        tags = self.data["TAGS"]["tag_data"][()]
        # Main dictionary
        metaData = {}
        # get polarimeters
        pol_in = get_string_from_tag(tags, "IVTEST_")
        vv = np.array([pp for pp in pol_in if len(pp) == 2])
        index = np.unique(vv, return_index=True)[1]
        pol_all = vv[np.unique(index)]
        #
        for pp in pol_all:
            cases_pp = get_string_from_tag(tags, f"{pp}_")
            lna_in = np.unique([cc.split("_")[0] for cc in cases_pp])
            #
            # log.info("Polarimeter %s (LNAs):%s \n",pp,lna_in)
            print(f"Polarimeter {pp} (LNAs):{lna_in}")
            dictLnas = {}
            for ll in lna_in:
                cur0, count0 = load_one_curve_polna(
                    self.dfile, tags, pp, ll, tag_ref="SET_VGVD_"
                )
                dictLnas[ll] = {"curves": cur0, "info": count0}
                #
                metaData[pp] = dictLnas
        #
        self.allivcurves = {**metaData}
        return metaData

    def plotting_ivcurve(self, idout=None):
        #
        md = self.allivcurves
        #
        if idout is None:
            idout = self.idout
        #
        pol_module = md.keys()
        print(f"\n Plotting\n\tPolarimeters:\n {pol_module}")

        for pp in pol_module:
            lna_name = md[pp].keys()
            for ll in lna_name:
                curAll = md[pp][ll]["curves"]
                plt.figure(figsize=(18.0 / 2.54, 10.0 / 2.54))
                plt.subplot(1, 2, 1)
                plt.title(f"{pp} ({ll})")
                plt.xlabel("VD [mV]")
                plt.ylabel("ID [uA]")
                plt.plot(curAll["DrainV"], curAll["DrainI"], ".-", alpha=0.5)
                #
                plt.subplot(1, 2, 2)
                plt.tick_params(labelleft=False)
                plt.xlabel("VG [mV]")  # ; plt.ylabel('ID [uA]')
                plt.title(f"{pp} ({ll})")
                plt.plot(curAll["GateV"], curAll["DrainI"], ".-", alpha=0.5)
                #
                plt.savefig(f"Fig_{idout}_{pp}_{ll}.png", dpi=300, box_inches="tigh")
                plt.close()

    def run(self):
        #
        self.plotting_ivcurve()
        #
        self.savePickle(f"Table_{self.idout}.pkl")


if __name__ == "__main__":
    from argparse import ArgumentParser, RawDescriptionHelpFormatter

    parser = ArgumentParser(
        description="Obtains and plots the I-V curve test from one file",
        formatter_class=RawDescriptionHelpFormatter,
        epilog="""

Usage example:

    python3 procanalysis_ivcurves.py 2020_12_25_19-30-04.h5 --idout 20210318_TesIVcurve_TestDec2020_25_19-30-04
    
""",
    )

    parser.add_argument(
        "--input",
        "-i",
        metavar="FILENAME",
        type=str,
        dest="filename",
        default="",
        help="Name of file with IV curve test (in JSON format).",
    )

    parser.add_argument(
        "--idout",
        "-io",
        metavar="FILENAME",
        type=str,
        dest="idout",
        default="Test_IVcurve",
        help="Identification name to write the output (file and figures). "
        "If not provided, the idout is 'Test_IVcurve'.",
    )
    parser.add_argument(
        "--pickle",
        "-pkl",
        metavar="FILENAME",
        type=str,
        dest="picklein",
        default="",
        help="" "",
    )

    args = parser.parse_args()

    log.basicConfig(level=log.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    proc = IVcurve_analysis(args=args)
    proc.run()
