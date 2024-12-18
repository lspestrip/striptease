#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# This file contains the new LSPE-Strip official pipeline for functional verification.
# It includes different analysis modalities: total analysis, housekeeping analysis and thermal analysis

# July 23rd 2023, Brescia (Italy) - December 5th 2024, Bologna (Italy)

# Libraries & Modules
import argparse
import logging
import os
import shutil
import sys

from astropy.time import Time
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from rich.logging import RichHandler

# MyLibraries & MyModules
sys.path.append('pipeline/')
import f_strip as fz
import stripop_tot as strip_a
import stripop_pol_hk as strip_b
import stripop_thermal_hk as strip_c


def main():
    """
        Pipeline for the functional verification of the LSPE-Strip instrument.
        This pipeline can be used in three different operative modalities:

        A) "tot"
        -> Performs the analysis of one or more polarimeters producing a complete report.
        The analysis can include plots of: Even-Odd Output, Scientific Data, FFT, correlation and Matrices.
        The reports produced include also info about the state of the housekeeping parameters and the thermal sensors.

            Parameters:

        - **path_file** (``str``): location of the data file and hdf5 file index (without the name of the file)
        - **start_datetime** (``str``): start time
        - **end_datetime** (``str``): end time
        - **name_pol** (``str``): name of the polarimeter. If more than one write them spaced into ' '.

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

        B) "pol_hk"
        -> Performs only the analysis of the Housekeeping parameters of the polarimeter(s) provided.

            Parameters:

        - **path_file** (``str``): location of the data file, it is indeed the location of the hdf5 file's index
        - **start_datetime** (``str``): start time
        - **end_datetime** (``str``): end time
        - **name_pol** (``str``): name of the polarimeter. If more than one write them spaced into ' '.

            Other Flags:

        - **corr_plot** (``bool``): If true, compute the correlation plot of the HK.
        - **corr_mat** (``bool``): If true, compute the correlation matrices of the HK.
        - **corr_t** (``float``): LimSup for the corr value between two dataset: if overcome a warning is produced.
        - **hk_sam_exp_med** (``dict``): contains the exp sampling delta between two consecutive timestamps of HK
        - **hk_sam_tolerance** (``dict``): contains the acceptance sampling tolerances of the hk parameters: I,V,O
        - **output_report_dir** (`str`): Path from the pipeline dir to the dir that contains the reports of the analysis
        - **output_plot_dir** (`str`): Path from the pipeline dir to the dir that contains the plots of the analysis.
        - **report_to_plot** (`str`): Path from the Report dir to the dir that contain the plots of the analysis.

        C) "thermal_hk"
        -> Performs only the analysis of the thermal sensors of Strip.

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

        Final Note: During the spectral analysis the average of all periodograms is computed to produce the spectrogram.
        Changing the nperseg parameter allow to reach lower frequencies in the FFT plot:
        in particular, the limInf of the x-axis is fs/nperseg.

    """
    # Use the module logging to produce nice messages on the shell
    logging.basicConfig(level="INFO", format='%(message)s',
                        datefmt="[%X]", handlers=[RichHandler()])

    # Command Line used to start the pipeline
    command_line = " ".join(sys.argv)

    # Create the top-level argument parser by instantiating ArgumentParser
    # Note: the description is optional. It will appear if the help (-h) is required from the command line
    parser = argparse.ArgumentParser(prog='PROGRAM', description="Official pipeline for the functional verification "
                                                                 "of the LSPE-Strip instrument.\n"
                                                                 "Please choose one of the modalities A, B or C. "
                                                                 "Remember to provide all the positional arguments.")

    ####################################################################################################################
    # Create a COMMON ARGUMENT parser for shared arguments
    common_parser = argparse.ArgumentParser(add_help=False)
    # path_file
    common_parser.add_argument("path_file", action='store', type=str,
                               help='- Location of the hdf5 file index (database)')
    # start_datetime
    common_parser.add_argument("start_datetime", action='store', type=str,
                               help='- Starting datetime of the analysis. Format: "YYYY-MM-DD hh:mm:ss".')
    # end_datetime
    common_parser.add_argument("end_datetime", action='store', type=str,
                               help='- Ending datetime of the analysis. Format: "YYYY-MM-DD hh:mm:ss".')

    # TOML information -------------------------------------------------------------------------------------------------
    # toml_file_path
    common_parser.add_argument("--toml_file_path", "-toml",
                               action='store', type=str,
                               help='Complete path of the TOML file used to start the pipeline')
    # Sampling Parameters ----------------------------------------------------------------------------------------------
    # Housekeeping Sampling Expected Median
    common_parser.add_argument('--hk_sam_exp_med', '-hk_sem',
                               type=lambda x: [float(val) for val in x.split(',')], default=[1.4, 1.4, 60., 60., 60.],
                               help='Contains the exp sampling delta between two consecutive timestamps of the hk. '
                                    '(default: %(default)s)', metavar='')
    # Housekeeping Sampling Tolerance
    common_parser.add_argument('--hk_sam_tolerance', '-hk_st',
                               type=lambda x: [float(val) for val in x.split(',')], default=[0.1, 0.1, 0.5, 0.5, 0.5],
                               help='Contains the acceptance sampling tolerances of the hk parameters: I,V,O. '
                                    '(default: %(default)s)', metavar='')
    # Thermal Sensors Sampling Expected Median
    common_parser.add_argument('--ts_sam_exp_med', '-ts_sem', type=float, default=60.,
                               help='the exp sampling delta between two consecutive timestamps of the Thermal Sensors. '
                                    '(default: %(default)s)', metavar='')
    # Thermal Sensors Sampling Tolerance
    common_parser.add_argument('--ts_sam_tolerance', '-ts_st', type=float, default=1.,
                               help='the acceptance sampling tolerances of the Thermal Sensors (default: %(default)s).',
                               metavar='')
    # Spikes -----------------------------------------------------------------------------------------------------------
    # Spikes Data
    common_parser.add_argument('--spike_data', '-sd', action="store_true", default=False,
                               help='If true, the code will look for spikes in Sci-data and TS measures')
    # Spikes FFT
    common_parser.add_argument('--spike_fft', '-sf', action="store_true", default=False,
                               help='If true, the code will look for spikes in FFT of Sci-data and TS measures')

    # Correlation Parameters -------------------------------------------------------------------------------------------
    # Correlation Plot
    common_parser.add_argument('--corr_plot', '-cp', action="store_true", default=False,
                               help='If true, the code will compute the correlation plots '
                                    'of the even-odd and scientific data.')
    # Correlation Matrices
    common_parser.add_argument('--corr_mat', '-cm', action="store_true", default=False,
                               help='If true, the code will compute the correlation matrices '
                                    'of the even-odd and scientific data.')
    # Correlation Threshold
    common_parser.add_argument('--corr_t', '-ct', type=float, default=0.4,
                               help='Floating point number used as lim sup for the corr value between two dataset: '
                                    'if the corr value is higher than the threshold, a warning is produced and stored. '
                                    '(default: %(default)s).', metavar='')
    # Cross Correlation
    common_parser.add_argument('--cross_corr', '-cc', action="store_true", default=False,
                               help='If true, compute the 55x55 corr matrices between the exits of all polarimeters.')

    # Output parameters ------------------------------------------------------------------------------------------------
    # Output directory of the plots
    common_parser.add_argument('--output_plot_dir', '-opd', type=str, default='../RESULTS/PIPELINE',
                               help='Path of the dir that will contain the plots of the analysis '
                                    'starting from the dir striptease where the pipeline is run'
                                    '(default: %(default)s).', metavar='')
    # Output directory of the reports
    common_parser.add_argument('--output_report_dir', '-ord', type=str,
                               default='../RESULTS/PIPELINE/Reports',
                               help='Path of the dir that will contain the reports with the results of the analysis '
                                    'starting from the dir striptease where the pipeline is run'
                                    '(default: %(default)s).', metavar='')

    # Report to plot path
    common_parser.add_argument('--report_to_plot', '-r2p', type=str, default='../..',
                               help='Path of the dir that will contain the plots of the analysis '
                                    'starting from the specific sub-directory contained into "Reports", '
                                    'the dir that contains the md reports '
                                    '(default: %(default)s).', metavar='')

    ####################################################################################################################
    # Create subparsers
    subparsers = parser.add_subparsers(help='Operation modalities of the pipeline.', dest="subcommand")

    ####################################################################################################################
    # MODALITY A: TOT
    # Analyzes all the polarimeters provided by the user
    ####################################################################################################################

    # Create the parser for the command A: "tot"
    parser_A = subparsers.add_parser("tot", parents=[common_parser],
                                     help="A) Analyzes all the polarimeters provided.")

    # Positional Arguments (mandatory)
    # name_pol
    parser_A.add_argument('name_pol', type=str, help="- str containing the name(s) of the polarimeter(s). "
                                                     "Write \'all\' to perform the complete analysis")

    # Flags (optional)
    # Thermal Sensors
    parser_A.add_argument('--thermal_sensors', '-ts', action="store_true", default=False,
                          help='If true, the code will analyze the Thermal Sensors of Strip'
                               '(default: %(default)s).')
    # Housekeeping Parameters
    parser_A.add_argument('--housekeeping', '-hk', action="store_true", default=False,
                          help='If true, the code will analyze the Housekeeping parameters of the Polarimeters '
                               '(default: %(default)s).')
    # Even Odd All
    parser_A.add_argument('--even_odd_all', '-eoa', type=str, default='EOA',
                          help='Choose which data analyze by adding a letter in the string: '
                               'even samples (E), odd samples (O) or all samples (A) (default: %(default)s).',
                          metavar='')
    # Scientific Data
    parser_A.add_argument('--scientific', '-sci', action="store_true", default=False,
                          help='If true, compute the double demodulation and analyze the scientific data '
                               '(default: %(default)s).')
    # Rms
    parser_A.add_argument('--rms', '-rms', action="store_true", default=False,
                          help='If true, compute the rms on the scientific output and data '
                               '(default: %(default)s).')
    # Scientific Output Sampling Tolerance
    parser_A.add_argument('--sam_tolerance', '-st', type=float, default=0.005,
                          help='The acceptance sampling tolerances of the Scientific Output of Strip '
                               '(default: %(default)s).', metavar='')
    # Smoothing length
    parser_A.add_argument('--smooth', '-sm', type=int, default=1,
                          help='Smoothing length used to flatter the data. smooth=1 equals no smooth '
                               '(default: %(default)s).', metavar='')
    # Rolling Window
    parser_A.add_argument('--window', '-w', type=int, default=2,
                          help='Integer number used to convert the array of the data into a matrix '
                               'with a number "window" of elements per row and then calculate the RMS on every row '
                               '(default: %(default)s).', metavar='')
    # FFT
    parser_A.add_argument('--fourier', '-fft', action="store_true",
                          help='If true, the code will compute the power spectra of the scientific data.')

    # noise level
    parser_A.add_argument('--noise_level', '-nl', action="store_true",
                          help='If true, the code will compute the White Noise level and 1/f noise '
                               'of the FFT of scientific data.')

    # nperseg FFT data
    parser_A.add_argument('--nperseg', '-nps', type=int, default=256,
                          help='int value that defines the number of elements of the array of scientific data'
                               'on which the fft is calculated (default: %(default)s).', metavar='')
    # nperseg FFT Thermal
    parser_A.add_argument('--nperseg_thermal', '-nps_th', type=int, default=256,
                          help='int value that defines the number of elements of the array of thermal measures'
                               'on which the fft is calculated (default: %(default)s).', metavar='')

    ####################################################################################################################
    # MODALITY B: POL_HK
    # Analyzes the housekeeping parameters of the polarimeters provided by the user.
    ####################################################################################################################

    # Create the parser for the command B: "pol_hk"
    parser_B = subparsers.add_parser('pol_hk', parents=[common_parser],
                                     help="B) Analyzes the housekeeping parameters of the polarimeters provided.")

    # Positional Argument (mandatory)
    # name_pol
    parser_B.add_argument('name_pol', type=str, help="- str containing the name(s) of the polarimeter(s). "
                                                     "Write \'all\' to perform the complete analysis")

    ####################################################################################################################
    # MODALITY C: THERMAL_HK
    # Analyzes the thermal sensors of LSPE-Strip.
    ####################################################################################################################

    # Create the parser for the command C: "thermal_hk"
    parser_C = subparsers.add_parser('thermal_hk', parents=[common_parser],
                                     help="C) Analyzes the Thermal Sensors of LSPE-Strip.")

    # Flags (optional)
    # FFT
    parser_C.add_argument('--fourier', '-fft', action="store_true",
                          help='If true, the code will compute the power spectra of the thermal measures.')
    # nperseg FFT Thermal
    parser_C.add_argument('--nperseg_thermal', '-nps_th', type=int, default=256,
                          help='int value that defines the number of elements of the array of thermal measures'
                               'on which the fft is calculated (default: %(default)s).', metavar='')
    # Status
    parser_C.add_argument('--status', '-stat', type=int, default=2, choices=[0, 1, 2],
                          help='int value that defines the status of the multiplexer of the TS to analyze: 0 or 1. '
                               'If it is set on 2, both states will be analyzed (default: %(default)s).')

    ####################################################################################################################
    # Call .parse_args() on the parser to get the Namespace object that contains all the user’s arguments.
    args = parser.parse_args()
    logging.info(args)

    ####################################################################################################################
    ####################################################################################################################
    # CHECKS OF THE PARAMETERS
    ####################################################################################################################
    ####################################################################################################################

    # TOML File --------------------------------------------------------------------------------------------------------
    # Check if the toml file provided by the user exists.

    # Initialize a bool to True -> We are using a toml file to run the pipeline
    toml_usage = True
    try:
        Path(args.toml_file_path)

    except TypeError:
        logging.warning('Running the code from the command line without TOML files.')
        # We are not using the toml file to run the pipeline
        toml_usage = False
        pass

    except AttributeError:
        logging.error('Modality not selected. Type -h for help!')
        raise SystemExit(1)

    if toml_usage:
        if not Path(args.toml_file_path).exists():
            logging.error(f'The target directory {args.toml_file_path} does not exist. '
                          f'Please select a real location of the toml file to start the pipeline.\n\n')
            raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # Path of the Data Test directory ----------------------------------------------------------------------------------
    # Check if the dir provided by the user exists.
    try:
        Path(args.path_file)
    except AttributeError:
        logging.error('Modality not selected. Type -h for help!\n\n')
        raise SystemExit(1)

    except ValueError:
        logging.error(f'The parameter {args.path_file} should be a string. Please check it again.\n'
                      f'Type -h for help!\n\n')
        raise SystemExit(1)

    if not Path(args.path_file).exists():
        logging.error(f'The target directory {args.path_file} does not exist or does not contain the hdf5 file index.\n'
                      f'Please select a real location of the hdf5 file index.\n'
                      'Note: Do not add the name of the parameter: just write the path!\n'
                      'Also: quotation marks are needed in the TOML file.\n\n')
        raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # Datetime ---------------------------------------------------------------------------------------------------------
    # Check on the format of datatime objects: start_datetime & end_datetime
    if not fz.datetime_check(args.start_datetime):
        logging.error('start_datetime: wrong datetime format.\n\n')
        raise SystemExit(1)
    if not fz.datetime_check(args.end_datetime):
        logging.error('end_datetime: wrong datetime format.\n\n')
        raise SystemExit(1)

    # Consequentiality of the datetime
    if args.end_datetime < args.start_datetime:
        logging.error('end_datetime is before than start_datetime: wrong datetime values.\n\n')
        raise SystemExit(1)

    # Same datetime
    if args.end_datetime == args.start_datetime:
        logging.error('end_datetime is equal to start_datetime: wrong datetime values.\n\n')
        raise SystemExit(1)

    # Check the minimal duration of the analysis: must be longer than 2 minutes to avoid crashes in the processing
    if (Time(args.end_datetime) - Time(args.start_datetime)).sec < 120:
        logging.error("The duration of the analysis is too short: please make sure that the difference between "
                      "start_datetime and end_datetime is bigger than 120 seconds.\n"
                      "This will avoid crashes during the analysis.\n\n")
        raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # Name Pol ---------------------------------------------------------------------------------------------------------
    # Check the names of the polarimeters
    if args.subcommand == "tot" or args.subcommand == "pol_hk":

        # Case with all the polarimeter
        if args.name_pol == "all":
            # Assign all pol names to the corresponding arg
            args.name_pol = ("B0 B1 B2 B3 B4 B5 B6 "
                             "I0 I1 I2 I3 I4 I5 I6 "
                             "G0 G1 G2 G3 G4 G5 G6 "
                             "O0 O1 O2 O3 O4 O5 O6 "
                             "R0 R1 R2 R3 R4 R5 R6 "
                             "V0 V1 V2 V3 V4 V5 V6 "
                             "W1 W2 W3 W4 W5 W6 "
                             "Y0 Y1 Y2 Y3 Y4 Y5 Y6")

        # Create a list of polarimeters names
        name_pol = args.name_pol.split()
        # Check the names of the polarimeters provided
        if not fz.name_check(name_pol):
            logging.error('The names of the polarimeters provided are not valid. Please check the parameter name_pol. '
                          '\nThe names must be written as follows: \'B0 B1\'.\n'
                          'If you want to analyze all of them write \'all\'.\n\n')
            raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    ####################################################################################################################
    # PARAMETERS OF THE TOTAL ANALYSIS
    if args.subcommand == "tot":

        # Thermal Sensors ----------------------------------------------------------------------------------------------
        # Check if the parameter is a bool
        if not isinstance(args.thermal_sensors, bool):
            logging.error("The parameter thermal_sensors must be a bool. Please check it again.\n\n")
            raise SystemExit(1)
        # --------------------------------------------------------------------------------------------------------------

        # Housekeeping Parameters --------------------------------------------------------------------------------------
        # Check if the parameter is a bool
        if not isinstance(args.housekeeping, bool):
            logging.error("The parameter housekeeping must be a bool. Please check it again.\n\n")
            raise SystemExit(1)
        # --------------------------------------------------------------------------------------------------------------

        # Scientific ---------------------------------------------------------------------------------------------------
        # Check if the parameter is a bool
        if not isinstance(args.scientific, bool):
            logging.error("The parameter scientific must be a bool. Please check it again.\n\n")
            raise SystemExit(1)
        # --------------------------------------------------------------------------------------------------------------

        # EOA string ---------------------------------------------------------------------------------------------------
        # Check if the str is a combination of the E, O, A letters
        # Create a set of E,O,A
        args.even_odd_all = set(str(args.even_odd_all).upper())
        if not args.even_odd_all.issubset({"E", "O", "A"}):
            logging.error('Wrong Data Name: please choose between the options: E, O, A, EO, EA, OA, EOA.\n\n')
            raise SystemExit(1)
        # --------------------------------------------------------------------------------------------------------------

        # Root Mean Square RMS -----------------------------------------------------------------------------------------
        # Check if the parameter is a bool
        if not isinstance(args.rms, bool):
            logging.error("The parameter rms must be a bool. Please check it again.\n\n")
            raise SystemExit(1)
        # --------------------------------------------------------------------------------------------------------------

        # Smoothing length ---------------------------------------------------------------------------------------------
        # Check if the parameter is an int
        if not isinstance(args.smooth, int):
            logging.error("The parameter smooth must be an int. Please check it again.\n\n")
            raise SystemExit(1)
        # --------------------------------------------------------------------------------------------------------------

        # Mobile Window length -----------------------------------------------------------------------------------------
        # Check if the parameter is an int
        if not isinstance(args.window, int):
            logging.error("The parameter window must be an int. Please check it again.\n\n")
            raise SystemExit(1)
        # --------------------------------------------------------------------------------------------------------------
    ####################################################################################################################

    # FFT - SPECTRAL ANALYSIS
    # Fast Fourier Transformed FFT -------------------------------------------------------------------------------------
    # Check if the parameter is a bool
    if args.subcommand == "tot" or args.subcommand == "thermal_hk":
        if not isinstance(args.fourier, bool):
            logging.error("The parameter fourier must be a bool. Please check it again.\n\n")
            raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # nperseg (Number of points per segment) ---------------------------------------------------------------------------
    # Check if the parameter is an int
    if args.subcommand == "tot":
        if not isinstance(args.nperseg, int):
            logging.error("The parameter nperseg must be an int. Please check it again.\n\n")
            raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # nperseg_thermal (Number of points per segment of TS measures) ----------------------------------------------------
    # Check if the parameter is an int
    if args.subcommand == "tot" or args.subcommand == "thermal_hk":
        if not isinstance(args.nperseg_thermal, int):
            logging.error("The parameter nperseg_thermal must be an int. Please check it again.\n\n")
            raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # SPIKES
    if args.subcommand == "tot" or args.subcommand == "thermal_hk":
        # Spike Data -------------------------------------------------------------------------------------------------
        # Check if the parameter is a bool
        if not isinstance(args.spike_data, bool):
            logging.error("The parameter spike_data must be a bool. Please check it again.\n\n")
            raise SystemExit(1)
        # --------------------------------------------------------------------------------------------------------------

        # Spike FFT ----------------------------------------------------------------------------------------------------
        # Check if the parameter is a bool
        if not isinstance(args.spike_fft, bool):
            logging.error("The parameter spike_fft must be a bool. Please check it again.\n\n")
            raise SystemExit(1)
        # ------------------------------------------------------------------------------------------------------------------

    # Data Sampling Tolerance ------------------------------------------------------------------------------------------
    # Check if the parameter is a float
    if args.subcommand == "tot":
        try:
            args.sam_tolerance = float(args.sam_tolerance)
        except ValueError:
            logging.error("The parameter sam_tolerance must be a float. Please check it again.\n\n")
            raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # Housekeeping Sampling Expected Median ----------------------------------------------------------------------------
    # Check if the parameter is a float
    if args.subcommand == "tot" or args.subcommand == "pol_hk":
        for i in range(len(args.hk_sam_exp_med)):
            try:
                args.hk_sam_exp_med[i] = float(args.hk_sam_exp_med[i])
            except ValueError:
                logging.error("The 3 parameters of hk_sam_exp_med must be float. Please check them again.\n\n")
                raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # Housekeeping Sampling Tolerance ----------------------------------------------------------------------------------
    # Check if the parameter is a float
    if args.subcommand == "tot" or args.subcommand == "pol_hk":
        for i in range(len(args.hk_sam_tolerance)):
            try:
                args.hk_sam_tolerance[i] = float(args.hk_sam_tolerance[i])
            except ValueError:
                logging.error("The 3 parameters of hk_sam_tolerance must be float. Please check them again.\n\n")
                raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # Store the values into a dict
    hk_sam_exp_med = {"I": args.hk_sam_exp_med[0], "V": args.hk_sam_exp_med[1],
                      "O": args.hk_sam_exp_med[2], "M": args.hk_sam_exp_med[3],
                      "P": args.hk_sam_exp_med[4]}
    hk_sam_tolerance = {"I": args.hk_sam_tolerance[0], "V": args.hk_sam_tolerance[1],
                        "O": args.hk_sam_tolerance[2], "M": args.hk_sam_tolerance[3],
                        "P": args.hk_sam_tolerance[4]}

    # Thermal Sensors Sampling Expected Median -------------------------------------------------------------------------
    # Check if the parameter is a float
    if args.subcommand == "tot" or args.subcommand == "thermal_hk":
        try:
            args.ts_sam_exp_med = float(args.ts_sam_exp_med)
        except ValueError:
            logging.error("The parameter ts_sam_exp_med must be a float. Please check it again.\n\n")
            raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # Thermal Sensors Sampling Tolerance -------------------------------------------------------------------------------
    # Check if the parameter is a float
    if args.subcommand == "tot" or args.subcommand == "thermal_hk":
        try:
            args.ts_sam_tolerance = float(args.ts_sam_tolerance)
        except ValueError:
            logging.error("The parameter ts_sam_tolerance must be a float. Please check it again.\n\n")
            raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    ####################################################################################################################
    # COMMON PARAMETERS

    # Correlation Plot -------------------------------------------------------------------------------------------------
    # Check if the parameter is a bool
    if not isinstance(args.corr_plot, bool):
        logging.error("The parameter corr_plot must be a bool. Please check it again.\n\n")
        raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # Correlation Matrix -----------------------------------------------------------------------------------------------
    # Check if the parameter is a bool
    if not isinstance(args.corr_mat, bool):
        logging.error("The parameter corr_mat must be a bool. Please check it again.\n\n")
        raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # Correlation Threshold --------------------------------------------------------------------------------------------
    # Check if the parameter is a float
    try:
        args.corr_t = float(args.corr_t)
    except ValueError:
        logging.error("The parameter corr_t must be a float. Please check it again.\n\n")
        raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # Cross Correlation Matrix -----------------------------------------------------------------------------------------
    # Check if the parameter is a bool
    if args.subcommand == "tot":
        if not isinstance(args.cross_corr, bool):
            logging.error("The parameter cross_corr must be a bool. Please check it again.\n\n")
            raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # Output Plot Directory --------------------------------------------------------------------------------------------
    # Check if the parameter is a string
    if not isinstance(args.output_plot_dir, str):
        logging.error("The parameter output_plot_dir must be a str. Please check it again.\n\n")
        raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # Output Report Directory ------------------------------------------------------------------------------------------
    # Check if the parameter is a string
    if not isinstance(args.output_report_dir, str):
        logging.error("The parameter output_report_dir must be a str. Please check it again.\n\n")
        raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    # Report to Plot Directory -----------------------------------------------------------------------------------------
    # Check if the parameter is a string
    if not isinstance(args.report_to_plot, str):
        logging.error("The parameter report_to_plot must be a str. Please check it again.\n\n")
        raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    ####################################################################################################################
    # PARAMETERS OF THE THERMAL SENSORS

    # Status -----------------------------------------------------------------------------------------------------------
    if args.subcommand == "thermal_hk":
        if args.status not in ([0, 1, 2]):
            logging.error('Invalid status value. Please choose between the values 0 and 1 for a single analysis. '
                          'Choose the value 2 to have both.\n\n')
            raise SystemExit(1)
    # ------------------------------------------------------------------------------------------------------------------

    ####################################################################################################################
    # Reports Requirements

    logging.info('\nLoading dir and templates information...')

    # Directory where to save all the reports of a given analysis
    date_dir = fz.dir_format(f"{args.start_datetime}__{args.end_datetime}")

    # Creating the correct path for the PLOT dir: adding the date_dir

    # 1) From the striptease directory
    args.output_plot_dir = f"{args.output_plot_dir}/{date_dir}"
    # Check if the dir exists. If not, it will be created.
    Path(args.output_plot_dir).mkdir(parents=True, exist_ok=True)

    # 2) From the Report directory
    args.report_to_plot = f"{args.report_to_plot}/{date_dir}"

    # Creating the correct path for the REPORT dir: adding the date_dir
    args.output_report_dir = f"{args.output_report_dir}/{date_dir}"
    # Check if the dir exists. If not, it will be created.
    Path(args.output_report_dir).mkdir(parents=True, exist_ok=True)

    ####################################################################################################################
    # TOML Information
    # Saving the TOML file used to start the pipeline in the report directory

    if toml_usage:
        # Extract the TOML file name from the input path
        toml_file_name = os.path.basename(args.toml_file_path)

        # Construct the output file path by joining the output directory with the file name
        output_file_path = os.path.join(args.output_report_dir, toml_file_name)

        try:
            # Copy the file in the output dir
            shutil.copy(args.toml_file_path, output_file_path)
            logging.info(f"TOML file copied successfully to {output_file_path}\n")
        except FileNotFoundError:
            logging.error(f"The file {args.toml_file_path} does not exist.\n")
        except Exception as e:
            logging.error(f"An error occurred: {e}\n")

    ####################################################################################################################
    # Operations: A-B-C
    if args.subcommand == "tot":
        logging.info('The total analysis is beginning... Take a seat!')
        # Total Analysis Operation
        strip_a.tot(path_file=args.path_file, start_datetime=args.start_datetime, end_datetime=args.end_datetime,
                    thermal_sensors=args.thermal_sensors, housekeeping=args.housekeeping,
                    sam_tolerance=args.sam_tolerance,
                    hk_sam_exp_med=hk_sam_exp_med, hk_sam_tolerance=hk_sam_tolerance,
                    ts_sam_exp_med=args.ts_sam_exp_med, ts_sam_tolerance=args.ts_sam_tolerance,
                    name_pol=args.name_pol, eoa=args.even_odd_all, scientific=args.scientific, rms=args.rms,
                    smooth=args.smooth, window=args.window,
                    fft=args.fourier, noise_level=args.noise_level,
                    nperseg=args.nperseg, nperseg_thermal=args.nperseg_thermal,
                    spike_data=args.spike_data, spike_fft=args.spike_fft,
                    corr_plot=args.corr_plot, corr_mat=args.corr_mat, corr_t=args.corr_t, cross_corr=args.cross_corr,
                    output_plot_dir=args.output_plot_dir, output_report_dir=args.output_report_dir,
                    report_to_plot=args.report_to_plot)

    elif args.subcommand == "pol_hk":
        logging.info('The housekeeping analysis is beginning...')
        # Housekeeping Analysis Operation
        strip_b.pol_hk(path_file=args.path_file, start_datetime=args.start_datetime, end_datetime=args.end_datetime,
                       name_pol=args.name_pol,
                       hk_sam_exp_med=hk_sam_exp_med, hk_sam_tolerance=hk_sam_tolerance,
                       corr_plot=args.corr_plot, corr_mat=args.corr_mat, corr_t=args.corr_t,
                       output_plot_dir=args.output_plot_dir, output_report_dir=args.output_report_dir,
                       report_to_plot=args.report_to_plot
                       )

    elif args.subcommand == "thermal_hk":
        # Thermal Sensors Analysis Operation
        logging.info('The thermal analysis is beginning...')

        # If status is not specified, the analysis is done on both the states of the multiplexer
        if args.status == 2:
            for status in [0, 1]:
                strip_c.thermal_hk(path_file=args.path_file,
                                   start_datetime=args.start_datetime, end_datetime=args.end_datetime,
                                   status=status, fft=args.fourier, nperseg_thermal=args.nperseg_thermal,
                                   ts_sam_exp_med=args.ts_sam_exp_med, ts_sam_tolerance=args.ts_sam_tolerance,
                                   spike_data=args.spike_data, spike_fft=args.spike_fft,
                                   corr_plot=args.corr_plot, corr_mat=args.corr_mat, corr_t=args.corr_t,
                                   output_plot_dir=args.output_plot_dir, output_report_dir=args.output_report_dir,
                                   report_to_plot=args.report_to_plot)
        else:
            strip_c.thermal_hk(path_file=args.path_file,
                               start_datetime=args.start_datetime, end_datetime=args.end_datetime,
                               status=args.status, fft=args.fourier, nperseg_thermal=args.nperseg_thermal,
                               ts_sam_exp_med=args.ts_sam_exp_med, ts_sam_tolerance=args.ts_sam_tolerance,
                               spike_data=args.spike_data, spike_fft=args.spike_fft,
                               corr_plot=args.corr_plot, corr_mat=args.corr_mat, corr_t=args.corr_t,
                               output_plot_dir=args.output_plot_dir, output_report_dir=args.output_report_dir,
                               report_to_plot=args.report_to_plot)

    ####################################################################################################################
    # REPORT Production
    ####################################################################################################################
    logging.info(f"\nI am putting the header report into: {args.output_report_dir}.")

    # Convert the Namespace object to a dictionary
    args_dict = vars(args)

    # Dictionary with the data used to create the report
    header_report_data = {
        "command_line": command_line,
        "path_file": args.path_file,
        "analysis_date": str(f"{args.start_datetime} - {args.end_datetime}"),
        "report_to_plot": args.report_to_plot,
        "output_report_dir": args.output_report_dir,
        "args_dict": args_dict
    }

    # root: location of the file.txt with the information to build the report
    root = "pipeline/templates/validation_templates"
    templates_dir = Path(root)

    # Creating the Jinja2 environment
    env = Environment(loader=FileSystemLoader(templates_dir))
    # Getting instructions to create the head of the report
    header_template = env.get_template('report_header.txt')

    # Report generation: header
    filename = Path(f"{args.output_report_dir}/1_report_{args.subcommand}_head.md")
    with open(filename, 'w') as outf:
        outf.write(header_template.render(header_report_data))

    # Final operations on Reports
    if args.subcommand == "tot":
        ################################################################################################################
        # MD REPORT MERGING
        ################################################################################################################
        # Write the correct name of the General Report
        report_name = fz.dir_format(f"00_Report_{args.start_datetime}__{args.end_datetime}")
        # Merge all the MD report into a single file
        logging.info(f"Merging all MD reports into: {report_name}.md\nEnjoy!\n\n")
        fz.merge_report(md_reports_path=args.output_report_dir,
                        total_report_path=f"{args.output_report_dir}/{report_name}.md")

        ################################################################################################################
        # JSON PRODUCTION
        ################################################################################################################
        logging.info(f"Converting CSV report into JSON\n")
        # Convert the CSV Report File into a JSON Report File
        fz.csv_to_json(csv_file_path=f"{args.output_report_dir}/CSV/{report_name}.csv",
                       json_file_path=f"{args.output_report_dir}/JSON/{report_name}.json")


if __name__ == "__main__":
    main()
