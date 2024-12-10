# -*- encoding: utf-8 -*-

# This file contains the main functions used in the bachelor thesis of Francesco Andreetto (2020)
# updated to be used on the new version of the pipeline for functional verification of LSPE-STRIP (2024)

# October 29th 2022, Brescia (Italy) - December 5th 2024, Bologna (Italy)

# Libraries & Modules
import h5py
import scipy.signal
import warnings

from astropy.time import Time, TimeDelta
from datetime import datetime
from matplotlib import pyplot as plt
from numba import njit
from pathlib import Path
from scipy.optimize import curve_fit
from striptease import DataFile, DataStorage
from typing import Dict, Any

import csv
import json
import logging
import numpy as np
import scipy.stats as scs
import scipy.ndimage as scn


def binning_func(data_array, bin_length: int):
    """
    Operates a binning of the data_array by doing a mean of a number of samples equal to bin_length\n
    Parameters:\n
    - **data_array** (``list``): array-like object
    - **bin_length** (``int``): number of elements on which the mean is calculated\n
    """
    # Initialize a new list
    new_data_array = []

    # Check the dimension of the bin_length
    if bin_length <= 1:
        logging.warning("If bin_length < 1 it's not a binning operation")
        return data_array
    if bin_length >= len(data_array):
        logging.warning("bin_length is too large for this array to bin.")
        return data_array

    # Operate the Binning
    else:
        chunk_n = int(len(data_array) / bin_length)
        for i in range(chunk_n):
            new_data_array.append(np.mean(data_array[i * bin_length:i * bin_length + bin_length]))
        return new_data_array


def csv_to_json(csv_file_path: str, json_file_path):
    """
    Convert a csv file into a json file.

        Parameters:\n
    - **csv_file_path** (``str``): path of the csv file that have to be converted
    - **json_file_path** (``str``): path of the json file converted
    """
    json_array = []

    # read csv file
    with open(csv_file_path, encoding='utf-8') as csv_file:
        # load csv file data using csv library's dictionary reader
        csvReader = csv.DictReader(csv_file)

        # convert each csv row into python dict
        for row in csvReader:
            # add this python dict to json array
            json_array.append(row)

    # Check if the Json Path exists, if not it is created
    # Note: 55 is the number of char of the name of the reports
    logging.info(json_file_path)
    json_dir = json_file_path[:-55]
    logging.info(json_dir)
    Path(json_dir).mkdir(parents=True, exist_ok=True)

    # convert python json_array to JSON String and write to file
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json_string = json.dumps(json_array, indent=4)
        json_file.write(json_string)


