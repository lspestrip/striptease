#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from argparse import ArgumentParser
from collections import namedtuple
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import sqlite3
import sys

from astropy.time import Time, TimeDelta

from rich.console import Console
from rich.table import Table

from striptease import polarimeter_iterator

Tag = namedtuple("Tag", ["tag", "mjd_start", "mjd_end"])

STRFTIME_DEFAULT = "%Y-%m-%d %H:%M:%S"


def format_time(
    time: Optional[Time], use_mjd: bool = False, homogeneous_units: bool = False
) -> str:
    "Given a astropy.time.Time object, produces a string representing its value"

    if time is None:
        return "–"

    if use_mjd:
        if isinstance(time, Time):
            return "{}".format(time.mjd)

        return "{}".format(time)

    if isinstance(time, Time):
        return str(time.to_datetime())

    if isinstance(time, TimeDelta):
        seconds = time.to_datetime().total_seconds()

        if homogeneous_units or seconds < 240:
            return "{:.1f} s".format(seconds)

        if seconds < 3600:
            return "{:.1f} m".format(seconds / 60.0)

        if seconds < 86400:
            return "{:.1f} h".format(seconds / 3600.0)

        return "{:.1f} d".format(seconds / 86400.0)

    assert False, "Unhandled case"


class ExtendedJSONEncoder(json.JSONEncoder):
    def __init__(self, use_mjd: bool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_mjd = use_mjd

    def default(self, o):
        if isinstance(o, Time):
            if self.use_mjd:
                return o.mjd

            return o.to_datetime().strftime(STRFTIME_DEFAULT)

        return o


def create_intervals(tag_list: List[Tag]) -> List[Dict[str, Any]]:
    """Create a list of intervals starting from a list of tags

    The result is a list of dictionaries with the following keys:

    - `mjd_start`: the time when the electronics was turned on, or
      `None`

    - `mjd_end`: the time when the electronics was turned off,
      or `None`

    The ``None`` value is used whenever the polarimeter was on before
    the first tag in the list, or if it was still on after the last
    tag in the list.

    """

    intervals = []  # typing: List[Dict[str, Any]]
    old_state = None  # typing: Optional[Bool]
    interval_start = None  # typing: Optional[Time]

    for cur_tag in tag_list:
        # This variable is either True or False, depending on whether
        # the electronics was turned on or off
        new_state = cur_tag.tag.startswith("ELECTRONICS_ENABLE")

        if new_state != old_state:
            if new_state:
                # A new interval begins
                interval_start = cur_tag.mjd_start
            else:
                # The current interval ends
                if not interval_start:
                    intervals.append({"mjd_start": None, "mjd_end": cur_tag.mjd_end})
                else:
                    intervals.append(
                        {"mjd_start": interval_start, "mjd_end": cur_tag.mjd_end}
                    )

                interval_start = None

            old_state = new_state

    if interval_start:
        # The polarimeter was still acquiring when the last tag was saved
        intervals.append((interval_start, -1))

    return intervals


def print_intervals(
    polarimeter: str,
    intervals: List[Dict[str, Any]],
    console: Console,
    use_mjd: bool = False,
    homogeneous_units: bool = False,
):
    "Use rich.tables to print a table of the intervals for this polarimeter"

    table = Table(title=f"Acquisitions for {polarimeter}")

    table.add_column("Start")
    table.add_column("End")
    table.add_column("Duration", justify="right")

    for interval in intervals:
        table.add_row(
            format_time(
                interval["mjd_start"],
                use_mjd=use_mjd,
                homogeneous_units=homogeneous_units,
            ),
            format_time(
                interval["mjd_end"],
                use_mjd=use_mjd,
                homogeneous_units=homogeneous_units,
            ),
            format_time(
                interval["mjd_end"] - interval["mjd_start"],
                use_mjd=use_mjd,
                homogeneous_units=homogeneous_units,
            ),
        )

    console.print(table)


def process_one_polarimeter(cursor, polarimeter: str):
    # The order of the fields here must match the order in the "Tag" type
    cursor.execute(
        "select tag, mjd_start, mjd_end from tags where tag = ? or tag = ? order by mjd_start",
        (f"ELECTRONICS_ENABLE_{polarimeter}", f"ELECTRONICS_DISABLE_{polarimeter}"),
    )
    tags = [
        Tag(
            tag=x[0],
            mjd_start=Time(x[1], format="mjd"),
            mjd_end=Time(x[2], format="mjd"),
        )
        for x in cursor.fetchall()
    ]

    intervals = create_intervals(tags)

    return intervals


def main():
    parser = ArgumentParser()

    parser.add_argument(
        "--use-mjd",
        "-m",
        default=False,
        action="store_true",
        help="Print times and time intervals using MJD instead of date/time values",
    )

    parser.add_argument(
        "--homogeneous-units",
        "-u",
        default=False,
        action="store_true",
        help="""Use the same measurement unit for time intervals (seconds) instead of
        s (seconds), m (minutes), h (hours), and d (days).""",
    )

    parser.add_argument(
        "--polarimeter",
        "-p",
        default=[],
        type=str,
        action="append",
        help="""Name of the polarimeter to consider in the search. You can use the -p
        switch several times. Default: all""",
    )

    parser.add_argument(
        "--json",
        "-j",
        default=False,
        action="store_true",
        help="""Instead of printing tables, send a JSON document to stdout containing the
        results of the query""",
    )

    parser.add_argument("db_path", help="Path to the database of tests")

    args = parser.parse_args()

    if not args.polarimeter:
        args.polarimeter = list([x[2] for x in polarimeter_iterator()])

    db_path = Path(args.db_path)
    db = sqlite3.connect(db_path)

    curs = db.cursor()
    console = Console()

    intervals = {}
    for polarimeter in args.polarimeter:
        intervals[polarimeter] = process_one_polarimeter(
            cursor=curs,
            polarimeter=polarimeter,
        )

    if args.json:
        json.dump(
            intervals, fp=sys.stdout, cls=ExtendedJSONEncoder, use_mjd=args.use_mjd
        )
    else:
        for polarimeter in args.polarimeter:
            print_intervals(
                polarimeter,
                intervals[polarimeter],
                console,
                use_mjd=args.use_mjd,
                homogeneous_units=args.homogeneous_units,
            )


if __name__ == "__main__":
    main()
