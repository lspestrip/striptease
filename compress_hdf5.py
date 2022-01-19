#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from datetime import datetime
from io import BytesIO
from pathlib import Path
from argparse import ArgumentParser
import json
import logging

from rich.progress import Progress
from rich.logging import RichHandler
import pyzstd

DEFAULT_THRESHOLD = 0.02


def get_json_file_name(filename: Path) -> Path:
    return Path(filename.parent / ("." + str(filename.name) + ".compressed_info.json"))


def get_compressed_file_name(filename: Path) -> Path:
    return Path(str(filename) + ".zst")


def process_file(filename: Path, threshold, delete):
    if filename.suffix == ".zst":
        logging.info(f'"{filename}" is already compressed')
        return

    compr_file_name = get_compressed_file_name(filename)
    if compr_file_name.exists() and compr_file_name.is_file():
        logging.info(f'"{filename}" already has a compressed copy, "{compr_file_name}"')
        return

    json_file_name = get_json_file_name(filename)

    try:
        with json_file_name.open("rt") as inpf:
            compr_info = json.load(inpf)

        # We were able to find the file and read it, so it means there is
        # no need to process the file.
        logging.info(
            f'"{filename}" was already been tested ({compr_info["compression_ratio"]:.1f}%)'
        )
        return
    except Exception:
        pass

    buf = BytesIO()
    uncompr_len = filename.stat().st_size

    with Progress() as progress:
        task = progress.add_task(filename.name, total=uncompr_len)

        def callback(total_input, total_output, read_data, write_data):
            progress.update(task, completed=total_input)

        with filename.open("rb") as inpf:
            pyzstd.compress_stream(
                inpf,
                buf,
                level_or_option=9,
                callback=callback,
                read_size=13_107_200,
                write_size=13_159_100,
            )

    compr_len = len(buf.getvalue())
    compr_ratio = compr_len / uncompr_len * 100
    logging.info(f'"{filename}": {uncompr_len} → {compr_len} ({compr_ratio:.2f}%)')

    if compr_ratio < threshold:
        compr_filename = Path(str(filename) + ".zst")
        with compr_filename.open("wb") as outf:
            outf.write(buf.getvalue())
        logging.info(f'File "{compr_filename}" has been written')

        if delete:
            filename.unlink()
            logging.info(f'File "{filename}" was deleted')

    with open(json_file_name, "wt") as outf:
        json.dump(
            {
                "uncompressed_size": uncompr_len,
                "compressed_size": compr_len,
                "filename": str(filename),
                "compression_ratio": compr_ratio,
                "date": str(datetime.now()),
            },
            outf,
        )


def main():
    logging.basicConfig(
        level="INFO", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
    )

    parser = ArgumentParser()
    parser.add_argument(
        "--delete",
        "-d",
        help="When a file is compressed, delete the original file",
        action="store_true",
    )
    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Fraction of file size under which the file will be compressed (default: {})".format(
            DEFAULT_THRESHOLD
        ),
    )
    parser.add_argument("file_list", nargs="+")
    args = parser.parse_args()

    filenames = [Path(x) for x in args.file_list]

    for cur_filename in filenames:
        process_file(cur_filename, threshold=args.threshold, delete=args.delete)


if __name__ == "__main__":
    main()
