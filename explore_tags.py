#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from argparse import ArgumentParser
from collections import namedtuple, OrderedDict
from pathlib import Path
import sys

import h5py

from striptease import DataFile

DEFAULT_OUTPUT_FILENAME = "-"

Tag = namedtuple(
    "Tag",
    [
        "filename",
        "id",
        "tag_name",
        "mjd_start",
        "mjd_end",
        "start_comment",
        "end_comment",
    ],
)


def output_tsv(outf, tags):
    template_str = (
        "{filename:12s}\t{id:6d}\t{tag_name:32s}\t"
        + "{mjd_start:14.9f}\t{mjd_end:14.9f}\t"
        + "{start_comment}\t{end_comment}"
    )
    for tag in tags:
        print(
            template_str.format(
                filename=tag.filename,
                id=tag.id,
                tag_name=tag.tag_name,
                mjd_start=tag.mjd_start,
                mjd_end=tag.mjd_end,
                start_comment=tag.start_comment,
                end_comment=tag.end_comment,
            ),
            file=outf,
        )


def output_csv(outf, tags):
    import csv

    writer = csv.writer(outf, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
    for tag in tags:
        writer.writerow(tag)


def output_json(outf, tags):
    import json

    dictionary = {"tags": []}
    for tag in tags:
        dictionary["tags"].append(
            OrderedDict(
                [
                    ("file_name", tag.filename),
                    ("id", int(tag.id)),
                    ("tag_name", tag.tag_name),
                    ("mjd_start", float(tag.mjd_start)),
                    ("mjd_end", float(tag.mjd_end)),
                    ("start_comment", tag.start_comment),
                    ("end_comment", tag.end_comment),
                ]
            )
        )

    json.dump(dictionary, outf, indent=2)


OUTPUT_FORMATS = {
    "tsv": (output_tsv, "tsv"),
    "csv": (output_csv, "csv"),
    "json": (output_json, "json"),
}


DEFAULT_OUTPUT_FORMAT = "tsv"


def parse_arguments():
    parser = ArgumentParser(description="Inspect the tags saved in a Strip HDF5 file",)

    parser.add_argument(
        "--format",
        "-f",
        metavar="FMT",
        type=str,
        default=DEFAULT_OUTPUT_FORMAT,
        help="""Format to be used for the output. 
Possible values are {format_list} (default is {default})
""".format(
            format_list=", ".join(OUTPUT_FORMATS.keys()), default=DEFAULT_OUTPUT_FORMAT
        ),
    )

    parser.add_argument(
        "--output",
        "-o",
        default=DEFAULT_OUTPUT_FILENAME,
        type=str,
        help="""Name of the output file. Use '{{ext}}' to make
the code pick the best extension, depending
on the value of --format"", e.g., \"my_output.{{ext}}\". Use
"-" to print the output to the terminal. Default is {default}""".format(
            default=DEFAULT_OUTPUT_FILENAME
        ),
    )

    parser.add_argument(
        "filenames",
        metavar="HDF5_FILE",
        type=str,
        nargs="+",
        help="Path to the HDF5 file(s)",
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    tags = []
    for input_file in args.filenames:
        filepath = Path(input_file)
        f = DataFile(filepath)
        f.read_file_metadata()
        tags += [
            Tag(
                filename=input_file,
                id=x.id,
                tag_name=x.name,
                mjd_start=x.mjd_start,
                mjd_end=x.mjd_end,
                start_comment=x.start_comment,
                end_comment=x.end_comment,
            )
            for x in f.tags
        ]

    writer_fn, ext = OUTPUT_FORMATS[args.format]

    if "{ext}" in args.output:
        output_file_name = args.output.format(ext=ext)
    else:
        output_file_name = args.output

    if output_file_name != "-":
        with open(output_file_name, "wt") as outf:
            writer_fn(outf, tags)

        print(f"Tags written to file {output_file_name}")
    else:
        writer_fn(sys.stdout, tags)


if __name__ == "__main__":
    main()
