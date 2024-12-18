#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# This program is used to run the new version of the pipeline for functional verification of LSPE-STRIP (2024) using
# TOML files passed by the command line

# September 29th 2023, Brescia (Italy) - March 28th 2024, Bologna (Italy)

# Libraries & Modules
import argparse
import logging
import subprocess
import toml


def load_toml_config(toml_file_path):
    """
        Load the arguments of a TOML file into a dict.

            Parameters:\n
        - **toml_file_path** (`str`): path to the TOML configuration file
    """
    try:
        # Open the TOML file to read the instructions
        with open(toml_file_path, 'r') as toml_file:
            # Loading the arguments from the toml_file
            config = toml.load(toml_file)
        return config
    # If the file is not found an empty dict is returned
    except FileNotFoundError:
        return {}


def main():
    # Create an argument parser to accept the TOML file as an argument
    parser = argparse.ArgumentParser(description='Run the official pipeline for functional verification of Strip '
                                                 'with arguments from a TOML file')
    # Add the argument config_file
    parser.add_argument('config_file', help='Path to the TOML configuration file')

    # Call .parse_args() on the parser to get the Namespace object that contains all the user’s arguments.
    args = parser.parse_args()

    # Load configuration from the specified TOML file
    config = load_toml_config(args.config_file)

    # Extract the arguments from the TOML file
    program_args = config.get('official_pipeline_args', {})

    # Build the command to call the pipeline
    command = [
        'python',  # Use the Python interpreter
        'official_pipeline.py',  # Name of the program
    ]

    # Counter for the positional arguments
    pos_arg = 0
    # Number of positional arguments
    n_pos_arg = 5

    # Add arguments from the TOML file to the command
    for key, value in program_args.items():
        # The thermal operation doesn't need argument pol_name
        if value == "thermal_hk":
            n_pos_arg = 4

        if pos_arg < n_pos_arg:
            # Positional arguments added to the command
            command.extend([f'{value}'])
            pos_arg += 1
        else:
            # Flags (need '--')
            if value == "false":
                pass
            elif value == "true":
                # Boolean flags added to the command
                command.extend(['--' + key])
            else:
                # Other flags added to the command
                command.extend(['--' + key, f"{value}"])

    # Execute the pipeline with the specified arguments
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error calling 'official_pipeline.py': {e}")


if __name__ == '__main__':
    main()
