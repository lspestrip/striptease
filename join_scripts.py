#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import sys


def main():
    if len(sys.argv) == 1:
        print("Usage: join_scripts.py JSON_FILE1...")
        sys.exit(1)

    filenames = sys.argv[1:]
    commands = []
    for curfilename in filenames:
        with open(curfilename, "rt") as inpf:
            commands += json.load(inpf)

        json.dump(commands, sys.stdout, indent=4)


if __name__ == "__main__":
    main()
