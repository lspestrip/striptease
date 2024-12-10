# -*- encoding: utf-8 -*-

# This file contains the Class Thermal_Sensors
# Use this Class with the new version of the pipeline for functional verification of LSPE-STRIP (2024).
# August 15th 2023, Brescia (Italy) - April 15th 2024, Brescia (Italy)

# Libraries & Modules
import logging
import numpy as np
import scipy
import scipy.stats as scs

from astropy.time import Time
from datetime import datetime
from matplotlib import pyplot as plt
from pathlib import Path
from rich.logging import RichHandler
from scipy import signal
from striptease import DataStorage

# MyLibraries & MyModules
import f_strip as fz

# Use the module logging to produce nice messages on the shell
logging.basicConfig(level="INFO", format='%(message)s',
                    datefmt="[%X]", handlers=[RichHandler()])


########################################################################################################
# Class: Thermal_Sensors
########################################################################################################
class Thermal_Sensors:

    def __init__(self, path_file: str, start_datetime: str, end_datetime: str, status: int, output_plot_dir: str,
                 nperseg_thermal: int,
                 ):
        """
        Constructor

            Parameters:
                - **path_file** (``str``): location of the data file and hdf5 file index (without the name of the file)
                - **start_datetime** (``str``): start time
                - **end_datetime** (``str``): end time
                - **status** (``int``): status of the multiplexer of the TS to analyze: 0, 1 or 2 (for both 0 and 1).
                - **output_plot_dir** (``str``): output directory of the plots
                - **nperseg_thermal** (``int``): number of elements of thermal measures on which the fft is calculated.
                Then the average of all periodograms is computed to produce the spectrogram.
                Changing this parameter allow to reach lower frequencies in the FFT plot:
                in particular, the limInf of the x-axis is fs/nperseg.

        """
        # Member DataStorage: used to load and store thermal measures
        self.ds = DataStorage(path_file)

        # Julian Date MJD
        # Used by load_cryo to store the thermal measures
        self.date = [Time(start_datetime).mjd, Time(end_datetime).mjd]
        # Gregorian Date [in string format]
        self.gdate = [Time(start_datetime), Time(end_datetime)]
        # Directory where to save all plot for a given analysis
        self.date_dir = fz.dir_format(f"{self.gdate[0]}__{self.gdate[1]}")
        # Output directory of the plots
        self.output_plot_dir = output_plot_dir

        self.status = status
        # Dict containing the names of the TS divided in the two states: "0" and "1".
        # The TS in each state are divided in groups whose names suggest their positions on Strip or their functions.
        if self.status == 0:
            self.ts_names = {
                "TILES": ["TS-CX4-Module-G", "TS-CX6-Module-O", "TS-CX2-Module-V"],
                "FRAME": ["TS-CX10-Frame-120", "TS-DT6-Frame-South"],
                "POLAR": ["TS-CX12-Pol-W", "TS-CX14-Pol-Qy"],
                "100-200K": ["TS-CX16-Filter", "TS-DT3-Shield-Base"],  # , "TS-SP2-L-Support" # Excluded for now
                # "VERIFY": ["EX-CX18-SpareCx"],  # Excluded for now
                "COLD_HEAD": ["TS-SP1-SpareDT"]}
        elif self.status == 1:
            self.ts_names = {
                "TILES": ["TS-CX3-Module-B", "TS-CX7-Module-I", "TS-CX1-Module-R", "TS-CX5-Module-Y"],
                "FRAME": ["TS-CX8-Frame-0", "TS-CX9-Frame-60", "TS-CX11-Frame-North", "TS-CX15-IF-Frame-0"],
                "POLAR": ["TS-CX13-Pol-Qx"],
                "100-200K": ["TS-DT5-Shield-Side"],  # , "TS-CX17-Wheel-Center" # Excluded for now
                "VERIFY": ["EX-DT2-SpareDT"],
            }
        # The following TS was also excluded during the system level tests in March 2023.
        # Pay attention if it must be included for your purpose now!
        # TS-SP2-SpareCx

        # Thermal Measures
        # List of the Timestamps of every measure (the Timestamps are the same for every TS of a specific status)
        thermal_times = []
        # Dictionary for the raw/calibrated dataset
        raw = {}
        calibrated = {}
        thermal_data = {"raw": raw, "calibrated": calibrated}
        # Dictionary of all the measures
        self.ts = {"thermal_times": thermal_times, "thermal_data": thermal_data}

        # nperseg: number of elements on which the periodogram is calculated.
        self.nperseg_thermal = nperseg_thermal

        # --------------------------------------------------------------------------------------------------------------
        # Warnings
        # Which warnings are we expecting?
        time_warning = []
        corr_warning = []
        # spike_warning = []
        self.warnings = {"time_warning": time_warning,
                         "corr_warning": corr_warning,
                         # "spike_warning": spike_warning
                         }

    # ------------------------------------------------------------------------------------------------------------------
    # THERMIC METHODS
    # ------------------------------------------------------------------------------------------------------------------
    def Load_TS(self):
        """
        Load all Thermal Sensor's data taking the names from the list in the constructor.
        """
        # Use a for with the function "zip" to tell the function load_cryo below to store raw or calibrated data.
        for calib, bol in zip(["raw", "calibrated"], [True, False]):
            for group in self.ts_names.keys():
                for sensor_name in self.ts_names[group]:
                    # Store TS measures and Timestamps using load_cryo
                    self.ts["thermal_times"], self.ts["thermal_data"][calib][sensor_name] \
                        = self.ds.load_cryo(self.date, sensor_name, get_raw=bol)
                    # Conversion to list to better handle the data array
                    self.ts["thermal_data"][calib][sensor_name] = list(self.ts["thermal_data"][calib][sensor_name])

    def Clean_TS(self):
        """
        Clean all Thermal Sensor measures removing those whose acquisition presents Nan values
        """
        # Find TS with Nan values
        problematic_TS = []
        for ts_name, array in self.ts["thermal_data"]["calibrated"].items():
            if np.isnan(array).any():
                problematic_TS.append(ts_name)

        for ts_name in problematic_TS:
            # Remove the key of the dictionary: remove TS from the analysis
            del self.ts["thermal_data"]["calibrated"][ts_name]
            # Remove the TS name form the list
            for group in self.ts_names.keys():
                try:
                    self.ts_names[group].remove(ts_name)
                except ValueError:
                    pass

            # Print & store a warning message
            msg = f"\nNan Values Found: Thermal Sensors {ts_name} (status {self.status}) removed from the analysis.\n\n"
            logging.info(msg)
            self.warnings["time_warning"].append(msg)

    def Norm_TS(self) -> []:
        """
        Check if the Timestamps array and the CALIBRATED DATA array have the same length.
        Normalize all Thermal Sensor's Timestamps putting one every 20 seconds from the beginning of the dataset.
        Return a list of problematic TS
        """
        # Initialize a list to store all the TS with sampling problems
        problematic_ts = []
        # Initialize a boolean variable to True meaning there is no sampling problems
        good_sampling = True

        for group in self.ts_names.keys():
            for sensor_name in self.ts_names[group]:
                # Check the lengths of the arrays
                len_times = len(self.ts["thermal_times"])
                len_data = len(self.ts["thermal_data"]["calibrated"][sensor_name])
                # If Timestamps and Data don't have the same length
                if len_times != len_data:

                    # 1) A datum hasn't been stored yet but its timestamp had been already collected
                    # No need of data manipulations
                    if len_times == len_data + 1:
                        pass

                    # 2) A datum of the status of the multiplexer has been stored in the time interval given,
                    # but its timestamp had been collected before the start_datetime given,
                    # hence a warning is produced and stored
                    else:
                        good_sampling = False
                        # Print & store a warning message
                        msg = (f"The Thermal sensor: {sensor_name} has a sampling problem.\n"
                               f"The array of Timestamps has a wrong length. "
                               f"Length difference len_data - len_times = {len_data - len_times}.\n")
                        logging.error(msg)
                        self.warnings["time_warning"].append(msg)

                        # Storing the problematic TS
                        problematic_ts.append(sensor_name)

        # If there are sampling problems
        if not good_sampling:
            pass
        else:
            # Print & store a warning message
            msg = f"\nThe assignment of the Timestamps of the Thermal Sensors in the status {self.status} is good.\n\n"
            logging.info(msg)
            self.warnings["time_warning"].append(msg)

        # Set the starting point for the new Timestamps: 0s for status 0 and 10s for status 1
        if self.status == 0:
            start = 0.
        elif self.status == 1:
            start = 10.
        else:
            start = np.nan
            logging.error("Invalid status value. Please choose between the values 0 and 1 for a single analysis.")
            SystemExit(1)

        # Convert to seconds the timestamps
        self.ts["thermal_times"] = start + self.ts["thermal_times"].unix - self.ts["thermal_times"][0].unix
        # Conversion to list to better handle the data array
        self.ts["thermal_times"] = list(self.ts["thermal_times"])

        return problematic_ts

    def TS_Sampling_Table(self, sam_exp_med: float, sam_tolerance: float) -> {}:
        """
        Create a dictionary with the info of the Thermal Sensors sampling.
        The dictionary has two keys "md" and "csv" - each containing a list with the info to create the relative report
        The current code produces a table with the following information:
        1. TS name
        2. Number of sampling jumps
        3. Median jump
        4. Expected median jump
        5. The 5th percentile
        6. The 95th percentile.

            Parameters:\n
        - **sam_exp_med** (``dict``): contains the exp sampling delta between two consecutive Timestamps of the TS
        - **sam_tolerance** (``dict``): contains the acceptance sampling tolerances of the TS
        """

        # [MD] Initialize a result list to contain the md table
        md_results = []
        # [CSV] Initialize a result list to contain the csv table
        csv_results = []

        # Initialize a result dict for the reports
        sampling_results = {"md": md_results, "csv": csv_results}

        # Initialize a string to collect the names of the TS with problems
        problematic_TS = ""

        # Find jumps in the Timestamps
        jumps = fz.find_jump(self.ts["thermal_times"], exp_med=sam_exp_med, tolerance=sam_tolerance)

        # Check if there are jumps
        # No Jumps detected
        if jumps["n"] == 0:

            # [MD] Good Sampling
            sampling_results["md"].append([f"\nThe sampling of the Thermal Sensors in status {self.status} is good: "
                                           f"no jumps in the TS Timestamps.\n"])
            # [CSV] Good Sampling
            sampling_results["csv"].append([""])
            sampling_results["csv"].append([f"Thermal Sensors Sampling status {self.status}:",
                                            "GOOD", "No jumps in TS Timestamps"])
            sampling_results["csv"].append([""])

        # Jumps detected
        else:

            # [MD] Preparing Table Heading
            sampling_results["md"].append(
                "| Data Name | # Jumps | &Delta;t Median [s] | Exp &Delta;t Median [s] | Tolerance "
                "| 5th percentile | 95th percentile |\n"
                "|:---------:|:-------:|:-------------------:|:-----------------------:|:---------:"
                "|:--------------:|:---------------:|\n")

            # [CSV] Preparing Table Heading
            sampling_results["csv"].append(["Data Name", "# Jumps", "Delta t Median [s]", "Exp Delta t Median",
                                            "Tolerance", "5th percentile", "95th percentile"])
            sampling_results["csv"].append([""])

            # Collect all TS names into a str
            for group in self.ts_names.keys():
                for sensor_name in self.ts_names[group]:
                    problematic_TS += f"{sensor_name} "

            # [MD] Storing TS sampling information
            sampling_results["md"].append(
                f"|TS status {self.status}: {problematic_TS}"
                f"|{jumps['n']}|{jumps['median']}|{jumps['exp_med']}|{jumps['tolerance']}"
                f"|{jumps['5per']}|{jumps['95per']}|\n")

            # [CSV] Storing TS sampling information
            sampling_results["csv"].append([f"TS status {self.status}: {problematic_TS}", f"{jumps['n']}",
                                            f"{jumps['median']}", f"{jumps['exp_med']}", f"{jumps['tolerance']}",
                                            f"{jumps['5per']}", f"{jumps['95per']}"])
            sampling_results["csv"].append([""])

        return sampling_results

    def Analyse_TS(self) -> {}:
        """
        Analise all Thermal Sensors' output: calculate the mean the std deviation for both raw and calibrated samples.
        """
        # Dictionary for raw and calibrated mean
        raw_m = {}
        cal_m = {}
        # Dictionary for raw and calibrated std dev
        raw_std = {}
        cal_std = {}
        # Dictionary for raw and calibrated nan percentage
        raw_nan = {}
        cal_nan = {}
        # Dictionary for raw and calibrated max
        raw_max = {}
        cal_max = {}
        # Dictionary for raw and calibrated min
        raw_min = {}
        cal_min = {}

        results = {
            "raw": {"max": raw_max, "min": raw_min, "mean": raw_m, "dev_std": raw_std, "nan_percent": raw_nan},
            "calibrated": {"max": cal_max, "min": cal_min, "mean": cal_m, "dev_std": cal_std, "nan_percent": cal_nan}
        }

        for calib in ["raw", "calibrated"]:
            for group in self.ts_names.keys():
                for sensor_name in self.ts_names[group]:
                    # Initialize the Nan percentage to zero
                    results[calib]["nan_percent"][sensor_name] = 0.

                    # Collect the TS data in the variable data to better handle them
                    data = self.ts["thermal_data"][calib][sensor_name]
                    # Calculate the mean of the TS data
                    m = np.mean(data)

                    # If the mean is Nan, at least one of the measures is Nan
                    if np.isnan(m):
                        # If there is no TS data, the Nan percentage is 100%
                        if len(data) == 0:
                            logging.warning(f"No measures found for {sensor_name}.")
                            results[calib]["nan_percent"][sensor_name] = 100.
                        # Otherwise, compute the Nan percentage
                        else:
                            # Find the number of nan measures in data
                            n_nan = len([t for t in np.isnan(data) if t == True])
                            results[calib]["nan_percent"][sensor_name] = round((n_nan / len(data)), 4) * 100.

                        # If the Nan percentage is smaller than 5%, the dataset is valid
                        if results[calib]["nan_percent"][sensor_name] < 5:
                            # The Nan values are found and removed
                            data = np.delete(data, np.argwhere(np.isnan(data)))
                            # The mean is calculated again
                            m = np.mean(data)

                    # Check if the std dev is zero
                    if np.std(data) == 0:
                        msg = f"Std Dev for {sensor_name} is 0 "
                        # Check if it is due to the fact that there is only one datum
                        if len(self.ts["thermal_data"][calib][sensor_name]) == 1:
                            logging.warning(msg + "because there is only one measure in the dataset.")
                        else:
                            logging.warning(msg)

                    # If possible, collect the other variables of interests: max, min, mean and std deviation
                    try:
                        results[calib]["max"][sensor_name] = max(data)
                    except ValueError:
                        results[calib]["max"][sensor_name] = -np.inf
                        logging.error("No measure found: impossible to find the max of the dataset.")

                    try:
                        results[calib]["min"][sensor_name] = min(data)
                    except ValueError:
                        results[calib]["min"][sensor_name] = np.inf
                        logging.error("No measure found: impossible to find the min of the dataset.")

                    results[calib]["mean"][sensor_name] = m
                    results[calib]["dev_std"][sensor_name] = np.std(data)

        return results

    def Thermal_table(self, results) -> {}:
        """
        Create a dictionary containing a string and a list to produce a table of thermal results.
        The string contains the code for Markdown reports, the list is used for CSV reports.
        In the table there are the following info:
        1. Sensor name
        2. Status of acquisition (0 or 1)
        3. Group of the sensor
        4. Max value measured
        5. Min value measured
        6. Mean value
        7. Standard deviation
        8. NaN percentage
        for both RAW and calibrated (CAL) Temperatures.
        """
        # [MD] Initialize a result string to contain the md table
        md_table = " "
        # [CSV] Initialize a result list to contain the csv table
        csv_table = []

        for calib in ['raw', 'calibrated']:

            # [MD] Heading of the table
            md_table += (f"\n\n"
                         f"{calib} data"
                         f"\n\n"
                         "| TS Name | Status | Group | Max value [K] | Min value [K] | Mean [K] | Std_Dev [K] | NaN % |"
                         "\n"
                         "|:-------:|:------:|:-----:|:-------------:|:-------------:|:--------:|:-----------:|:-----:|"
                         "\n"
                         )

            # [CSV] Heading of the table
            csv_table.append([""])
            csv_table.append([f"{calib} data"])
            csv_table.append([""])
            csv_table.append(["TS Name", "Status", "Group",
                              "Max value [K]", "Min value [K]", "Mean [K]", "Std_Dev [K]", "NaN %"])
            csv_table.append([""])

            for group in self.ts_names.keys():
                for sensor_name in self.ts_names[group]:
                    # [MD] Filling the table with values
                    md_table += (f"|{sensor_name}|{self.status}|{group}|"
                                 f"{round(results[calib]['max'][sensor_name], 4)}|"
                                 f"{round(results[calib]['min'][sensor_name], 4)}|"
                                 f"{round(results[calib]['mean'][sensor_name], 4)}|"
                                 f"{round(results[calib]['dev_std'][sensor_name], 4)}|"
                                 f"{round(results[calib]['nan_percent'][sensor_name], 4)}"
                                 f"\n")

                    # [CSV] Filling the table with values
                    csv_table.append([f"{sensor_name}", f"{self.status}", f"{group}",
                                      f"{round(results[calib]['max'][sensor_name], 4)}",
                                      f"{round(results[calib]['min'][sensor_name], 4)}",
                                      f"{round(results[calib]['mean'][sensor_name], 4)}",
                                      f"{round(results[calib]['dev_std'][sensor_name], 4)}",
                                      f"{round(results[calib]['nan_percent'][sensor_name], 4)}"])

        # Initialize a dictionary with the two tables: MD and CSV
        table = {"md": md_table, "csv": csv_table}
        return table

    def Plot_TS(self, show=False):
        """
        Plot all the calibrated acquisitions of Thermal Sensors.\n

            Parameter:\n
            - **show** (``bool``): *True* -> show the plot and save the figure, *False* -> save the figure only
        """

        col = ["cornflowerblue", "indianred", "limegreen", "gold"]

        # Prepare the shape of the fig: in each row there is a subplot with the data of the TS of a same group.
        n_rows = len(self.ts_names.keys())
        fig, axs = plt.subplots(nrows=n_rows, ncols=1, constrained_layout=True, figsize=(13, 15))

        # Set the title of the figure
        fig.suptitle(f'Plot Thermal Sensors status {self.status} - Date: {self.gdate[0]}', fontsize=10)

        # Plot the dataset
        for i, group in enumerate(self.ts_names.keys()):
            for j, sensor_name in enumerate(self.ts_names[group]):
                # Make sure that the time array and the data array have the same length
                values = fz.same_length(self.ts["thermal_times"], self.ts["thermal_data"]["calibrated"][sensor_name])
                # Plot the TS data vs time
                axs[i].scatter(values[0], values[1], marker=".", color=col[j], label=sensor_name)

                # Subplots properties
                # Title
                axs[i].set_title(f"TS GROUP {group} - Status {self.status}")
                # XY-axis
                axs[i].set_xlabel("Time [s]")
                axs[i].set_ylabel("Temperature [K]")
                # Subplot Legend
                axs[i].legend(prop={'size': 9}, loc=7)

        # Procedure to save the png of the plot in the correct dir
        path = f"{self.output_plot_dir}/Thermal_Output/"
        Path(path).mkdir(parents=True, exist_ok=True)
        fig.savefig(f'{path}Thermal_status_{self.status}.png')

        # If show is True the plot is visible on video
        if show:
            plt.show()
        plt.close(fig)

    def Plot_FFT_TS(self, all_in: bool, show=False):
        """
        Plot the FFT of the calibrated acquisitions of Thermal Sensors of the polarimeter.\n
            Parameters:\n
         - **show** (``bool``): *True* -> show the plot and save the figure, *False* -> save the figure only
         - **all_in** (``bool``): *True* -> show all the FFT of TS in one plot *False* -> different plots for the groups
        """

        # Prepare the shape of the fig: in each row there is a subplot with the data of the TS of a same group.
        n_rows = len(self.ts_names.keys())

        # All FFT of TS in one plot
        if all_in:
            fig, axs = plt.subplots(nrows=1, ncols=1, constrained_layout=True, figsize=(15, 10))
        else:
            fig, axs = plt.subplots(nrows=n_rows, ncols=1, constrained_layout=True, figsize=(15, 15))

        # Set the title of the figure
        fig.suptitle(f'Plot Thermal Sensors FFT status {self.status}- Date: {self.gdate[0]}', fontsize=15)

        # Note: the steps used by the periodogram are 1/20, the sampling frequency of the thermal measures.
        fs = 1 / 20.
        for i, group in enumerate(self.ts_names.keys()):
            for j, sensor_name in enumerate(self.ts_names[group]):
                # The COLD HEAD TS has a specific color: cyan
                if sensor_name == "TS-SP1-SpareDT":
                    color = "cyan"
                # The other TS will have another color: teal
                else:
                    color = "teal"
                # Calculate the periodogram
                # Choose the length of the data segment (between 10**4 and nperseg provided) on which calculate the fft
                # Changing this parameter allow to reach lower freq in the plot: the limInf of the x-axis is fs/nperseg.
                f, s = fz.fourier_transformed(times=self.ts["thermal_times"],
                                              values=self.ts["thermal_data"]["calibrated"][sensor_name],
                                              nperseg=min(int(fs * 10 ** 4), self.nperseg_thermal), f_max=25., f_min=0.)
                # All FFT of TS in one plot
                if all_in:
                    axs.plot(f, s,
                             linewidth=0.2, label=f"{sensor_name}", marker=".", markersize=6)
                    # XY-axis
                    axs.set_yscale("log")
                    axs.set_xscale("log")
                    axs.set_xlabel(f"$Frequency$ $[Hz]$", size=14)
                    axs.set_ylabel(f"PSD [K**2/Hz]", size=14)
                    # Legend
                    axs.legend(prop={'size': 9}, loc=3)
                else:
                    # Plot the periodogram (fft)
                    axs[i].plot(f, s,
                                linewidth=0.2, label=f"{sensor_name}", marker=".", markerfacecolor=color, markersize=4)

                    # Subplots properties
                    # Title
                    axs[i].set_title(f"FFT TS GROUP {group}")
                    # XY-axis
                    axs[i].set_yscale("log")
                    axs[i].set_xscale("log")
                    axs[i].set_xlabel(f"$Frequency$ $[Hz]$")
                    axs[i].set_ylabel(f"PSD [K**2/Hz]")
                    # Legend
                    axs[i].legend(prop={'size': 9}, loc=7)

        # Procedure to save the png of the plot in the correct dir
        path = f"{self.output_plot_dir}/Thermal_Output/FFT/"
        Path(path).mkdir(parents=True, exist_ok=True)

        # Set figure name
        fig_name = f"FFT_Thermal_status_{self.status}"
        # All FFT of TS in one plot
        if all_in:
            fig_name += "_All"
        # Save the figure
        fig.savefig(f'{path}{fig_name}.png', dpi=600)

        # If show is True the plot is visible on video
        if show:
            plt.show()
        plt.close(fig)

    # ------------------------------------------------------------------------------------------------------------------
    # SPIKE ANALYSIS
    # ------------------------------------------------------------------------------------------------------------------
    def Spike_Report(self, fft: bool, ts_sam_exp_med: int) -> {}:
        """
            Look up for 'spikes' in the TS output of Strip or in their FFT.\n
            Create a dictionary containing two tables in which the spikes found are listed:
             1. in MD language (basically a str)
             2. in CSV language (a list)
             Parameters:
            - **fft** (``bool``): if true, the code looks for spikes in the fft.
            - **nperseg** (``int``): number of elements of the array on which the fft is calculated
        """
        # Initializing a bool to see if the caption of the table is already in the report
        cap = False

        # [MD] Initialize a result string to contain the md table
        rows = ""
        md_spike_tab = ""
        # [CSV] Initialize a result list to contain the csv table
        csv_spike_tab = []

        # Initialize list for x_data
        x_data = []

        for name in self.ts["thermal_data"]["calibrated"].keys():

            # Compute FFT of TS Measures using welch method
            if fft:
                x_data, y_data = fz.fourier_transformed(times=self.ts["thermal_times"],
                                                        values=self.ts["thermal_data"]["calibrated"][name],
                                                        nperseg=min(len(self.ts["thermal_data"]["calibrated"][name]),
                                                                    self.nperseg_thermal),
                                                        f_max=25., f_min=0)
            # fs=ts_sam_exp_med / 60,

                # Limit the FFT values below 25Hz: we are interested in long periodic behaviour, hence small frequencies
                x_data = [x for x in x_data if x < 25.]
                # Limit the Power Spectral Density values to the frequencies that are < 25Hz
                y_data = y_data[:len(x_data)]
                # Set threshold values for spike research
                threshold = 3
                # Set the number of chunks in which the FFT dataset is divided to search the spikes
                n_chunk = 10
                data_type = "FFT"

            # No FFT calculation: using TS outputs
            else:
                y_data = self.ts["thermal_data"]["calibrated"][name]
                # Set threshold values for spike research
                threshold = 3
                # Set the number of chunks in which the TS dataset is divided to search the spikes
                n_chunk = 5
                data_type = "TS"

            logging.info(f"Parsing: {data_type} of {name}")
            # Find and store spikes indexes of the TS measures or of the FFT of TS measures
            spike_idxs = fz.find_spike(y_data, data_type=data_type,
                                       threshold=threshold, n_chunk=min(n_chunk, len(y_data)))
            # Spikes NOT detected
            if not spike_idxs:
                logging.info(f"No spikes in {name}: {data_type}.\n")
            # Spikes detected
            else:
                logging.info(f"Spikes found in {name}: {data_type}\n")

                # Spikes in the TS dataset
                if not fft:
                    # Create the caption for the table of the spikes in Output
                    if not cap:
                        # [MD] Storing Table Heading
                        md_spike_tab += (
                            "\n| Spike Number | Data Type | Sensor Name "
                            "| Gregorian Date | Julian Date [JHD]| Spike Value - Median [ADU]| MAD [ADU] |\n"
                            "|:------------:|:---------:|:----:"
                            "|:--------------:|:----------------:|:-------------------------:|:---------:|\n")

                        # [CSV] Storing Table Heading
                        csv_spike_tab.append([""])
                        csv_spike_tab.append(["Spike Number", "Data Type", "Sensor Name", "Gregorian Date",
                                              "Julian Date [JHD]", "Spike Value - Median [ADU]", "MAD [ADU]", ""])
                        cap = True

                    for idx, item in enumerate(spike_idxs):
                        # Calculate the Gregorian date in which the spike happened
                        greg_date = fz.date_update(start_datetime=self.gdate[0],
                                                   n_samples=item, sampling_frequency=ts_sam_exp_med / 60, ms=True)
                        # Convert the Gregorian date string to a datetime object
                        greg_datetime = datetime.strptime(f"{greg_date}000",
                                                          "%Y-%m-%d %H:%M:%S.%f")
                        # Convert the Datetime object to a Julian date
                        julian_date = Time(greg_datetime).jd

                        # [MD] Fill the table with TS spikes information
                        rows += f"|{idx + 1}|{data_type}|{name}" \
                                f"|{greg_date}|{julian_date}" \
                                f"|{np.round(y_data[item] - np.median(y_data), 6)}" \
                                f"|{np.round(scs.median_abs_deviation(y_data), 6)}|\n"

                        # [CSV] Fill the table with TS spikes information
                        csv_spike_tab.append([f"{idx + 1}", f"{data_type}", f"{name}",
                                              f"{greg_date}", f"{julian_date}",
                                              f"{np.round(y_data[item] - np.median(y_data), 6)}",
                                              f"{np.round(scs.median_abs_deviation(y_data), 6)}"])

                # Spikes in the FFT of TS
                else:
                    # Select the more relevant spikes
                    spike_idxs = fz.select_spike(spike_idx=spike_idxs, s=y_data, freq=x_data)

                    # Create the heading for the table of the spikes in TS FFT
                    # [MD] Heading of the table
                    md_spike_tab += (
                        "\n| Spike Number | Data Type | Sensor Name | Frequency Spike "
                        "|Spike Value - Median [ADU]| MAD [ADU] |\n"
                        "|:------------:|:---------:|:----:|:---------------:"
                        "|:------------------------:|:---------:|\n")

                    # [CSV] Heading of the table
                    csv_spike_tab.append([""])
                    csv_spike_tab.append(["Spike Number", "Data Type", "Sensor Name",
                                          "Frequency Spike", "Spike Value - Median [ADU]", "MAD [ADU]"])
                    cap = True

                    for idx, item in enumerate(spike_idxs):
                        # [MD] Fill the table with the FFT values
                        rows += (f"|{idx + 1}|FFT TS|{name}"
                                 f"|{np.round(x_data[item], 6)}"
                                 f"|{np.round(y_data[item] - np.median(y_data), 6)}"
                                 f"|{np.round(scs.median_abs_deviation(y_data), 6)}|\n")

                        # [CSV] Fill the table with FFT values
                        csv_spike_tab.append([f"{idx + 1}", "FFT TS", f"{name}",
                                              f"{np.round(x_data[item], 6)}",
                                              f"{np.round(y_data[item] - np.median(y_data), 6)}",
                                              f"{np.round(scs.median_abs_deviation(y_data), 6)}"])

            if cap:
                md_spike_tab += rows

        # Initialize a dictionary with the two tables: MD and CSV
        spike_tab = {"md": md_spike_tab, "csv": csv_spike_tab}
        return spike_tab
