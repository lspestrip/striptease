# -*- encoding: utf-8 -*-

from collections import namedtuple
import logging as log
from pathlib import Path
import sqlite3
from typing import Union, List, Tuple, Set, Dict

import astropy.time
from rich.progress import track
import numpy as np

from .hdf5files import HDF5_FILE_SUFFIXES, EARLIEST_ACCEPTABLE_MJD, DataFile, Tag


#: Basic information about a HDF5 data file
#:
#: Fields are:
#:
#: - ``path``: a ``pathlib.Path`` object containing the path to the file
#:
#: - ``size``: size of the file, in bytes
#:
#: - ``mjd_range``: a 2-tuple containing the MJD of the first and last
#:   scientific/housekeeping sample in the file (``float`` values)
HDF5FileInfo = namedtuple("HDF5FileInfo", ["path", "size", "mjd_range"])


def extract_mjd_range(
    mjd_range: Union[
        Tuple[float, float],
        Tuple[astropy.time.Time, astropy.time.Time],
        Tuple[str, str],
        Tag,
    ]
) -> Tuple[float, float]:
    """Convenience function that returns the start and end MJD from a 2-tuple/tag

    If a 2-tuple is provided, it can either be:

    1. A pair of MJD dates, each expressed as a floating-point number;
    2. A pair of strings, each representing a date that is parseable
       by ``astropy.time.Time``;
    3. A pair of ``astropy.time.Time`` objects.
    """

    if isinstance(mjd_range, Tag):
        return (mjd_range.mjd_start, mjd_range.mjd_end)

    if isinstance(mjd_range[0], astropy.time.Time):
        return tuple(x.mjd for x in mjd_range)

    if isinstance(mjd_range[0], str):
        return tuple(astropy.time.Time(x).mjd for x in mjd_range)

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
    database_name="index.db",
    update_database=False,
    update_hdf5=False,
) -> sqlite3.Connection:

    db_path = Path(path) / database_name
    db = sqlite3.connect(db_path)
    create_storage_db(db)

    curs = db.cursor()
    visited_files = set()  # type: Set[str]

    files_to_update = []  # type: List[Path]
    for cur_suffix in HDF5_FILE_SUFFIXES:
        files_to_update += list(Path(path).glob(f"**/*{cur_suffix}"))

    files_to_update.sort()
    log.info(f"{len(files_to_update)} files match the glob pattern")
    for file_name in track(files_to_update) if update_database else files_to_update:
        # Follow symlinks and remove "." and ".."
        file_name = file_name.resolve()
        visited_files.add(str(file_name))

        curs.execute(
            "SELECT first_sample, last_sample FROM files WHERE path = ?",
            (str(file_name.absolute()),),
        )
        entry = curs.fetchone()
        if (
            entry
            and (entry[0] > EARLIEST_ACCEPTABLE_MJD)
            and (entry[1] > EARLIEST_ACCEPTABLE_MJD)
        ):
            # The entry is already in the database, so we can skip opening the file
            continue

        if not update_database:
            log.warning(
                (
                    "file {file_name} is not in database {db_path} or has a "
                    "wrong MJD range, consider using update_database=True"
                ).format(file_name=file_name, db_path=db_path)
            )
        else:
            log.info(
                f'file "{file_name}" not found in database "{db_path}", adding its metadata'
            )

            try:
                with DataFile(file_name) as hdf5:
                    first_sample, last_sample = hdf5.mjd_range
                    computed = hdf5.computed_mjd_range
            except OSError as e:
                log.error(f'unable to read metadata from "{file_name}" (OSError): {e}')
                continue
            except RuntimeError as e:
                log.error(
                    f'unable to read metadata from "{file_name}" (RuntimeError): {e}'
                )
                continue

            curs.execute(
                "INSERT INTO files VALUES (:path, :size, :first_sample, :last_sample)",
                {
                    "path": str(file_name.absolute()),
                    "size": file_name.stat().st_size,
                    "first_sample": float(first_sample),
                    "last_sample": float(last_sample),
                },
            )

            if update_hdf5 and computed:
                log.info(
                    f'Writing MJD range ({first_sample}, {last_sample}) back in "{file_name}"'
                )
                with DataFile(file_name, "r+") as hdf5:
                    hdf5.hdf5_file.attrs["FIRST_SAMPLE"] = first_sample
                    hdf5.hdf5_file.attrs["LAST_SAMPLE"] = last_sample

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

    # Now check that there are no files that have been deleted but are still present
    # in the database
    curs.execute("SELECT path FROM files ORDER BY first_sample")
    for (cur_path,) in curs.fetchall():
        if cur_path not in visited_files:
            log.warning(
                f"{cur_path} is present in the database {db_path} but is missing from disk"
            )
            if update_database:
                curs.execute("DELETE FROM files WHERE path = ?", (cur_path,))
                db.commit()
                log.info(f"entry {cur_path} was deleted from the database")

    return db