def data_plot(pol_name: str,
              dataset: dict,
              timestamps: list,
              start_datetime: str,
              begin: int, end: int,
              type: str,
              even: str, odd: str, all: str,
              demodulated: bool, rms: bool,
              fft: bool, noise_level: bool,
              window: int, smooth_len: int, nperseg: int,
              output_plot_dir: str, output_report_dir: str,
              show: bool):
    """
    Generic function that create a Plot of the dataset provided.\n
    Parameters:\n
    - **pol_name** (``str``): name of the polarimeter we want to analyze
    - **dataset** (``dict``): dictionary containing the dataset with the output of a polarimeter
    - **timestamps** (``list``): list containing the Timestamps of the output of a polarimeter
    - **start_datetime** (``str``): start time
    - **begin**, **end** (``int``): interval of dataset that has to be considered\n

    - **type** (``str``): defines the scientific output, *"DEM"* or *"PWR"*\n
    - **even**, **odd**, **all** (int): used to set the transparency of the dataset (0=transparent, 1=visible)\n

    - **demodulated** (``bool``): if true, demodulated data are computed, if false even-odd-all output are plotted
    - **rms** (``bool``) if true, the rms are computed

    - **fft** (``bool``) if true, the fft are computed
    - **noise_level** (``bool``) if true, 1/f slope and white noise level are plotted on FFT plots computed;

    - **window** (``int``): number of elements on which the RMS is calculated
    - **smooth_len** (``int``): number of elements on which the mobile mean is calculated
    - **nperseg** (``int``): number of elements of the array of scientific data on which the fft is calculated
    - **output_plot_dir** (`str`): Path from the pipeline dir to the dir that contains the plots of the analysis
    - **output_report_dir** (`str`): Path from the pipeline dir to the dir that contains the reports of the analysis
    - **show** (``bool``): *True* -> show the plot and save the figure, *False* -> save the figure only
    """
    # Initialize the plot directory
    path_dir = ""

    # Initialize the name of the plot
    name_plot = f"{pol_name} "

    # Initialize the marker size in the legend
    marker_scale = 2.
    # ------------------------------------------------------------------------------------------------------------------
    # Step 1: define the operations: FFT, RMS, OUTPUT

    # Calculate fft
    if fft:
        # Update the name of the plot
        name_plot += " FFT"
        # Update the name of the plot directory
        path_dir += "/FFT"
        if noise_level and demodulated:
            name_plot += "+Noise_Level"
    else:
        pass

    # Calculate rms
    if rms:
        # Update the name of the plot
        name_plot += " RMS"
        # Update the name of the plot directory
        path_dir += "/RMS"
    else:
        pass

    if not fft and not rms:
        # Update the name of the plot directory
        path_dir += "/SCIDATA" if demodulated else "/OUTPUT"

    # ------------------------------------------------------------------------------------------------------------------
    # Step 2: define type of data
    # Demodulated Scientific Data vs Scientific Output
    if type == "DEM":
        # Update the name of the plot
        name_plot += " DEMODULATED" if demodulated else f" {type} {EOA(even, odd, all)}"
        # Update the name of the plot directory
        path_dir += "/DEMODULATED" if demodulated else f"/{type}"
    elif type == "PWR":
        # Update the name of the plot
        name_plot += " TOTPOWER" if demodulated else f" {type} {EOA(even, odd, all)}"
        # Update the name of the plot directory
        path_dir += "/TOTPOWER" if demodulated else f"/{type}"
    else:
        logging.error("Wrong type! Choose between DEM or PWR!")
        raise SystemExit(1)

    # ------------------------------------------------------------------------------------------------------------------
    # Step 3: Creating the Plot

    # Updating the start datatime for the plot title
    begin_date = date_update(n_samples=begin, start_datetime=start_datetime, sampling_frequency=100)

    # Creating the figure with the subplots
    fig, axs = plt.subplots(nrows=2, ncols=4, constrained_layout=True, figsize=(20, 12))
    # Title of the figure
    fig.suptitle(f'POL {name_plot}\nDate: {begin_date}', fontsize=14)

    logging.info(f"Plot of POL {name_plot}")
    # The 4 plots are repeated on two rows (uniform Y-scale below)
    for row in range(2):
        col = 0  # type: int
        for exit in ["Q1", "Q2", "U1", "U2"]:

            # Plot Statistics
            # Mean
            m = ""
            # Std deviation
            std = ""
            # Max Value
            max_val = ""
            # Min Value
            min_val = ""

            # Setting the Y-scale uniform on the 2nd row
            if row == 1:
                # Avoid UserWarning on y-axis log-scale
                try:
                    # Set the y-axis of the current plot as the first of the raw
                    axs[row, col].sharey(axs[1, 0])
                except ValueError as e:
                    logging.warning(f"{e} "
                                    f"Negative data found in Spectral Analysis (FFT): impossible to use log scale.\n\n")
                    continue
                except Exception as e:
                    logging.warning(f"{e} "
                                    f"Negative data found in Spectral Analysis (FFT): impossible to use log scale.\n\n")
                    continue

            # ----------------------------------------------------------------------------------------------------------
            # Demodulation: Scientific Data
            if demodulated:
                # Avoid ValueError during Scientific Data Processing
                try:
                    # Creating a dict with the Scientific Data of an exit of a specific type and their new timestamps
                    sci_data = demodulation(dataset=dataset, timestamps=timestamps,
                                            type=type, exit=exit, begin=begin, end=end)

                    # --------------------------------------------------------------------------------------------------
                    # RMS Calculation
                    if rms:
                        # Calculate the RMS of the Scientific Data
                        rms_sd = RMS(sci_data["sci_data"], window=window, exit=exit, eoa=0, begin=begin, end=end)

                        # ----------------------------------------------------------------------------------------------
                        # Plot of FFT of the RMS of the SciData DEMODULATED/TOTPOWER
                        if fft:
                            # f, s = fourier_transformed(times, values, nperseg, f_max, f_min)
                            f, s = scipy.signal.welch(rms_sd, fs=50, nperseg=min(len(rms_sd), nperseg),
                                                      scaling="spectrum")
                            axs[row, col].plot(f[f < 25.], s[f < 25.],
                                               linewidth=0.2, marker=".", markersize=2, color="mediumvioletred",
                                               label=f"{name_plot[3:]}")
                        # ----------------------------------------------------------------------------------------------

                        # ----------------------------------------------------------------------------------------------
                        # Plot of RMS of the SciData DEMODULATED/TOTPOWER
                        else:
                            # Smoothing of the rms of the SciData. Smooth_len=1 -> No smoothing
                            rms_sd = mob_mean(rms_sd, smooth_len=smooth_len)

                            # Calculate Plot Statistics
                            # Mean
                            m = round(np.mean(rms_sd), 2)
                            # Std deviation
                            std = round(np.std(rms_sd), 2)
                            # Max value
                            max_val = round(max(rms_sd), 2)
                            # Min value
                            min_val = round(min(rms_sd), 2)

                            # Plot RMS
                            axs[row, col].plot(sci_data["times"][begin:len(rms_sd) + begin], rms_sd,
                                               linewidth=0.2, marker=".", markersize=2,
                                               color="mediumvioletred", label=f"{name_plot[3:]}")
                        # ----------------------------------------------------------------------------------------------
                    # --------------------------------------------------------------------------------------------------

                    # --------------------------------------------------------------------------------------------------
                    # Scientific Data Processing
                    else:
                        # Plot of the FFT of the SciData DEMODULATED/TOTPOWER ------------------------------------------
                        if fft:
                            f, s = fourier_transformed(times=sci_data["times"][begin:end],
                                                       values=sci_data["sci_data"][exit][begin:end],
                                                       nperseg=nperseg, f_max=25., f_min=0)

                            axs[row, col].plot(f, s,
                                               linewidth=0.2, marker=".", markersize=2, color="mediumpurple",
                                               label=f"{name_plot[3:]}")

                            # Computing Noise Level: WN + 1/f
                            if noise_level:
                                # Filter the fft to get the WN level
                                freq_fil, fft_fil = wn_filter_fft(f[50:], s[50:], mad_number=6.0)
                                # Create the WN array
                                wn = np.ones(len(f)) * np.median(fft_fil)
                                # Filtered the fft to get the 1/f noise curve
                                x_fil_data, y_fil_data = one_f_filter_fft(f, s)
                                # Get the fitted y values
                                y_fit, slope = get_y_fit_data(x_fil_data=x_fil_data, y_fil_data=y_fil_data)
                                # Get the knee frequency
                                knee_f = get_knee_freq(x=x_fil_data, y=y_fit, target_y=wn[0])

                                # Write info on the file only the 2nd time
                                if row == 1:
                                    # Define the name of the noise report file
                                    noise_report_name = dir_format(f"Noise_Report_{start_datetime}.txt")
                                    # Write the info about the current polarimeter
                                    with open(f"{output_report_dir}/{noise_report_name}", "a") as file:
                                        file.write(f"{pol_name}\t{name_plot[20:]}\t{exit}\t"
                                                   f"{np.round(wn[0], 2)}\t"
                                                   f"{np.round(slope, 2)}\t"
                                                   f"{np.round(knee_f, 2)}\n")

                                # Plotting the WN and 1/f
                                # 1/f Fitted
                                axs[row, col].plot(x_fil_data, y_fit, color="limegreen",
                                                   label=f"1/f fitted data. Slope: {np.round(slope, 2)}")
                                # WN level
                                axs[row, col].plot(f, wn,  color="orange",
                                                   label=f"WN level: {np.round(wn[0], 2)} ADU**2/Hz")
                                # Knee_freq
                                axs[row, col].plot(knee_f, wn[0], "*", color="black",
                                                   label=f"Knee Frequency = {np.round(knee_f, 2)}GHz")
                                # Set xy scale log
                                axs[row, col].set_xscale('log')
                                axs[row, col].set_yscale('log')

                        # Plot of the SciData DEMODULATED/TOTPOWER -----------------------------------------------------
                        elif not fft:
                            # Smoothing of the SciData  Smooth_len=1 -> No smoothing
                            y = mob_mean(sci_data["sci_data"][exit][begin:end], smooth_len=smooth_len)

                            # Calculate Plot Statistics
                            # Mean
                            m = f"= {round(np.mean(y), 2)}"
                            # Std deviation
                            std = f"= {round(np.std(y), 2)}"
                            # Max value
                            max_val = round(max(y), 2)
                            # Min value
                            min_val = round(min(y), 2)

                            # Plot SciData
                            axs[row, col].plot(sci_data["times"][begin:len(y) + begin], y,
                                               linewidth=0.2, marker=".", markersize=2,
                                               color="mediumpurple", label=f"{name_plot[3:]}")
                    # --------------------------------------------------------------------------------------------------

                except ValueError as e:
                    logging.warning(f"{e}. Impossible to process {name_plot}.\n\n")
                    pass
            # ----------------------------------------------------------------------------------------------------------

            # ----------------------------------------------------------------------------------------------------------
            # Output
            else:
                # If even, odd, all are equal to 0
                if not (even or odd or all):
                    # Do not plot anything
                    logging.error("No plot can be printed if even, odd, all values are all 0.")
                    raise SystemExit(1)

                # When at least one in even, odd, all is different from 0
                else:
                    # Avoid ValueError during Scientific Output Processing
                    try:

                        # ----------------------------------------------------------------------------------------------
                        # RMS Calculations
                        if rms:
                            rms_even = []
                            rms_odd = []
                            rms_all = []
                            # Calculate the RMS of the Scientific Output: Even, Odd, All
                            if even:
                                rms_even = RMS(dataset[type], window=window, exit=exit, eoa=2, begin=begin, end=end)
                            if odd:
                                rms_odd = RMS(dataset[type], window=window, exit=exit, eoa=1, begin=begin, end=end)
                            if all:
                                rms_all = RMS(dataset[type], window=window, exit=exit, eoa=0, begin=begin, end=end)

                            # ------------------------------------------------------------------------------------------
                            # Plot of FFT of the RMS of the Output DEM/PWR
                            if fft:
                                if even:
                                    f, s = scipy.signal.welch(rms_even, fs=50, nperseg=min(len(rms_even), nperseg),
                                                              scaling="spectrum")
                                    axs[row, col].plot(f[f < 25.], s[f < 25.], color="royalblue",
                                                       linewidth=0.2, marker=".", markersize=2,
                                                       alpha=even, label=f"Even samples")
                                if odd:
                                    f, s = scipy.signal.welch(rms_odd, fs=50, nperseg=min(len(rms_odd), nperseg),
                                                              scaling="spectrum")
                                    axs[row, col].plot(f[f < 25.], s[f < 25.], color="crimson",
                                                       linewidth=0.2, marker=".", markersize=2,
                                                       alpha=odd, label=f"Odd samples")
                                if all:
                                    f, s = scipy.signal.welch(rms_all, fs=100, nperseg=min(len(rms_all), nperseg),
                                                              scaling="spectrum")
                                    axs[row, col].plot(f[f < 25.], s[f < 25.], color="forestgreen",
                                                       linewidth=0.2, marker=".", markersize=2,
                                                       alpha=all, label="All samples")
                            # ------------------------------------------------------------------------------------------

                            # ------------------------------------------------------------------------------------------
                            # Plot of RMS of the Output DEM/PWR
                            else:
                                if even:
                                    axs[row, col].plot(timestamps[begin:end - 1:2][:-window - smooth_len + 1],
                                                       mob_mean(rms_even, smooth_len=smooth_len)[:-1],
                                                       color="royalblue", linewidth=0.2, marker=".", markersize=2,
                                                       alpha=even, label="Even Output")
                                    # Plot Statistics
                                    # Mean
                                    m += f"\nEven = {round(np.mean(rms_even), 2)}"
                                    # Std deviation
                                    std += f"\nEven = {round(np.std(rms_even), 2)}"

                                if odd:
                                    axs[row, col].plot(timestamps[begin + 1:end:2][:-window - smooth_len + 1],
                                                       mob_mean(rms_odd, smooth_len=smooth_len)[:-1],
                                                       color="crimson", linewidth=0.2, marker=".", markersize=2,
                                                       alpha=odd, label="Odd Output")
                                    # Plot Statistics
                                    # Mean
                                    m += f"\nOdd = {round(np.mean(rms_odd), 2)}"
                                    # Std deviation
                                    std += f"\nOdd = {round(np.std(rms_odd), 2)}"

                                if all != 0:
                                    axs[row, col].plot(timestamps[begin:end][:-window - smooth_len + 1],
                                                       mob_mean(rms_all, smooth_len=smooth_len)[:-1],
                                                       linewidth=0.2, marker=".", markersize=2,
                                                       color="forestgreen", alpha=all, label="All Output")
                                    # Plot Statistics
                                    # Mean
                                    m += f"\nAll = {round(np.mean(rms_all), 2)}"
                                    # Std deviation
                                    std += f"\nAll = {round(np.std(rms_all), 2)}"
                            # ------------------------------------------------------------------------------------------
                        # ----------------------------------------------------------------------------------------------

                        # ----------------------------------------------------------------------------------------------
                        # Scientific Output Processing
                        else:
                            # ------------------------------------------------------------------------------------------
                            # Plot of the FFT of the Output DEM/PWR
                            if fft:
                                if even:
                                    f, s = fourier_transformed(times=timestamps[begin:end - 1:2],
                                                               values=dataset[type][exit][begin:end - 1:2],
                                                               nperseg=nperseg, f_max=25., f_min=0)
                                    axs[row, col].plot(f, s,
                                                       color="royalblue", alpha=even,
                                                       linewidth=0.2, marker=".", markersize=2,
                                                       label="Even samples")
                                if odd:
                                    f, s = fourier_transformed(times=timestamps[begin + 1:end:2],
                                                               values=dataset[type][exit][begin + 1:end:2],
                                                               nperseg=nperseg, f_max=25., f_min=0)
                                    axs[row, col].plot(f, s,
                                                       color="crimson", alpha=odd,
                                                       linewidth=0.2, marker=".", markersize=2,
                                                       label="Odd samples")
                                if all:
                                    f, s = fourier_transformed(times=timestamps[begin:end],
                                                               values=dataset[type][exit][begin:end],
                                                               nperseg=nperseg, f_max=25., f_min=0)
                                    axs[row, col].plot(f, s,
                                                       color="forestgreen", alpha=all,
                                                       linewidth=0.2, marker=".", markersize=2,
                                                       label="All samples")

                            # ------------------------------------------------------------------------------------------

                            # ------------------------------------------------------------------------------------------
                            # Plot of the Output DEM/PWR
                            else:
                                if not rms:
                                    if even != 0:
                                        axs[row, col].plot(timestamps[begin:end - 1:2][:- smooth_len],
                                                           mob_mean(dataset[type][exit][begin:end - 1:2],
                                                                    smooth_len=smooth_len)[:-1],
                                                           color="royalblue", alpha=even,
                                                           marker="*", markersize=0.005, linestyle=" ",
                                                           label="Even Output")
                                        marker_scale = 1000.

                                        # Plot Statistics
                                        # Mean
                                        m += f"\nEven = {round(np.mean(dataset[type][exit][begin:end - 1:2]), 2)}"
                                        # Std deviation
                                        std += f"\nEven = {round(np.std(dataset[type][exit][begin:end - 1:2]), 2)}"

                                    if odd != 0:
                                        axs[row, col].plot(timestamps[begin + 1:end:2][:- smooth_len],
                                                           mob_mean(dataset[type][exit][begin + 1:end:2],
                                                                    smooth_len=smooth_len)[:-1],
                                                           color="crimson", alpha=odd,
                                                           marker="*", markersize=0.005, linestyle=" ",
                                                           label="Odd Output")
                                        marker_scale = 1000.

                                        # Plot Statistics
                                        # Mean
                                        m += f"\nOdd = {round(np.mean(dataset[type][exit][begin + 1:end:2]), 2)}"
                                        # Std deviation
                                        std += f"\nOdd = {round(np.std(dataset[type][exit][begin + 1:end:2]), 2)}"

                                    if all != 0:
                                        axs[row, col].plot(timestamps[begin:end][:- smooth_len],
                                                           mob_mean(dataset[type][exit][begin:end],
                                                                    smooth_len=smooth_len)[:-1],
                                                           color="forestgreen", alpha=all,
                                                           marker="*", markersize=0.005, linestyle=" ",
                                                           label="All Output")
                                        marker_scale = 1000.

                                        # Plot Statistics
                                        # Mean
                                        m += f"\nAll = {round(np.mean(dataset[type][exit][begin:end]), 2)}"
                                        # Std deviation
                                        std += f"\nAll = {round(np.std(dataset[type][exit][begin:end]), 2)}"
                            # ------------------------------------------------------------------------------------------
                        # ----------------------------------------------------------------------------------------------

                    except ValueError as e:
                        logging.warning(f"{e}. Impossible to process {name_plot}.\n\n")
                        pass
            # ----------------------------------------------------------------------------------------------------------

            # ----------------------------------------------------------------------------------------------------------
            # Subplots properties
            # ----------------------------------------------------------------------------------------------------------
            # Title subplot
            title = f'{exit}'
            if not fft:
                title += f"\n$Mean$:{m}\n$STD$:{std}"
                if demodulated:
                    title += f"\n$Min$={min_val}\n $Max$={max_val}"

            axs[row, col].set_title(title, size=12)

            # Treat UserWarning as errors to catch them
            warnings.simplefilter("ignore", UserWarning)

            # X-axis default label
            x_label = "Time [s]"

            # FFT Plots arrangements
            if fft:
                x_label = "Frequency [Hz]"

                try:
                    axs[row, col].set_xscale('log')
                except ValueError as e:
                    logging.warning(f"{e} "
                                    f"Negative data found in Spectral Analysis (FFT): impossible to use log scale.\n\n")
                    continue
                except Exception as e:
                    logging.warning(f"{e} "
                                    f"Negative data found in Spectral Analysis (FFT): impossible to use log scale.\n\n")
                    continue

            # X-axis label
            axs[row, col].set_xlabel(f"{x_label}", size=10)

            # Y-axis
            y_label = "Output [ADU]"
            if fft:
                y_label = "Power Spectral Density [ADU**2/Hz]"

                try:
                    axs[row, col].set_yscale('log')
                except ValueError as e:
                    logging.warning(f"{e} "
                                    f"Negative data found in Spectral Analysis (FFT): impossible to use log scale.\n\n")
                    continue
                except Exception as e:
                    logging.warning(f"{e} "
                                    f"Negative data found in Spectral Analysis (FFT): impossible to use log scale.\n\n")
                    continue

            else:
                if rms:
                    y_label = "RMS [ADU]"

            # Y-Axis label
            axs[row, col].set_ylabel(f"{y_label}", size=10)

            # Legend
            axs[row, col].legend(loc="lower left", markerscale=marker_scale, fontsize=10)

            # Skipping to the following column of the subplot grid
            col += 1

    # ------------------------------------------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------------------
    # Step 4: producing the png file in the correct dir

    # Creating the name of the png file: introducing _ in place of white spaces
    name_file = dir_format(name_plot)

    logging.debug(f"Title plot: {name_plot}, name file: {name_file}, name dir: {path_dir}")

    # Output dir path
    path = f'{output_plot_dir}/{path_dir}/'
    # Checking existence of the dir
    Path(path).mkdir(parents=True, exist_ok=True)
    try:
        # Save the png figure
        fig.savefig(f'{path}{name_file}.png')
    except ValueError as e:
        logging.warning(f"{e}. Impossible to save the pictures.\n\n")
        pass

    # If true, show the plot on video
    if show:
        plt.show()
    plt.close(fig)
    # ------------------------------------------------------------------------------------------------------------------
    return 1


