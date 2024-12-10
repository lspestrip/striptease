# -*- encoding: utf-8 -*-

# This file contains the function "thermal_hk" that operates an analysis of the Thermal Sensors (TS) of Strip.
# This function will be used during the system level test campaign of the LSPE-Strip instrument.

# August 18th 2023, Brescia (Italy) - April 15th 2024, Brescia (Italy)

# Libraries & Modules
import csv
import logging
import os
import time

from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from rich.logging import RichHandler

# My Modules
import thermalsensors as ts
import f_strip as fz
import f_correlation_strip as fz_c

# Use the module logging to produce nice messages on the shell
logging.basicConfig(level="INFO", format='%(message)s',
                    datefmt="[%X]", handlers=[RichHandler()])


def thermal_hk(path_file: str, start_datetime: str, end_datetime: str,
               status: str, fft: bool, nperseg_thermal: int,
               ts_sam_exp_med: float, ts_sam_tolerance: float,
               spike_data: bool, spike_fft: bool,
               corr_t: float, corr_plot: bool, corr_mat: bool,
               output_plot_dir: str, output_report_dir: str,
               report_to_plot: str):
    """
        Performs the analysis of one or more polarimeters producing a complete report.
        The analysis can include plots of: Even-Odd Output, Scientific Data, FFT and correlation Matrices.
        The reports produced include also info about the state of the housekeeping parameters and the thermal sensors.

        Parameters:

        - **path_file** (``str``): location of the data file, it is indeed the location of the hdf5 file's index
        - **start_datetime** (``str``): start time
        - **end_datetime** (``str``): end time

            Other Flags:

        - **status** (``int``): status of the multiplexer of the TS to analyze: 0, 1 or 2 (which stands for both 0 & 1).
        - **fft** (``bool``): If true, the code computes the power spectra of the scientific data.
        - **nperseg_thermal** (``int``): number of elements of thermal measures on which the fft is calculated.
        - **ts_sam_exp_med** (``float``): the exp sampling delta between two consecutive timestamps of TS.
        - **ts_sam_tolerance** (``float``): the acceptance sampling tolerances of the TS.
        - **spike_data** (``bool``): If true, the code will look for spikes in Sci-data.
        - **spike_fft** (``bool``): If true, the code will look for spikes in FFT.
        - **corr_plot** (``bool``): If true, compute the correlation plot of the TS.
        - **corr_mat** (``bool``): If true, compute the correlation matrices of the TS.
        - **corr_t** (``float``): LimSup for the corr value between two dataset: if overcome a warning is produced.
        - **output_report_dir** (`str`): Path from the pipeline dir to the dir that contains the reports of the analysis
        - **output_plot_dir** (`str`): Path from the pipeline dir to the dir that contains the plots of the analysis.
        - **report_to_plot** (`str`): Path from the Report dir to the dir that contain the plots of the analysis.
    """
    logging.info("Starting the Pipeline: Total Operation.")

    # Starting chronometer
    start_code_time = time.time()

    logging.info('\nLoading dir and templates information...')

    # REPORTS ----------------------------------------------------------------------------------------------------------

    # [MD] Markdown REPORT ---------------------------------------------------------------------------------------------
    # Initializing the data-dict for the md report
    report_data = {"output_plot_dir": output_plot_dir, "report_to_plot": report_to_plot}

    # [CSV] REPORT -----------------------------------------------------------------------------------------------------
    # General Information about the whole procedure are collected in a csv file

    # csv_output_dir := directory that contains the csv reports
    csv_output_dir = f"{output_report_dir}/CSV"
    Path(csv_output_dir).mkdir(parents=True, exist_ok=True)

    # [CSV] Heading of the csv file
    csv_general = [
        ["THERMAL SENSORS REPORT CSV"],
        [""],
        ["Path dataset file", "Start Date Time", "End Date Time"],
        [f"{path_file}", f"{start_datetime}", f"{end_datetime}"],
        [""],
        ["Warnings List"],
        [""],
        [""]
    ]

    # [CSV] Open and append information
    # TS Report Name
    report_name = fz.dir_format(f"TS_Report_{start_datetime}__{end_datetime}")
    with open(f'{csv_output_dir}/{report_name}.csv',
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
    # ------------------------------------------------------------------------------------------------------------------

    ####################################################################################################################
    # Thermal Sensors Analysis
    ####################################################################################################################
    # Defining the list of statuses used for the analysis: 0, 1 or both
    if status == 0 or status == 1:
        status = [status]
    elif status == 2:
        status = [0, 1]

    logging.info('\nReady to analyze the Thermal Sensors.\n')
    for stat in status:
        # Creating the TS
        TS = ts.Thermal_Sensors(path_file=path_file, start_datetime=start_datetime, end_datetime=end_datetime,
                                status=stat, nperseg_thermal=nperseg_thermal, output_plot_dir=output_plot_dir)

        # Loading the TS
        logging.info(f'Loading TS. Status {stat}')
        TS.Load_TS()

        # TS Sampling warnings -----------------------------------------------------------------------------------------
        sampling_table = TS.TS_Sampling_Table(sam_exp_med=ts_sam_exp_med, sam_tolerance=ts_sam_tolerance)
        # [MD] Storing TS sampling warnings
        sampling_warn.extend(sampling_table["md"])
        # [CSV] Storing TS sampling warnings
        csv_general = sampling_table["csv"]
        # --------------------------------------------------------------------------------------------------------------
        # [CSV] REPORT: write TS sampling in the report ----------------------------------------------------------------
        with open(f'{csv_output_dir}/{report_name}.csv',
                  'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(csv_general)
        logging.info("####################\n"
                     "CSV Report updated: TS Sampling Table written.\n####################\n")
        # --------------------------------------------------------------------------------------------------------------

        ################################################################################################################
        # SPIKE RESEARCH
        ################################################################################################################
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
            csv_general = spike_table["csv"]

            # [CSV] REPORT: write TS Dataset spikes --------------------------------------------------------------------
            with open(f'{csv_output_dir}/{report_name}.csv',
                      'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(csv_general)
            logging.info("####################\n"
                         "CSV Report updated: TS Dataset spikes written.\n####################\n")
            # ----------------------------------------------------------------------------------------------------------

        # Looking for spikes in the FFT of TS Dataset
        if spike_fft:
            logging.info('Looking for spikes in the FFT of the Thermal dataset.')
            # Collect the spike Table for TS FFT
            spike_table = TS.Spike_Report(fft=True, ts_sam_exp_med=ts_sam_exp_med)
            # [MD]
            spike_warn.extend(spike_table["md"])
            # [CSV]
            csv_general = spike_table["csv"]

            # [CSV] REPORT: write TS FFT spikes --------------------------------------------------------------------
            with open(f'{csv_output_dir}/{report_name}.csv',
                      'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(csv_general)
            logging.info("####################\n"
                         "CSV Report updated: TS FFT spikes written.\n####################\n")
            # ----------------------------------------------------------------------------------------------------------
        ################################################################################################################

        # Normalizing TS measures
        logging.info(f'Normalizing TS. Status {stat}')
        _ = TS.Norm_TS()

        # TS Time warnings ----------------------------------------------------------------------------------------
        # [MD]
        t_warn.extend(TS.warnings["time_warning"])
        # [CSV]
        csv_general.append(TS.warnings["time_warning"])
        # --------------------------------------------------------------------------------------------------------------

        # [CSV] REPORT: write TS time warnings in the report -----------------------------------------------------------
        with open(f'{csv_output_dir}/{report_name}.csv',
                  'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(csv_general)
        logging.info("####################\n"
                     "CSV Report updated: TS Sampling Table written.\n####################\n")
        # ----------------------------------------------------------------------------------------------------------

        # Analyzing TS and collecting the results ------------------------------------------------------------------
        logging.info(f'Analyzing TS. Status {stat}')
        ts_results = TS.Analyse_TS()

        # Preparing tables for the reports
        logging.info(f'Producing TS table for the report. Status {stat}')
        TS_table = TS.Thermal_table(results=ts_results)
        # [MD]
        th_table = TS_table["md"]
        # [CSV]
        csv_general = TS_table["csv"]
        # ----------------------------------------------------------------------------------------------------------

        # [CSV] write TS results table in the report ---------------------------------------------------------------
        with open(f'{csv_output_dir}/{report_name}.csv',
                  'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(csv_general)
        logging.info("####################\n"
                     "CSV Report updated: TS Table written.\n####################\n")
        # ----------------------------------------------------------------------------------------------------------

        # Plots of all TS
        logging.info(f'Plotting all TS measures for status {stat} of the multiplexer.')
        TS.Plot_TS()

        # Fourier's analysis if asked
        if fft:
            logging.info(f'Plotting the FFT of all the TS measures for status {stat} of the multiplexer.')
            # Plot of the FFT of all TS measures
            for all_in in [True, False]:
                TS.Plot_FFT_TS(all_in=all_in)

        # ----------------------------------------------------------------------------------------------------------
        # [MD] REPORT TS
        # ----------------------------------------------------------------------------------------------------------
        logging.info(f"\nOnce ready, I will put the TS report for the status {stat} into: {output_report_dir}.")

        # Updating the report_data dict
        report_data.update({'th_tab': th_table, 'status': stat})

        # Getting instructions to create the TS report
        template_ts = env.get_template('report_thermals.txt')

        # Report TS generation
        filename = Path(f"{output_report_dir}/3_report_ts_status_{stat}.md")

        # Overwrite reports produced through the previous version of the pipeline
        # Create a new white file where to write
        with open(filename, 'w') as outf:
            outf.write(template_ts.render(report_data))
        logging.info("###########################################################################################\n"
                     "Thermal Sensors - Markdown Report Ready!\n\n")

    ####################################################################################################################
    # Correlation plots and matrices: TS
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

        logging.info("-----------------------------------------------------------------------------------------------\n"
                     "Thermal Sensors: Correlation Plots and Matrices\n"
                     "-----------------------------------------------------------------------------------------------\n"
                     )
        # Define TS in both status 0 and 1
        ts_0 = ts.Thermal_Sensors(path_file=path_file, start_datetime=start_datetime,
                                  end_datetime=end_datetime,
                                  status=0, nperseg_thermal=nperseg_thermal, output_plot_dir=output_plot_dir)
        ts_1 = ts.Thermal_Sensors(path_file=path_file, start_datetime=start_datetime,
                                  end_datetime=end_datetime,
                                  status=1, nperseg_thermal=nperseg_thermal, output_plot_dir=output_plot_dir)
        # Loading thermal measures
        ts_0.Load_TS()
        ts_1.Load_TS()
        # Cleaning thermal measures from Nan values
        ts_0.Clean_TS()
        ts_1.Clean_TS()
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

            # Correlation Plot
            if corr_plot:
                logging.warning(
                    f'---------------------------------------------------------------------------------'
                    f'\nCorrelation plot with threshold {corr_t}. '
                    f'\n{n1} - {n2}.\n\n')
                # Store correlation warnings from the correlation plot
                correlation_warnings = fz_c.correlation_plot(list1=[],
                                                             list2=[],
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

            # Correlation Matrix
            if corr_mat:
                logging.warning(
                    f'---------------------------------------------------------------------------------'
                    f'\nCorrelation matrix with threshold {corr_t}. '
                    f'\n{n1} - {n2}.\n\n')
                # Store/Overwrite correlation warnings from the correlation matrix
                correlation_warnings = fz_c.correlation_mat(dict1=d1,
                                                            dict2=d2,
                                                            data_name1=f"{n1}", data_name2=f"{n2}",
                                                            start_datetime=start_datetime,
                                                            show=False, plot_dir=output_plot_dir)
                # [MD] Store/Overwrite correlation warnings
                gen_warn = correlation_warnings["md"]
                # [CSV] Store/Overwrite correlation warnings
                csv_general = correlation_warnings["csv"]

            # Store correlation warnings (only once, to avoid repetitions)
            # [MD] Collecting correlation warnings
            corr_warn.extend(gen_warn)

            # [CSV] REPORT: write Polarimeter Correlation warnings in the report -----------------------------------
            with open(f'{csv_output_dir}/{report_name}.csv',
                      'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(csv_general)
            logging.info(f"\n####################\n"
                         f"CSV Report updated: Correlations {n1} - {n2}.\n####################\n")
            # ------------------------------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------------------
    # [MD] REPORT CORRELATION PLOT:
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

    # Stopping chronometer
    end_code_time = time.time()
    # Calculate running time of the code
    elapsed_time = end_code_time - start_code_time

    # Printing the elapsed time
    logging.info(f"############################################################################################\n"
                 f"Elapsed Time: {round(elapsed_time, 2)} s ({(round(elapsed_time/60., 2))} min)\n"
                 "############################################################################################\n")

    return
