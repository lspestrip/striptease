# -*- encoding: utf-8 -*-

# This file contains the main correlation functions used in the new version of the pipeline
# for functional verification of LSPE-STRIP (2024)

# September 19th 2023, Delft (Netherlands) - January 31st 2024, Bologna (Italy)

# Libraries & Modules
import logging
import numpy as np
import pandas as pd
import seaborn as sn

from matplotlib import pyplot as plt
from pathlib import Path

# MyLibraries & MyModules
import polarimeter as pol
import f_strip as fz


def correlation_plot(list1: [], list2: [], dict1: dict, dict2: dict, time1: [], time2: [],
                     data_name1: str, data_name2: str, measure_unit1: str, measure_unit2: str,
                     start_datetime: str, show=False, down_sampling=True,
                     corr_t=0.4, plot_dir='../RESULTS/PIPELINE') -> []:
    """
        Create a Correlation Plot of two dataset: two list, two dictionaries or one list and one dictionary.\n
        Return a dictionary of warnings that highlights which data are highly correlated.

            Parameters:\n
        - **list1**, **list2** (``list``): lists of n1 and n2 elements
        - **dict1**, **dict2** (``dict``): dictionaries with N1, N2 keys
        - **time1**, **time2** (``list``): lists of timestamps: not necessary if the dataset have same length.
        - **data_name1**, **data_name2** (``str``): names of the dataset. Used for titles, labels and to save the png.
        - **measure_unit1**, **measure_unit2** (``str``): measure units. Used for labels in the plots.
        - **start_datetime** (``str``): begin date of dataset. Used for the title of the figure and to save the png.
        - **end_datetime** (``str``): end date of dataset. Used for the title of the figure and to save the png.
        - **show** (``bool``):\n
            *True* -> show the plot and save the figure\n
            *False* -> save the figure only
        - **down_sampling** (``bool``):\n
            *True* -> down-sampling between arrays with mismatched length is computed\n
            *False* -> interpolation between arrays with mismatched length is computed\n
        - **corr_t** (``float``): LimSup for the corr value between two dataset: if overcome a warning is produced.
        - **plot_dir** (``str``): path where the plots are organized in directories and saved.
    """
    # [MD] Initialize a correlation list
    md_correlation = []
    # [CSV] Initialize a correlation list
    csv_correlation = []

    # Initialize a warning dict for the reports
    warnings = {"md": md_correlation, "csv": csv_correlation}

    # Initialize a bool that express the case of self correlations in the datasets
    self_correlation = False

    ####################################################################################################################
    # Data comprehension
    ####################################################################################################################
    # Type check
    # Data lists and timestamps arrays must be lists
    if not (all(isinstance(l, list) for l in (list1, list2, time1, time2))):
        logging.error("Wrong type: check if list1, list2, time1, time2 are list.")
    # dict1 and dict2 must be dictionaries
    if not (all(isinstance(d, dict) for d in (dict1, dict2))):
        logging.error("Wrong type: check if dict1 and dict2 are dictionaries.")

    ####################################################################################################################
    # Case 1 : two 1D lists
    # Single plot: scatter correlation between two list
    ####################################################################################################################
    if list1 != [] and list2 != [] and dict1 == {} and dict2 == {}:
        n_rows = 1
        n_col = 1
        fig_size = (4, 4)

    ####################################################################################################################
    # Case 2: one 1D list and one dictionary with N keys
    # Plot 1xN: scatter correlation between a list and the exits of a dictionary
    ####################################################################################################################
    elif list1 != [] and list2 == [] and dict1 != {} and dict2 == {}:
        # If the object are different, the sampling frequency may be different
        # hence the timestamps array must be provided to interpolate
        if time1 == [] or time2 == []:
            logging.error("Different sampling frequency: provide timestamps array.")
            raise SystemExit(1)
        else:
            n_rows = 1
            n_col = len(dict1.keys())
            fig_size = (4 * n_col, 4 * n_rows)

    ####################################################################################################################
    # Case 3: two dictionaries with N and M keys
    # Plot NxM: scatter correlation between each dictionary exit
    ####################################################################################################################
    elif list1 == [] and list2 == [] and dict1 != {} and dict2 != {}:
        n_rows = len(dict1.keys())
        n_col = len(dict2.keys())
        fig_size = (4 * n_col, 4 * n_rows)

    ####################################################################################################################
    # Case 4: Self Correlation - one dictionary with N keys, correlating to itself
    # Plot NxN: scatter correlation between each dictionary exit
    ####################################################################################################################
    elif list1 == [] and list2 == [] and dict1 != {} and dict2 == {}:
        # Self correlation: assign to the second dataset all the properties of the first one
        dict2 = dict1
        time2 = time1
        data_name2 = "Self_Correlation"
        measure_unit2 = measure_unit1
        self_correlation = True
        n_rows = len(dict1.keys())
        n_col = len(dict2.keys())
        fig_size = (4 * n_col, 4 * n_rows)

    ####################################################################################################################
    # Last Case: wrong dataset
    ####################################################################################################################
    else:
        msg = ("Wrong data. Please insert only two of the four dataset: list1, list2, dict1 or dict2. "
               "Please do not insert list2 if there is not an list1. "
               "Please do not insert dict2 if there is not a dict1.")
        logging.error(f"{msg}")
        raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    logging.debug(f"Number of col:{n_col}, of row:{n_rows}, fig size: {fig_size}")
    # Creating the name of the data: used for the fig title and to save the png
    data_name = f"{data_name1}-{data_name2}"
    # Creating the figure with the subplots
    fig, axs = plt.subplots(nrows=n_rows, ncols=n_col, constrained_layout=True, figsize=fig_size)
    # Set the title
    fig.suptitle(f'Correlation {data_name} \n Date: {start_datetime}', fontsize=10)

    ####################################################################################################################
    # list1 vs list2
    ####################################################################################################################
    if n_col == 1:

        # Check if the dataset is a TS and store the label for the plots
        label1 = f"{data_name1} Temperature [K]" if data_name1[0] in ("T", "E") else f"{data_name1} {measure_unit1}"
        label2 = f"{data_name2} Temperature [K]" if data_name2[0] in ("T", "E") else f"{data_name2} {measure_unit2}"

        # --------------------------------------------------------------------------------------------------------------
        # Arrays with different length must be interpolated or down-sampled

        # Down-sampling
        if down_sampling:
            x, y, label_x, label_y = fz.down_sampling(list1, list2, label1, label2)

        # Interpolation
        else:
            x, y, label_x, label_y = fz.interpolation(list1, list2, time1, time2, label1, label2)
        # --------------------------------------------------------------------------------------------------------------

        # --------------------------------------------------------------------------------------------------------------
        # Plot: list1 vs list2
        axs.plot(x, y, "*", color="firebrick", label="Corr Data")
        # XY-axis
        axs.set_xlabel(f"{label_x}")
        axs.set_ylabel(f"{label_y}")
        # Legend
        axs.legend(prop={'size': 9}, loc=4)

        # --------------------------------------------------------------------------------------------------------------
        # Calculate the correlation coefficient matrix
        correlation_matrix = np.corrcoef(x, y)
        # Extract the correlation coefficient between the two datasets from the matrix
        correlation_value = correlation_matrix[0, 1]

        logging.info("High correlations found will be listed below.\n\n")
        # Print a warning if the correlation value overcomes the threshold, then store it for the report
        if np.abs(correlation_value) > corr_t:
            warn_msg = (f"Found high correlation value: {round(correlation_value, 4)}"
                        f" between {data_name1} and {data_name2}.")
            logging.warning(warn_msg)

            # [MD] Collecting correlation values
            warnings["md"].append(f"|{data_name1}|{data_name2}|{round(correlation_value, 4)}|\n")

            # [CSV] Collecting correlation values
            warnings["csv"].append([""])
            warnings["csv"].append(["Data 1 Name", "Data 2 Name", "Correlation Value"])
            warnings["csv"].append([""])
            warnings["csv"].append([f"{data_name1}", f"{data_name2}", f"{round(correlation_value, 4)}"])
    # ------------------------------------------------------------------------------------------------------------------

    elif n_col > 1:
        ################################################################################################################
        # dict1 vs dict2
        ################################################################################################################
        if n_rows > 1:
            # length of the shortest sub-set in the dictionary.
            min_len = np.inf
            for r, r_exit in enumerate(dict1.keys()):
                for c, c_exit in enumerate(dict2.keys()):

                    ####################################################################################################
                    # Do not plot self correlation plots for now
                    if self_correlation and c_exit == r_exit:
                        pass
                    ####################################################################################################
                    else:
                        # Share x-axis and y-axis on the subplots
                        if r == 0:
                            axs[r, c].sharey(axs[1, 0])
                            axs[r, c].sharex(axs[1, 0])

                        # Assign the current sub-sets
                        sub_set1 = dict1[r_exit]
                        sub_set2 = dict2[c_exit]
                        # Assign the current labels
                        label1 = f"{data_name1} {r_exit} {measure_unit1}"
                        label2 = f"{data_name2} {c_exit} {measure_unit2}"

                        # ----------------------------------------------------------------------------------------------
                        # Sub-set of the dictionaries (lists) with different length must be interpolated or down-sampled

                        # Down-sampling
                        if down_sampling:
                            x, y, label_x, label_y = fz.down_sampling(sub_set1, sub_set2, label1, label2)

                        # Interpolation
                        else:
                            x, y, label_x, label_y = fz.interpolation(sub_set1, sub_set2, time1, time2, label1, label2)
                        # ----------------------------------------------------------------------------------------------
                        # Plot dict1 vs dict2 (each subset1 vs subset2)
                        axs[r, c].plot(x, y, "*", color="teal", label="Corr Data")

                        # Subplot title
                        axs[r, c].set_title(f'Corr {c_exit} - {r_exit}')
                        # XY-axis
                        axs[r, c].set_xlabel(f"{label_x}")
                        axs[r, c].set_ylabel(f"{label_y}")
                        # Legend
                        axs[r, c].legend(prop={'size': 9}, loc=4)

                        # Modify the original dictionary, not to have length mismatch in the dataframes
                        dict1[r_exit] = x
                        dict2[c_exit] = y
                        if len(x) < min_len:
                            min_len = len(x)
                            # logging.debug(f"min length: {min_len}")

            ############################################################################################################
            # Calculate Correlations of the dictionaries
            ############################################################################################################
            # Adjust dataset lengths
            for r_exit in dict1.keys():
                dict1[r_exit] = dict1[r_exit][:min_len - 1]
            for c_exit in dict2.keys():
                dict2[c_exit] = dict2[c_exit][:min_len - 1]

            # Convert dictionaries to DataFrames
            df1 = pd.DataFrame(dict1)
            df2 = pd.DataFrame(dict2)
            logging.info("\nGoing to produce the correlation matrix.")

            # Initialize an empty DataFrame for correlations
            correlation_matrix = pd.DataFrame(index=df1.columns, columns=df2.columns)
            logging.info("Done.\nHigh correlations found will be listed below.\n\n")

            ############################################################################################################
            # Calculate Self Correlations
            if self_correlation:
                keys = df1.columns
                for i in range(len(keys) - 1):
                    if np.abs(correlation_matrix.loc[keys[i], keys[i + 1]]) > corr_t:
                        warn_msg = (f"Found high correlation value between {keys[i]} and {keys[i + 1]}: "
                                    f"{round(correlation_matrix.loc[keys[i], keys[i + 1]], 4)}.")
                        logging.warning(warn_msg)

                        # [MD] Collecting the warning
                        warnings["md"].append(
                            f"|{data_name1} {keys[i]}|{data_name2} {keys[i + 1]}"
                            f"|{correlation_matrix.loc[keys[i], keys[i + 1]]}|\n")

                        # [CSV] Collecting the warning
                        warnings["csv"].append([""])
                        warnings["csv"].append(["Data 1 Name", "Data 2 Name", "Correlation Value"])
                        warnings["csv"].append([""])
                        warnings["csv"].append([f"{data_name1} {keys[i]}", f"{data_name2} {keys[i + 1]}",
                                                f"{correlation_matrix.loc[keys[i], keys[i + 1]]}"])

            ############################################################################################################
            # Calculate Normal Correlations
            else:
                for key1 in df1.columns:
                    for key2 in df2.columns:
                        correlation_matrix.loc[key1, key2] = df1[key1].corr(df2[key2])

                        # Print a warning if the correlation value overcomes the threshold, then store it
                        if np.abs(correlation_matrix.loc[key1, key2]) > corr_t:
                            warn_msg = (f"Found high correlation value between {key1} and {key2}: "
                                        f"{round(correlation_matrix.loc[key1, key2], 4)}.")
                            logging.warning(warn_msg)

                            # [MD] Collecting the warning
                            warnings["md"].append(
                                f"|{data_name1} {key1}|{data_name2} {key2}"
                                f"|{correlation_matrix.loc[key1, key2]}|\n")

                            # [CSV] Collecting the warning
                            warnings["csv"].append([f"{data_name1} {key1}", f"{data_name2} {key2}",
                                                    f"{correlation_matrix.loc[key1, key2]}"])

        ################################################################################################################
        # list1 vs dict1
        ################################################################################################################
        else:
            for c, exit in enumerate(dict1.keys()):
                # Assign the current sub-set of the dictionary
                sub_set1 = dict1[exit]
                # Assign the current labels
                label1 = f"{data_name1} {measure_unit1}"
                label2 = f"{data_name2} {measure_unit2}"

                # Arrays with different length must be interpolated

                # Down-sampling
                if down_sampling:
                    x, y, label_x, label_y = fz.down_sampling(list1, sub_set1, label1, label2)

                # Interpolation
                else:
                    x, y, label_x, label_y = fz.interpolation(list1, sub_set1, time1, time2, label1, label2)
                # ------------------------------------------------------------------------------------------------------

                # Plotting the data
                axs[c].plot(x, y, "*", color="lawngreen", label="Corr Data")

                # Subplot title
                axs[c].set_title(f'Corr {data_name1} -  {data_name2} {exit}')
                # XY-axis
                axs[c].set_xlabel(f"{label_x} ")
                axs[c].set_ylabel(f"{label_y}")
                # Legend
                axs[c].legend(prop={'size': 9}, loc=4)

                ########################################################################################################
                # Calculate the correlation coefficient matrix
                correlation_matrix = np.corrcoef(x, y)
                # Extract the correlation coefficient between the two datasets from the matrix
                correlation_value = correlation_matrix[0, 1]
                # Print a warning if the correlation value overcomes the threshold, then store it for the report
                if np.abs(correlation_value) > corr_t:
                    warn_msg = (f"Found high correlation value between {data_name1} and {data_name2} "
                                f"in {exit}: {round(correlation_value, 4)}.")
                    logging.warning(warn_msg)

                    # [MD] Collecting the warning
                    warnings["md"].append(f"|{data_name1}|{data_name2} {exit}|{round(correlation_value, 4)}|\n")

                    # [CSV] Collecting the warning
                    warnings["csv"].append([f"{data_name1}",
                                            f"{data_name2} {exit}",
                                            f"{round(correlation_value, 4)}"])

    # If n_col is not bigger than 1, warnings are produced
    else:
        return warnings

    # ------------------------------------------------------------------------------------------------------------------
    # Procedure to save the png of the plot in the correct dir
    path = f'{plot_dir}/Correlation_Plot/'
    # Check if the dir exists. If not, it will be created.
    Path(path).mkdir(parents=True, exist_ok=True)
    fig.savefig(f'{path}{data_name}_CorrPlot.png')
    # ------------------------------------------------------------------------------------------------------------------

    # If show is True the plot is visible on video
    if show:
        plt.show()
    plt.close("all")

    return warnings


