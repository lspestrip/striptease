# -*- encoding: utf-8 -*-

from collections import namedtuple
from pathlib import Path
from typing import Union, List, Set

from astropy.time import Time
import csv
import h5py
import numpy as np
from datetime import datetime
from scipy.interpolate import interp1d

from .biases import BiasConfiguration

__all__ = [
    "get_hk_descriptions",
    "HkDescriptionList",
    "DataFile",
    "scan_data_path",
]

VALID_GROUPS = ["BIAS", "DAQ"]
VALID_SUBGROUPS = ["POL", "BOARD"]
VALID_DETECTORS = ["Q1", "Q2", "U1", "U2"]
VALID_DATA_TYPES = ["PWR", "DEM"]

#: Information about a tag loaded from a HDF5 file
#:
#: Fields are:
#: - ``id``: unique integer number
#: - ``mjd_start``: start time of the tag (MJD)
#: - ``mjd_end``: stop time of the tag (MJD)
#: - ``name``: string containing the name of the tag
#: - ``start_comment``: comment put at the start
#: - ``end_comment``: comment put at the end
Tag = namedtuple(
    "Tag", ["id", "mjd_start", "mjd_end", "name", "start_comment", "end_comment",]
)


def check_group_and_subgroup(group, subgroup):
    if not group.upper() in VALID_GROUPS:
        valid_choices = ", ".join(['"' + x + '"' for x in VALID_GROUPS])
        raise ValueError(f"Group {group.upper()} must be one of {valid_choices}")

    if not subgroup.upper() in VALID_SUBGROUPS:
        valid_choices = ", ".join(['"' + x + '"' for x in VALID_SUBGROUPS])
        raise ValueError(f"Subgroup {subgroup.upper()} must be one of {valid_choices}")

    return True


def hk_list_file_name(group, subgroup):
    return (
        Path(__file__).parent.parent
        / "data"
        / "hk_pars_{}_{}.csv".format(subgroup.upper(), group.upper(),)
    )


class HkDescriptionList:
    """Result of a call to get_hk_descriptions

    This class acts like a dictionary that associates the name of an
    housekeeping parameter with a description. It provides a nice
    textual representation when printed on the screen::

        l = get_hk_descriptions("BIAS", "POL")

        # Print the description of one parameter
        if "VG4A_SET" in l:
            print(l["VG4A_SET"])

        # Print all the descriptions in a nicely-formatted table
        print(l)

    """

    def __init__(self, group, subgroup, hklist):
        self.group = subgroup
        self.subgroup = group
        self.hklist = hklist

    def __contains__(self, k):
        return self.hklist.__contains__(k)

    def __iter__(self, k):
        return self.hklist.__iter__(k)

    def __len__(self):
        return self.hklist.__len__()

    def __getitem__(self, key):
        return self.hklist.__getitem__(key)

    def __str__(self):
        result = f"Parameters for {self.group}/{self.subgroup}\n\n"

        result += "{:15s}{}\n".format("HK name", "Description")

        table_body = ""
        linewidth = 0
        for key in sorted(self.hklist.keys()):
            cur_line = f"{key:15s}{self.hklist[key]}\n"
            if len(cur_line) - 1 > linewidth:
                linewidth = len(cur_line) - 1

            table_body += cur_line

        return result + ("-" * linewidth) + "\n" + table_body


def get_group_subgroup(parameter):
    """
    Gets the group and subgroup names of a given parameter

    Args:
        parameter (str): The HK parameter name

    Returns:

        group, subgroup (str): the strings of the group and subgroup of the parameter

    """
    for g in VALID_GROUPS:
        for s in VALID_SUBGROUPS:
            par_fname = hk_list_file_name(g, s)
            with par_fname.open(mode="r") as csv_file:
                csv_reader = csv.DictReader(csv_file)
                for row in csv_reader:
                    if parameter == row["HK_PAR"]:
                        return g, s
        print("Parameter %s does not exist" % parameter)
        return None, None


def get_hk_descriptions(group, subgroup):
    """Reads the list of housekeeping parameters with their own description.

    Args:
        group (str): The subgroup. It must either be ``BIAS``
            or ``DAQ``.

        subgroup (str): The group to load. It can either be ``POL_XY`` or
            ``BOARD_X``, with `X` being the module letter, and `Y`
            the number of the polarimeter.

    Returns:

        A dictionary containing the association between the name
        of the housekeeping parameter and its description.

    Examples::

        list = get_hk_descriptions("DAQ", "POL_G0")

    """
    check_group_and_subgroup(group, subgroup)
    par_fname = hk_list_file_name(group, subgroup)

    hklist = {}
    with par_fname.open(mode="r") as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            hklist[row["HK_PAR"]] = row["Description"]

    return HkDescriptionList(group, subgroup, hklist)


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


