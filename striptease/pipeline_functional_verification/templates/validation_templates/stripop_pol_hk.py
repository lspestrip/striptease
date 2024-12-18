# -*- encoding: utf-8 -*-

# This file contains the function "pol_hk" that operates an analysis of the Thermal Sensors (TS) of Strip.
# This function will be used during the system level test campaign of the LSPE-Strip instrument.

# August 18th 2023, Brescia (Italy) - January 31st 2024, Bologna (Italy)

# Libraries & Modules
import csv
import logging

from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from rich.logging import RichHandler

# MyLibraries & MyModules
import polarimeter as pol
import f_correlation_strip as fz_c

# Use the module logging to produce nice messages on the shell
logging.basicConfig(level="INFO", format='%(message)s',
                    datefmt="[%X]", handlers=[RichHandler()])


def pol_hk(path_file: str, start_datetime: str, end_datetime: str, name_pol: str,
           corr_plot: bool, corr_mat: bool, corr_t: float,
           hk_sam_exp_med: dict, hk_sam_tolerance: dict,
           output_plot_dir: str, output_report_dir: str,
           report_to_plot: str):
    """
        Performs only the analysis of the Housekeeping parameters of the polarimeter(s) provided.

            Parameters:

        - **path_file** (``str``): location of the data file, it is indeed the location of the hdf5 file's index
        - **start_datetime** (``str``): start time
        - **end_datetime** (``str``): end time
        - **name_pol** (``str``): name of the polarimeter. If more than one, write them into ' ' separated by space.

            Other Flags:
        - **corr_plot** (``bool``): If true, compute the correlation plot of the HK.
        - **corr_mat** (``bool``): If true, compute the correlation matrices of the HK.
        - **corr_t** (``float``): LimSup for the corr value between two dataset: if overcome a warning is produced.
        - **hk_sam_exp_med** (``dict``): contains the exp sampling delta between two consecutive timestamps of HK
        - **hk_sam_tolerance** (``dict``): contains the acceptance sampling tolerances of the hk parameters: I,V,O
        - **output_report_dir** (`str`): Path from striptease to the dir that contains the reports of the analysis.
        - **output_plot_dir** (`str`): Path from striptease to the dir that contains the plots of the analysis.
        - **report_to_plot** (`str`): Path from the Report dir to the dir that contain the plots of the analysis.
    """
    logging.info('\nLoading dir and templates information...\n')

    # REPORTS ----------------------------------------------------------------------------------------------------------

    # [MD] Markdown REPORT ---------------------------------------------------------------------------------------------
    # Initializing the data-dict for the report
    report_data = {"output_plot_dir": output_plot_dir, "report_to_plot": report_to_plot}

    # Initializing a boolean variable to create a new report file or to overwrite the old ones
    first_report = True

    # [CSV] REPORT -----------------------------------------------------------------------------------------------------
    # HK Information about the whole procedure are collected in a csv file

    # csv_output_dir := directory that contains the csv reports
    csv_output_dir = f"{output_report_dir}/CSV"
    Path(csv_output_dir).mkdir(parents=True, exist_ok=True)

    # Heading of the csv file
    csv_general = [
        ["HOUSEKEEPING REPORT CSV"],
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
    with open(f'{csv_output_dir}/HK_Report_{start_datetime}__{end_datetime}.csv',
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

    # General warning lists used in case of repetitions
    gen_warn = []

    # root: location of the file.txt with the information to build the report
    root = "templates/validation_templates"
    templates_dir = Path(root)

    # Creating the Jinja2 environment
    env = Environment(loader=FileSystemLoader(templates_dir))
    # ------------------------------------------------------------------------------------------------------------------

    logging.info('Ready to analyze the HouseKeeping Parameters.\n')
    ####################################################################################################################
    # HOUSEKEEPING PARAMETERS - Single Polarimeter
    ####################################################################################################################
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
        with open(f'{csv_output_dir}/HK_Report_{start_datetime}__{end_datetime}.csv',
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
        # Loading the HK
        logging.warning('--------------------------------------------------------------------------------------'
                        f'\nHousekeeping Analysis of {np}.\nLoading HK.\n')
        p.Load_HouseKeeping()

        # HK Sampling warnings -------------------------------------------------------------------------------------
        HK_sampling_table = p.HK_Sampling_Table(sam_exp_med=hk_sam_exp_med, sam_tolerance=hk_sam_tolerance)
        # [MD] Storing HK sampling table
        sampling_warn.extend(HK_sampling_table["md"])
        # [CSV] Storing HK sampling table
        csv_general = HK_sampling_table["csv"]
        # ----------------------------------------------------------------------------------------------------------

        # Normalizing the HK measures
        logging.info(f'Polarimeter {np}: Normalizing HK.\n')
        problematic_hk = p.Norm_HouseKeeping()

        # HK Time warnings -----------------------------------------------------------------------------------------
        # [MD] Storing problematic HK (time warnings)
        t_warn.extend(p.warnings["time_warning"])
        # [CSV] Storing problematic HK
        csv_general.append(problematic_hk)
        # ----------------------------------------------------------------------------------------------------------

        # [CSV] REPORT: write HK sampling & time warnings in the report --------------------------------------------
        with open(f'{csv_output_dir}/HK_Report_{start_datetime}__{end_datetime}.csv',
                  'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(csv_general)
        logging.info(f"####################\n"
                     f"CSV Report updated: HK {np} Sampling Table written.\n####################\n")
        # ----------------------------------------------------------------------------------------------------------

        # Analyzing HK and collecting the results
        logging.info('Analyzing HK.\n')
        hk_results = p.Analyse_HouseKeeping()

        # Preparing tables for the report
        logging.info(f'Polarimeter {np}: Producing HK table for the report.\n')
        HK_table = p.HK_table(results=hk_results)

        # [CSV] Storing the HK results table
        csv_general = HK_table["csv"]
        # [CSV] REPORT: write HK Table in the report ---------------------------------------------------------------
        with open(f'{csv_output_dir}/HK_Report_{start_datetime}__{end_datetime}.csv',
                  'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(csv_general)
        logging.info(f"####################\n"
                     f"CSV Report updated: HK {np} Table written.\n####################\n")
        # ----------------------------------------------------------------------------------------------------------

        # Plots of the Bias HK (Tensions and Currents) and of the Offsets
        logging.info(f'Polarimeter {np}: Plotting Bias HK and Offsets.\n')
        for hk_kind in ["I", "V", "O"]:
            p.Plot_Housekeeping(hk_kind=hk_kind, show=False)

        # ----------------------------------------------------------------------------------------------------------
        # [MD] REPORT HK
        # ----------------------------------------------------------------------------------------------------------
        logging.info(f"\nOnce ready, I will put the HK report into: {output_report_dir}.\n")

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
        # --------------------------------------------------------------------------------------------------------------

        ################################################################################################################
        # CORRELATION Plots and Matrices: HK
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

            # Produce all correlation plots and matrix using all the combinations
            for d1, t1, n1, u1, d2, t2, n2, u2 in possible_combos:

                # --------------------------------------------------------------------------------------------------
                # Correlation Plot
                # --------------------------------------------------------------------------------------------------
                if corr_plot:
                    logging.warning(
                        f'---------------------------------------------------------------------------------'
                        f'\nPolarimeter {np}: Correlation plot with threshold {corr_t}. '
                        f'\n{n1} - {n2}.\n')
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
                        f'\nPolarimeter {np}: Correlation matrix with threshold {corr_t}. '
                        f'\n{n1} - {n2}.\n')
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
                with open(f'{csv_output_dir}/HK_Report_{start_datetime}__{end_datetime}.csv',
                          'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerows(csv_general)
                logging.info(f"####################\n"
                             f"CSV Report updated: {np} correlations {n1} - {n2}.\n####################\n")
                # --------------------------------------------------------------------------------------------------

        # Updating the bool first_report to False at the end of the first for cycle: from now on the info are appended
        first_report = False

    # ------------------------------------------------------------------------------------------------------
    # [MD] REPORT WARNINGS
    # ------------------------------------------------------------------------------------------------------
    # Updating the report_data dict for the warning report
    report_data.update({"t_warn": t_warn,
                        "sampling_warn": sampling_warn,
                        "corr_warn": corr_warn
                        })

    # Getting instructions to create the head of the report
    template_w = env.get_template('report_warnings.txt')

    # Report generation
    filename = Path(f"{output_report_dir}/2_report_tot_warnings.md")
    with open(filename, 'w') as outf:
        outf.write(template_w.render(report_data))

    return
