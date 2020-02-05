# -*- encoding: utf-8 -*-

from typing import Union, List, Set

from pathlib import Path
from astropy.time import Time
import h5py
from datetime import datetime


def parse_datetime_from_filename(filename):
    """Extract a datetime from a HDF5 file name

    Example::

        >>> parse_datetime_from_filename("2019_11_12_05-34-17.h5")
        datetime.datetime(2019, 11, 12, 5, 34, 17)
    """

    basename = Path(filename).name
    try:
        assert len(basename) == 22
        return datetime(
            year=int(basename[0:4]),
            month=int(basename[5:7]),
            day=int(basename[8:10]),
            hour=int(basename[11:13]),
            minute=int(basename[14:16]),
            second=int(basename[17:19]),
        )
    except:
        raise RuntimeError(f"Invalid HDF5 filename: {filename}")


def scan_board_names(group_names: List[str]) -> Set[str]:
    """Scan a list of group names and return the set of boards in it.

    Example::

        >>> group_names(["BOARD_G", "COMMANDS", "LOG", "POL_G0", "POL_G6"])
        set("G")
    """
    result = set()  # type: Set[str]
    for curname in group_names:
        if (len(curname) == 7) and (curname[0:6] == "BOARD_"):
            result.add(curname[6].upper())

    return result


def scan_polarimeter_names(group_names: List[str]) -> Set[str]:
    """Scan a list of group names and return the set of polarimeters in it.

    Example::

        >>> group_names(["BOARD_G", "COMMANDS", "LOG", "POL_G0", "POL_G6"])
        set("G0", "G6")
    """
    result = set()  # type: Set[str]
    for curname in group_names:
        if (len(curname) == 6) and (curname[0:4] == "POL_"):
            result.add(curname[4:6].upper())

    return result


class DataFile:
    """A HDF5 file containing Strip data

    Class fields:
    
    - ``filepath``: a ``Path`` object containing the full path of the
                    HDF5 file

    - ``datetime``: a Python ``datetime`` object containing the time
                    when the acquisition started

    - ``hdf5_groups``: a list of ``str`` objects containing the names
                       of the groups in the HDF5 file. To initialize
                       this field, you must call
                       ``DataFile.read_file_metadata`` first.

    - ``polarimeters``: a Python ``set`` object containing the names
                        of the polarimeters whose measurements have
                        been saved in this file. To initialize this
                        field, you must call
                        ``DataFile.read_file_metadata`` first.

    """

    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.datetime = parse_datetime_from_filename(self.filepath)
        self.hdf5_groups = []

    def __str__(self):
        return f'striptease.DataFile("{self.filepath}")'

    def read_file_metadata(self):
        "Open the file and checks the contents"

        with h5py.File(self.filepath, "r") as inpf:
            self.hdf5_groups = list(inpf.keys())

        self.boards = scan_board_names(self.hdf5_groups)
        self.polarimeters = scan_polarimeter_names(self.hdf5_groups)


def scan_data_path(path: Union[str, Path]) -> List[DataFile]:
    result = []  # type: List[DataFile]
    for file_name in Path(path).glob("**/*.h5"):
        # file_name is a Path object
        curfile = DataFile(file_name)
        try:
            curfile.read_file_metadata()
        except OSError:
            pass
        result.append(curfile)

    return sorted(result, key=lambda n: n.datetime)