def datetime_check(date_str: str) -> bool:
    """
    Check if the string is in datatime format "YYYY-MM-DD hh:mm:ss" or not.
    Parameters:\n
    - **date** (``str``): string with the datetime
    """
    date_format = "%Y-%m-%d %H:%M:%S"
    try:
        datetime.strptime(date_str, date_format)
        return True
    except ValueError:
        return False


def date_update(start_datetime: str, n_samples: int, sampling_frequency: int, ms=False) -> Time:
    """
    Calculates and returns the new Gregorian date in which the analysis begins, given a number of samples that
    must be skipped from the beginning of the dataset.
    Parameters:\n
    - **start_datetime** (``str``): start time of the dataset
    - **n_samples** (``int``): number of samples that must be skipped\n
    - **sampling_freq** (``int``): number of data collected per second
    - **ms** (``bool``): if True the new Gregorian date has also milliseconds
    """
    # Convert the str in a Time object: Julian Date MJD
    jdate = Time(start_datetime).mjd
    # A second expressed in days unit
    s = 1 / 86_400
    # Julian Date increased
    jdate += s * (n_samples / sampling_frequency)
    # New Gregorian Date
    if not ms:
        new_date = Time(jdate, format="mjd").to_datetime().strftime("%Y-%m-%d %H:%M:%S")
    else:
        new_date = Time(jdate, format="mjd").to_datetime().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    return new_date