def find_time_in_files(files: List[HDF5FileInfo], mjd: float, first=0, last=None):
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

    def __init__(
        self,
        path: Union[str, Path],
        database_name="index.db",
        update_database=False,
        update_hdf5=False,
    ):
        """Load a database of HDF5 files

        Load a database of HDF5 files from the specified path. The database is a SQLite3
        file saved in a file named `database_name` in folder `path`. If the flag
        `update_database` is ``True``, the database will be created/updated whenever
        needed; if it is false, it will be only read. If ``update_hdf5`` is ``True``,
        whenever MJD ranges must be computed because they are not present in a HDF5
        file, they will be written back to the HDF5 file itself.

        Beware that ``update_database=True`` requires that you have write permission
        on the database file; similarly, ``update_hdf5=True`` requires to have write
        permission on the HDF5 files.
        """
        self.basepath = path
        self.db = scan_data_path(
            path,
            database_name=database_name,
            update_database=update_database,
            update_hdf5=update_hdf5,
        )
        self.opened_files = {}  # type: Dict[Path, DataFile]

    def _open_file(self, path: Union[str, Path]) -> DataFile:
        return self.opened_files.get(Path(path), DataFile(path))

    def get_list_of_files(self) -> List[HDF5FileInfo]:
        """Return a list of all the files in the storage path"""
        curs = self.db.cursor()
        curs.execute(
            """
            SELECT path, size_in_bytes, first_sample, last_sample
            FROM files
            ORDER BY first_sample
        """
        )

        return [
            HDF5FileInfo(path=x[0], size=x[1], mjd_range=(x[2], x[3]))
            for x in curs.fetchall()
        ]

    def files_in_range(
        self,
        mjd_range: Union[
            Tuple[float, float],
            Tuple[astropy.time.Time, astropy.time.Time],
            Tuple[str, str],
            Tag,
        ],
    ) -> List[HDF5FileInfo]:
        """Return a list of the files that contain data within the MJD range"""

        first_mjd, last_mjd = extract_mjd_range(mjd_range)

        curs = self.db.cursor()
        # The WHERE clause considers three possibilities:
        # 1. The first part of the file falls within the time range we're looking for
        # 2. The last part of the file falls within the time range we're looking for
        # 3. The entirety of the file falls within the time range we're looking for
        curs.execute(
            """
            SELECT path, size_in_bytes, first_sample, last_sample
            FROM files
            WHERE ((:query_start >= first_sample) AND (:query_start <= last_sample))
               OR ((:query_end >= first_sample) AND (:query_end <= last_sample))
               OR ((:query_start <= first_sample) AND (:query_end >= last_sample))
            ORDER BY first_sample
        """,
            {"query_start": first_mjd, "query_end": last_mjd},
        )

        return [
            HDF5FileInfo(path=x[0], size=x[1], mjd_range=(x[2], x[3]))
            for x in curs.fetchall()
        ]

    def _load(
        self,
        mjd_range: Union[
            Tuple[float, float],
            Tuple[astropy.time.Time, astropy.time.Time],
            Tuple[str, str],
            Tag,
        ],
        load_fn,
    ):
        "Private function, used by load_sci and load_hk"

        start_mjd, end_mjd = extract_mjd_range(mjd_range)
        time, data = None, None
        for cur_file in self.files_in_range((start_mjd, end_mjd)):
            hdf5_file = self._open_file(cur_file.path)
            hdf5_file.read_file_metadata(force=False)

            cur_time, cur_data = load_fn(hdf5_file)
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

    def get_tags(
        self,
        mjd_range: Union[
            Tuple[float, float],
            Tuple[astropy.time.Time, astropy.time.Time],
            Tuple[str, str],
            Tag,
        ],
    ) -> List[Tag]:
        """Return a list of all the tags falling within a MJD range

        The function returns a list of all the tags found in the HDF5 files in the
        storage directory that fall (even partially) within the range of MJD specified
        by `mjd_range`. The range can either be:

        1. A pair of floating-point values, each representing a MJD date;
        2. A pair of strings, each representing a date (e.g., ``2021-12-10 10:39:45``);
        3. A pair of instances of ``astropy.time.Time``;
        4. A single instance of the :class:`.Tag` class.

        The list of tags is always sorted in chronological order.

        The function is quite fast because it uses a cache instead of
        reading the HDF5 files themselves.
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
        return [
            Tag(
                id=row[0],
                name=row[1],
                mjd_start=row[2],
                mjd_end=row[3],
                start_comment=row[4],
                end_comment=row[5],
            )
            for row in curs.fetchall()
        ]

    def load_sci(
        self,
        mjd_range: Union[
            Tuple[float, float],
            Tuple[astropy.time.Time, astropy.time.Time],
            Tuple[str, str],
            Tag,
        ],
        *args,
        **kwargs,
    ):
        """Load scientific data within a specified MJD time range

        This function operates in the same way as :meth:`.DataFile.load_sci`, but it
        takes as input a time range that can cross the HDF5 file boundaries. The
        parameter `mjd_time` range can be one of the following:

        1. A pair of floating-point values, each representing a MJD date;
        2. A pair of strings, each representing a date (e.g., ``2021-12-10 10:39:45``);
        3. A pair of instances of ``astropy.time.Time``;
        4. A single instance of the :class:`.Tag` class.

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
        takes as input a time range that can cross the HDF5 file boundaries.The
        parameter `mjd_time` range can be one of the following:

        1. A pair of floating-point values, each representing a MJD date;
        2. A pair of strings, each representing a date (e.g., ``2021-12-10 10:39:45``);
        3. A pair of instances of ``astropy.time.Time``;
        4. A single instance of the :class:`.Tag` class.

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
        return self._load(mjd_range, load_fn=lambda f: f.load_hk(*args, **kwargs))
