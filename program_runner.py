#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from argparse import ArgumentParser
import json
import time
import sys

from striptease import StripConnection

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

DEFAULT_WAIT_TIME_S = 0.5

def warning(msg):
    print(bcolors.WARNING + msg + bcolors.ENDC)

def okblue(msg):
    print(bcolors.OKBLUE + msg + bcolors.ENDC)

def okgreen(msg):
    print(bcolors.OKGREEN + msg + bcolors.ENDC)

def main():
    parser = ArgumentParser(description="Run a STRIP test procedure")
    parser.add_argument("--wait-time", metavar="SECONDS", type=float, default=DEFAULT_WAIT_TIME_S,
            help=f"Specify the amount of time to wait before running the next command. Default is {DEFAULT_WAIT_TIME_S}")
    parser.add_argument("json_files", metavar="JSON_FILE", type=str, nargs="*",
            help="Name of the JSON files containing the test procedures. More "
            "than one file can be provided. If no files are provided, the JSON record "
            "will be read from the terminal.")

    args = parser.parse_args()
    if len(args.json_files) == 0:
        commands = json.load(sys.stdin)
    else:
        commands = []
        for cur_file in args.json_files:
            commands += json.load(cur_file)

    print(f"{len(commands)} commands ready to be executed, let's go!")
    print("Going to establish a connection with the server…")
    conn = StripConnection()
    conn.login()
    print("…connection established")

    indent_level = 0
    for cur_command in commands:
        cmddict = cur_command["command"]
        color = ""
        
        if cur_command["kind"] == "tag":
            color = bcolors.OKGREEN
            if cur_command["command"]["type"] == "START":
                command_descr = f"start of tag {cmddict['tag']}"
                indent_level += 4
            else:
                command_descr = f"end of tag {cmddict['tag']}"
                indent_level -= 4
        elif cur_command["kind"] == "log":
            color = bcolors.OKBLUE
            command_descr = f"log message '{cmddict['message']}' ({cmddict['level']})"
        
        print(color + " " * indent_level + f"{cur_command['path']}: {command_descr}" + bcolors.ENDC)

        if cur_command["kind"] != "wait":
            conn.post(cur_command["path"], message=cmddict)
            time.sleep(args.wait_time)
        else:
            time.sleep(cmddict["wait_time_s"])

    conn.logout()


if __name__ == "__main__":
    main()