@njit
def diff_cons(v):
    """
    Calculate consecutive difference between the elements of an array.\n
    Parameters:\n
    - **v** is an array-like object\n
    The difference between each couple of samples of even-odd index is computed.
    """
    n = (len(v) // 2) * 2
    diff = (v[0:n:2] - v[1:n + 1:2])
    return diff


def down_sampling(list1: [], list2: [], label1: str, label2: str) -> ():
    """
    Create a new list operating the down-sampling (using median values) on the longest of the two arrays.\n
    Parameters:\n
   - **list1**, **list2** (``list``): array-like objects
    - **label1**, **label2** (``str``): names of the dataset. Used for labels for future plots.
    Return:\n
    A tuple containing: the interpolated array, the long array and the two data labels.
    """
    # Define the lengths of the arrays
    l1 = len(list1)
    l2 = len(list2)

    # No down-sampling needed
    if l1 == l2:
        # Do nothing, return list1, list2, label1 and label2
        return list1, list2, label1, label2

    # Down-sampling procedure
    else:
        # Define the length of the down-sampled array
        len_v = max(l1, l2)

        # Points on which the median will be calculated
        points_med = int(l1 / l2) if l1 > l2 else int(l2 / l1)

        # Define the array that must be down-sampled
        long_v, short_v = (list1, list2) if len(list1) > len(list2) else (list2, list1)
        # Define the correct labels
        long_label, short_label = (label1, label2) if len(list1) > len(list2) else (label2, label1)

        # Down-sampling of the longest array
        down_sampled_data = []
        for i in range(0, len_v, points_med):
            group = long_v[i:i + points_med]
            down_sampled_data.append(np.median(group))

        # Avoid length mismatch
        down_sampled_data = down_sampled_data[:min(l1, l2)]

        return down_sampled_data, short_v, long_label, short_label


def demodulate_array(array: list, type: str) -> list:
    """
    Demodulation over an array\n
    Calculate the double demodulation of the dataset.
    Depending on the type provided, consecutive means or differences are computed.
    Parameters:\n
    - **array** (``list``): array-like dataset
    - **type** (``str``) of data *"DEM"* or *"PWR"*
    """
    data = []
    # Calculate consecutive mean of PWR Outputs -> Get TOTAL POWER Scientific Data
    if type == "PWR":
        data = mean_cons(np.array(array))
    # Calculate consecutive differences of DEM Outputs -> Get DEMODULATED Scientific Data
    if type == "DEM":
        data = diff_cons(np.array(array))

    return data


def double_dem(dataset: list, type: str):
    """
    Calculate the double demodulation of the dataset.
    - **dataset** (``list``): numpy array
    - **type** (``str``) of data *"DEM"* or *"PWR"*
    If PWR calculates consecutive means, if DEM calculates consecutive differences
    """
    if type == "PWR":
        dataset = mean_cons(dataset)
    # Calculate consecutive differences of DEM Outputs -> Get DEMODULATED Scientific Data
    elif type == "DEM":
        dataset = diff_cons(dataset)
    else:
        logging.error("No PWR or DEM detected")

    return dataset


def demodulation(dataset: dict, timestamps: list, type: str, exit: str, begin=0, end=-1) -> Dict[str, Any]:
    """
    Demodulation\n
    Calculate the double demodulation of the dataset.
    Depending on the type provided, consecutive means or differences are computed.\n
    Timestamps are chosen as mean of the two consecutive times of the DEM/PWR data\n
    Parameters:\n
    - **dataset** (``dict``): dictionary ({}) containing the dataset with the output of a polarimeter
    - **timestamps** (``list``): list ([]) containing the Timestamps of the output of a polarimeter
    - **exit** (``str``) *"Q1"*, *"Q2"*, *"U1"*, *"U2"*\n
    - **type** (``str``) of data *"DEM"* or *"PWR"*
    - **begin**, **end** (``int``): interval of dataset that has to be considered
    """
    # Calculate consecutive mean of the Timestamps
    times = mean_cons(timestamps)
    data = {}

    # Calculate consecutive mean of PWR Outputs -> Get TOTAL POWER Scientific Data
    if type == "PWR":
        data[exit] = mean_cons(dataset[type][exit][begin:end])
    # Calculate consecutive differences of DEM Outputs -> Get DEMODULATED Scientific Data
    if type == "DEM":
        data[exit] = diff_cons(dataset[type][exit][begin:end])

    sci_data = {"sci_data": data, "times": times}
    return sci_data


def delta_method(values: list):
    """
    Compute the White Noise level from a dataset (from Nicole Grillo's Bachelor Thesis 2023).\n
    - **values** (``list``): array-like objects containing the data from which compute the White Noise;
    Return:\n
    A floating point number representing the WN level
    """
    # Calculate consecutive differences
    delta_values = values[1:] - values[:-1]
    # Consider only even values
    delta_values_even = delta_values[::2]
    # Delta Method Formula: median of the abs value of the difference between median and values
    mean_abs_dev = np.median(np.abs(np.median(delta_values_even) - delta_values_even))
    # Correction due to the propagation of errors
    return mean_abs_dev / (0.67449 * np.sqrt(2))


def dir_format(old_string: str) -> str:
    """
    Take a string and return a new string changing white spaces into underscores, ":" into "-" and removing ".000"\n
    Parameters:\n
    - **old_string** (``str``)
    """
    new_string = old_string.replace(" ", "_")
    new_string = new_string.replace(".000", "")
    new_string = new_string.replace(":", "-")
    return new_string


def EOA(even: int, odd: int, all: int) -> str:
    """
    Parameters:\n
    - **even**, **odd**, **all** (``int``)
    If these variables are different from zero, this function returns a string with the corresponding letters:\n
    - "E" for even (``int``)\n
    - "O" for odd (``int``)\n
    - "A" for all (``int``)\n
    """
    eoa = ""
    if even != 0:
        eoa += "E"
    if odd != 0:
        eoa += "O"
    if all != 0:
        eoa += "A"
    return eoa


def eoa_values(eoa_str: str) -> []:
    """
    Return a list in which each element is a tuple of 3 values.
    Those values can be 0 or 1 depending on the letters (e, o, a) provided.
    Note: if a letter is present in the eoa_str, then that letter will assume both value 0 and 1. Only 0 otherwise.
    Parameters:\n
    - **eoa_str** (``str``): string of 0,1,2 or 3 letters from a combination of the letters e, o and a
    """
    # Initialize a dictionary with 0 values for e,o,a keys
    eoa_dict = {"E": [0], "O": [0], "A": [0]}
    eoa_list = [char for char in eoa_str]

    # If a letter appears also the value 1 is included in the dictionary
    for key in eoa_dict.keys():
        if key in eoa_list:
            eoa_dict[key].append(1)

    # Store the combinations of 0 and 1 depending on which letters were provided
    eoa_combinations = [(val1, val2, val3)
                        for val1 in eoa_dict["E"]
                        for val2 in eoa_dict["O"]
                        for val3 in eoa_dict["A"]]

    return eoa_combinations


def error_propagation_corr(cov, params: list, wn_level: float) -> float:
    """
    Compute the value of the propagation of the errors (from Nicole Grillo's Bachelor Thesis 2023).\n
    Parameters:\n
    - **cov** (``Any``):
    - **params** (``list``)
    - **wn_level** (``float``)
    Return:\n
    A floating point value corresponding to the propagated error.
    """
    one_alpha = 1 / params[1]
    sig_c = (params[0] / wn_level) ** one_alpha
    der_f = sig_c
    der_sigma = one_alpha * sig_c * params[2] / wn_level
    der_alpha = params[2] * sig_c * np.log(params[0] / wn_level) * one_alpha ** 2

    return np.sqrt(
        der_f ** 2 * cov[2, 2] + der_sigma ** 2 * cov[0, 0] + der_alpha ** 2 * cov[1, 1] +
        2 * der_f * der_sigma * cov[2, 0] + 2 * der_f * der_alpha * cov[2, 1] + 2 * der_alpha * der_sigma * cov[0, 1])


def find_jump(v, exp_med: float, tolerance: float) -> {}:
    """
    Find the 'jumps' in a given Time astropy object: the samples should be consequential with a fixed growth rate.
    Hence, their consecutive differences should have an expected median within a certain tolerance.\n
    Parameters:\n
    - **v** is a Time object from astropy => i.e. Polarimeter.times\n
    - **exp_med** (``float``) expected median (in seconds) of the TimeDelta between two consecutive values of v
    - **tolerance** (``float``) threshold number of seconds over which a TimeDelta is considered as an error\n
    Return:\n
    - **jumps** a dictionary containing five keys:
        - **n** (``int``) is the number of jumps found
        - **idx** (``int``) index of the jump in the array
        - **value** (``float``) is the value of the jump in JHD
        - **s_value** (``float``) is the value of the jump in seconds
        - **median_ok** (``bool``) True if there is no jump in the vector, False otherwise
    """
    # Create a TimeDelta object from the Time object given in input
    dt = (v[1:] - v[:-1]).sec  # type: TimeDelta

    # Calculate the median of the TimeDelta
    med_dt = np.median(dt)
    median_ok = True

    # If the tolerance is overcome -> a warning message is produced
    if np.abs(np.abs(med_dt) - np.abs(exp_med)) > tolerance:
        msg = f"Median is out of range: {med_dt}, expected {exp_med}."
        logging.warning(msg)
        median_ok = False

    # Discrepancy between dt and their median
    err_t = dt - med_dt

    # Initializing the lists with the information about time jumps
    idx = []
    value = []
    s_value = []
    n = 0

    # Initializing the dict with the information about time jumps
    jumps = {"n": n, "idx": idx, "value": value, "s_value": s_value,
             "median": med_dt, "exp_med": exp_med, "tolerance": tolerance, "median_ok": median_ok,
             "5per": np.percentile(dt, 5), "95per": np.percentile(dt, 95)}

    # Store the info
    for i, item in enumerate(err_t):
        # logging.debug(f"Discrepancy value: {item}")
        if np.abs(item) > tolerance:
            jumps["n"] += 1
            jumps["idx"].append(i)
            # Convert the value in days
            jumps["value"].append(dt[i] / 86400)
            jumps["s_value"].append(dt[i])

    return jumps


def find_spike(v, data_type: str, threshold=4.4, n_chunk=10) -> []:
    """
    Look up for 'spikes' in a given array.\n
    Calculate the median and the mad and uses those to discern spikes.\n
    Parameters:\n
    - **v** is an array-like object
    - **type** (str): if "DEM" look for spikes in two sub arrays (even and odd output) if "FFT" select only spike up
    - **threshold** (int): value used to discern what a spike is
    - **n_chunk** (int): n of blocks in which v is divided. On every block the median is computed to find spikes.
    """
    # Initialize a spike list to collect the indexes of the problematic samples
    spike_idx = []
    # Number of steps of the algorithm
    steps = 1
    # If DEM output look for spike on even and odd: two steps needed
    if data_type == "DEM":
        steps = 2

    # Start spike algorithm
    for i in range(steps):
        # logging.debug(f"Step: {i+1}/{steps}.")
        new_v = v[i:-1 - i:steps]
        # Length of the new vector
        l = len(new_v)
        # Calculate the length of a chunk used to divide the array
        len_chunk = l // n_chunk
        # Repeat the research of the spikes on every chunk of data
        for n_rip in range(n_chunk):
            # Creating a sub array dividing the new_v in n_chunk
            _v_ = new_v[n_rip * len_chunk:(n_rip + 1) * len_chunk - 1]
            # Calculate the Median
            med_v = scn.median(_v_)  # type:float
            # Calculate the Mean Absolute Deviation
            mad_v = scs.median_abs_deviation(_v_)

            for idx, item in enumerate(_v_):
                if item > med_v + threshold * mad_v or item < med_v - threshold * mad_v:
                    s_idx = n_rip * len_chunk + idx
                    if data_type == "DEM":
                        s_idx = s_idx * 2 + i
                    spike_idx.append(s_idx)

            # If the data_type is an FFT
            if data_type == "FFT":
                # Selecting local spikes UP: avoiding contour spikes
                spike_idx = [i for i in spike_idx if v[i] > v[i - 1] and v[i] > v[i + 1]]

    if len(spike_idx) > 0:
        logging.warning(f"Found Spike in {data_type}!\n")
    return spike_idx


def fourier_transformed(times: list, values: list, nperseg: int, f_max=25., f_min=0.):
    """
    Compute the Fast Fourier Transformed of an array of data (update from Nicole Grillo's Bachelor Thesis 2023).
    Parameters:\n
    - **times** (``list``): array-like objects containing the timestamps of the data;
    - **values** (``list``): array-like objects containing the data to transform;
    - **nperseg** (``int``): number of elements of the array of scientific data on which the fft is calculated
    Return:\n
    - **freq** (``list``): array-like object containing the frequencies (x-axis in FFT plots);
    - **fft** (``list``): array-like object containing the transformed data.
    """

    freq, fft = scipy.signal.welch(values, fs=1 / np.median(times[1:] - times[:-1]),
                                   nperseg=nperseg)

    mask = (freq > f_min) & (freq <= f_max)
    freq = freq[mask]
    fft = fft[mask]

    return freq, fft


def get_y_fit_data(x_fil_data: list, y_fil_data: list) -> (list, float):
    """
    Compute a logarithmic transformation of the data and calculate a regression line on those transformed data.
    Returns a list of the y fitted values and the slope of that regression line.\n
    Parameters:\n
    - **x_fil_data**, **y_fil_data** (`list`): lists of data to be converted and fitted.
    """
    # Logarithmic transformation
    log_x = np.log10(x_fil_data)
    log_y = np.log10(y_fil_data)

    # Compute the regression line on transformed data
    # Linear Fit on log-log
    coefficients = np.polyfit(log_x, log_y, 1)
    slope, intercept = coefficients

    # Compute the y values for the regression line
    log_y_fit = slope * log_x + intercept
    # Get back to the original scale
    y_fit = 10 ** log_y_fit

    return y_fit, slope


def get_knee_freq(x: list, y: list, target_y: float):
    """
    Extrapolate the x value corresponding to a given y value on a log-log plot.\n
    Parameters:\n
    - **x** (`list`): array of x-values (data points);
    - **y** (`list`): array of y-values (data points) that should correspond to x-values;
    - target_y (`float`): The y-value for which the x-value is to be extrapolated.
    """
    # Convert inputs to numpy arrays
    x = np.asarray(x)
    y = np.asarray(y)
    # Check that x and y have the same length
    if len(x) != len(y):
        raise ValueError("x and y arrays must have the same length!")

    # Convert x and y to log scale
    log_x = np.log10(x)
    log_y = np.log10(y)

    # Fit a linear model to the log-transformed data
    slope, intercept, r_value, p_value, std_err = scs.linregress(log_y, log_x)

    # Convert the target_y to log scale
    log_target_y = np.log10(target_y)

    # Calculate the x-value for the given y-value
    log_x_target = slope * log_target_y + intercept
    x_target = 10 ** log_x_target

    return x_target


def get_tags_from_file(file_path: str) -> []:
    """
    Get the tags form a given file.\n
    Parameters:\n
    - **file_path** (``str``): Path of the data file\n
    Return:\n
    - **tags** (``list``): List containing the tags contained in the file
    """
    tags = []
    f = h5py.File(f"{file_path}")

    for cur_tag in f["TAGS"]["tag_data"]:
        tags.append(cur_tag)

    return tags


def get_tags_from_iso(dir_path: str, start_time: str, end_time: str) -> []:
    """
    Get the tags in a given time interval contained in a file dir.\n
    Parameters:\n
    - **dir_path** (``str``): Path of the data dir\n
    - **start_time** (``float``): start time in iso format\n
    - **end_time** (``float``): end time in iso format\n
    Return:\n
    - **tags** (``list``): List containing the tags contained in the file
    """
    # Create Datastorage from the file.hdf5
    ds = DataStorage(dir_path)

    # Date conversion from iso to mjd
    start_mjd = Time(start_time, format="iso")
    start_mjd.format = "mjd"
    end_mjd = Time(end_time, format="iso")
    end_mjd.format = "mjd"

    # Get the tags
    tags = ds.get_tags(mjd_range=(start_mjd, end_mjd))

    return tags


def get_tag_times(file_path: str, tag_name: str) -> []:
    """
    Find the start-time and the end-time of a given tag.\n
    Parameters:\n
    - **file_path** (``str``): Path of the data file\n
    - **file_tag** (``str``): Name of the tag of a specific subset of data (i.e. of a test)\n
    Return:\n
    - **t_tag** (``list``): List containing 4 elements: start and end time in mjd and iso format
    """
    # Initializing tag times list
    t_tag = []
    # Read the file
    f = h5py.File(file_path, "r")

    # Collect the tags
    data_tags = f["TAGS"]["tag_data"]

    # Find the Star-time and the End-time
    for index, value in enumerate(data_tags["tag"]):
        if tag_name == value.decode('UTF-8'):
            # Set start-time of the tag and convert it into unix
            t_0j = data_tags["mjd_start"][index]
            # Append start-time of the tag to the list (JD)
            t_tag.append(t_0j)

            # Set end-time of the tag
            t_1j = data_tags["mjd_end"][index]
            # Append end-time of the tag to the list (JD)
            t_tag.append(t_1j)

            # Convert into time strings
            t_0 = Time(t_0j, format="mjd")
            t_0.format = "iso"
            # Append start-time of the tag to the list (str)
            t_tag.append(t_0.value[:-4])

            t_1 = Time(t_1j, format="mjd")
            t_1.format = "iso"
            # Append end-time of the tag to the list (str)
            t_tag.append(t_1.value[:-4])

            logging.info(
                f"Start Datetime = {t_tag[0]} MJD ({t_tag[2]})\nEnd Datetime = {t_tag[1]} MJD ({t_tag[3]})\n")

    return t_tag


def interpolation(list1: [], list2: [], time1: [], time2: [], label1: str, label2: str) -> ():
    """
    Create a new list operating the down-sampling (using median values) on the longest of the two arrays.
    Parameters:\n
    - **list1**, **list2** (``list``): array-like objects;
    - **time1**, **time2** (``list``): lists of timestamps: not necessary if the dataset have same length;
    - **label1**, **label2** (``str``): names of the dataset. Used for labels for future plots.
    Return:\n
    A tuple containing: the interpolated array, the long array and the two data labels.
    """
    # If the arrays have same lengths, no interpolation needed
    if len(list1) == len(list2):
        # Do nothing, return list1, list2, label1 and label2
        return list1, list2, label1, label2

    # Interpolation procedure
    else:
        # Timestamps must be provided
        if time1 == [] or time2 == []:
            logging.error("Different sampling frequency: provide timestamps array.")
            raise SystemExit(1)
        else:
            # Find the longest list (x) and the shortest to be interpolated
            x, short_list, label_x, label_y = (list1, list2, label1, label2) if len(list1) > len(list2) \
                else (list2, list1, label2, label1)
            x_t, short_t = (time1, time2) if x is list1 else (time2, time1)

            # Interpolation of the shortest list
            logging.info("Interpolation of the shortest list.")
            y = np.interp(x_t, short_t, short_list)

            return x, y, label_x, label_y


def letter_combo(in_str: str) -> []:
    """
    Return a list in which each element is a combination of E,O,A letters.
    Parameters:\n
    - **in_str** (``str``): generic string of max 3 letters
    """
    result = []

    for length in range(1, 4):
        for i in range(len(in_str) - length + 1):
            result.append(in_str[i:i + length])

    return result


@njit  # optimize calculations
def mean_cons(v):
    """
    Calculate consecutive means between the elements of an array.\n
    Parameters:\n
    - **v** is an array-like object\n
    The mean on each couple of samples of even-odd index is computed.
    """
    n = (len(v) // 2) * 2
    mean = (v[0:n:2] + v[1:n + 1:2]) / 2
    return mean


def merge_report(md_reports_path: str, total_report_path: str):
    """
    Merge together all the md report files into a single md report file.\n
    Parameters:\n
    - **md_reports_path** (``str``): path of the md files that have to be merged
    - **total_report_path** (``str``): path of the md file merged
    """
    # Ensure the output directory exists, create it if not
    output_directory = Path(total_report_path).parent
    output_directory.mkdir(parents=True, exist_ok=True)

    # List all files .md that start with a number in the directory
    files = [f for f in Path(md_reports_path).iterdir() if f.suffix == '.md' and f.name[0].isdigit()]

    # Sort files based on the number at the beginning of their names
    files_sorted = sorted(files, key=lambda x: (int(x.name.split('_')[0]), x.name))

    # Create or overwrite the destination file
    with open(total_report_path, 'w', encoding='utf-8') as outfile:
        for file_path in files_sorted:
            with file_path.open('r', encoding='utf-8') as infile:
                outfile.write(infile.read() + '\n\n')


@njit
def mob_mean(v, smooth_len: int):
    """
    Calculate a mobile mean on a number of elements given by smooth_len, used to smooth plots.\n
    Parameters:\n
    - **v** is an array-like object
    - **smooth_len** (int): number of elements on which the mobile mean is calculated
    """
    m = np.zeros(len(v) - smooth_len + 1)
    for i in np.arange(len(m)):
        # Compute the mean on a number smooth_len of elements, than move forward the window by 1 element in the array
        m[i] = np.mean(v[i:i + smooth_len])
    return m


def name_check(names: list) -> bool:
    """
    Check if the names of the polarimeters in the list are wrong: not the same as the polarimeters of Strip.\n
    Parameters:\n
    - **names** (``list``): list of the names of the polarimeters
    """
    for n in names:
        # Check if the letter corresponds to one of the tiles of Strip
        if n[0] in (["B", "G", "I", "O", "R", "V", "W", "Y"]):
            pass
        else:
            return False
        # Check if the number is correct
        if n[1] in (["0", "1", "2", "3", "4", "5", "6", "7"]):
            pass
        else:
            return False
        # Check the white space after every polarimeter
        try:
            if n[2] != "":
                return False
        except IndexError:
            pass

        # The only exception is W7
        if n == "W7":
            return False
    return True


def noise_characterisation(times: list, values: dict, nperseg: int,
                           output_dir: str, pol_name: str, data_type: str,
                           f_max=50., f_min=0) -> []:
    """
    Plot the Fast Fourier Transformed of a dataset and evaluate the White noise level and the 1/f noise.
    Use two different methods: delta-method and interpolation. (from Nicole Grillo's Bachelor Thesis 2023).\n
    Parameters:\n
    - **times** (``list``): array-like object ts containing the timestamps of the data;
    - **values** (``dict``): dict containing the data to transform;
    - **nperseg** (``int``): number of elements of the array of scientific data on which the fft is calculated
    - **output_dir** (``str``): name of the dir where the plots must be saved
    - **pol_name** (``str``): name of the polarimeter analyzed
    - **data_type** (``str``): kind of the data analyzed
    - **f_max**, **f_min** (``int``): max and min frequency that limits the FFT analysis
    Return:\n
    - **result** (``list``): list of synthetic results of the analysis on WN and 1/f noise.
    """

    # Initialize a list to collect results for the report
    result = []
    # Initialize a dict to collect polarimeter results
    var = {}
    # Initialize a figure for the plots
    fig, axs = plt.subplots(nrows=2, ncols=4, constrained_layout=True, figsize=(18, 10))
    fig.suptitle(f'{pol_name} FFT Plots', fontsize=15)

    for i, exit in enumerate(["Q1", "Q2", "U1", "U2"]):
        freq, fft = fourier_transformed(times, values=values[exit], nperseg=nperseg, f_max=f_max, f_min=f_min)

        # Fitting section
        # params: [sigma, alpha, f_knee] see below the function "noise_interpolation"
        # This list contains the optimal values for the parameters of the function noise_interpolation
        # so that the sum of the squared residuals of f(xdata, *popt) - ydata is minimized.
        params, cov = curve_fit(noise_interpolation, freq, fft, maxfev=10000)
        ps = noise_interpolation(freq, *params)
        idx = np.argsort(freq)

        # Evaluate White Noise with delta method
        wn_delta = delta_method(values[exit])

        var[f"err_sigma_interpol_{exit}"] = results_rounding(np.sqrt(cov[0][0]), np.sqrt(cov[0][0]))
        var[f"err_alpha_interpol_{exit}"] = results_rounding(np.sqrt(cov[1][1]), np.sqrt(cov[1][1]))
        var[f"err_fknee_interpol_{exit}"] = results_rounding(np.sqrt(cov[2][2]), np.sqrt(cov[2][2]))

        wn_level_pwr = wn_delta ** 2 * 2 / 50

        var[f"sigma_fknee_delta_{exit}"] = results_rounding(error_propagation_corr(cov, params, wn_level_pwr),
                                                            error_propagation_corr(cov, params, wn_level_pwr))
        var[f"{exit}_fknee_delta"] = results_rounding(params[2] / (wn_level_pwr / params[0]) ** (1 / params[1]),
                                                      var[f"sigma_fknee_delta_{exit}"])
        var[f"{exit}_fknee_interp"] = results_rounding(params[2], var[f"err_fknee_interpol_{exit}"])
        var[f"{exit}_wn"] = np.sqrt(params[0] * 50) / np.sqrt(2)
        var[f"sigma{exit}_f"] = results_rounding(params[0], var[f"err_sigma_interpol_{exit}"])
        var[f"alpha{exit}_f"] = results_rounding(params[1], var[f"err_alpha_interpol_{exit}"])
        var[f"{exit}_wn_delta"] = wn_delta

        # --------------------------------------------------------------------------------------------------------------
        # Plot Section
        # --------------------------------------------------------------------------------------------------------------

        # Interpolation plots
        axs[0][i].plot(freq[idx], fft[idx], color='royalblue', label='data')
        axs[0][i].plot(freq[idx], ps[idx], color='black', label='interp method')
        axs[0][i].set_yscale('log')
        axs[0][i].set_xscale('log')
        axs[0][i].set_title(f"{pol_name} - {exit}")
        axs[0][i].set(xlabel='Frequency [Hz]', ylabel='Power [ADU^2/Hz]')
        axs[0][i].legend(fontsize="x-small")

        # Delta Method plots
        # Create a 1D empty array
        white_noise_delta = np.empty(len(freq))
        # Fill the array with the white noise pwr level
        white_noise_delta.fill(wn_level_pwr)
        # Calculate the 1/f signal
        one_over_f = (params[0] * (params[2] / freq) ** params[1])

        # FFT Plot
        axs[1][i].plot(freq, fft, color='royalblue', label='data', marker="*", markersize=2)
        # One over f Signal
        axs[1][i].plot(freq, one_over_f, color='black', label='interp method')
        # WN Delta method
        axs[1][i].plot(freq, white_noise_delta, color='red', label='delta method')
        # Knee frequency
        axs[1][i].plot(var[f"{exit}_fknee_delta"], params[0] * (params[2] / var[f"{exit}_fknee_delta"]) **
                       params[1], marker="o", markersize=3.5, markerfacecolor="gold")
        axs[1][i].set_yscale('log')
        axs[1][i].set_xscale('log')
        axs[0][i].set_title(f"{pol_name} - {exit}")
        axs[1][i].set(xlabel='Frequency [Hz]', ylabel='Power [ADU^2/Hz]')
        axs[1][i].legend(fontsize="x-small")

        # var[f"{data_type}{exit}_plots_file_name"] = str(plot_file_name)
        result.append(var)

    # Saving figure with the plots of all the exits
    plot_file_name = f"{output_dir}/WN_{pol_name}_{data_type}.png"
    plt.savefig(plot_file_name, bbox_inches="tight")

    return result


def noise_interpolation(f: list, sigma: float, alpha: float, f_knee: float):
    """
    Compute the noise using an interpolation method (from Nicole Grillo's Bachelor Thesis 2023).\n
    Parameters:\n
    - **f** (``list``): array-like object containing frequency values;
    - **sigma** (``float``): std deviation;
    - **alpha** (``float``): exponent;
    - **f_knee** (``float``): knee frequency.
    """
    return sigma * ((f_knee / f) ** alpha + 1)


def one_f_filter_fft(x_data: list, y_data: list):
    """
    Returns two lists ``x_filtered_data`` and ``y_filtered_data`` containing the filtered data received in input.\n
    The filtering operation is iterative: it parses the input list `y`. The 1st value is skipped, the 2nd is stored.
    The following values are stored only if they are smaller than the previous one, rejected if they are larger.

    Parameters:\n
    - **x_data**, **y_data** (``list``): input data lists.
    """
    x_filtered_data = []
    y_filtered_data = []

    ref_value = y_data[1]
    # Appending the first value of the list
    y_filtered_data.append(ref_value)
    x_filtered_data.append(x_data[1])

    for idx, cur_value in enumerate(y_data[2:]):
        # If the current value is smaller than the previous one accept it, else reject it
        if cur_value <= ref_value:
            y_filtered_data.append(cur_value)
            x_filtered_data.append(x_data[idx + 2])

            ref_value = cur_value

    return x_filtered_data[:-1], y_filtered_data[:-1]


def pol_list(path_dataset: Path) -> list:
    """
    Create a list of the polarimeters present in the datafile\n
    Parameters:\n
    - **path_dataset** (Path comprehensive of the name of the dataset file)
    """
    d = DataFile(path_dataset)
    # Read the Datafile
    d.read_file_metadata()
    # Initialize a list to collect pol names
    pols = []
    for cur_pol in sorted(d.polarimeters):
        # Append pol names to the list
        pols.append(f"{cur_pol}")
    return pols


def results_rounding(value: list, error: list) -> list:
    """
    Rounding function that avoid nonsense errors associated to ADU measurements.\n
    Parameters:\n

     - **value** (``list``): array-like object whose elements must be rounded\n
     - **error** (``list``): array-like object used to round the value one\n
    Return:\n
    **result** (``list``): array-like object with rounded elements.
    """
    if np.isnan(error) or np.isinf(error) or np.isinf(value) or np.isnan(value):
        return 1

    if error > value:
        return 1

    result = round(value, int(np.ceil(-np.log10(error))) + 1)

    return result


def RMS(data: dict, window: int, exit: str, eoa: int, begin=0, end=-1) -> []:
    """
    Calculate the RMS of a vector using the rolling window\n
    Parameters:\n
    - **data** is a dictionary with four keys (exits) of a particular type *"DEM"* or *"PWR"*
    - **window**: number of elements on which the RMS is calculated
    - **exit** (``str``) *"Q1"*, *"Q2"*, *"U1"*, *"U2"*
    - **eoa** (``int``): flag used to calculate RMS for:\n
        - all samples (*eoa=0*), can be used for Demodulated and Total Power scientific data (50Hz)\n
        - odd samples (*eoa=1*)\n
        - even samples (*eoa=2*)\n
    - **begin**, **end** (``int``): interval of dataset that has to be considered
    """
    rms = []
    if eoa == 0:
        try:
            rms = np.std(rolling_window(data[exit][begin:end], window), axis=1)
        except ValueError as e:
            logging.warning(f"{e}. "
                            f"Impossible to compute RMS.\n\n")
    elif eoa == 1:
        try:
            rms = np.std(rolling_window(data[exit][begin + 1:end:2], window), axis=1)
        except ValueError as e:
            logging.warning(f"{e}. "
                            f"Impossible to compute RMS.\n\n")
    elif eoa == 2:
        try:
            rms = np.std(rolling_window(data[exit][begin:end - 1:2], window), axis=1)
        except ValueError as e:
            logging.warning(f"{e}. "
                            f"Impossible to compute RMS.\n\n")
    else:
        logging.error("Wrong EOA value: it must be 0,1 or 2.")
        raise SystemExit(1)
    return rms


@njit
def rolling_window(v, window: int):
    """
    Rolling Window Function\n
    Parameters:\n
    -  **v** is an array-like object
    - **window** (int)
    Accepts a vector and return a matrix with:\n
    - A number of element per row fixed by the parameter window
    - The first element of the row j is the j element of the vector
    """
    shape = v.shape[:-1] + (v.shape[-1] - window + 1, window)
    strides = v.strides + (v.strides[-1],)
    return np.lib.stride_tricks.as_strided(v, shape=shape, strides=strides)


def same_length(array1, array2) -> []:
    """
    Check if the two array are of the same length. If not, the longer becomes as long as the smaller
    Parameters:\n
    - **array1**, **array2** (``array``): data arrays.
    """
    l1 = len(array1)
    l2 = len(array2)
    array1 = array1[:min(l1, l2)]
    array2 = array2[:min(l1, l2)]
    return [array1, array2]


def select_spike(spike_idx: list, s: list, freq: list) -> []:
    """
    Select the most relevant spikes in an array of FFT data.\n
    Parameters:\n
    - **spike_idx** (``list``): is an array-like object containing the indexes of the spikes present in the s array
    - **s** (``list``): is an array-like object that contains spikes
    - **freq** (``list``): is an array-like object that contains the frequency corresponding to the s values
    """
    # Select only the most "significant" spikes
    idx_sel = []
    # Divide the array in sub-arrays on the base of the frequency
    for a in range(-16, 8):
        s_spike = [s[i] for i in spike_idx if (10 ** (a / 4) < freq[i] < 10 ** ((a + 1) / 4))]
        # Keep only the idx of the maxes
        idx_sel += [i for i in spike_idx if
                    (10 ** (a / 4) < freq[i] < 10 ** ((a + 1) / 4)) and s[i] == max(s_spike)]
    return idx_sel


def tab_cap_time(pol_name: str, file_name: str, output_dir: str) -> str:
    """
    Create a new file .csv and write the caption of a tabular\n
    Parameters:\n
    - **pol_name** (``str``): name of the polarimeter
    - **file_name** (``str``): name of the file to create and in which insert the caption\n
    - **output_dir** (``str``): name of the dir where the csv file must be saved
    This specific function creates a tabular that collects the jumps in the dataset (JT).
    """
    new_file_name = f"JT_{pol_name}_{file_name}.csv"
    cap = [["# Jump", "Jump value [JHD]", "Jump value [s]", "Gregorian Date", "JHD Date"]]

    path = f'../RESULTS/PIPELINE/{output_dir}/Time_Jump/'
    Path(path).mkdir(parents=True, exist_ok=True)
    # Open the file to append the heading
    with open(f"{path}/{new_file_name}", 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(cap)

    return cap


def wn_filter_fft(x_data: list, y_data: list, mad_number=1.0) -> (list, list):
    """
    Returns two lists ``x_filtered_data`` and ``y_filtered_data`` containing the filtered lists received in input.\n
    The filtering operation is done removing from the input lists the values that are away from the median more than
    the specified number of mad (Median Absolute Deviation): mad_number.

    Parameters:\n
    - **x_data**, **y_data** (``list``): input data lists;
    - **mad_number** (``float``): number of mad within which a sample is accepted and not removed form the filter.\n
    """
    x_filtered_data = []
    y_filtered_data = []

    ref_value = y_data[0]
    mad = scipy.stats.median_abs_deviation(y_data)

    for val_x, val_y in zip(x_data, y_data):
        if val_x >= 0.5:
            if ref_value + mad_number * mad >= val_y >= ref_value - mad_number * mad:
                x_filtered_data.append(val_x)
                y_filtered_data.append(val_y)

    return x_filtered_data, y_filtered_data
