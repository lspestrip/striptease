#!/usr/bin/env python3

import json
import sys


def main():
    file_names = sys.argv[1:]
    for file_name in file_names:
        with open(file_name, "rt") as inpf:
            commands = json.load(inpf)

        if len(file_names) > 1:
            print(file_name)

        idx = 1
        for cur_cmd in commands:
            if cur_cmd["kind"] == "tag":
                print(f'{idx}. {cur_cmd["command"]["tag"]}')
                idx += 1


if __name__ == "__main__":
    main()
