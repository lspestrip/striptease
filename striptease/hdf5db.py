# -*- encoding: utf-8 -*-

from pathlib import Path
import sqlite3
from typing import Union, List, Tuple

import numpy as np

from .hdf5files import DataFile, Tag


def extract_mjd_range(
    mjd_range: Union[Tuple[float, float], Tag]
) -> Tuple[float, float]:
    "Convenience function that returns the start and end MJD from a 2-tuple/tag"

    if isinstance(mjd_range, Tag):
        return (mjd_range.mjd_start, mjd_range.mjd_end)
    else:
        return mjd_range  # Just return the tuple


def create_storage_db(db: sqlite3.Connection):
    curs = db.cursor()

    # List all the files in the archive
    curs.execute(
        """
CREATE TABLE IF NOT EXISTS files(
    path TEXT,
    size_in_bytes NUMBER,
    first_sample REAL,
    last_sample REAL
)
"""
    )

    # List of tags from all the files in the archive
    curs.execute(
        """
CREATE TABLE IF NOT EXISTS tags(
    id INTEGER PRIMARY KEY,
    mjd_start REAL,
    mjd_end REAL,
    tag TEXT,
    start_comment TEXT,
    end_comment TEXT
)
"""
    )

    db.commit()


def scan_data_path(
    path: Union[str, Path],
) -> Tuple[List[DataFile], sqlite3.Connection]:

    db = sqlite3.connect(Path(path) / "index.db")
    create_storage_db(db)

    file_list = []
    curs = db.cursor()
    for file_name in Path(path).glob("**/*.h5"):
        # Follow symlinks and remove "." and ".."
        file_name = file_name.resolve()

        # file_name is a Path object
        hdf5 = DataFile(file_name)

        curs.execute(
            """
            SELECT first_sample, last_sample
            FROM files
            WHERE path = ?
            """,
            (str(file_name.absolute()),),
        )
        entry = curs.fetchone()
        if entry:
            assert isinstance(entry, tuple)
            assert len(entry) == 2
            # The entry is already in the database, so we can skip opening the file
            hdf5.mjd_range = entry
        else:
            hdf5.read_file_metadata()  # This can take some time
            first_sample, last_sample = hdf5.mjd_range
            curs.execute(
                "INSERT INTO files VALUES (:path, :size, :first_sample, :last_sample)",
                {
                    "path": str(file_name.absolute()),
                    "size": file_name.stat().st_size,
                    "first_sample": float(first_sample),
                    "last_sample": float(last_sample),
                },
            )

            # If a tag is not closed when a HDF5 file is being opened, the
            # tag is left open and it will be properly closed in the next file.
            # Since the next file will contain *complete* information on the tag
            # (i.e., including the start time, which was written in the previous
            # file), we need to use a database which stores tags according to
            # their unique index. We use `INSERT OR REPLACE` so that a tag is
            # inserted twice, the second tag (presumably the one with both the
            # start and end times) will overwrite the first. SQLite is awesome!
            curs.executemany(
                "INSERT OR REPLACE INTO tags VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        int(x.id),
                        float(x.mjd_start),
                        float(x.mjd_end),
                        x.name,
                        x.start_comment,
                        x.end_comment,
                    )
                    for x in hdf5.tags
                ],
            )

            db.commit()

        file_list.append(hdf5)

    return (sorted(file_list, key=lambda x: x.mjd_range[0]), db)


def find_time_in_files(files: List[DataFile], mjd: float, first=0, last=None):
    """Search the HDF5 file that contains the specified MJD

    This is a textbook-like implementation of a binary search. Therefore, it is
    assumed that the files are listed in ascending chronological order, which
    is true if the list was built by ``scan_data_path``.

    The function returns the index of the item in `files` that includes the time
    `mjd` or the index of the last file that was recorded before the MJD time
    happened.
    """
    if last is None:
        last = len(files) - 1

    if first >= last:
        return min(first, last)

    mid = (first + last) // 2
    min_mjd, max_mjd = files[mid].mjd_range

    if (mjd >= min_mjd) and (mjd <= max_mjd):
        return mid
    elif mjd <= min_mjd:
        return find_time_in_files(files, mjd, first=first, last=mid - 1)
    else:
        return find_time_in_files(files, mjd, first=mid + 1, last=last)


