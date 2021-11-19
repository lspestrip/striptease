#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from pathlib import Path
import sys

from tqdm import tqdm
import h5py

from striptease import (
    find_first_and_last_samples_in_hdf5,
)


def main(args):
    if len(args) == 1:
        print(
            """Usage: fix_hdf5.py HDF5_FILE...

Scan the file and fix the value of FIRST_SAMPLE and LAST_SAMPLE, if it is
not set appropriately. (These values are the Modified Julian Dates of the
first and last samples found in the file.)

The file are modified in place, so you must have write permission. If
you see errors related to «lock» problems, set the environment variable
`HDF5_USE_FILE_LOCKING` to `FALSE`. Example:

    HDF5_USE_FILE_LOCKING='FALSE' ./fix_hdf5.py file1.h5 file2.h5

"""
        )
        sys.exit(1)

    messages = []
    for cur_file in tqdm(args[1:]):
        cur_file = Path(cur_file)
        with h5py.File(cur_file, mode="r+") as h5_file:
            min_mjd = h5_file.attrs.get("FIRST_SAMPLE", -1)
            max_mjd = h5_file.attrs.get("LAST_SAMPLE", -1)

            if (min_mjd > 0) and (max_mjd > min_mjd):
                messages.append(f'File "{cur_file}" looks ok, skipping…')
                continue

            min_mjd, max_mjd = find_first_and_last_samples_in_hdf5(h5_file)
            h5_file.attrs["FIRST_SAMPLE"] = min_mjd
            h5_file.attrs["LAST_SAMPLE"] = max_mjd

            messages.append(f'File "{cur_file}" has been fixed')

    for msg in messages:
        print(msg)


if __name__ == "__main__":
    main(sys.argv)