def extract_mean_from_time_range(times, values, time_range=None):
    """Calculate a mean value for a timeline

    Both "times" and "values" must be lists of values with the same
    length. The parameter `time_range` can either be `None` or a
    2-element tuple specifying the range of times to consider.

    """

    assert len(times) == len(values)

    if time_range:
        mjd_times = times.mjd
        mask = (mjd_times >= time_range[0]) & (mjd_times <= time_range[1])
        times = times[mask]
        values = values[mask]

        if len(values) > 3:
            average = np.mean(values)
        else:
            # Too few samples in the interval, interpolate
            # between the two extrema
            interpfn = interp1d(times, values, kind="previous")
            average = interpfn(time_range)
    else:
        average = np.mean(values)

    return average


class DataFile:
    """A HDF5 file containing timelines acquired by Strip

    This is basically a high-level wrapper over a `h5py.File`
    object. It assumes that the HDF5 file was saved by the acquisition
    software used in Bologna and Tenerife, and it provides some tools
    to navigate through the data saved in the file.

    Creating a `DataFile` object does not automatically open the file;
    this is done to preserve space. The file is lazily opened once you
    call one of the methods that need to access file data.

    The two methods you are going to use most of the time are:

    - :meth:`load_hk`
    - :meth:`load_sci`
    
    You can access these class fields directly:
    
    - ``filepath``: a ``Path`` object containing the full path of the
          HDF5 file

    - ``datetime``: a Python ``datetime`` object containing the time
          when the acquisition started

    - ``hdf5_groups``: a list of ``str`` objects containing the names
          of the groups in the HDF5 file. To initialize this field,
          you must call ``DataFile.read_file_metadata`` first.

    - ``polarimeters``: a Python ``set`` object containing the names
          of the polarimeters whose measurements have been saved in
          this file. To initialize this field, you must call
          ``DataFile.read_file_metadata`` first.

    - ``hdf5_file``: if the file has been opened using
          :meth:`read_file_metadata`, this is the `h5py.File` object.

    - ``tags``: a list of Tag objects; you must call
      :meth:`read_file_metadata` before reading it.

    This class can be used in ``with`` statements; in this case, it will
    automatically open and close the file::

        with DataFile(myfile) as inpf:
            # The variable "inpf" is a DataFile object in this context

    """

    def __init__(self, filepath):
        self.filepath = Path(filepath)

        try:
            self.datetime = parse_datetime_from_filename(self.filepath)
        except RuntimeError:
            self.datetime = None

            # Maybe this file was created by "join_hdf5.py". Let's check
            # it by looking for a section containing the names of the
            # files that have been joined
            with h5py.File(self.filepath, "r") as inpf:
                if "joined_files" in inpf and len(inpf["joined_files"]) > 0:
                    try:
                        self.datetime = parse_datetime_from_filename(
                            str(inpf["joined_files"][0], encoding="utf-8")
                        )
                    except RuntimeError:
                        pass

        self.hdf5_groups = []
        self.tags = None

    def __str__(self):
        return f'striptease.DataFile("{self.filepath}")'

    def read_file_metadata(self):
        "Open the file and checks the contents"

        self.hdf5_file = h5py.File(self.filepath, "r")
        self.hdf5_groups = list(self.hdf5_file)

        self.boards = scan_board_names(self.hdf5_groups)
        self.polarimeters = scan_polarimeter_names(self.hdf5_groups)

        self.tags = [
            Tag(
                x[0],
                x[1],
                x[2],
                bytes(x[3]).decode("utf-8"),
                bytes(x[4]).decode("utf-8"),
                bytes(x[5]).decode("utf-8"),
            )
            for x in self.hdf5_file["TAGS"]["tag_data"][:]
        ]

    def close_file(self):
        "Close the HDF5 file"

        if self.hdf5_file:
            self.hdf5_file.close()
            self.hdf5_file = None

    def __enter__(self):
        # Force opening the file and reading the metadata
        self.read_file_metadata()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_file()

    def load_hk(self, group, subgroup, par, verbose=False):
        """Loads scientific data from one detector of a given polarimeter

        Args:
        
            group (str): Either ``BIAS`` or ``DAQ``

            subgroup (str): Name of the housekeeping group. It can either
                be ``POL_XY`` or ``BOARD_X``, with `X` being the
                letter identifying the module, and `Y` the polarimeter
                number within the module. Possible examples are
                ``POL_G0`` and ``BOARD_Y``.

            par (str): Name of the housekeeping parameter,
                e.g. ``ID4_DIV``.

            verbose (bool): whether to echo the HK being loaded. Default is FALSE

        Returns:

             A tuple containing two NumPy arrays: the stream of times
             (using the astropy.time.Time datatype), and the stream of
             data.

        Example::

            from striptease.hdf5files import DataFile

            f = DataFile(filename)
            time, data = f.load_hk("POL_Y6", "BIAS", "VG4A_SET")

        """
        if not self.hdf5_groups:
            self.read_file_metadata()

        if verbose:
            print(f"{group.upper()}, {subgroup.upper()}, {par.upper()}")
        datahk = self.hdf5_file[subgroup.upper()][group.upper()][par.upper()]
        hk_time = Time(datahk["m_jd"], format="mjd")
        hk_data = datahk["value"]
        return hk_time, hk_data

    def load_sci(self, polarimeter, data_type, detector=[]):
        """Loads scientific data from one detector of a given polarimeter

        Args:

            polarimeter (str): Name of the polarimeter, in the form
                ``POL_XY`` or ``XY`` for short, with `X` being the
                module letter and `Y` the polarimeter number within
                the module.

            data_type (str): Type of data to load, either ``DEM`` or
                ``PWR``.

            detector (str): Either ``Q1``, ``Q2``, ``U1`` or ``U2``.
                You can also pass a list, e.g., ``["Q1", "Q2"]``. If
                no value is provided for this parameter, all the four
                detectors will be returned.

        Returns:

             A tuple containing two NumPy arrays: the stream of times
             (using the astropy.time.Time datatype), and the stream of
             data. For multiple detectors, the latter will be a list
             of tuples, where each column is named either ``DEMnn`` or
             ``PWRnn``, where ``nn`` is the name of the detector.


        Examples::

            from striptease.hdf5files import DataFile
            import numpy as np

            f = DataFile(filename)

            # Load the output of only one detector
            time, data = my_data.load_sci("POL_G0", "DEM", "Q1")
            print(f"Q1 mean output: {np.mean(data)}")

            # Load the output of several detectors at once
            time, data = my_data.load_sci("POL_G0", "DEM", ("Q1", "Q2"))
            print(f"Q1 mean output: {np.mean(data['DEMQ1'])}")

            # Load the output of all the four detectors
            time, data = my_data.load_sci("POL_G0", "DEM")
            print(f"Q1 mean output: {np.mean(data['DEMQ1'])}")

        """

        if not self.hdf5_groups:
            self.read_file_metadata()

        if len(polarimeter) == 2:
            polarimeter = "POL_" + polarimeter.upper()

        if not data_type.upper() in VALID_DATA_TYPES:
            raise ValueError(f"Invalid data type {data_type}")

        data_type = data_type.upper()

        scidata = self.hdf5_file[polarimeter]["pol_data"]

        scitime = Time(scidata["m_jd"], format="mjd")

        if isinstance(detector, str):
            if not detector.upper() in VALID_DETECTORS:
                raise ValueError(f"Invalid detector {detector}")
            detector = detector.upper()

            column_selector = f"{data_type}{detector}"
        else:
            if not detector:
                detector = ["Q1", "Q2", "U1", "U2"]

            column_selector = tuple([f"{data_type}{x}" for x in detector])

        return scitime, scidata[column_selector]

    def get_average_biases(
        self, polarimeter, time_range=None, calibration_tables=None
    ) -> BiasConfiguration:
        """Return a :class:`BiasConfiguration` object containing the average
values of biases for a polarimeter.

        The parameter `polarimeter` must be a string containing the
        name of the polarimeter, e.g., ``Y0``. The parameter
        `time_range`, if specified, is a 2-element tuple containing
        the start and end MJDs to consider in the average. If
        `calibration_tables` is specified, it must be an instance of
        the :class:`.CalibrationTables` class.

        The return value of this function is a :class:`BiasConfiguration` object

        If `calibration_tables` is specified, the values returned by
        this method are calibrated to physical units; otherwise, they
        are expressed in ADUs.

        """
        result = {}

        hk_name_to_parameter = {
            "VPIN": "vphsw",
            "IPIN": "iphsw",
        }
        for param_name in hk_name_to_parameter.keys():
            for phsw_pin in (0, 1, 2, 3):
                times, values = self.load_hk(
                    group="BIAS",
                    subgroup=f"POL_{polarimeter}",
                    par=f"{param_name}{phsw_pin}_HK",
                )

                average = extract_mean_from_time_range(times, values, time_range)

                if calibration_tables:
                    average = calibration_tables.adu_to_physical_units(
                        polarimeter=polarimeter,
                        hk=hk_name_to_parameter[param_name],
                        component=phsw_pin,
                        value=average,
                    )

                x = f"{param_name}{phsw_pin}".lower()
                result[x] = average

        parameter_to_hk_name = {
            "vgate": "vg",
            "vdrain": "vd",
            "idrain": "id",
        }
        for parameter in parameter_to_hk_name.keys():
            for amplifier in ["0", "1", "2", "3", "4", "4A", "5", "5A"]:
                try:
                    times, values = self.load_hk(
                        group="BIAS",
                        subgroup=f"POL_{polarimeter}",
                        par=f"{parameter_to_hk_name[parameter]}{amplifier}_HK",
                    )
                except KeyError:
                    # This usually happens with names like "VD4A_HK";
                    # we simply ignore them
                    continue

                average = extract_mean_from_time_range(times, values, time_range)

                if calibration_tables:
                    average = calibration_tables.adu_to_physical_units(
                        polarimeter=polarimeter,
                        hk=parameter,
                        component=f"H{amplifier}",
                        value=average,
                    )

                x = f"{parameter_to_hk_name[parameter]}{amplifier}".lower()
                result[x] = average

        return BiasConfiguration(**result)


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
