#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from argparse import ArgumentParser
from pathlib import Path
import logging as log
from rich.logging import RichHandler

from striptease import DataStorage


DEFAULT_DATABASE_NAME = "index.db"


def main():
    parser = ArgumentParser(prog="build_hdf5_database.py")
    parser.add_argument(
        "--database-name",
        "-d",
        type=str,
        default=DEFAULT_DATABASE_NAME,
        help="""Name of the file that will contain the database.
        The default is {default}""".format(
            default=DEFAULT_DATABASE_NAME
        ),
    )
    parser.add_argument(
        "--start-from-scratch",
        action="store_true",
        default=False,
        help="""If true, any existing database will be removed and a new one will
        be created from scratch. CAUTION: this might take a lot of time!""",
    )
    parser.add_argument("path", type=str, help="Path where the HDF5 files are stored")
    args = parser.parse_args()

    path = Path(args.path)

    log.basicConfig(level="INFO", format="%(message)s", handlers=[RichHandler()])

    log.info(f'looking for a database in "{path}" with name "{args.database_name}"')

    db_path = path / args.database_name
    if db_path.is_file():
        log.info(f'an existing database has been found in "{path}"')

        if args.start_from_scratch:
            log.info(
                '"--start-from-scratch" was specified, so I am removing the database'
            )
            db_path.unlink()
            log.info(f'database "{db_path}" was removed from disk')

    log.info(f"going to scan {path} for HDF5 files…")
    ds = DataStorage(path, database_name=args.database_name, update_database=True)
    log.info(
        "the database has been updated and now contains {} entries".format(
            len(ds.get_list_of_files())
        )
    )


if __name__ == "__main__":
    main()
