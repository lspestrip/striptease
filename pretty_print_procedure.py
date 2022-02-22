#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
import json
from argparse import ArgumentParser
from pathlib import Path
from typing import List, Any, Set

from rich.console import Console
from rich.table import Table


TAG_STYLES = {
    "tag_start": "bright_cyan",
    "tag_stop": "bright_black",
    "log": "green",
    "command": "white",
    "wait": "bright_blue",
}


def pretty_print_procedure(
    procedure: List[Any],
    file_name: str,
    console: Console,
    first_command_idx: int,
    types=Set[str],
):
    table = Table(title=file_name, show_header=True, show_footer=True)
    table.add_column(header="#", footer="#", justify="right")
    table.add_column(header="Type", footer="Type")
    table.add_column(header="Description", footer="Description")
    table.add_column(header="Board", footer="Board")
    table.add_column(header="Pol", footer="Pol")
    table.add_column(header="Value", footer="Value")

    for idx, command in enumerate(procedure):
        kind = command["kind"]

        params = command["command"] if "command" in command else None

        # Build up a useful description for the command
        data = ""
        description = ""
        if kind == "log":
            description = params["message"]
        elif kind == "tag":
            description = params["tag"]
        elif kind == "command":
            data = params["data"]
            if len(data) == 1:
                data = data[0]
            data = str(data)

            description = "{method} {base_addr}".format(
                method=params["method"],
                base_addr=params["base_addr"],
            )
        elif kind == "wait":
            description = f'{command["command"]["wait_time_s"]} s'

        # Be more explicit about the kind of command if it is a tag
        if kind == "tag":
            if params["type"] == "START":
                kind = "tag_start"
            else:
                kind = "tag_stop"

        if not (kind in types):
            continue

        table.add_row(
            str(idx + first_command_idx),
            kind,
            description,
            params.get("board", "–"),
            params.get("pol", "–"),
            data,
            style=TAG_STYLES[kind],
        )

    console.print(table)


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "--interactive",
        "-i",
        default=None,
        action="store_true",
        help="""
        The program usually detects if the output is being redirected
        and disables colors accordingly. Use this flag to force colors
        (useful if you are piping the output through a color-aware
        pager like 'less' with the option '--raw').""",
    )
    parser.add_argument(
        "--types",
        "-t",
        default="command,log,tag_start,tag_stop,wait",
        metavar="LIST",
        help="""Types of commands to be included in the output table,
        specified as a set of strings separated by a comma. Valid
        types are "command", "log", "tag_start", "tag_stop", and
        "wait"; the default is to include all the four types in
        the output.""",
    )
    parser.add_argument(
        "--num",
        "-N",
        metavar="NUMBER",
        default=None,
        type=int,
        help="Only print the first N (if N > 0) or last -N (if N < 0) commands. Pass 0 to print everything",
    )
    parser.add_argument("file_name")

    args = parser.parse_args()

    with Path(args.file_name).open("rb") as inpf:
        procedure = json.load(inpf)

    first_command_idx = 1
    if args.num is not None:
        if args.num > 0:
            procedure = procedure[0 : args.num]
        elif args.num < 0:
            first_command_idx = len(procedure) + args.num
            procedure = procedure[args.num :]
        else:
            # The user passed --num=0, so there is nothing to print
            return

    console = Console(force_terminal=args.interactive)
    pretty_print_procedure(
        procedure=procedure,
        file_name=args.file_name,
        console=console,
        first_command_idx=first_command_idx,
        types=set(args.types.split(",")),
    )


if __name__ == "__main__":
    main()
