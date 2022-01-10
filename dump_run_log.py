#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from typing import List, Any, Dict

from striptease import (
    connect_to_run_log,
    RunLogEntry,
    RUN_LOG_DATETIME_FORMAT,
    dump_procedure_as_json,
)


def entry_to_dict(entry: RunLogEntry) -> Dict[str, Any]:
    return {
        "id": entry.id,
        "start_time": entry.start_time.strftime(RUN_LOG_DATETIME_FORMAT),
        "end_time": entry.end_time.strftime(RUN_LOG_DATETIME_FORMAT),
        "duration_s": (entry.end_time - entry.start_time).total_seconds(),
        "wait_time_s": entry.wait_time_s,
        "wait_cmd_time_s": entry.wait_cmd_time_s,
        "full_path": str(entry.full_path),
        "number_of_commands": entry.number_of_commands,
    }


def print_table(entries: List[RunLogEntry], output_file):
    if not entries:
        return

    from rich.table import Table
    from rich.console import Console

    console = Console()

    table = Table()
    table.add_column("#")
    table.add_column("Start time")
    table.add_column("End time")
    table.add_column("Duration (s)")
    table.add_column("File name")
    table.add_column("# of cmds")
    table.add_column("Wait (s)")
    table.add_column("Wait command (s)")

    for entry in entries:
        table.add_row(
            str(entry.id),
            entry.start_time.strftime(RUN_LOG_DATETIME_FORMAT),
            entry.end_time.strftime(RUN_LOG_DATETIME_FORMAT),
            "{:.1f}".format((entry.end_time - entry.start_time).total_seconds()),
            Path(entry.full_path).name,
            str(entry.number_of_commands),
            "{:.2f}".format(entry.wait_time_s) if entry.wait_time_s else "",
            "{:.2f}".format(entry.wait_cmd_time_s) if entry.wait_cmd_time_s else "",
        )

    console.print(table)


def print_json(entries: List[RunLogEntry], output_file):
    import json

    json.dump([entry_to_dict(x) for x in entries], output_file)


def print_csv(entries: List[RunLogEntry], output_file):
    import csv

    if not entries:
        return

    fieldnames = list(entry_to_dict(entries[0]).keys())
    writer = csv.DictWriter(
        output_file,
        delimiter=",",
        quotechar='"',
        quoting=csv.QUOTE_NONNUMERIC,
        fieldnames=fieldnames,
    )

    writer.writeheader()
    writer.writerows([entry_to_dict(x) for x in entries])


FORMAT_FN = {
    "table": print_table,
    "json": print_json,
    "csv": print_csv,
}


def save_logged_procedure(blob: bytes, outf):
    import pyzstd
    import json

    json_string = pyzstd.decompress(blob).decode("utf-8")
    procedure = json.loads(json_string)
    dump_procedure_as_json(outf=outf, obj=procedure)


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "--format",
        "-f",
        metavar="IDENTIFIER",
        default="table",
        help="Select the output format. Possible values are"
        + ", ".join(FORMAT_FN.keys()),
    ),
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        default="",
        help="Specify the name of the output file where to save the output",
    )
    parser.add_argument(
        "--commands",
        metavar="#",
        default=None,
        type=int,
        help="If specified, dump the JSON commands ran for the entry number #",
    )

    args = parser.parse_args()

    db = connect_to_run_log()
    curs = db.cursor()

    if args.commands:
        curs.execute(
            """
SELECT zstd_json_procedure FROM run_log WHERE rowid = ?
""",
            (args.commands,),
        )
        blob = curs.fetchone()[0]

        if args.output:
            with open(args.output, "wt") as outf:
                save_logged_procedure(blob=blob, outf=outf)
        else:
            from sys import stdout

            save_logged_procedure(blob=blob, outf=stdout)

        return

    curs.execute(
        """
SELECT
    rowid,
    start_time,
    end_time,
    wait_time_s,
    wait_cmd_time_s,
    full_path,
    number_of_commands
FROM run_log
ORDER BY start_time
"""
    )
    entries = [
        RunLogEntry(
            id=row[0],
            start_time=datetime.strptime(row[1], RUN_LOG_DATETIME_FORMAT),
            end_time=datetime.strptime(row[2], RUN_LOG_DATETIME_FORMAT),
            wait_time_s=row[3],
            wait_cmd_time_s=row[4],
            full_path=Path(row[5]),
            number_of_commands=row[6],
            zstd_json_procedure=None,
        )
        for row in curs.fetchall()
    ]

    if args.output:
        with open(args.output, "wt") as outf:
            FORMAT_FN[args.format](entries, outf)
    else:
        from sys import stdout

        FORMAT_FN[args.format](entries, stdout)


if __name__ == "__main__":
    main()