def correlation_mat(dict1: {}, dict2: {}, data_name1: str, data_name2: str,
                    start_datetime: str, show=False, corr_t=0.4, plot_dir='../RESULTS/PIPELINE') -> []:
    """
        Plot a 4x4 Correlation Matrix of two generic dictionaries (also of one with itself).\n
        Return a list of warnings that highlight which data are highly correlated.

            Parameters:\n
        - **dict1**, **dict2** (dict): dataset
        - **data_name1**, **data_name2** (``str``): name of the dataset.
        Used for the title of the figure and to save the png.
        - **start_datetime** (``str``): begin date of dataset. Used for the title of the figure and to save the png.
        - **show** (``bool``):\n
            - *True* -> show the plot and save the figure\n
            - *False* -> save the figure only
        - **corr_t** (``int``): if it is overcome by one of the values of the matrix a warning is produced\n
        - **plot_dir** (``str``): path where the plots are organized in directories and saved.

    """
    # Creating the name of the data: used for the fig title and to save the png
    data_name = f"{data_name1}-{data_name2}"

    # Initialize a boolean variable for the heading of the table
    heading = False

    # [MD] Initialize a correlation list
    md_correlation = []
    # [CSV] Initialize a correlation list
    csv_correlation = []

    # Initialize a warning dict for the reports
    warnings = {"md": md_correlation, "csv": csv_correlation}

    # Initialize a boolean variable for the self correlation of a dataset
    self_correlation = False
    # If the second dictionary is not provided we are in a Self correlation case
    if dict2 == {}:
        self_correlation = True
        dict2 = dict1
    # Convert dictionaries to DataFrames
    df1 = pd.DataFrame(dict1)
    df2 = pd.DataFrame(dict2)

    # Initialize an empty DataFrame for correlations
    correlation_matrix = pd.DataFrame(index=df1.columns, columns=df2.columns)

    # ------------------------------------------------------------------------------------------------------------------
    # Calculate Correlations
    for key1 in df1.columns:
        for key2 in df2.columns:
            correlation_matrix.loc[key1, key2] = df1[key1].corr(df2[key2])

            if self_correlation:
                pass
            else:
                # Print a warning if the correlation value overcomes the threshold, then store it for the report
                if np.abs(correlation_matrix.loc[key1, key2]) > corr_t:
                    warn_msg = (f"Found high correlation value between {key1} and {key2}: "
                                f"{round(correlation_matrix.loc[key1, key2], 4)}.")
                    logging.warning(warn_msg)

                    # [MD] Collecting correlation values
                    warnings["md"].append(f"|{data_name1} {key1}|{data_name2} {key2}|"
                                          f"{correlation_matrix.loc[key1, key2]}|\n")
                    # [CSV] Storing the heading
                    if not heading:
                        warnings["csv"].append([""])
                        warnings["csv"].append(["Data 1 Name", "Data 2 Name", "Correlation Value"])
                        heading = True

                    # [CSV] Collecting correlation values
                    warnings["csv"].append([f"{data_name1} {key1}", f"{data_name2} {key2}",
                                            f"{correlation_matrix.loc[key1, key2]}"])

    # ------------------------------------------------------------------------------------------------------------------
    # Calculate Self Correlations
    if self_correlation:
        keys = df1.columns
        for i in range(len(keys) - 1):
            if np.abs(correlation_matrix.loc[keys[i], keys[i + 1]]) > corr_t:
                warn_msg = (f"Found high correlation value between {keys[i]} and {keys[i + 1]}: "
                            f"{round(correlation_matrix.loc[keys[i], keys[i + 1]], 4)}.")
                logging.warning(warn_msg)

                # [MD] Collecting correlation values
                warnings["md"].append(
                    f"|{data_name1} {keys[i]}|{data_name2} {keys[i + 1]}"
                    f"|{correlation_matrix.loc[keys[i], keys[i + 1]]}|\n")

                # [CSV] Storing the heading
                if not heading:
                    warnings["csv"].append([""])
                    warnings["csv"].append(["Data 1 Name", "Data 2 Name", "Correlation Value"])
                    heading = True

                # [CSV] Collecting correlation values
                warnings["csv"].append([f"{data_name1} {keys[i]}",
                                        f"{data_name2} {keys[i + 1]}",
                                        f"{correlation_matrix.loc[keys[i], keys[i + 1]]}"])

        # Put at Nan the values on the diagonal of the matrix (self correlations)
        for n in correlation_matrix.keys():
            correlation_matrix[n][n] = np.nan

    # Convert correlation matrix values to float
    correlation_matrix = correlation_matrix.astype(float)

    # Create a figure to plot the correlation matrices
    fig, axs = plt.subplots(nrows=1, ncols=2, constrained_layout=True, figsize=(20, 10))
    # Set the title of the figure
    fig.suptitle(f'Correlation Matrix {data_name} - Date: {start_datetime}', fontsize=12)

    pl_m1 = sn.heatmap(correlation_matrix, annot=True, ax=axs[0], cmap='coolwarm')
    pl_m1.set_title(f"Correlation {data_name}", fontsize=14)
    pl_m2 = sn.heatmap(correlation_matrix, annot=True, ax=axs[1], cmap='coolwarm', vmin=-0.4, vmax=0.4)
    pl_m2.set_title(f"Correlation {data_name} - Fixed Scale", fontsize=14)

    # Procedure to save the png of the plot in the correct dir
    path = f'{plot_dir}/Correlation_Matrix/'
    # Check if the dir exists. If not, it will be created.
    Path(path).mkdir(parents=True, exist_ok=True)
    fig.savefig(f'{path}{data_name}_CorrMat.png')

    # If show is True the plot is visible on video
    if show:
        plt.show()
    plt.close("all")

    return warnings


