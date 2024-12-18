# -*- encoding: utf-8 -*-

# This file contains the function "tot" that operates a complete analysis of a provided group of polarimeters.
# This function will be used during the system level test campaign of the LSPE-Strip instrument.

# August 14th 2023, Brescia (Italy) - January 31st 2024, Bologna (Italy)

# Libraries & Modules
import csv
import logging
import os

from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from rich.logging import RichHandler

# MyLibraries & MyModules
import f_strip as fz
import f_correlation_strip as fz_c
import polarimeter as pol
import thermalsensors as ts

# Use the module logging to produce nice messages on the shell
logging.basicConfig(level="INFO", format='%(message)s',
                    datefmt="[%X]", handlers=[RichHandler()])


def tot(path_file: str, start_datetime: str, end_datetime: str, name_pol: str,
        thermal_sensors: bool, housekeeping: bool, scientific: bool,
        eoa: str, rms: bool, smooth: int, window: int,
        fft: bool, nperseg: int, nperseg_thermal: int,
        spike_data: bool, spike_fft: bool,
        sam_tolerance: float,
        hk_sam_exp_med: [float, float, float], hk_sam_tolerance: [float, float, float],
        ts_sam_exp_med: float, ts_sam_tolerance: float,
        corr_plot: bool, corr_mat: bool, corr_t: float, cross_corr: bool,
        output_plot_dir: str, output_report_dir: str,
        report_to_plot: str):
    """
        Performs the analysis of one or more polarimeters producing a complete report.
        The analysis can include plots of: Even-Odd Output, Scientific Data, FFT, correlation and  Matrices.
        The reports produced include also info about the state of the housekeeping parameters and the thermal sensors.

            Parameters:

        - **path_file** (``str``): location of the data file and hdf5 file index (without the name of the file)
        - **start_datetime** (``str``): start time
        - **end_datetime** (``str``): end time
        - **name_pol** (``str``): name of the polarimeter. If more than one, write them into ' ' separated by space.

            Other Flags:

        - **eoa** (``str``): states which scientific data analyze. Even samples (e), odd samples (o), all samples (a).
        - **smooth** (``int``): Smoothing length used to flatter the data. smooth=1 equals no smooth.
        - **window** (``int``): Used to convert the array of the data into a matrix with "window" elements per row.
        - **scientific** (``bool``): If true, compute the double demodulation and analyze the scientific data.
        - **rms** (``bool``): If true, compute the rms on the scientific output and data.
        - **thermal_sensors** (``bool``): If true, the code analyzes the Thermal Sensors of Strip.
        - **housekeeping** (``bool``): If true, the code analyzes the Housekeeping parameters of the Polarimeters.
        - **fft** (``bool``): If true, the code computes the power spectra of the scientific data.
        - **nperseg** (``int``): number of elements of the array of scientific data on which the fft is calculated
        - **nperseg_thermal** (``int``): number of elements of thermal measures on which the fft is calculated.
        - **spike_data** (``bool``): If true, the code will look for spikes in Sci-data.
        - **spike_fft** (``bool``): If true, the code will look for spikes in FFT.
        - **sam_tolerance** (``float``): the acceptance sampling tolerances of the Scientific Output.
        - **ts_sam_exp_med** (``float``): the exp sampling delta between two consecutive timestamps of TS.
        - **ts_sam_tolerance** (``float``): the acceptance sampling tolerances of the TS.
        - **hk_sam_exp_med** (``dict``): the exp sampling delta between two consecutive timestamps of hk.
        - **hk_sam_tolerance** (``dict``): the acceptance sampling tolerances of the hk parameters: I,V,O.
        - **corr_plot** (``bool``): If true, compute the correlation plot of the even-odd and scientific data.
        - **corr_mat** (``bool``): If true, compute the correlation matrices of the even-odd and scientific data.
        - **corr_t** (``float``): LimSup for the corr value between two dataset: if overcome a warning is produced.
        - **cross_corr** (``bool``): If true, compute the 55x55 correlation matrices between all the polarimeters.
        - **output_report_dir** (`str`): Path from the pipeline dir to the dir that contains the reports of the analysis
        - **output_plot_dir** (`str`): Path from the pipeline dir to the dir that contains the plots of the analysis.
        - **report_to_plot** (`str`): Path from the Report dir to the dir that contain the plots of the analysis.
    """
    logging.info('\nLoading dir and templates information...')

    # REPORTS ----------------------------------------------------------------------------------------------------------

    # [MD] Markdown REPORT ---------------------------------------------------------------------------------------------
    # Initializing the data-dict for the md report
    report_data = {"output_plot_dir": output_plot_dir, "report_to_plot": report_to_plot}

    # Initializing a boolean variable to create a new report file or to overwrite the old ones
    first_report = True

    # [CSV] REPORT -----------------------------------------------------------------------------------------------------
    # General Information about the whole procedure are collected in a csv file

    # csv_output_dir := directory that contains the csv reports
    csv_output_dir = f"{output_report_dir}/CSV"
    Path(csv_output_dir).mkdir(parents=True, exist_ok=True)

    # [CSV] Heading of the csv file
    csv_general = [
        ["GENERAL REPORT CSV"],
        [""],
        ["Path dataset file", "Start Date Time", "End Date Time"],
        [f"{path_file}", f"{start_datetime}", f"{end_datetime}"],
        [""],
        ["N Polarimeters"],
        [f"{len(name_pol.split())}"],
        [""],
        ["Warnings List"],
        [""],
        [""]
    ]

    # [CSV] Open and append information
    with open(f'{csv_output_dir}/General_Report_{start_datetime}__{end_datetime}.csv',
              'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(csv_general)
    logging.info("####################\n"
                 "CSV Report updated: Heading written.\n####################\n")
    # ------------------------------------------------------------------------------------------------------------------
    # [MD] Initializing warning lists
    t_warn = []
    sampling_warn = []
    corr_warn = []
    spike_warn = []

    # General warning lists used in case of repetitions
    gen_warn = []

    # root: location of the file.txt with the information to build the report
    root = "templates/validation_templates"
    templates_dir = Path(root)

    # Creating the Jinja2 environment
    env = Environment(loader=FileSystemLoader(templates_dir))

    logging.info('\nReady to analyze Strip.')

    ####################################################################################################################
    # Thermal Sensors Analysis
    ####################################################################################################################
    if not thermal_sensors:
        pass
    else:
        logging.info('\nReady to analyze the Thermal Sensors.\n')
        for status in [0, 1]:
            TS = ts.Thermal_Sensors(path_file=path_file, start_datetime=start_datetime, end_datetime=end_datetime,
                                    status=status, nperseg_thermal=nperseg_thermal, output_plot_dir=output_plot_dir)

            # Loading the TS
            logging.info(f'Loading TS. Status {status}')
            TS.Load_TS()

            # TS Sampling warnings -------------------------------------------------------------------------------------
            sampling_table = TS.TS_Sampling_Table(sam_exp_med=ts_sam_exp_med, sam_tolerance=ts_sam_tolerance)
            # [MD] Storing TS sampling warnings
            sampling_warn.extend(sampling_table["md"])
            # [CSV] Storing TS sampling warnings
            csv_general = sampling_table["csv"]
            # ----------------------------------------------------------------------------------------------------------
            # [CSV] REPORT: write TS sampling in the report ------------------------------------------------------------
            with open(f'{csv_output_dir}/General_Report_{start_datetime}__{end_datetime}.csv',
                      'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(csv_general)
            logging.info("####################\n"
                         "CSV Report updated: TS Sampling Table written.\n####################\n")
            # ----------------------------------------------------------------------------------------------------------

            ############################################################################################################
            # TS SPIKE RESEARCH
            ############################################################################################################
            spike_warn = []
            csv_general = []

            # Looking for spikes in the TS Dataset
            if spike_data:
                logging.info('Looking for spikes in the Thermal dataset.')
                # Collect the spike Table for TS Output
                spike_table = TS.Spike_Report(fft=False, ts_sam_exp_med=ts_sam_exp_med)
                # [MD]
                spike_warn.extend(spike_table["md"])
                # [CSV]
                csv_general.append(spike_table["csv"])

                # [CSV] REPORT: write TS Dataset spikes ----------------------------------------------------------------
                with open(f'{csv_output_dir}/General_Report_{start_datetime}__{end_datetime}.csv',
                          'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerows(csv_general)
                logging.info("####################\n"
                             "CSV Report updated: TS Dataset spikes written.\n####################\n")
                # ------------------------------------------------------------------------------------------------------

            # Looking for spikes in the FFT of TS Dataset
            if spike_fft:
                logging.info('Looking for spikes in the FFT of the Thermal dataset.')
                # Collect the spike Table for TS FFT
                spike_table = TS.Spike_Report(fft=True, ts_sam_exp_med=ts_sam_exp_med)
                # [MD]
                spike_warn.extend(spike_table["md"])
                # [CSV]
                csv_general.append(spike_table["csv"])

                # [CSV] REPORT: write TS FFT spikes --------------------------------------------------------------------
                with open(f'{csv_output_dir}/TS_Report_{start_datetime}__{end_datetime}.csv',
                          'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerows(csv_general)
                logging.info("####################\n"
                             "CSV Report updated: TS FFT spikes written.\n####################\n")
                # ------------------------------------------------------------------------------------------------------
            ############################################################################################################

            # Normalizing TS measures
            logging.info(f'Normalizing TS. Status {status}')
            _ = TS.Norm_TS()

            # TS Time warnings -----------------------------------------------------------------------------------------
            # [MD]
            t_warn.extend(TS.warnings["time_warning"])
            # [CSV]
            csv_general.append(TS.warnings["time_warning"])
            # ----------------------------------------------------------------------------------------------------------

            # [CSV] REPORT: write TS sampling & time warnings in the report --------------------------------------------
            with open(f'{csv_output_dir}/General_Report_{start_datetime}__{end_datetime}.csv',
                      'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(csv_general)
            logging.info("####################\n"
                         "CSV Report updated: TS Sampling Table written.\n####################\n")
            # ----------------------------------------------------------------------------------------------------------

            # Analyzing TS and collecting the results ------------------------------------------------------------------
            logging.info(f'Analyzing TS. Status {status}')
            ts_results = TS.Analyse_TS()

            # Preparing tables for the reports
            logging.info(f'Producing TS table for the report. Status {status}')
            TS_table = TS.Thermal_table(results=ts_results)
            # [MD]
            th_table = TS_table["md"]
            # [CSV]
            csv_general = TS_table["csv"]
            # ----------------------------------------------------------------------------------------------------------

            # [CSV] write TS results table in the report ---------------------------------------------------------------
            with open(f'{csv_output_dir}/General_Report_{start_datetime}__{end_datetime}.csv',
                      'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(csv_general)
            logging.info("####################\n"
                         "CSV Report updated: TS Table written.\n####################\n")
            # ----------------------------------------------------------------------------------------------------------

            # Plots of all TS measures
            logging.info(f'Plotting all TS measures for status {status} of the multiplexer.')
            TS.Plot_TS()

            # Fourier's analysis if asked
            if fft:
                logging.info(f'Plotting the FFT of all the TS measures for status {status} of the multiplexer.')
                # Plot of the FFT of all TS measures
                TS.Plot_FFT_TS()

            # ----------------------------------------------------------------------------------------------------------
            # REPORT TS
            # ----------------------------------------------------------------------------------------------------------
            logging.info(f"\nOnce ready, I will put the TS report for the status {status} into: {output_report_dir}.")

            # Updating the report_data dict
            report_data.update({'th_tab': th_table, 'status': status})

            # Getting instructions to create the TS report
            template_ts = env.get_template('report_thermals.txt')

            # Report TS generation
            filename = Path(f"{output_report_dir}/3_report_ts_status_{status}.md")

            # Overwrite reports produced through the previous version of the pipeline
            # Create a new white file where to write
            with open(filename, 'w') as outf:
                outf.write(template_ts.render(report_data))
            logging.info("###########################################################################################\n"
                         "Thermal Sensors - Markdown Report Ready!\n\n")

    ####################################################################################################################
    # Multi Polarimeter Analysis
    ####################################################################################################################
    # Cross Correlation Matrices (55x55 matrix)
    if cross_corr:
        logging.warning(
            f'-------------------------------------------------------------------------------------'
            f'\nCross Correlation Matrices between all the polarimeters.')
        cross_corr_mat = fz_c.cross_corr_mat(path_file=path_file,
                                             start_datetime=start_datetime, end_datetime=end_datetime,
                                             show=False, corr_t=corr_t, plot_dir=output_plot_dir)
        # [MD] Storing high correlation values
        corr_warn.extend(cross_corr_mat["md"])
        # [CSV] Storing high correlation values
        csv_general = cross_corr_mat["csv"]

        # [CSV] write Cross Correlations results in the report ---------------------------------------------------------
        with open(f'{csv_output_dir}/General_Report_{start_datetime}__{end_datetime}.csv',
                  'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(csv_general)
            logging.info("####################\n"
                         "CSV Report updated: Cross Correlation Warnings written.\n####################\n")
        # --------------------------------------------------------------------------------------------------------------

    ####################################################################################################################
    # Single Polarimeter Analysis
    ####################################################################################################################
    logging.info("\nReady to analyze the Polarimeters now.")
    # Converting the string of polarimeters into a list
    name_pol = name_pol.split()

    # Repeating the analysis for all the polarimeters in the list
    for np in name_pol:

        # Messages for report and user
        # --------------------------------------------------------------------------------------------------------------
        msg = f'Parsing {np}'

        # [CSV]
        csv_general = [
            [""],
            [f"{msg}"],
            [""]
        ]
        # [CSV] write which polarimeter is parsed ---------------------------------------------------------
        with open(f'{csv_output_dir}/General_Report_{start_datetime}__{end_datetime}.csv',
                  'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(csv_general)
        # -------------------------------------------------------------------------------------------------

        # [MD]
        # Updating the report_data dict
        report_data.update({"pol_name": np})

        logging.warning(f'--------------------------------------------------------------------------------------'
                        f'\n{msg}\n')
        # --------------------------------------------------------------------------------------------------------------

        # Initializing a Polarimeter
        p = pol.Polarimeter(name_pol=np, path_file=path_file,
                            start_datetime=start_datetime, end_datetime=end_datetime, output_plot_dir=output_plot_dir)

        ################################################################################################################
        # Housekeeping Analysis
        ################################################################################################################
        if not housekeeping:
            pass
        else:
            logging.warning('--------------------------------------------------------------------------------------'
                            f'\nHousekeeping Analysis of {np}.\nLoading HK.')
            # Loading the HK
            p.Load_HouseKeeping()

            # HK Sampling warnings -------------------------------------------------------------------------------------
            HK_sampling_table = p.HK_Sampling_Table(sam_exp_med=hk_sam_exp_med, sam_tolerance=hk_sam_tolerance)
            # [MD]
            sampling_warn.extend(HK_sampling_table["md"])
            # [CSV] Storing HK sampling table
            csv_general = HK_sampling_table["csv"]
            # ----------------------------------------------------------------------------------------------------------

            # Normalizing the HK measures
            logging.info('Normalizing HK.')
            problematic_hk = p.Norm_HouseKeeping()

            # HK Time warnings -----------------------------------------------------------------------------------------
            # [MD]
            t_warn.extend(p.warnings["time_warning"])
            # [CSV]
            csv_general.append(problematic_hk)
            # ----------------------------------------------------------------------------------------------------------

            # [CSV] REPORT: write HK sampling & time warnings in the report --------------------------------------------
            with open(f'{csv_output_dir}/General_Report_{start_datetime}__{end_datetime}.csv',
                      'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(csv_general)
            logging.info(f"####################\n"
                         f"CSV Report updated: HK {np} Sampling Table written.\n####################\n")
            # ----------------------------------------------------------------------------------------------------------

            # Analyzing HK and collecting the results
            logging.info('Analyzing HK.')
            hk_results = p.Analyse_HouseKeeping()

            # Preparing tables for the report
            logging.info('Producing HK table for the report.')
            HK_table = p.HK_table(results=hk_results)

            # [CSV] Storing the HK results table
            csv_general = HK_table["csv"]
            # [CSV] REPORT: write HK Table in the report ---------------------------------------------------------------
            with open(f'{csv_output_dir}/General_Report_{start_datetime}__{end_datetime}.csv',
                      'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(csv_general)
            logging.info(f"####################\n"
                         f"CSV Report updated: HK {np} Table written.\n####################\n")
            # ----------------------------------------------------------------------------------------------------------

            # Plots of the Bias HK (Tensions and Currents) and of the Offsets
            logging.info('Plotting Bias HK and Offsets.')
            for hk_kind in ["I", "V", "O"]:
                p.Plot_Housekeeping(hk_kind=hk_kind, show=False)

            # ----------------------------------------------------------------------------------------------------------
            # [MD] REPORT HK
            # ----------------------------------------------------------------------------------------------------------
            logging.info(f"\nOnce ready, I will put the HK report into: {output_report_dir}.")

            # Updating the report_data dict
            report_data.update({"hk_table": HK_table["md"]})

            # Getting instructions to create the HK report
            template_hk = env.get_template('report_hk.txt')

            # [MD] Report HK generation
            filename = Path(f"{output_report_dir}/4_report_hk.md")

            # Overwrite reports produced through the previous version of the pipeline
            if first_report:
                # Create a new white file where to write
                with open(filename, 'w') as outf:
                    outf.write(template_hk.render(report_data))
            # Avoid overwriting between following polarimeters
            else:
                # Append at the end of the file
                with open(filename, 'a') as outf:
                    outf.write(template_hk.render(report_data))

            logging.info("###########################################################################################\n"
                         f"HK Parameters of Pol {np} - Markdown Report Ready!\n\n")

        ################################################################################################################
        # Scientific Output Analysis
        ################################################################################################################
        # Loading the Scientific Outputs
        logging.warning('--------------------------------------------------------------------------------------'
                        '\nScientific Analysis. \nLoading Scientific Outputs.')
        p.Load_Pol()

        # Holes: Analyzing Scientific Output Sampling --------------------------------------------------------------
        csv_general = p.Pol_Sampling_Table(sam_tolerance=sam_tolerance)
        sampling_warn.extend(p.warnings["sampling_warning"])
        # ----------------------------------------------------------------------------------------------------------

        # [CSV] REPORT: write Polarimeter Sampling Table (Jumps) in the report -------------------------------------
        with open(f'{csv_output_dir}/General_Report_{start_datetime}__{end_datetime}.csv',
                  'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(csv_general)
        logging.info(f"####################\n"
                     f"CSV Report updated: Polarimeter {np} Sampling Table written.\n####################\n")
        # ----------------------------------------------------------------------------------------------------------

        # Looking for spikes in the dataset ------------------------------------------------------------------------

        # Output Spikes
        if spike_data:
            logging.info('Looking for spikes in the dataset.')
            spike_table = p.Spike_Report(fft=False, nperseg=0)
            # [MD]
            spike_warn.extend(spike_table["md"])
            # [CSV]
            csv_general = spike_table["csv"]

            # [CSV] REPORT: write Polarimeter Spikes Table in the report -------------------------------------------
            with open(f'{csv_output_dir}/General_Report_{start_datetime}__{end_datetime}.csv',
                      'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(csv_general)
            logging.info(f"####################\n"
                         f"CSV Report updated: Polarimeter {np} Spikes Table written.\n####################\n")
            # ------------------------------------------------------------------------------------------------------

        # FFT Spikes
        if spike_fft:
            logging.info('Looking for spikes in the FFT of the dataset.')
            spike_table = p.Spike_Report(fft=True, nperseg=10 ** 6)
            # [MD]
            spike_warn.extend(spike_table["md"])
            # [CSV]
            csv_general = spike_table["csv"]

            # [CSV] REPORT: write Polarimeter FFT Spikes Table in the report ---------------------------------------
            with open(f'{csv_output_dir}/General_Report_{start_datetime}__{end_datetime}.csv',
                      'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(csv_general)
            logging.info(f"####################\n"
                         f"CSV Report updated: Polarimeter {np} FFT Spikes Table written.\n####################\n")
        # ----------------------------------------------------------------------------------------------------------

        # Preparing the Polarimeter for the analysis: normalization and data cleanse
        logging.info('Preparing the Polarimeter.')
        # Dataset in function of time [s]
        p.Prepare(norm_mode=1)

        for type in ['DEM', 'PWR']:
            # Plot the Scientific Output
            logging.info(f'Plotting {type} Outputs.')
            p.Plot_Output(type=type, begin=0, end=-1, show=False)

            ########################################################################################################
            # Even Odd All Analysis
            ########################################################################################################
            if eoa == ' ':
                pass
            else:
                logging.warning(f'---------------------------------------------------------------------------------'
                                f'\nEven-Odd-All Analysis. Data type: {type}.')
                combos = fz.eoa_values(eoa)
                for combo in combos:
                    # If even, odd, all are equal to 0
                    if all(value == 0 for value in combo):
                        # Do nothing
                        pass
                    else:
                        # Showing which plots will be produced
                        logging.info(f'\nEven = {combo[0]}, Odd = {combo[1]}, All = {combo[2]}.')

                        # Plot of Even-Odd-All Outputs
                        logging.info(f'Plotting Even Odd All Outputs. Type {type}.')
                        fz.data_plot(pol_name=np, dataset=p.data, timestamps=p.times,
                                     start_datetime=start_datetime, end_datetime=end_datetime, begin=0, end=-1,
                                     type=type, even=combo[0], odd=combo[1], all=combo[2],
                                     demodulated=False, rms=False, fft=False,
                                     window=window, smooth_len=smooth, nperseg=nperseg,
                                     show=False)

                        # Plot of Even-Odd-All RMS
                        if rms:
                            # Plotting Even Odd All Outputs RMS
                            logging.info(f'Plotting Even Odd All Outputs RMS. Type {type}.')
                            fz.data_plot(pol_name=np, dataset=p.data, timestamps=p.times,
                                         start_datetime=start_datetime, end_datetime=end_datetime, begin=0, end=-1,
                                         type=type, even=combo[0], odd=combo[1], all=combo[2],
                                         demodulated=False, rms=True, fft=False,
                                         window=window, smooth_len=smooth, nperseg=nperseg,
                                         show=False)

                        # Plot of FFT of Even-Odd-All Outputs
                        if fft:
                            logging.warning("----------------------------------------------------------------------"
                                            "\nSpectral Analysis Even-Odd-All")
                            # Plotting Even Odd All FFT
                            logging.info(f'Plotting Even Odd All FFT. Type {type}.')
                            fz.data_plot(pol_name=np, dataset=p.data, timestamps=p.times,
                                         start_datetime=start_datetime, end_datetime=end_datetime, begin=0, end=-1,
                                         type=type, even=combo[0], odd=combo[1], all=combo[2],
                                         demodulated=False, rms=False, fft=True,
                                         window=window, smooth_len=smooth, nperseg=nperseg,
                                         show=False)

                            # Plot of FFT of RMS of Even-Odd-All Outputs
                            if rms:
                                # Plotting Even Odd All FFT of the RMS
                                logging.info(f'Plotting Even Odd All FFT of the RMS. Type {type}.')
                                fz.data_plot(pol_name=np, dataset=p.data, timestamps=p.times,
                                             start_datetime=start_datetime, end_datetime=end_datetime,
                                             begin=0, end=-1,
                                             type=type, even=combo[0], odd=combo[1], all=combo[2],
                                             demodulated=False, rms=True, fft=True,
                                             window=window, smooth_len=smooth, nperseg=nperseg,
                                             show=False)

                # --------------------------------------------------------------------------------------------------
                # REPORT EOA OUTPUT
                # --------------------------------------------------------------------------------------------------
                # Produce the report only the second time: when all the plots are ready
                if type == "PWR":
                    logging.info(f"\nOnce ready, I will put the EOA report into: {output_report_dir}.")

                    eoa_letters = fz.letter_combo(str(eoa))
                    # Note: the current version of the MD reports don't use eoa_letters
                    # report_eoa.txt -> Jinja2 treats the list as a str.

                    # Updating the report_data dict
                    report_data.update({"name_pol": np, "fft": fft, "rms": rms, "eoa_letters": eoa_letters})

                    # Getting instructions to create the HK report
                    template_eoa = env.get_template('report_eoa.txt')

                    # [MD] Report HK generation
                    filename = Path(f"{output_report_dir}/5_report_eoa.md")

                    # Overwrite reports produced through the previous version of the pipeline
                    if first_report:
                        # Create a new white file where to write
                        with open(filename, 'w') as outf:
                            outf.write(template_eoa.render(report_data))
                    # Avoid overwriting between following polarimeters
                    else:
                        # Append at the end of the file
                        with open(filename, 'a') as outf:
                            outf.write(template_eoa.render(report_data))

                    logging.info(
                        "##########################################################################################\n"
                        f"Scientific Output EOA of Polarimeter {np} - Markdown Report Ready!\n\n")

            ########################################################################################################
            # Scientific Data Analysis
            ########################################################################################################
            if not scientific:
                pass
            else:
                logging.warning("----------------------------------------------------------------------------------"
                                "\nScientific Data Analysis.")
                logging.info(f'\nPlot of Scientific Data. Type {type}.')

                # Plot of Scientific Data
                fz.data_plot(pol_name=np, dataset=p.data, timestamps=p.times,
                             start_datetime=start_datetime, end_datetime=end_datetime, begin=0, end=-1,
                             type=type, even=1, odd=1, all=1,
                             demodulated=True, rms=False, fft=False,
                             window=window, smooth_len=smooth, nperseg=nperseg,
                             show=False)

                # Plot of RMS of Scientific Data
                if rms:
                    logging.info(f'Plot of RMS of Scientific Data. Type {type}.')
                    fz.data_plot(pol_name=np, dataset=p.data, timestamps=p.times,
                                 start_datetime=start_datetime, end_datetime=end_datetime, begin=0, end=-1,
                                 type=type, even=1, odd=1, all=1,
                                 demodulated=True, rms=True, fft=False,
                                 window=window, smooth_len=smooth, nperseg=nperseg,
                                 show=False)

                # Plot of FFT of Scientific Data
                if fft:
                    logging.warning("------------------------------------------------------------------------------"
                                    "\nSpectral Analysis Scientific Data.")
                    logging.info(f'Plot of FFT of Scientific Data. Type {type}.')
                    fz.data_plot(pol_name=np, dataset=p.data, timestamps=p.times,
                                 start_datetime=start_datetime, end_datetime=end_datetime, begin=0, end=-1,
                                 type=type, even=1, odd=1, all=1,
                                 demodulated=True, rms=False, fft=True,
                                 window=window, smooth_len=smooth, nperseg=nperseg,
                                 show=False)

                    # Plot of FFT of the RMS of Scientific Data
                    if rms:
                        logging.info(f'Plot of FFT of the RMS of Scientific Data. Type {type}.')
                        fz.data_plot(pol_name=np, dataset=p.data, timestamps=p.times,
                                     start_datetime=start_datetime, end_datetime=end_datetime, begin=0, end=-1,
                                     type=type, even=1, odd=1, all=1,
                                     demodulated=True, rms=True, fft=True,
                                     window=window, smooth_len=smooth, nperseg=nperseg,
                                     show=False)

                # --------------------------------------------------------------------------------------------------
                # REPORT SCIENTIFIC DATA
                # --------------------------------------------------------------------------------------------------
                # Produce the report only the second time: when all the plots are ready
                if type == "PWR":
                    logging.info(f"\nOnce ready, I will put the SCIENTIFIC DATA report into: {output_report_dir}.")

                    report_data.update({"name_pol": np, "fft": fft})

                    # Getting instructions to create the SCIDATA report
                    template_sci = env.get_template('report_sci.txt')

                    # Report SCIDATA generation
                    filename = Path(f"{output_report_dir}/6_report_sci.md")

                    # Overwrite reports produced through the previous version of the pipeline
                    if first_report:
                        # Create a new white file where to write
                        with open(filename, 'w') as outf:
                            outf.write(template_sci.render(report_data))
                    # Avoid overwriting between following polarimeters
                    else:
                        # Append at the end of the file
                        with open(filename, 'a') as outf:
                            outf.write(template_sci.render(report_data))

                    logging.info(
                        "##########################################################################################\n"
                        f"Scientific Data of Polarimeter {np} - Markdown Report Ready!\n\n")

            ########################################################################################################
            # Correlation plots and matrices
            # Scientific Output
            ########################################################################################################
            # Output Self correlations
            # Output vs TS
            # Output vs HK
            ########################################################################################################
            if corr_plot or corr_mat:
                # List used to contain all possible data combinations to calculate correlations
                possible_combos = []
                logging.warning(f'---------------------------------------------------------------------------------'
                                f'\nCorrelation Analysis. Type {type}.\n')

                # --------------------------------------------------------------------------------------------------
                # Scientific Output Self correlation
                # --------------------------------------------------------------------------------------------------
                # Collecting all possible combinations of Output correlations
                possible_combos.extend([
                    # Output self correlation
                    (p.data[type], p.times, f"{np}_{type}", "Output [ADU]",
                     {}, [], "Self_Corr", "Output [ADU]")
                ])

                # --------------------------------------------------------------------------------------------------
                # Scientific Output vs TS
                # --------------------------------------------------------------------------------------------------
                if not thermal_sensors:
                    pass
                else:
                    for status in [0, 1]:
                        # Initializing a TS
                        TS = ts.Thermal_Sensors(path_file=path_file, start_datetime=start_datetime,
                                                end_datetime=end_datetime,
                                                status=status, nperseg_thermal=nperseg_thermal,
                                                output_plot_dir=output_plot_dir)
                        # Loading thermal measures
                        TS.Load_TS()
                        # Normalizing thermal times
                        _ = TS.Norm_TS()

                        # Collecting all possible data combinations between Outputs and TS
                        possible_combos.extend([
                            # Output vs TS_status 0 or 1
                            (p.data[type], p.times, f"{np}_{type}", "Output [ADU]",
                             TS.ts["thermal_data"]["calibrated"], TS.ts["thermal_times"],
                             f"TS_{status}", "Temperature [K]")
                        ])

                # --------------------------------------------------------------------------------------------------
                # Output vs HK
                # --------------------------------------------------------------------------------------------------
                if not housekeeping:
                    pass
                else:
                    # Loading the Housekeeping parameters
                    p.Load_HouseKeeping()
                    # Normalizing the Housekeeping parameters
                    p.Norm_HouseKeeping()

                    # Define the HK key, unit of measure and first HK
                    for item, unit, first_hk in [("I", "[µA]", "ID0_HK"), ("V", "[mV]", "VD0_HK")]:
                        # Collecting all possible data combinations between Outputs and TS
                        possible_combos.extend([
                            # Output vs TS_status 0 or 1
                            (p.data[type], p.times, f"{np}_{type}", "Output [ADU]",
                             p.hk[item], p.hk_t[item][first_hk],
                             f"Bias_{item}", f"{unit}")
                        ])

                # Produce all correlation plots and matrix using all the combinations of the Outputs
                # d -> data
                # t -> timestamps
                # n -> (data) name
                # u -> unit of measure
                for d1, t1, n1, u1, d2, t2, n2, u2 in possible_combos:

                    # ----------------------------------------------------------------------------------------------
                    # Correlation Plot
                    # ----------------------------------------------------------------------------------------------
                    if corr_plot:
                        logging.warning(
                            f'---------------------------------------------------------------------------------'
                            f'\nCorrelation plot with threshold {corr_t}. '
                            f'\n{n1} - {n2}.')
                        # Store correlation warnings from the correlation plot

                        correlation_warnings = fz_c.correlation_plot(array1=[], array2=[],
                                                                     dict1=d1, dict2=d2,
                                                                     time1=list(t1), time2=list(t2),
                                                                     data_name1=f"{n1}", data_name2=f"{n2}",
                                                                     measure_unit1=f"{u1}", measure_unit2=f"{u2}",
                                                                     start_datetime=start_datetime,
                                                                     show=False,
                                                                     corr_t=corr_t,
                                                                     plot_dir=output_plot_dir)
                        # [MD] Collecting correlation warnings
                        gen_warn = correlation_warnings["md"]
                        # [CSV] Collecting correlation warnings
                        csv_general = correlation_warnings["csv"]

                    # ----------------------------------------------------------------------------------------------
                    # Correlation Matrix
                    # ----------------------------------------------------------------------------------------------
                    if corr_mat:
                        logging.warning(
                            f'---------------------------------------------------------------------------------'
                            f'\nCorrelation matrix with threshold {corr_t}. '
                            f'\n{n1} - {n2}.')
                        # Store/Overwrite correlation warnings from the correlation matrix
                        correlation_warnings = fz_c.correlation_mat(dict1=d1, dict2=d2,
                                                                    data_name1=f"{n1}", data_name2=f"{n2}",
                                                                    start_datetime=start_datetime,
                                                                    show=False, plot_dir=output_plot_dir)
                        # [MD] Collecting correlation warnings
                        gen_warn = correlation_warnings["md"]
                        # [CSV] Collecting correlation warnings
                        csv_general = correlation_warnings["csv"]

                    # Store correlation warnings (only once, to avoid repetitions)
                    # [MD] Collecting correlation warnings
                    corr_warn.extend(gen_warn)

                    # [CSV] REPORT: write Polarimeter Correlation warnings in the report ---------------------------
                    with open(f'{csv_output_dir}/General_Report_{start_datetime}__{end_datetime}.csv',
                              'a', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerows(csv_general)
                    logging.info(f"####################\n"
                                 f"CSV Report updated: Polarimeter {np} correlations {n1} - {n2}.\n"
                                 f"####################\n")
                    # ----------------------------------------------------------------------------------------------

        ################################################################################################################
        # Other Correlation plots and matrices: HK & TS
        ################################################################################################################
        if corr_plot or corr_mat:
            # List used to contain all possible data combinations to calculate correlations
            possible_combos = []

            # ----------------------------------------------------------------------------------------------------------
            # HK Correlations
            # Bias Currents I vs Bias Voltages V
            # Bias Currents I Self Correlations
            # Bias Voltages V Self Correlations
            # ----------------------------------------------------------------------------------------------------------
            if not housekeeping:
                pass
            else:
                logging.info("Housekeeping: Correlation Plots and Matrices")
                # Loading the HK parameters
                p.Load_HouseKeeping()
                # Normalizing the HK parameters
                p.Norm_HouseKeeping()

                # Collecting all possible combinations of HK correlations
                # Note: time is fixed for all I and V: hence the timestamps are defined by the first HK parameter
                possible_combos.extend([
                    # I vs V
                    (p.hk["I"], p.hk_t["I"]["ID0_HK"], "Bias_I", "[µA]",
                     p.hk["V"], p.hk_t["V"]["VD0_HK"], "Bias_V", "[mV]"),
                    # I Self Correlations
                    (p.hk["I"], p.hk_t["I"]["ID0_HK"], "Bias_I", "[µA]",
                     {}, [], "Self_Corr", "[µA]"),
                    # V Self Correlations
                    (p.hk["V"], p.hk_t["V"]["VD0_HK"], "Bias_V", "[mV]",
                     {}, [], "Self_Corr", "[mV]")
                ])

                # ------------------------------------------------------------------------------------------------------
                # HK vs TS
                # Bias Currents I vs TS status 0 or 1
                # Bias Voltages V vs TS status 0 or 1
                # ------------------------------------------------------------------------------------------------------
                if not thermal_sensors:
                    pass
                else:
                    for status in [0, 1]:
                        # Initializing a TS
                        TS = ts.Thermal_Sensors(path_file=path_file, start_datetime=start_datetime,
                                                end_datetime=end_datetime,
                                                status=status, nperseg_thermal=nperseg_thermal,
                                                output_plot_dir=output_plot_dir)
                        # Loading thermal measures
                        TS.Load_TS()
                        # Normalizing thermal times
                        _ = TS.Norm_TS()

                        # Collecting all possible combinations of Hk with TS
                        possible_combos.extend([
                            # Bias Currents I vs TS status 0 or 1
                            (p.hk["I"], p.hk_t["I"]["ID0_HK"], "Bias_I", "[µA]",
                             TS.ts["thermal_data"]["calibrated"], TS.ts["thermal_times"],
                             f"TS_status_{status}", "Temperature [K]"),
                            # Bias Voltages V vs TS status 0 or 1
                            (p.hk["V"], p.hk_t["V"]["VD0_HK"], "Bias_V", "[mV]",
                             TS.ts["thermal_data"]["calibrated"], TS.ts["thermal_times"],
                             f"TS_status_{status}", "Temperature [K]")
                        ])

                # Produce all correlation plots and matrix using all the combinations
                for d1, t1, n1, u1, d2, t2, n2, u2 in possible_combos:

                    # --------------------------------------------------------------------------------------------------
                    # Correlation Plot
                    # --------------------------------------------------------------------------------------------------
                    if corr_plot:
                        logging.warning(
                            f'---------------------------------------------------------------------------------'
                            f'\nCorrelation plot with threshold {corr_t}. '
                            f'\n{n1} - {n2}.')
                        # Store correlation warnings from the correlation plot
                        correlation_warnings = fz_c.correlation_plot(array1=[], array2=[],
                                                                     dict1=d1, dict2=d2,
                                                                     time1=list(t1), time2=list(t2),
                                                                     data_name1=f"{n1}", data_name2=f"{n2}",
                                                                     measure_unit1=f"{u1}", measure_unit2=f"{u2}",
                                                                     start_datetime=start_datetime,
                                                                     show=False,
                                                                     corr_t=corr_t,
                                                                     plot_dir=output_plot_dir)
                        # [MD] Collecting correlation warnings
                        gen_warn = correlation_warnings["md"]
                        # [CSV] Collecting correlation warnings
                        csv_general = correlation_warnings["csv"]

                    # --------------------------------------------------------------------------------------------------
                    # Correlation Matrix
                    # --------------------------------------------------------------------------------------------------
                    if corr_mat:
                        logging.warning(
                            f'---------------------------------------------------------------------------------'
                            f'\nCorrelation matrix with threshold {corr_t}. '
                            f'\n{n1} - {n2}.')
                        # Store/Overwrite correlation warnings from the correlation matrix
                        correlation_warnings = fz_c.correlation_mat(dict1=d1, dict2=d2,
                                                                    data_name1=f"{n1}", data_name2=f"{n2}",
                                                                    start_datetime=start_datetime,
                                                                    show=False, plot_dir=output_plot_dir)
                        # [MD] Collecting correlation warnings
                        gen_warn = correlation_warnings["md"]
                        # [CSV] Collecting correlation warnings
                        csv_general = correlation_warnings["csv"]

                    # Store correlation warnings (only once, to avoid repetitions)
                    # [MD] Collecting correlation warnings
                    corr_warn.extend(gen_warn)

                    # [CSV] REPORT: write Correlation warnings in the report -------------------------------------------
                    with open(f'{csv_output_dir}/General_Report_{start_datetime}__{end_datetime}.csv',
                              'a', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerows(csv_general)
                    logging.info(f"####################\n"
                                 f"CSV Report updated: correlations {n1} - {n2}.\n####################\n")
                    # --------------------------------------------------------------------------------------------------

        # Updating the bool first_report to False at the end of the first for cycle: from now on the info are appended
        first_report = False

    ####################################################################################################################
    # Other Correlation plots and matrices: TS
    ####################################################################################################################
    if corr_plot or corr_mat:
        # List used to contain all possible TS data combinations to calculate correlations
        possible_combos = []

        # --------------------------------------------------------------------------------------------------------------
        # TS Correlations
        # TS 0 vs TS 1
        # TS 0 self correlation
        # TS 1 self correlation
        # --------------------------------------------------------------------------------------------------------------
        if not thermal_sensors:
            pass
        else:
            logging.info("Thermal Sensors: Correlation Plots and Matrices")
            # Define TS in both status 0 and 1
            ts_0 = ts.Thermal_Sensors(path_file=path_file, start_datetime=start_datetime,
                                      end_datetime=end_datetime,
                                      status=0, nperseg_thermal=nperseg_thermal,
                                      output_plot_dir=output_plot_dir)
            ts_1 = ts.Thermal_Sensors(path_file=path_file, start_datetime=start_datetime,
                                      end_datetime=end_datetime,
                                      status=1, nperseg_thermal=nperseg_thermal,
                                      output_plot_dir=output_plot_dir)
            # Loading thermal measures
            ts_0.Load_TS()
            ts_1.Load_TS()
            # Normalizing thermal times
            _ = ts_0.Norm_TS()
            _ = ts_1.Norm_TS()

            # Collecting all possible combinations of TS correlations
            possible_combos.extend([
                # TS 0 vs TS 1
                (ts_0.ts["thermal_data"]["calibrated"], ts_0.ts["thermal_times"],
                 "TS_status_0", "Temperature [K]",
                 ts_1.ts["thermal_data"]["calibrated"], ts_1.ts["thermal_times"],
                 "TS_status_1", "Temperature [K]"),
                # TS 0 self correlation
                (ts_0.ts["thermal_data"]["calibrated"], ts_0.ts["thermal_times"],
                 "TS_status_0", "Temperature [K]",
                 {}, [], "Self_Corr", "Temperature [K]"),
                # TS 1 self correlation
                (ts_1.ts["thermal_data"]["calibrated"], ts_1.ts["thermal_times"],
                 "TS_status_1", "Temperature [K]",
                 {}, [], "Self_Corr", "Temperature [K]",)
            ])

            # Produce all correlation plots and matrix using all the combinations
            for d1, t1, n1, u1, d2, t2, n2, u2 in possible_combos:

                # ------------------------------------------------------------------------------------------------------
                # Correlation Plot
                # ------------------------------------------------------------------------------------------------------
                if corr_plot:
                    logging.warning(
                        f'---------------------------------------------------------------------------------'
                        f'\nCorrelation plot with threshold {corr_t}. '
                        f'\n{n1} - {n2}.')
                    # Store correlation warnings from the correlation plot
                    correlation_warnings = fz_c.correlation_plot(array1=[],
                                                                 array2=[],
                                                                 dict1=d1,
                                                                 dict2=d2,
                                                                 time1=list(t1),
                                                                 time2=list(t2),
                                                                 data_name1=f"{n1}",
                                                                 data_name2=f"{n2}",
                                                                 measure_unit1=f"{u1}",
                                                                 measure_unit2=f"{u2}",
                                                                 start_datetime=start_datetime,
                                                                 show=False,
                                                                 corr_t=corr_t,
                                                                 plot_dir=output_plot_dir)

                    # [MD] Collecting correlation warnings
                    gen_warn = correlation_warnings["md"]
                    # [CSV] Collecting correlation warnings
                    csv_general = correlation_warnings["csv"]

                # ------------------------------------------------------------------------------------------------------
                # Correlation Matrix
                # ------------------------------------------------------------------------------------------------------
                if corr_mat:
                    logging.warning(
                        f'---------------------------------------------------------------------------------'
                        f'\nCorrelation matrix with threshold {corr_t}. '
                        f'\n{n1} - {n2}.')
                    # Store/Overwrite correlation warnings from the correlation matrix
                    correlation_warnings = fz_c.correlation_mat(dict1=d1,
                                                                dict2=d2,
                                                                data_name1=f"{n1}", data_name2=f"{n2}",
                                                                start_datetime=start_datetime,
                                                                show=False, plot_dir=output_plot_dir)
                    # [MD] Collecting correlation warnings
                    gen_warn = correlation_warnings["md"]
                    # [CSV] Collecting correlation warnings
                    csv_general = correlation_warnings["csv"]

                # Store correlation warnings (only once, to avoid repetitions)
                # [MD] Collecting correlation warnings
                corr_warn.extend(gen_warn)

                # [CSV] REPORT: write Polarimeter Correlation warnings in the report -----------------------------------
                with open(f'{csv_output_dir}/General_Report_{start_datetime}__{end_datetime}.csv',
                          'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerows(csv_general)
                logging.info(f"####################\n"
                             f"CSV Report updated: Correlations {n1} - {n2}.\n####################\n")
                # ------------------------------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------------------
    # [MD] REPORT CORRELATION PLOT
    # ------------------------------------------------------------------------------------------------------------------
    if corr_plot:
        logging.info(f"\nOnce ready, I will put the CORR PLOT report into: {output_report_dir}.")

        # Get png files name from the dir Correlation_Plot sorted in alphabetic order
        png_files = sorted([file for file in os.listdir(f"{output_plot_dir}/Correlation_Plot/")
                            if file.lower().endswith('.png')])
        report_data.update({"png_files": png_files})

        # Getting instructions to create the CORR PLOT report
        template_cp = env.get_template('report_corr_plot.txt')

        # [MD] Report CORR PLOT generation
        filename = Path(f"{output_report_dir}/7_report_corr_plot.md")

        # Overwrite reports produced through the previous version of the pipeline
        with open(filename, 'w') as outf:
            outf.write(template_cp.render(report_data))

        logging.info("############################################################################################\n"
                     "Correlation Plots - Markdown Report Ready!\n\n")

    # ------------------------------------------------------------------------------------------------------
    # [MD] REPORT CORRELATION MATRIX
    # ------------------------------------------------------------------------------------------------------
    if corr_mat:
        logging.info(f"\nOnce ready, I will put the CORR MATRIX report into: {output_report_dir}.")

        # Get png files name from the dir Correlation_Matrix sorted in alphabetic order
        png_files = sorted([file for file in os.listdir(f"{output_plot_dir}/Correlation_Matrix/")
                            if file.lower().endswith('.png')])

        # Adding Correlation Matrix png files
        report_data.update({"png_files": png_files})
        # Adding Cross Correlation Bool
        report_data.update({"cross": cross_corr})
        if cross_corr:

            # Get png files name from the dir Cross_Corr sorted in alphabetic order
            png_cross_files = sorted([file for file in os.listdir(f"{output_plot_dir}/Cross_Corr/")
                                      if file.lower().endswith('.png')])
            report_data.update({"png_cross_files": png_cross_files})

        # Getting instructions to create the CORR MAT report
        template_cm = env.get_template('report_corr_mat.txt')

        # Report CORR MAT generation
        filename = Path(f"{output_report_dir}/8_report_corr_mat.md")

        # Overwrite reports produced through the previous version of the pipeline
        with open(filename, 'w') as outf:
            outf.write(template_cm.render(report_data))

        logging.info("############################################################################################\n"
                     "Correlation Matrix - Markdown Report Ready!\n\n")
    # ------------------------------------------------------------------------------------------------------
    # [MD] REPORT WARNINGS
    # ------------------------------------------------------------------------------------------------------
    # Updating the report_data dict for the warning report
    report_data.update({"t_warn": t_warn,
                        "sampling_warn": sampling_warn,
                        "corr_warn": corr_warn,
                        "spike_warn": spike_warn
                        })

    # Getting instructions to create the head of the report
    template_w = env.get_template('report_warnings.txt')

    # Report generation
    filename = Path(f"{output_report_dir}/2_report_tot_warnings.md")
    with open(filename, 'w') as outf:
        outf.write(template_w.render(report_data))

    return
