# -*- encoding: utf-8 -*-

# This file contains the Class Polarimeter
# Part of this code was used in Francesco Andreetto's bachelor thesis (2020) and master thesis (2023).
# Use this Class with the new version of the pipeline for functional verification of LSPE-STRIP (2024).

# November 1st 2022, Brescia (Italy) - May 13th 2024, Bologna (Italy)

# Libraries & Modules
import logging
import numpy as np
import scipy.stats as scs
import scipy.signal

from astropy.time import Time
import astropy.units as u
from datetime import datetime
from matplotlib import pyplot as plt
from pathlib import Path
from rich.logging import RichHandler
from striptease import DataStorage
from typing import List, Dict, Any

# MyLibraries & MyModules
import f_strip as fz

# Use the module logging to produce nice messages on the shell
logging.basicConfig(level="INFO", format='%(message)s',
                    datefmt="[%X]", handlers=[RichHandler()])


########################################################################################################
# Class: Polarimeter
########################################################################################################
class Polarimeter:

    def __init__(self, name_pol: str, path_file: str, start_datetime: str, end_datetime: str, output_plot_dir: str):
        """
        Constructor

            Parameters:
                - **name_pol** (``str``): name of the polarimeter.
                - **path_file** (``str``): location of the data file and hdf5 file index (without the name of the file)
                - **start_datetime** (``str``): start time
                - **end_datetime** (``str``): end time
                - **output_plot_dir** (``str``): output directory of the plots
        """
        # Store the name of the polarimeter
        self.name = name_pol
        # Create a Datastorage from the path of the file
        self.ds = DataStorage(str(path_file))

        # Sampling Frequency of Strip. Std value = 100 Hz
        self.STRIP_SAMPLING_FREQ = 0
        # Normalization Modality: 0 (output vs index), 1 (output vs time in s), 2 (output vs time in Julian Date JHD)
        self.norm_mode = 0

        # Julian Date MJD
        self.date = [Time(start_datetime).mjd, Time(end_datetime).mjd]
        # Gregorian Date [in string format]
        self.gdate = [Time(start_datetime), Time(end_datetime)]
        # Directory where to save all plot for a given analysis
        self.date_dir = fz.dir_format(f"{self.gdate[0]}__{self.gdate[1]}")
        # Time(self.date, format="mjd").to_datetime().strftime("%Y-%m-%d %H:%M:%S")
        # Output directory of the plots
        self.output_plot_dir = output_plot_dir

        # Dictionary for scientific Analysis
        self.times = []  # type: List[float]

        # Dictionaries for scientific outputs PWR and DEM
        power = {}
        dem = {}
        self.data = {"DEM": dem, "PWR": power}

        # Dictionary for Housekeeping Analysis
        self.hk_list = {"V": ["VG0_HK", "VD0_HK", "VG1_HK", "VD1_HK", "VG2_HK", "VD2_HK", "VG3_HK", "VD3_HK",
                              "VG4_HK", "VD4_HK", "VD5_HK", "VG5_HK"],
                        "I": ["IG0_HK", "ID0_HK", "IG1_HK", "ID1_HK", "IG2_HK", "ID2_HK", "IG3_HK", "ID3_HK",
                              "IG4_HK", "ID4_HK", "IG5_HK", "ID5_HK"],
                        "O": ["DET0_OFFS", "DET1_OFFS", "DET2_OFFS", "DET3_OFFS"],
                        "M": ["POL_MODE"],
                        "P": ["PIN0_CON", "PIN1_CON", "PIN2_CON", "PIN3_CON"]
                        }
        # Dictionaries for HK parameters: Voltages, Currents, Offsets, Pol_Mode, Pin_Con
        tensions = {}
        currents = {}
        offset = {}
        pol_mode = {}
        pin_con = {}
        # Dictionaries for timestamps of HK parameters
        t_tensions = {}
        t_currents = {}
        t_offset = {}
        t_pol_mode = {}
        t_pin_con = {}
        self.hk = {"V": tensions, "I": currents, "O": offset, "M": pol_mode, "P": pin_con}
        self.hk_t = {"V": t_tensions, "I": t_currents, "O": t_offset, "M": t_pol_mode, "P": t_pin_con}

        # Warnings lists
        time_warning = []
        sampling_warning = []
        corr_warning = []
        eo_warning = []
        spike_warning = []
        self.warnings = {"time_warning": time_warning,
                         "sampling_warning": sampling_warning,
                         "corr_warning": corr_warning,
                         "eo_warning": eo_warning,
                         "spike_warning": spike_warning}

    def Load_Pol(self):
        """
        Load all dataset in the polarimeter.
        - All type "DEM" and "PWR"
        - All the exit "Q1", "Q2", "U1", "U2"
        """
        for type in self.data.keys():
            for exit in ["Q1", "Q2", "U1", "U2"]:
                self.times, self.data[type][exit] = self.ds.load_sci(mjd_range=self.date, polarimeter=self.name,
                                                                     data_type=type, detector=exit)
        # Reset the sampling frequency
        self.STRIP_SAMPLING_FREQ = 0

    def Load_X(self, type: str):
        """
        Load only a specific type of dataset "PWR" or "DEM" in the polarimeter.

            Parameters:\n
                - **type** (``str``) *"DEM"* or *"PWR"*
        """
        for exit in ["Q1", "Q2", "U1", "U2"]:
            self.times, self.data[type][exit] = self.ds.load_sci(mjd_range=self.date, polarimeter=self.name,
                                                                 data_type=type, detector=exit)
        # Reset the sampling frequency
        self.STRIP_SAMPLING_FREQ = 0

    def Load_Times(self, range: []):
        """
        Load the Timestamps in the polarimeter and put to 0 the STRIP Sampling Frequency.
        Useful to calculate quickly the STRIP Sampling Frequency in the further steps without loading the whole Pol.

            Parameters:\n
                - **range** (``Time``) is an array-like object containing the Time objects: start_date and end_date.
        """
        self.times, _ = self.ds.load_sci(mjd_range=range, polarimeter=self.name, data_type="DEM", detector="Q1")
        # Reset the sampling frequency
        self.STRIP_SAMPLING_FREQ = 0

    def Date_Update(self, n_samples: int, modify=True) -> Time:
        """
        Calculates and returns the new Gregorian date in which the experience begins, given a number of samples that
        must be skipped from the beginning of the dataset.

            Parameters:\n
                - **n_samples** (``int``) number of samples that must be skipped\n
                - **modify** (``bool``)\n
                    \t*"True"* -> The beginning date is definitely modified and provided.\n
                    \t*"False"* -> A copy of the beginning date is modified and provided.\n
        """
        # A second expressed in days unit
        s = 1 / 86_400
        if modify:
            # Julian Date increased
            self.date[0] += s * (n_samples / 100)
            # Gregorian Date conversion
            self.gdate[0] = Time(self.date[0], format="mjd").to_datetime().strftime("%Y-%m-%d %H:%M:%S")
            return self.gdate[0]
        else:
            new_jdate = self.date[0]
            # Julian Date increased
            new_jdate += s * (n_samples / 100)
            # Gregorian Date conversion
            new_date = Time(new_jdate, format="mjd").to_datetime().strftime("%Y-%m-%d %H:%M:%S")
            return new_date

    def Clip_Values(self):
        """
        Data cleansing: Scientific Outputs with value zero at the beginning and at the end are removed from the dataset
        Control that a channel doesn't turn on before the others (maybe unuseful)
        """
        begin_zerovalues_idx = 0
        end_zerovalues_idx = 10_000_000

        for type in [x for x in self.data.keys() if not self.data[x] == {}]:
            for exit in ["Q1", "Q2", "U1", "U2"]:
                for count, item in reversed(list(enumerate(self.data[type][exit]))):
                    if item != 0:
                        end_zerovalues_idx = np.min([end_zerovalues_idx, count + 1])
                        break
                for count, item in enumerate(self.data[type][exit]):
                    if item != 0:
                        begin_zerovalues_idx = np.max([begin_zerovalues_idx, count])
                        break

        # Cleansing operations
        self.times = self.times[begin_zerovalues_idx:end_zerovalues_idx + 1]
        for type in [x for x in self.data.keys() if not self.data[x] == {}]:
            for exit in ["Q1", "Q2", "U1", "U2"]:
                self.data[type][exit] = self.data[type][exit][begin_zerovalues_idx:end_zerovalues_idx + 1]

        # Updating the new beginning time of the dataset
        _ = self.Date_Update(n_samples=begin_zerovalues_idx, modify=True)

    def STRIP_SAMPLING_FREQUENCY_HZ(self, warning=True):
        """
        Calculate the Strip Sampling Frequency by dividing the # of output saved during a period of time. Std value=100.
        It depends on the electronics hence it's the same for all polarimeters.
        Note: it must be defined before time normalization.
        """
        # Calculate the Strip Sampling Frequency
        self.STRIP_SAMPLING_FREQ = int(
            len(self.times) / (self.times[-1].datetime - self.times[0].datetime).total_seconds())

        if warning:
            if int(self.STRIP_SAMPLING_FREQ) != 100:
                msg = f"Sampling frequency is {self.STRIP_SAMPLING_FREQ} different from the std value of 100.\n " \
                      f"This can cause inversions in even-odd sampling. \n" \
                      f"Some changes in the offset might have occurred: Some channel turned off?\n" \
                      f"There is at least a hole in the sampling: after the normalization, seconds are not significant."
                logging.error(msg)
                self.warnings["eo_warning"].append(msg)

    def Fix_Timestamps(self, j_info: {}):
        """
        Fix the timestamps assignment applying a jump forward in time.
        Parameters:\n **j_info** (``{}``) dictionary obtained from the function `find_jump` in the module `f_strip.py`;
        """
        for i in range(0, j_info["n"] - 1, 2):
            print(i)
            self.times[j_info["idx"][i] + 1:j_info["idx"][i + 1] + 1] += \
                u.day * np.mean([np.abs(j_info["value"][i]), np.abs(j_info["value"][i + 1])])

    def Norm(self, norm_mode: int):
        """
        Timestamps Normalization\n
        Parameters:\n **norm_mode** (``int``) can be set in two ways:
        0) the output is expressed in function of the number of samples
        1) the output is expressed in function of the time in s from the beginning of the experience
        2) the output is expressed in function of the number of the Julian Date JHD
        """
        if norm_mode == 0:
            # Outputs vs Number of samples
            self.times = np.arange(len(self.times))
        if norm_mode == 1:
            # Outputs vs Seconds
            self.times = self.times.unix - self.times[0].unix
        if norm_mode == 2:
            # Outputs vs JHD
            self.times = self.times.value

    def Prepare(self, norm_mode: int):
        """
        Prepare the polarimeter in two steps:\n
            1. Calculate Strip Sampling Frequency
            2. Normalize timestamps

                Parameters:\n
            **norm_mode** (``int``) can be set in two ways:
                0) the output is expressed in function of the number of samples
                1) the output is expressed in function of the time in s from the beginning of the experience
                2) the output is expressed in function of the number of the Julian Date JHD
        """
        self.norm_mode = norm_mode

        # This function would remove zero-value data from the beginning and from the end of a dataset,
        # but it produces a weird behaviour for the pol R1 in 2023/03/13
        # self.Clip_Values()

        if self.STRIP_SAMPLING_FREQ > 0:
            logging.warning(f"The dataset has already been normalized. "
                            f"Strip Sampling Frequency = {self.STRIP_SAMPLING_FREQ}.")
            return 0
        # 1. Calculate Strip Sampling Frequency
        self.STRIP_SAMPLING_FREQUENCY_HZ()
        # 2. Normalize timestamps
        self.Norm(norm_mode)

        logging.info(f"Pol {self.name}: the dataset is now normalized.")
        if norm_mode == 0:
            logging.info("Dataset in function of sample number [#]")
        if norm_mode == 1:
            logging.info("Dataset in function of time [s].")

    def Demodulation(self, type: str, exit: str, begin=0, end=-1) -> Dict[str, Any]:
        """
        Demodulation\n
        Calculate the Scientific data DEMODULATED or TOTAL POWER at 50Hz\n
        Timestamps are chosen as mean of the two consecutive times of the DEM/PWR data\n

            Parameters:\n
        - **exit** (``str``) *"Q1"*, *"Q2"*, *"U1"*, *"U2"*\n
        - **type** (``str``) of data *"DEM"* or *"PWR"*
        - **begin**, **end** (``int``): indexes of the data that have to be considered
        """
        # Mean of the two consecutive times
        times = fz.mean_cons(self.times)
        data = {}
        if type == "PWR":
            # Mean of two consecutive outputs
            data[exit] = fz.mean_cons(self.data[type][exit][begin:end])
        if type == "DEM":
            # Difference of two consecutive outputs
            data[exit] = fz.diff_cons(self.data[type][exit][begin:end])

        sci_data = {"sci_data": data, "times": times}
        return sci_data

    # ------------------------------------------------------------------------------------------------------------------
    # HOUSE-KEEPING ANALYSIS
    # ------------------------------------------------------------------------------------------------------------------
    def Load_HouseKeeping(self):
        """
        Load House-Keeping parameters using the module load_hk of the striptease library.
        Take the names of the HK parameters from the list in the constructor.
        """
        # Iterate over items I, V, O, M, P
        for item in self.hk_list.keys():
            # Define the correct group of HK
            group = "DAQ" if item == "O" else "BIAS"
            # Iterate over specific HK
            for hk_name in self.hk_list[item]:
                self.hk_t[item][hk_name], self.hk[item][hk_name] = self.ds.load_hk(mjd_range=self.date,
                                                                                   group=group,
                                                                                   subgroup=f"POL_{self.name}",
                                                                                   par=hk_name
                                                                                   )

    def Norm_HouseKeeping(self) -> []:
        """
        Check if the Timestamps array and the House-keeping data array have the same length.
        Normalize all House-Keeping's timestamps putting one every 1.4 seconds from the beginning of the dataset.
        Return a list of problematic HK
        """
        # Initialize a list of problematic HK
        problematic_hk = []
        # Initialize a boolean variable to True meaning there is no sampling problems
        good_sampling = True
        for item in self.hk_list.keys():
            for hk_name in self.hk_list[item]:
                # Checking the length of the data array and the timestamps array
                l1 = len(self.hk_t[item][hk_name])
                l2 = len(self.hk[item][hk_name])
                # If the lengths are different print and store a warning
                if l1 != l2:
                    good_sampling = False
                    msg = (f"The House-Keeping: {hk_name} has a sampling problem. "
                           f"The array of Timestamps has a wrong length\n")
                    logging.error(msg)

                    # [MD] Append the message with the problematic HK
                    self.warnings["time_warning"].append(msg + "\n")

                    # [CSV] Append the name of a problematic HK
                    problematic_hk.append(f"{self.name} - {hk_name}")

                # Convert to seconds the timestamps of Housekeeping Parameters: Offsets, Currents and Voltages
                self.hk_t[item][hk_name] = self.hk_t[item][hk_name].unix - self.hk_t[item][hk_name][0].unix

        # In the end if there are no sampling problems a message is printed and stored
        if good_sampling:
            msg = "\nThe assignment of the Timestamps of the House-Keeping parameters is good.\n"
            logging.info(msg)
            self.warnings["time_warning"].append(msg)

        return problematic_hk

    def Analyse_HouseKeeping(self) -> {}:
        """
        Analise the following HouseKeeping parameters: I Drain, I Gate, V Drain, V Gate, Offset.\n
        See self.hk_list in the constructor.\n
        Calculate the mean the std deviation.
        """
        I_m = {}
        V_m = {}
        O_m = {}
        # Initialize a dict for the mean values of the HK
        mean = {"I": I_m, "V": V_m, "O": O_m}

        I_std = {}
        V_std = {}
        O_std = {}
        # Initialize a dict for the dev_std of the values of the HK
        dev_std = {"I": I_std, "V": V_std, "O": O_std}

        I_nan = {}
        V_nan = {}
        O_nan = {}
        # Initialize a dict for the percentage of nan values in the HK
        nan_percent = {"I": I_nan, "V": V_nan, "O": O_nan}

        I_max = {}
        V_max = {}
        O_max = {}
        # Initialize a dict for the max values of the HK
        hk_max = {"I": I_max, "V": V_max, "O": O_max}

        I_min = {}
        V_min = {}
        O_min = {}
        # Initialize a dict for the min values of the HK
        hk_min = {"I": I_min, "V": V_min, "O": O_min}

        # Initialize a dict for the results of the analysis of the HK
        results = {"max": hk_max, "min": hk_min, "mean": mean, "dev_std": dev_std, "nan_percent": nan_percent}

        # Cycle over the HK (excluding the "M": POL_MODE and "P": PIN_CON)
        for item in (k for k in self.hk_list.keys() if k not in ["M", "P"]):
            for hk_name in self.hk_list[item]:
                results["nan_percent"][item][hk_name] = 0.

                data = self.hk[item][hk_name]
                m = np.mean(data)
                # Check if the mean isnan
                if np.isnan(m):
                    n_nan = len([t for t in np.isnan(data) if t == True])

                    # No data -> 100% nan values
                    if len(data) == 0:
                        results["nan_percent"][item][hk_name] = 100.
                    # Calculate % nan
                    else:
                        results["nan_percent"][item][hk_name] = round((n_nan / len(data)), 4) * 100.

                    # If the nan % is smaller than 5% remove the nan values and calculate the mean once more
                    if results["nan_percent"][item][hk_name] < 5:
                        data = np.delete(data, np.argwhere(np.isnan(data)))
                        m = np.mean(data)

                results["max"][item][hk_name] = max(data)
                results["min"][item][hk_name] = min(data)
                results["mean"][item][hk_name] = m
                results["dev_std"][item][hk_name] = np.std(data)

        return results

    def HK_table(self, results: dict) -> {}:
        """
        Create a dictionary containing a string and a list to produce a table of Housekeeping results.
        The string contains the code for Markdown reports, the list is used for CSV reports.
        In the table there are the following info:
            1. HK-Parameter name
            2. Max value
            3. Min value
            4. Mean value
            5. Standard deviation
            6. NaN percentage
        The HouseKeeping parameters included are: I Drain, I Gate, V Drain, V Gate, Offset.

            Parameters:\n
        **results** (``dict``): contains the info about hk analysis obtained with Analyze_Housekeeping
        """
        # Initialize a string to contain the md table
        md_table = " "
        # Initialize a list to contain the csv table
        csv_table = []

        # Cycle over the HK (excluding the "M": POL_MODE)
        for item in (k for k in self.hk_list.keys() if k not in ["M", "P"]):
            # Voltage V
            if item == "V":
                unit = "[mV]"
                title = f"Voltage {unit}"
            # Current I
            elif item == "I":
                unit = "[&mu;A]"
                title = f"Current {unit}"
            # Offset O
            else:
                unit = "[ADU]"
                title = f"Offset {unit}"

            # [MD] Heading of the table
            md_table += (f"\n"
                         f"- {title}\n\n"
                         f"| Parameter | Max Value {unit} | Min Value {unit} | Mean {unit} | Std_Dev {unit} | NaN % |"
                         "\n"
                         " |:---------:|:-----------:|:-----------:|:------:|:---------:|:-----:|"
                         "\n"
                         )
            # [CSV] Heading of the table
            csv_table.append([""])
            csv_table.append([f"{title}"])
            csv_table.append([""])
            csv_table.append(["Parameter", f"Max Value {unit}", f"Min Value {unit}",
                              f"Mean {unit}", f"Std_Dev {unit}", "NaN %"])
            csv_table.append([""])

            for hk_name in self.hk_list[item]:
                # [MD] Filling the table with values
                md_table += (f"|{hk_name}|{round(results['max'][item][hk_name], 4)}|"
                             f"{round(results['min'][item][hk_name], 4)}|"
                             f"{round(results['mean'][item][hk_name], 4)}|"
                             f"{round(results['dev_std'][item][hk_name], 4)}|"
                             f"{round(results['nan_percent'][item][hk_name], 4)}|"
                             f"\n"
                             )

                # [CSV] Filling the table with values
                csv_table.append([f"{hk_name}", f"{round(results['max'][item][hk_name], 4)}",
                                  f"{round(results['min'][item][hk_name], 4)}",
                                  f"{round(results['mean'][item][hk_name], 4)}",
                                  f"{round(results['dev_std'][item][hk_name], 4)}",
                                  f"{round(results['nan_percent'][item][hk_name], 4)}"])

        # Initialize a dictionary with the two tables: MD and CSV
        table = {"md": md_table, "csv": csv_table}
        return table

    def HK_Sampling_Table(self, sam_exp_med: dict, sam_tolerance: dict) -> {}:
        """
        Create a dictionary with the info of the housekeeping parameter sampling.
        The dictionary has two keys "md" and "csv" - each contains a list with the info to create the relative report
        The current code produces a table with the following information:
            1. HK-Parameter name
            2. Number of sampling jumps
            3. Median jump
            4. Expected median jump
            5. The 5th percentile
            6. The 95th percentile
        The HouseKeeping parameters included are: I Drain, I Gate, V Drain, V Gate, Offset.

            Parameters:\n
        - **sam_exp_med** (``dict``): contains the exp sampling delta between two consecutive timestamps of the hk
        - **sam_tolerance** (``dict``): contains the acceptance sampling tolerances of the hk parameters: I,V,O
        """
        # Initialize a warning dict and a jump list to collect info about the samplings
        sampling_info = {}

        # [MD] Initialize a result list
        md_results = []
        # [CSV] Initialize a result list
        csv_results = []

        # Initialize a result dict for the reports
        sampling_results = {"md": md_results, "csv": csv_results}

        # Initialize a boolean variable: if true, no jumps occurred
        good_sampling = True

        # Find jumps in the timestamps of the HK parameters: V, I, O
        # Cycle over the HK (excluding the "M": POL_MODE and "P": PIN_CON)
        for item in (k for k in self.hk_list.keys() if k not in ["M", "P"]):
            for hk_name in self.hk_list[item]:
                jumps = fz.find_jump(self.hk_t[item][hk_name],
                                     exp_med=sam_exp_med[item], tolerance=sam_tolerance[item])

                # Store the dict if there are jumps
                if jumps["n"] > 0:
                    good_sampling = False
                    sampling_info.update({f"{hk_name}": jumps})

        # No Jumps detected
        if good_sampling:
            sampling_results["md"].append(["\nThe sampling of the House-Keeping parameters is good: "
                                           "no jumps in the HK Timestamps\n"])
            sampling_results["csv"].append(["House-Keeping Sampling:", "GOOD", "No jumps in HK Timestamps"])
            sampling_results["csv"].append([""])

        # Jumps detected
        else:

            # [MD] Preparing Table caption
            sampling_results["md"].append(
                "| HK Name | # Jumps | &Delta;t Median [s] | Exp &Delta;t [s] | Tolerance "
                "| 5th percentile | 95th percentile |\n"
                "|:---------:|:-------:|:-------------------:|:-----------------------:|:---------:"
                "|:--------------:|:---------------:|\n")
            # [CSV] Preparing Table caption
            sampling_results["csv"].append(["HK Name", "# Jumps", "Delta t Median [s]", "Exp Delta t Median [s]",
                                            "Tolerance", "5th percentile", "95th percentile"])
            sampling_results["csv"].append([""])

            # Saving...
            for name in sampling_info.keys():
                # [MD] Storing HK sampling information
                sampling_results["md"].append(
                    f"|{name}|{sampling_info[name]['n']}"
                    f"|{sampling_info[name]['median']}|{sampling_info[name]['exp_med']}"
                    f"|{sampling_info[name]['tolerance']}"
                    f"|{sampling_info[name]['5per']}|{sampling_info[name]['95per']}|\n")

                # [CSV] Storing TS sampling information
                sampling_results["csv"].append([f"{name}",
                                                f"{sampling_info[name]['n']}",
                                                f"{sampling_info[name]['median']}",
                                                f"{sampling_info[name]['exp_med']}",
                                                f"{sampling_info[name]['tolerance']}",
                                                f"{sampling_info[name]['5per']}",
                                                f"{sampling_info[name]['95per']}"])

        return sampling_results

    # ------------------------------------------------------------------------------------------------------------------
    # PLOT FUNCTION
    # ------------------------------------------------------------------------------------------------------------------

    def Plot_Housekeeping(self, hk_kind: str, show=False):
        """
        Plot all the acquisitions of the chosen HouseKeeping parameters of the polarimeter.

            Parameters:\n

            - **hk_kind** (``str``): defines the hk to plot.
            *V* -> Drain Voltage and Gate Voltage\n
            *I* -> Drain Current and Gate Current\n
            *O* -> the Offsets\n
            *M* -> POL_MODE: Modality of biasing of the amplifiers: open (5) or closed (3) loop\n
            *P* -> PIN_CON: Modality of setting the phase switch (four elements of value 5 or 6)
            - **show** (``bool``):
            *True* -> show the plot and save the figure\n
            *False* -> save the figure only\n
        """
        # --------------------------------------------------------------------------------------------------------------
        # Step 1: define data
        if hk_kind not in ["V", "I", "O", "M", "P"]:
            logging.error(f"Wrong name: no HK parameters is defined by {hk_kind}. Choose between V, I, O, M or P")
            raise SystemExit(1)

        # Voltage
        elif hk_kind == "V":
            col = "plum"
            label = "Voltage [mV]"
            n_rows = 6
            n_col = 2
            fig_size = (8, 15)

        # Current
        elif hk_kind == "I":
            col = "gold"
            label = "Current [$\mu$A]"
            n_rows = 6
            n_col = 2
            fig_size = (8, 15)

        # Offset
        elif hk_kind == "O":
            col = "teal"
            label = "Offset [ADU]"
            n_rows = 2
            n_col = 2
            fig_size = (8, 8)

        # Pol Mode
        elif hk_kind == "M":
            col = "crimson"
            label = "Modality [ADU]"
            n_rows = 1
            n_col = 1
            fig_size = (4, 4)

        # Pin Con
        elif hk_kind == "P":
            col = "limegreen"
            label = "PIN_CON [ADU]"
            n_rows = 2
            n_col = 2
            fig_size = (8, 8)

        # Nothing else
        else:
            col = "black"
            label = ""
            n_rows = 0
            n_col = 0
            fig_size = (0, 0)

        hk_name = self.hk_list[hk_kind]

        fig, axs = plt.subplots(nrows=n_rows, ncols=n_col, constrained_layout=True, figsize=fig_size, sharey='row')
        fig.suptitle(f'Plot {self.name} Housekeeping parameters: {hk_kind}\nDate: {self.gdate[0]}', fontsize=14)
        for i in range(n_rows):
            for j in range(n_col):

                # Set plot title
                plot_title = f"{hk_name[2 * i + j]}"

                # Check length mismatch
                l1 = len(self.hk_t[hk_kind][hk_name[2 * i + j]])
                l2 = len(self.hk[hk_kind][hk_name[2 * i + j]])
                if l1 != l2:
                    msg = f"The House-Keeping: {hk_name[2 * i + j]} has a sampling problem.\n"
                    logging.error(msg)
                    self.warnings["time_warning"].append(msg + "<br />")

                # Modality of Biasing Open-Closed Loop (one plot only)
                if hk_kind == "M":
                    axs.scatter(self.hk_t[hk_kind][hk_name[2 * i + j]][:min(l1, l2)],
                                self.hk[hk_kind][hk_name[2 * i + j]][:min(l1, l2)], marker=".", color=col)
                    # X-Axis
                    axs.set_xlabel("Time [s]")
                    # Y-Axis
                    axs.set_ylabel(f"{label}")
                    # Title
                    axs.set_title(plot_title, size=10)

                # Other HK: V, I, O, P
                else:
                    axs[i, j].scatter(self.hk_t[hk_kind][hk_name[2 * i + j]][:min(l1, l2)],
                                      self.hk[hk_kind][hk_name[2 * i + j]][:min(l1, l2)], marker=".", color=col)

                    if hk_kind in ["I", "V", "O"]:
                        # Calculate Plot Statistics
                        # Mean
                        m = round(np.mean(self.hk[hk_kind][hk_name[2 * i + j]][:min(l1, l2)]), 2)
                        # std deviation
                        std = round(np.std(self.hk[hk_kind][hk_name[2 * i + j]][:min(l1, l2)]), 2)
                        # Max value
                        max_val = round(max(self.hk[hk_kind][hk_name[2 * i + j]][:min(l1, l2)]), 4)
                        # Min value
                        min_val = round(min(self.hk[hk_kind][hk_name[2 * i + j]][:min(l1, l2)]), 4)
                        plot_title += f"\n$Mean$={m} - $STD$={std}\n$Max$={max_val} - $Min$={min_val}"

                    # X-Axis
                    axs[i, j].set_xlabel("Time [s]")
                    # Y-Axis
                    axs[i, j].set_ylabel(f"{label}")
                    # Title
                    axs[i, j].set_title(plot_title, size=10)

        # Creating the name of the png file
        name_file = f"{self.name}_HK_{hk_kind}"

        # Creating the directory path
        path = f'{self.output_plot_dir}/HK/'
        Path(path).mkdir(parents=True, exist_ok=True)
        fig.savefig(f'{path}{name_file}.png')

        # If true, show the plot on video
        if show:
            plt.show()
        plt.close(fig)

    def Plot_Band(self, type: str, demodulated: bool, output_path: str,
                  s_start: int, s_duration: int,
                  f_i: float, f_f: float,
                  binning: bool, binning_length=5, show=True):
        """
        Plot the bands of the 4 exits PWR/DEM or TOT_POWER/DEMODULATED of the Polarimeter\n
        Parameters:\n
        - **type** (``str``) of data *"DEM"* or *"PWR"*\n
        - **demodulated** (``bool``): if true, demodulated data are computed, if false even-odd-all output are plotted
        - **file_path** (``str``): Path of the data file.hdf5 (including its name)\n
        - **output_path** (``str``): Path of the dir where the band plots are saved

        - **s_start** (``int``): Number of seconds from the tag acquisition to the beginning of first band
        - **s_duration** (``int``): Duration of the first band in seconds
        - **f_i** (``float``): initial frequency at which the band starts
        - **f_f** (``float``): final frequency at which the band arrives

        - **binning** (``bool``): *True* -> bin the dataset loaded, *False* -> no binning
        - **binning_length** (``int``): number of elements on which the mean in the binning is calculated
        - **show** (``bool``): *True* -> show the plot and save the figure, *False* -> save the figure only
        """
        # Setting channel name
        channel_name = self.name
        logging.info(f"Plotting the bands of {channel_name}")

        # SciData or Output
        data = {}
        # Setting sampling frequency
        fs = 100

        if demodulated:
            # Setting data name
            data_name = "TOTAL_PWR" if type == "PWR" else "DEMODULATED"
            # Setting sampling frequency
            fs = 50
            # Collecting Scientific Data
            for exit in ["Q1", "Q2", "U1", "U2"]:
                data[exit] = fz.demodulate_array(self.data[type][exit], type)
        else:
            # Collecting Scientific Output
            data = self.data[type]
            # Setting data name
            data_name = type

        # --------------------------------------------------------------------------------------------------------------
        # Write on the file the information about the bands
        # Create band file name
        band_file_name = f"{self.name}_Bands_{fz.dir_format(self.gdate[0].value)}_{data_name}"
        # Open file
        file_out = open(f"{output_path}/{band_file_name}.txt", "w")
        # Write
        file_out.write(
            f"Channel Name  exit BW Cent_freq Max_Signal_value Min_Signal_value \n")
        # Close file
        file_out.close()
        # --------------------------------------------------------------------------------------------------------------

        # Naive way to calculate the number of bands in the experiment
        # not looking at the actual behaviour of the data
        # ------------------------------------------------------------------------------------
        # Experiment global duration (Delta time in s)
        dt = (self.gdate[1] - self.gdate[0]).sec
        logging.info(f"Global time = {dt}")
        # Removing Starting seconds to get the actual experiment duration
        dt -= s_start
        logging.info(f"Experiment time =  {dt}")
        # Calculate the number of possible bands in the experiment
        s_num = int(dt / (s_duration + 1))
        logging.info(f"# of Bands Overlapped: {s_num}")
        # ------------------------------------------------------------------------------------

        # --------------------------------------------------------------------------------------------------------------
        # Plotting the Bands
        # --------------------------------------------------------------------------------------------------------------
        fig, axs = plt.subplots(2, 2, gridspec_kw={'hspace': 0.5},
                                figsize=(13, 12))
        axs = np.reshape(axs, 4)
        # Setting Figure Title
        fig_title = f"{channel_name} - {data_name}\nDate: {self.gdate[0]}"
        if binning:
            fig_title += f"\nBinning length = {binning_length}."
        fig.suptitle(f"{fig_title}", size=15)

        for o, exit in enumerate(["Q1", "Q2", "U1", "U2"]):

            # Set the grid for the subplots
            axs[o].grid(True)

            # Setting the correct beginning/end of the experiment
            start = s_start * fs
            stop = start + s_duration * fs

            # Initialize lists to collect the Statistics values of all the bands, they will be then mediated
            BW = []
            Cent_freq = []
            Max = []
            Min = []

            for i in range(s_num):

                # X-axis
                # ------------------------------------------------------------------------------------------------------
                # Number of samples from the beginning of the experiment
                samples_number = fs * s_duration

                if i == 0:
                    samples_number = samples_number
                else:
                    # Add 1 s of samples
                    samples_number += 1 * fs

                # Create the frequency array in the range between the f_i and the f_f
                freq = np.arange(samples_number) * (f_f - f_i) / (samples_number - 1) + f_i
                # Frequency step between consecutive values (needed in Band width formula below)
                delta_f = freq[1] - freq[0]
                # ------------------------------------------------------------------------------------------------------

                # Y Axis
                # ------------------------------------------------------------------------------------------------------
                # Select the relevant samples
                Int = data[exit][start:stop]
                # Define the Offset of the signal
                offset = max(Int)
                # Normalization: define the effective shift from the offset
                Int_0 = offset - Int
                # ------------------------------------------------------------------------------------------------------

                # Band Calculation (mean values computed on the i bands)
                # ------------------------------------------------------------------------------------------------------
                # Sum of all the elements of the signal-array
                Sum_Int = np.sum(Int_0)
                # Square root of the elements of the signal-array
                Int_sq = np.square(Int_0, dtype=np.float64)
                # Sum of all the elements of the signal-array
                Sum_Int_sq = np.sum(Int_sq, dtype=np.float64)

                # Band Width formula
                BW.append(round(((np.square(Sum_Int, dtype=np.float64)) * delta_f) / Sum_Int_sq, 2))
                # Band Center
                Cent_freq.append(round(sum(Int_0 * freq) / Sum_Int, 2))
                # Max Value of the Signal
                Max.append(max(Int_0))
                # Min Value of the Signal
                Min.append(min(Int_0))
                # ------------------------------------------------------------------------------------------------------

                # Write on the file the information about all the bands
                # Open
                file_out = open(f"{output_path}/{band_file_name}.txt", "a")
                # Write
                file_out.write(
                    f"{channel_name} {exit} {BW[i]} {Cent_freq[i]} {Max[i]} {Min[i]}\n")
                # Close
                file_out.close()
                # ------------------------------------------------------------------------------------------------------

                # Binning operation
                # ------------------------------------------------------------------------------------------------------
                if binning:
                    axs[o].plot(fz.binning_func(data_array=freq, bin_length=binning_length),
                                fz.binning_func(data_array=Int_0 * (-1), bin_length=binning_length),
                                ".", markersize=0.5)
                # ------------------------------------------------------------------------------------------------------
                else:
                    # Plot of the Normalized Signal
                    axs[o].plot(freq, Int_0 * (-1), ".", markersize=0.5)

                # Update start and stop time for the new band
                # Start of the new band
                start = stop
                # End of the new band
                stop = stop + (s_duration + 1) * fs

            # Calculate mean values to write title and Axis Labels
            BW_mean = round(np.mean(BW), 2)
            Cent_freq_mean = round(np.mean(Cent_freq), 2)
            Max_mean = round(np.mean(Max), 2)
            Min_mean = round(np.mean(Min), 2)
            # Set title
            axs[o].set_title(f'{exit}\nBW={str(BW_mean)}\n'
                             f'Cent_f={str(Cent_freq_mean)}\n'
                             f'Max={Max_mean}\nMin={Min_mean}')
            # Set X Axis label
            axs[o].set_xlabel("Frequency [GHz]", size=13)
            # Set Y Axis label
            axs[o].set_ylabel("Signal Level [ADU]", size=13)

        # Set figure name
        figure_name = f"{output_path}{band_file_name}"
        if binning:
            figure_name = f"{figure_name}_binned"
        # Save the figure
        plt.savefig(f"{figure_name}.png")
        # Show the figure
        if show:
            plt.show()
        plt.close(fig)

        return

    def Plot_Output(self, type: str, begin: int, end: int, show=True):
        """
        Plot the 4 exits PWR or DEM of the Polarimeter\n
        Parameters:\n
        - **type** (``str``) of data *"DEM"* or *"PWR"*\n
        - **begin**, **end** (``int``): indexes of the data that have to be considered\n
        - **show** (``bool``): *True* -> show the plot and save the figure, *False* -> save the figure only
        """
        # Creating the figure
        fig = plt.figure(figsize=(20, 6))

        # Saving the beginning date
        begin_date = self.Date_Update(n_samples=begin, modify=False)
        # Title of the figure
        fig.suptitle(f'{self.name} Output {type} - Date: {begin_date}', fontsize=18)

        o = 0
        for exit in ["Q1", "Q2", "U1", "U2"]:
            o = o + 1
            # Create 4 subplots on one line
            ax = fig.add_subplot(1, 4, o)

            # Calculate Plot Statistics
            # mean
            m = round(np.mean(self.data[type][exit][begin:end]), 2)
            # std deviation
            std = round(np.std(self.data[type][exit][begin:end]), 2)

            # Max value
            max_val = round(max(self.data[type][exit][begin:end]), 4)
            # Min value
            min_val = round(min(self.data[type][exit][begin:end]), 4)

            # Plot of DEM/PWR Outputs
            ax.plot(self.times[begin:end], self.data[type][exit][begin:end], "*",  markersize=0.005, linestyle=" ")
            # Title
            ax.set_title(f"{exit}\n$Mean$={m} - $STD$={std}\n$Max$={max_val} - $Min$={min_val}", size=14)
            # X-Axis

            ax.set_xlabel("Time [s]", size=15)
            # Y-Axis
            ax.set_ylabel(f"Output {type} [ADU]", size=15)
        plt.tight_layout()

        # Create the path for the output dir
        path = f"{self.output_plot_dir}/OUTPUT/"
        Path(path).mkdir(parents=True, exist_ok=True)
        # Save the figure
        fig.savefig(f'{path}{self.name}_{type}.png', dpi=400)
        # Show the figure
        if show:
            plt.show()
        plt.close(fig)

    # ------------------------------------------------------------------------------------------------------------------
    # TIMESTAMPS JUMP ANALYSIS
    # ------------------------------------------------------------------------------------------------------------------

    def Jump_Plot(self, show=True):
        """
        Plot the Timestamps and the Delta-time between two consecutive Timestamps.\n
        Note: the Polarimeter must be Loaded but not Prepared hence DO NOT normalize the Timestamps!
        Parameters:\n
        - **show** (bool):\n
            *True* -> show the plot and save the figure\n
            *False* -> save the figure only
        """

        fig, axs = plt.subplots(nrows=1, ncols=2, constrained_layout=True, figsize=(13, 3))
        # Timestamps: dot-shape jumps expected
        axs[0].plot(np.arange(len(self.times)), self.times.value, '*')
        axs[0].set_title(f"{self.name} Timestamps")
        axs[0].set_xlabel("# Sample")
        axs[0].set_ylabel("Time [s]")

        # Delta t
        deltat = self.times.value[:-1] - self.times.value[1:]  # t_n - t_(n+1)
        # Plot Delta-time
        axs[1].plot(deltat, "*", color="forestgreen")
        axs[1].set_title(f"$\Delta$t {self.name}")
        axs[1].set_xlabel("# Sample")
        axs[1].set_ylabel("$\Delta$ t [s]")
        axs[1].set_ylim(-1.0, 1.0)

        path = f'{self.output_plot_dir}/{self.date_dir}/Timestamps_Jump_Analysis/'
        Path(path).mkdir(parents=True, exist_ok=True)
        fig.savefig(f'{path}{self.name}_Timestamps.png')
        if show:
            plt.show()
        plt.close(fig)

    def Pol_Sampling_Table(self, sam_tolerance: float) -> []:
        """
        Return a list to produce a CSV table that contains a description of jumps in Polarimeter Timestamps.
        This function store also a table in Markdown format in the member warnings of the Polarimeter (self.warnings)

        The current code produces a table with the following information:

        1. Name_Polarimeter
        2. Jump_Index
        3. Jump_Value [JHD]
        4. Jump_Value [s]
        5. Gregorian Date
        6. Julian Date

            Parameters:\n

        - **start_datetime** (``str``): start time that defines the polarimeter, format: "%Y-%m-%d %H:%M:%S".
        - **sam_tolerance** (``float``): the acceptance sampling tolerances of the scientific output
        """
        # [CSV] Initialize a result list
        csv_results = []

        logging.info("Looking for jumps...\n")
        # Find jumps into Timestamps array
        jumps = fz.find_jump(v=self.times, exp_med=0.01, tolerance=sam_tolerance)
        logging.info("Done.\n")

        # No Jumps detected
        if jumps["n"] == 0:
            sam_warn = ("\nThe sampling of the Scientific Output is good: "
                        "no jumps found in the Timestamps.\n")
            logging.info(sam_warn)
            # Saving the warning message
            self.warnings["sampling_warning"].append(sam_warn + "\n")

        # Jumps detected
        else:
            t_warn = f"In the dataset there are {jumps['n']} Time Jumps.\n"
            logging.info(t_warn + "\n\n")
            # Saving the warning message
            self.warnings["sampling_warning"].append(t_warn + "\n")

            # [MD] Preparing Table Heading
            md_tab_content = (f"\nTime Jumps Pol {self.name}\n"
                              f"| # Jump | Jump value [JHD] | Jump value [s] | Gregorian Date | Julian Date [JHD]|\n"
                              f"|:------:|:----------------:|:--------------:|:--------------:|:----------------:|\n")

            # [CSV] Preparing Table Heading
            csv_results.append([""])
            csv_results.append([f"Time Jumps Pol {self.name}"])
            csv_results.append([""])
            csv_results.append(["# Jump", "Jump value [JHD]", "Jump value [s]", "Gregorian Date", "Julian Date [JHD]"])

            # Initializing the jump number
            i = 1

            for idx, j_value, j_val_s in zip(jumps["idx"], jumps["value"], jumps["s_value"]):
                # Saving the Julian Date at which the Jump happened
                jump_instant = self.times.value[idx]
                # Saving the Gregorian Date at which the Jump happened
                greg_jump_instant = Time(jump_instant, format="mjd").to_datetime().strftime("%Y-%m-%d %H:%M:%S")

                # [MD] Storing Polarimeter jumps information
                md_tab_content += f"|{i}|{j_value}|{j_val_s}|{greg_jump_instant}|{jump_instant}|\n"

                # [CSV] Storing Polarimeter jumps information
                csv_results.append([f"{i}", f"{j_value}", f"{j_val_s}", f"{greg_jump_instant}", f"{jump_instant}"])

                # Increasing the jump number
                i += 1

            # Report: storing the table
            md_tab_content += "\n"
            self.warnings["sampling_warning"].append(md_tab_content)

        return csv_results

    # ------------------------------------------------------------------------------------------------------------------
    # SPIKE ANALYSIS
    # ------------------------------------------------------------------------------------------------------------------
    def Spike_Report(self, fft: bool, nperseg: int) -> {}:
        """
        Create a dictionary with the info of the spikes in Output and FFT of the Outputs.
        The dictionary has two keys "md" and "csv" - that contain a list and a str with the info to create the report.

        Look up for 'spikes' in the DEM and PWR output of the Polarimeter and in their FFT.\n
        Create a table in md and CSV language in which the spikes found are listed.
        - **fft** (``bool``): if true, the code looks for spikes in the fft.
        - **nperseg** (``int``): number of elements of the array on which the fft is calculated
        """
        # Initializing a bool to see if the caption of the table is already in the report
        cap = False

        # [MD] Initialize strings for the rows of the table
        rows = ""
        md_spike_tab = ""
        # [CSV] Initialize a result list
        csv_spike_tab = []

        # Initialize list for x_data
        x_data = []

        for type in self.data.keys():
            for exit in self.data[type].keys():

                # Compute FFT Measures using welch method
                if fft:
                    x_data, y_data = fz.fourier_transformed(times=self.times, values=self.data[type][exit],  # fs=100,
                                                            nperseg=min(len(self.data[type][exit]), nperseg))
                    x_data = [x for x in x_data if x < 25.]
                    y_data = y_data[:len(x_data)]
                    threshold = 3
                    n_chunk = 10
                    data_type = "FFT"
                    data_name = f"FFT {type}"

                # No FFT calculation: using outputs
                else:
                    y_data = self.data[type][exit]
                    threshold = 8
                    n_chunk = 10
                    data_type = type
                    data_name = type

                # Find and store spikes indexes
                spike_idxs = fz.find_spike(y_data, data_type=data_type, threshold=threshold, n_chunk=n_chunk)

                # No spikes detected
                if len(spike_idxs) == 0:
                    msg = f"\nNo spikes detected in {data_name} {exit} Output.\n"
                    logging.info(msg)

                # Spikes detected
                else:
                    # Look for spikes in the dataset
                    if not fft:
                        # Create the caption for the table of the spikes in Output
                        if not cap:
                            # [MD] Storing Table Heading
                            md_spike_tab += (
                                "\n| Spike Number | Data Type | Exit "
                                "| Gregorian Date | Julian Date [JHD]| Spike Value - Median [ADU]| MAD [ADU] |\n"
                                "|:------------:|:---------:|:----:"
                                "|:--------------:|:----------------:|:-------------------------:|:---------:|\n")

                            # [CSV] Storing Table Heading
                            csv_spike_tab.append([""])
                            csv_spike_tab.append(["Spike Number", "Data Type", "Exit",
                                                  "Gregorian Date", "Julian Date [JHD]",
                                                  "Spike Value - Median [ADU]", "MAD [ADU]"])
                            cap = True

                        for idx, item in enumerate(spike_idxs):
                            # Calculate the Gregorian date in which the spike happened
                            greg_date = fz.date_update(start_datetime=self.gdate[0],
                                                       n_samples=item, sampling_frequency=100, ms=True)
                            # Gregorian date string to a datetime object
                            greg_datetime = datetime.strptime(f"{greg_date}000",
                                                              "%Y-%m-%d %H:%M:%S.%f")
                            # Datetime object to a Julian date
                            julian_date = Time(greg_datetime).jd

                            # [MD] Fill the table with spikes information
                            rows += f"|{idx + 1}|{data_name}|{exit}|{greg_date}|{julian_date}" \
                                    f"|{np.round(y_data[item] - np.median(y_data), 6)}" \
                                    f"|{np.round(scs.median_abs_deviation(y_data), 6)}|\n"

                            # [CSV] Fill the table with spikes information
                            csv_spike_tab.append([f"{idx + 1}", f"{data_name}", f"{exit}",
                                                  f"{greg_date}", f"{julian_date}",
                                                  f"{np.round(y_data[item] - np.median(y_data), 6)}",
                                                  f"{np.round(scs.median_abs_deviation(y_data), 6)}"])

                    # Spikes in the FFT
                    else:
                        # Select the more relevant spikes
                        spike_idxs = fz.select_spike(spike_idx=spike_idxs, s=y_data, freq=x_data)

                        logging.warning(f"# Spikes found in {data_name} {exit}: {len(spike_idxs)}.\n\n")

                        # Create the caption for the table of the spikes in FFT
                        if not cap:
                            # [MD] Storing Table Heading
                            md_spike_tab += (
                                "\n| Spike Number | Data Type | Exit | Frequency Spike "
                                "|Spike Value - Median [ADU]| MAD [ADU] |\n"
                                "|:------------:|:---------:|:----:|:---------------:"
                                "|:------------------------:|:---------:|\n")

                            # [CSV] Storing Table Heading
                            csv_spike_tab.append([""])
                            csv_spike_tab.append(["Spike Number", "Data Type", "Exit", "Frequency Spike",
                                                  "Spike Value - Median [ADU]", "MAD [ADU]"])
                            cap = True

                        for idx, item in enumerate(spike_idxs):
                            # [MD] Storing FFT spikes information
                            rows += (f"|{idx + 1}|{data_name}|{exit}"
                                     f"|{np.round(x_data[item], 6)}"
                                     f"|{np.round(y_data[item] - np.median(y_data), 6)}"
                                     f"|{np.round(scs.median_abs_deviation(y_data), 6)}|\n")

                            # [CSV] Storing FFT spikes information
                            csv_spike_tab.append([f"{idx + 1}", f"{data_name}", f"{exit}",
                                                  f"{np.round(x_data[item], 6)}",
                                                  f"{np.round(y_data[item] - np.median(y_data), 6)}",
                                                  f"{np.round(scs.median_abs_deviation(y_data), 6)}"])

            if cap:
                md_spike_tab += rows

        # Initialize a dictionary with the two tables: MD and CSV
        spike_tab = {"md": md_spike_tab, "csv": csv_spike_tab}
        return spike_tab

    def spike_CSV(self) -> []:
        """
            Look up for 'spikes' in the DEM and PWR output of the Polarimeter.\n
            Create list of str to be written in a CSV file in which the spikes found are listed.
        """
        # Initializing a bool to see if the caption of the table is already in the report
        cap = False
        # [CSV] Initialize a spike list
        spike_list = []
        rows = [[""]]
        for type in self.data.keys():
            for exit in self.data[type].keys():

                # Find and store spikes indexes
                spike_idxs = fz.find_spike(self.data[type][exit], data_type=type)

                # [CSV] Storing Table Heading
                if len(spike_idxs) != 0:
                    if not cap:
                        spike_list = [
                            [""],
                            ["Spike in dataset"],
                            [""],
                            ["Spike Number", "Data Type", "Exit", "Spike Time [JHD]", "Spike Value - Median [ADU]"]
                        ]
                        cap = True

                    # [CSV] Storing spikes information
                    for idx, item in enumerate(spike_idxs):
                        rows.append([f"{idx + 1}", f"{type}", f"{exit}", f"{self.times[item]}",
                                     f"{self.data[type][exit][item] - np.median(self.data[type][exit])}",
                                     f""])
        if cap:
            spike_list = spike_list + rows
        else:
            spike_list = [["No spikes detected in DEM and PWR Output.<br /><p></p>"]]

        return spike_list

    def Inversion_EO_Time(self, jumps_pos: list, threshold=3.):
        """
        Find the inversions between even and odd output during the sampling due to time jumps.\n
        It could be also used to find even-odd inversions given a generic vector of position defining the intervals.\n

            Parameters:\n
        - **jump_pos** (``list``): obtained with the function find_jump: it contains the indexes of the time jumps.\n
        """
        logging.basicConfig(level="INFO", format='%(message)s',
                            datefmt="[%X]", handlers=[RichHandler()])  # <3
        l = len(jumps_pos)
        # No jumps in the Timestamps
        if l == 0:
            msg = f"No jumps in the timeline: hence no inversions even-odd are due to time jumps.\n"
            logging.warning(msg)
            self.warnings["eo_warning"].append(msg)

        # Jumps in the Timestamps
        else:
            for type in self.data.keys():
                for idx, item in enumerate(jumps_pos):
                    if idx == 0:
                        a = 0
                    else:
                        a = jumps_pos[idx - 1]

                    b = item

                    if l > idx + 1:
                        c = jumps_pos[idx + 1]
                    else:
                        c = -1

                    for exit in self.data[type].keys():
                        logging.debug(f"{exit}) a: {a}, b: {b}, c: {c}")
                        # Calculate the Mean Absolute Deviation of even/odd Outputs
                        mad_even = scs.median_abs_deviation(self.data[type][exit][b:c - 1:2])
                        mad_odd = scs.median_abs_deviation(self.data[type][exit][b + 1:c:2])

                        # Calculate the Median Value of even/odd Outputs
                        m_even_1 = np.median(self.data[type][exit][a:b - 1:2])
                        m_even_2 = np.median(self.data[type][exit][b:c - 1:2])

                        m_odd_1 = np.median(self.data[type][exit][a + 1:b:2])
                        m_odd_2 = np.median(self.data[type][exit][b + 1:c:2])

                        # Evaluate the inversion between Even and Odd samples
                        if (
                                (m_even_1 > m_even_2 + threshold * mad_even and m_odd_1 < m_odd_2 - threshold * mad_odd)
                                or
                                (m_even_1 < m_even_2 - threshold * mad_even and m_odd_1 > m_odd_2 + threshold * mad_odd)
                        ):
                            # Store the inversion index
                            inversion_jdate = self.times[item]
                            inversion_date = Time(inversion_jdate, format="mjd").to_datetime().strftime(
                                "%Y-%m-%d %H:%M:%S")

                            msg = f"Inversion Even-Odd at {inversion_date} in {type} Output in channel {exit}.<br />"

                            self.warnings["eo_warning"].append(msg)
                            logging.warning(msg)
