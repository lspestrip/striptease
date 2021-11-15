#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import sys
from striptease import dump_procedure_as_json


def main():
    if (len(sys.argv) < 2) or sys.argv[1] == "--help":
        print(
            """"Usage: join_scripts.py JSON_FILE1...

Example:

  join_scripts.py script1.json script2.json > joined_file.json
"""
        )

        sys.exit(1)

    filenames = sys.argv[1:]
    commands = []
    for curfilename in filenames:
        with open(curfilename, "rt") as inpf:
            commands += json.load(inpf)

    dump_procedure_as_json(sys.stdout, commands)


if __name__ == "__main__":
    main()