def cross_corr_mat(path_file: str, start_datetime: str, end_datetime: str, show=False, corr_t=0.4,
                   plot_dir='../RESULTS/PIPELINE') -> {}:
    """
        Plot 55x55 matrices of every data-kind DEM/PWR of every exit combination: Q1, Q2, U1, U2.
        Return a dict of warnings that highlight which data are highly correlated.

            Parameters:\n
        - **path_file** (``str``): location of the data file, it is indeed the location of the hdf5 file's index
        - **start_datetime** (``str``): begin date of dataset. Used for the title of the figure and to save the png.
        - **end_datetime** (``str``): end date of dataset. Used for the title of the figure and to save the png.
        - **show** (``bool``):\n
                - *True* -> show the plot and save the figure\n
                - *False* -> save the figure only
        - **corr_t** (``int``): if it is overcome by one of the values of the matrix a warning is produced\n
        - **plot_dir** (``str``): path where the plots are organized in directories and saved.
    """
    # [MD] Initializing a list to collect the warnings
    md_war = []
    # [CSV] Initializing a list to collect the warnings
    csv_war = [[""],
               [""],
               ["Cross Correlation between Polarimeters"],
               [""],
               ["Data 1 Name", "Data 2 Name", "Correlation Value"],
               ]

    warnings = {"md": md_war, "csv": csv_war}

    # length of the shortest array in the dictionary: needed for correlation with Dataframes
    min_len = np.inf

    # Creating the path to store the png file containing the matrix
    plot_dir = f"{plot_dir}/Cross_Corr/"
    # Check if the dir exists. If not, it will be created.
    Path(plot_dir).mkdir(parents=True, exist_ok=True)

    polar_names = ["B0", "B1", "B2", "B3", "B4", "B5", "B6", "I0", "I1", "I2", "I3", "I4", "I5", "I6",
                   "G0", "G1", "G2", "G3", "G4", "G5", "G6", "O0", "O1", "O2", "O3", "O4", "O5", "O6",
                   "R0", "R1", "R2", "R3", "R4", "R5", "R6", "V0", "V1", "V2", "V3", "V4", "V5", "V6",
                   "W1", "W2", "W3", "W4", "W5", "W6", "Y0", "Y1", "Y2", "Y3", "Y4", "Y5", "Y6"]

    # Initialize the main dictionary
    polars = {"DEM": {}, "PWR": {}}

    # Initialize the sub-dictionaries for each exit ("Q1", "Q2", "U1", "U2")
    all_exits = ["Q1", "Q2", "U1", "U2"]

    for exit in all_exits:
        # Initialize the sub-dictionary for each category
        polars["DEM"][exit] = {pol_n: [] for pol_n in polar_names}
        polars["PWR"][exit] = {pol_n: [] for pol_n in polar_names}

    # Loading all polarimeters
    # Time needed on a 3h dataset: ~ 5sec/pol => ~ 5 minutes tot
    for name in polar_names:
        # Define a Polarimeter
        p = pol.Polarimeter(name_pol=name, path_file=path_file,
                            start_datetime=start_datetime, end_datetime=end_datetime, output_plot_dir=plot_dir)
        # Loading scientific Output
        logging.info(f"\nLoading Polarimeter {name}.")
        p.Load_Pol()

        # Fill the dictionary "polars" with all the data of the polarimeters
        for kind in ["DEM", "PWR"]:
            for exit in all_exits:
                polars[kind][exit][name] = p.data[kind][exit]
                # Looking for the shortest array
                l = len(p.data[kind][exit])
                if l < min_len:
                    min_len = l

    # Fixing length mismatch
    for name in polar_names:
        for kind in ["DEM", "PWR"]:
            for exit in all_exits:
                polars[kind][exit][name] = polars[kind][exit][name][:min_len - 1]

    # Producing 55x55 correlation matrices
    # ------------------------------------------------------------------------------------------------------------------
    # Total number of matrices: 20.
    # Q1 vs Q1, Q2, U1, U2;
    # Q2 vs Q2, U1, U2;
    # U1 vs U1, U2;
    # U2 vs U2;
    # 4 output ( Q1, Q2, U1, U2) vs all other x2 data type (DEM/PWR)

    # Repetition of the procedure for the two data type: DEM/PWR
    for kind in ["DEM", "PWR"]:

        # Combinations of the exits: Q1, Q2, U1, U2
        for i in range(len(all_exits)):
            for j in range(i, len(all_exits)):
                exit_1 = all_exits[i]
                exit_2 = all_exits[j]

                data_name = f"{kind}_{exit_1}_{exit_2}"
                # logging.debug(f"Combination: ({exit_1}, {exit_2})")

                # Convert dictionaries to DataFrames
                df1 = pd.DataFrame(polars[kind][exit_1])
                df2 = pd.DataFrame(polars[kind][exit_2])

                # Initialize an empty DataFrame for correlations
                correlation_matrix = pd.DataFrame(index=df1.columns, columns=df2.columns)

                # Calculate Correlations
                for key1 in df1.columns:
                    for key2 in df2.columns:
                        correlation_matrix.loc[key1, key2] = df1[key1].corr(df2[key2])

                # Remove self-correlations on the diagonal
                if exit_1 == exit_2:
                    for n in polar_names:
                        correlation_matrix.loc[n, n] = np.nan

                # Combination of the names in pol_names
                for n_1 in range(len(polar_names)):
                    for n_2 in range(n_1 + 1, len(polar_names)):
                        name_1 = polar_names[n_1]
                        name_2 = polar_names[n_2]
                        # logging.debug(corr_matrix)
                        # logging.debug(corr_matrix[name_1])
                        # Print a warning if the correlation value overcomes the threshold, then store it
                        if np.abs(correlation_matrix[name_1][name_2]) > corr_t:
                            warn_msg = (f"Found high correlation value between "
                                        f"{name_1} {exit_1} {kind} and {name_2} {exit_2} {kind}:"
                                        f" {round(correlation_matrix[name_1][name_2], 4)}.")
                            logging.warning(warn_msg)

                            # [MD] Collecting the warning
                            warnings["md"].append(
                                f"|{name_1} {exit_1} {kind} |{name_2} {exit_2} {kind} "
                                f"|{correlation_matrix[name_1][name_2]}|\n")

                            # [CSV] Collecting the warning
                            warnings["csv"].append([f"{name_1} {exit_1} {kind}", f"{name_2} {exit_2} {kind}",
                                                    f"{correlation_matrix[name_1][name_2]}"])

                # Convert correlation matrix values to float
                correlation_matrix = correlation_matrix.astype(float)

                # Create a heatmap using Seaborn
                plt.figure(figsize=(20, 16))
                sn.heatmap(correlation_matrix, annot=True, cmap='coolwarm', linewidths=.5, vmin=-0.8, vmax=0.8,
                           annot_kws={"size": 4}, xticklabels=True, yticklabels=True)
                plt.title(f'Correlation Matrix {data_name}', fontsize=40)

                # Save the heatmap as a PNG file
                plt.savefig(f'{plot_dir}/{data_name}_corr_mat.png', dpi=300)

                # Show the figure on video
                if show:
                    plt.show()
                plt.close('all')
    return warnings