class DataStorage:
    """The storage where HDF5 files are kept

    This class builds an index of all the files in a directory containing the
    HDF5 files saved by the LSPE/Strip data server. It can be used to load
    scientific/housekeeping data without caring of file boundaries.

    Example::

        from striptease import DataStorage

        ds = DataStorage("/database/STRIP/HDF5/")
        # One whole day of tags!
        tags = ds.get_tags(mjd_range=(59530.0, 59531.0))
        for cur_tag in tags:
            print(cur_tag)
    """

    def __init__(self, path: Union[str, Path]):
        self.basepath = path
        self.file_list, self.db = scan_data_path(path)

    def _files_in_range(
        self,
        mjd_interval: Tuple[float, float],
    ):
        """Return a list of the indexes of the files that contain data within the MJD range"""

        if not self.file_list:
            return []

        first_mjd, last_mjd = mjd_interval
        assert (
            first_mjd <= last_mjd
        ), f"Wrong range {mjd_interval} passed to DataStorage.files_in_range"
        first_idx = find_time_in_files(self.file_list, first_mjd)
        last_idx = find_time_in_files(self.file_list, last_mjd)
        if self.file_list[first_idx].mjd_range[0] > last_mjd:
            # The time is too far in the past
            return []

        if self.file_list[last_idx].mjd_range[1] < first_mjd:
            # The time is too far in the future
            return []

        return list(range(first_idx, last_idx + 1))

    def _load(
        self,
        mjd_range: Union[Tuple[float, float], Tag],
        load_fn,
    ):
        "Private function, used by load_sci and load_hk"

        start_mjd, end_mjd = extract_mjd_range(mjd_range)
        indexes = self._files_in_range(mjd_range)
        if not indexes:
            return None, None

        time, data = None, None
        for idx in indexes:
            # Reopen the file if it was closed and leave it open for possible later usage
            self.file_list[idx].read_file_metadata(force=False)

            cur_time, cur_data = load_fn(self.file_list[idx])
            mask = (cur_time.value >= start_mjd) & (cur_time.value <= end_mjd)
            cur_time = cur_time[mask]
            cur_data = cur_data[mask]

            if time is None:
                time = cur_time
                data = cur_data
            else:
                assert time[-1] < cur_time[0], f"Non-consecutive times in {mjd_range}"
                time = np.concatenate((time, cur_time))
                data = np.concatenate((data, cur_data))

        return time, data

    def get_tags(self, mjd_range: Union[Tuple[float, float], Tag]) -> List[Tag]:
        """Return a list of all the tags falling within a MJD range

        The function returns a list of all the tags found in the HDF5 files in the
        storage directory that fall (even partially) within the range of MJD specified
        by `mjd_range`. The function is quite fast because it uses a cache instead of
        reading the HDF5 files themselves.

        You can pass a :class:`.Tag` object instead of a MJD time range.
        """

        # To check if a tag falls within mjd_range, we check
        # if any of the two extrema of the tag TTT…TTT falls
        # within the range:
        #
        #  start_mjd                       end_mjd
        #      |------------------------------|
        #      .                              .
        #  TTTTTTTTT                          .
        #      .                              .
        #      .       TTTTTTTTT              .
        #      .                              .
        #      .                           TTTTTTTTT

        mjd_start, mjd_end = extract_mjd_range(mjd_range)

        curs = self.db.cursor()
        curs.execute(
            """
            SELECT id, tag, mjd_start, mjd_end, start_comment, end_comment
            FROM tags
            WHERE (mjd_start >= :range_start AND mjd_start <= :range_end)
               OR (mjd_end >= :range_end AND mjd_end <= :range_end)
            ORDER BY mjd_start
            """,
            {"range_start": mjd_start, "range_end": mjd_end},
        )
        return [Tag(*row) for row in curs.fetchall()]

    def load_sci(self, mjd_range: Union[Tuple[float, float], Tag], *args, **kwargs):
        """Load scientific data within a specified MJD time range

        This function operates in the same way as :meth:`.DataFile.load_sci`, but it
        takes as input a time range (expressed in MJD) which can cross the HDF5 file
        boundaries.

        You can pass a :class:`.Tag` object instead of a MJD time range.

        Example::

            from striptease import DataStorage

            ds = DataStorage("/database/STRIP/HDF5/")
            # Caution! One whole day of scientific data!
                times, data = ds.load_sci(
                    mjd_range=(59530.0, 59531.0),
                    polarimeter="R0",
                    data_type="DEM",
                    detector=["Q1"],
                )

        """
        return self._load(mjd_range, load_fn=lambda f: f.load_sci(*args, **kwargs))

    def load_hk(self, mjd_range: Union[Tuple[float, float], Tag], *args, **kwargs):
        """Load housekeeping data within a specified MJD time range

        This function operates in the same way as :meth:`.DataFile.load_hk`, but it
        takes as input a time range (expressed in MJD) which can cross the HDF5 file
        boundaries.

        You can pass a :class:`.Tag` object instead of a MJD time range.

        Example::

            from striptease import DataStorage

            ds = DataStorage("/database/STRIP/HDF5/")
            # Caution! One whole day of scientific data!
            times, data = ds.load_hk(
                mjd_range=(59530.0, 59531.0),
                group="BIAS",
                subgroup="POL_R0",
                par="VG1_HK",
            )

        """
        return self._load(mjd_range, load_fn=lambda f: f.load_sci(*args, **kwargs))
