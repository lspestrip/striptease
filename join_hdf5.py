#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from argparse import ArgumentParser
import astropy.time
import numpy as np
from pathlib import Path
import h5py
import sys
from tqdm import tqdm

DEFAULT_OUTPUT_FILENAME = "joined.h5"


def parse_datetime(s):
    if s is None:
        return None

    try:
        # Let's try to interpret "s" as a Julian Date first
        jd = float(s)
    except ValueError:
        # If we reach this point, it surely is not a JD
        jd = astropy.time.Time(s).jd

    return jd


def copy_dataset(name, source, dest, objtype, start_time=None, end_time=None):
    if isinstance(objtype, h5py.Group):
        dest.require_group(name)
    elif isinstance(objtype, h5py.Dataset):

        # Caution! The code assumes that all the datasets are one-dimensional!

        source_dataset = source[name]

        try:
            dataset = dest.require_dataset(
                name,
                shape=(0,),
                dtype=source_dataset.dtype,
                chunks=True,
                maxshape=(None,),
                exact=True,
            )
        except TypeError:
            # If require_dataset raises a TypeError, it means that the
            # dataset already exists but it does not matches the shape
            # above (0 elements). In this case, just append the data
            dataset = dest[name]

        mask = np.ones(source_dataset.shape[0], dtype=bool)
        if (
            ("m_jd" in source_dataset.dtype.fields)
            and (len(source_dataset) > 0)
            and (start_time or end_time)
        ):
            if start_time:
                mask = mask & (source_dataset["m_jd"] >= start_time)
            if end_time:
                mask = mask & (source_dataset["m_jd"] <= end_time)

        num_of_elements = source_dataset[mask].shape[0]

        dataset.resize(dataset.shape[0] + num_of_elements, axis=0)
        dataset[-num_of_elements:] = source_dataset[mask]
    else:
        # Unsupported type, just skip this
        pass

    return None  # This ensures that visititems keeps running


def copy_hdf5(source, dest, start_time=None, end_time=None):
    class Counter:
        counter = 0

        def increment(self):
            self.counter += 1

    count = Counter()
    source.visit(lambda x: count.increment())

    with tqdm(desc=source.filename, total=count.counter) as progress_bar:

        def visit_function(name, objtype):
            copy_dataset(
                name=name,
                source=source,
                dest=dest,
                objtype=objtype,
                start_time=start_time,
                end_time=end_time,
            )
            progress_bar.update()

        source.visititems(visit_function)


def parse_args():
    parser = ArgumentParser(
        description="Join two or more HDF5 files containing Strip data"
    )

    parser.add_argument(
        "--start-time",
        "-f",
        metavar="TIME",
        help="""Time of the first sample to save in the
result. If not specified, the first sample in the output will
be the first sample in the first input file. The value of TIME
can either be a datetime in the format YYYY-MM-DDTHH:MM:SS 
(e.g., "2020-05-06T18:33:21") or a Julian Date.""",
    )

    parser.add_argument(
        "--end-time",
        "-t",
        metavar="TIME",
        help="""Time of the last sample to save in the
result. If not specified, the first sample in the output
will be the first sample in the first input file. The format
for TIME is the same as for --start-time.""",
    )

    parser.add_argument(
        "--output",
        "-o",
        dest="output_filename",
        default=DEFAULT_OUTPUT_FILENAME,
        metavar="FILE",
        help=f"""Path of the file to save as output.
If not specified, the standard name {DEFAULT_OUTPUT_FILENAME}
will be used.""",
    )

    parser.add_argument(
        "filenames",
        metavar="HDF5_FILE",
        type=str,
        nargs="+",
        help="Path to the HDF5 file",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    args.start_time = parse_datetime(args.start_time)
    args.end_time = parse_datetime(args.end_time)

    # As the creation of the joined file can take some time, better
    # check if all the files exist before starting the main loop

    error_condition = False
    for cur_input_filename in args.filenames:
        cur_path = Path(cur_input_filename)
        if not (cur_path.exists() and cur_path.is_file()):
            print(
                f"Error, file '{cur_path}' does not exist or is not a valid file",
                file=sys.stderr,
            )
            # Don't stop the program now, but continue checking the
            # other files before exiting
            error_condition = True

    if error_condition:
        sys.exit(1)

    # Now the main loop begins
    copied_files = []
    with h5py.File(args.output_filename, "w") as outf:
        for cur_input_filename in args.filenames:
            with h5py.File(cur_input_filename, "r") as inpf:
                copy_hdf5(
                    source=inpf,
                    dest=outf,
                    start_time=args.start_time,
                    end_time=args.end_time,
                )

            copied_files.append(cur_input_filename)

        maxlen = max([len(x) for x in copied_files])

        outf.require_dataset(
            "joined_files",
            (len(copied_files),),
            dtype=f"S{maxlen}",
            data=[bytes(x, "utf-8") for x in copied_files],
        )


if __name__ == "__main__":
    main()