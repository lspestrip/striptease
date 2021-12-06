# -*- encoding: utf-8 -*-

from collections import namedtuple
from io import BytesIO
from pathlib import Path
from typing import List, Set

# Compression libraries
import bz2
import gzip
import lzma
import pyzstd

from astropy.time import Time
import csv
import h5py
import numpy as np
from scipy.interpolate import interp1d

from .biases import BiasConfiguration

# Any MJD value smaller than this will be considered invalid. We must
# perform this kind of checks because the electronics has the nasty
# habit of registering a few samples here and there with dates that
# are way back in the past.
EARLIEST_ACCEPTABLE_MJD = Time("2018-01-01").mjd

VALID_GROUPS = ["BIAS", "DAQ"]
VALID_SUBGROUPS = ["POL", "BOARD"]
VALID_DETECTORS = ["Q1", "Q2", "U1", "U2"]
VALID_DATA_TYPES = ["PWR", "DEM"]

HDF5_GZIP_FILE_SUFFIXES = [".gz", ".gzip"]
HDF5_BZIP2_FILE_SUFFIXES = [".bz2", ".bzip2"]
HDF5_ZSTD_FILE_SUFFIXES = [".zst", ".zstd"]
HDF5_XZ_FILE_SUFFIXES = [".xz", ".lzma"]
HDF5_RAW_FILE_SUFFIXES = [".h5", ".hdf5"]
HDF5_FILE_SUFFIXES = (
    HDF5_GZIP_FILE_SUFFIXES
    + HDF5_BZIP2_FILE_SUFFIXES
    + HDF5_ZSTD_FILE_SUFFIXES
    + HDF5_XZ_FILE_SUFFIXES
    + HDF5_RAW_FILE_SUFFIXES
)


class HDF5ReadError(Exception):
    """Raised when a HDF5 file does not matches the specifications"""

    pass


#: Information about a tag loaded from a HDF5 file
#:
#: Fields are:
#:
#: - ``id``: unique integer number
#:
#: - ``mjd_start``: start time of the tag (MJD)
#:
#: - ``mjd_end``: stop time of the tag (MJD)
#:
#: - ``name``: string containing the name of the tag
#:
#: - ``start_comment``: comment put at the start
#:
#: - ``end_comment``: comment put at the end
Tag = namedtuple(
    "Tag", ["id", "mjd_start", "mjd_end", "name", "start_comment", "end_comment"]
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
        / "hk_pars_{}_{}.csv".format(subgroup.upper(), group.upper())
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


def find_first_and_last_samples_in_hdf5(hdf5_file):
    """Search the minimum and maximum MJD time in the HDF5 (slow!)

    Return the MJD of the first and last samples recorded in the HDF5
    file ``hdf5_file`` (which must have been already opened).

    If the HDF5 contains the ``FIRST_SAMPLE`` and ``LAST_SAMPLE``, the
    function returns these values; otherwise, it scans all the datasets
    and find the minimum. The latter options is quite slow (it takes
    several seconds for file), but it is needed because the data server
    currently (2021/11/18) has a bug that prevents valid values from
    being written into HDF5 files.
    """

    min_mjd = hdf5_file.attrs.get("FIRST_SAMPLE", -1)
    if min_mjd < EARLIEST_ACCEPTABLE_MJD:
        min_mjd = -1

    max_mjd = hdf5_file.attrs.get("LAST_SAMPLE", -1)
    if max_mjd < EARLIEST_ACCEPTABLE_MJD:
        max_mjd = -1

    def find_extrema(name, obj):
        nonlocal min_mjd, max_mjd
        if isinstance(obj, h5py.Dataset) and len(obj) > 0:
            if (obj.dtype.names is not None) and ("m_jd" in obj.dtype.names):
                mjd = obj["m_jd"]
                # Filter out bad values
                mjd = mjd[mjd >= EARLIEST_ACCEPTABLE_MJD]

                cur_min = mjd[0]
                cur_max = mjd[-1]
                if (min_mjd < 0) or (cur_min < min_mjd):
                    min_mjd = cur_min
                if (max_mjd < 0) or (cur_max > max_mjd):
                    max_mjd = cur_max

    if (min_mjd < 0) or (max_mjd < 0):
        # No meaningful values for FIRST_SAMPLE and LAST_SAMPLE:
        # use the slow approach of crawling through all the datasets
        # in the file
        hdf5_file.visititems(find_extrema)

    return min_mjd, max_mjd


def _open_file(filepath, filemode):
    "Open a HDF5 file, applying a decompression step if necessary"

    suffix = Path(filepath).suffix
    if suffix not in HDF5_FILE_SUFFIXES:
        raise HDF5ReadError(f'Unknown file suffix {suffix} for file "{filepath}"')

    decompressor_fn = None
    if suffix in HDF5_GZIP_FILE_SUFFIXES:
        decompressor_fn = gzip.decompress
    elif suffix in HDF5_BZIP2_FILE_SUFFIXES:
        decompressor_fn = bz2.decompress
    elif suffix in HDF5_ZSTD_FILE_SUFFIXES:
        decompressor_fn = pyzstd.decompress
    elif suffix in HDF5_XZ_FILE_SUFFIXES:
        decompressor_fn = lzma.decompress
    elif suffix in HDF5_RAW_FILE_SUFFIXES:
        # In this case we just call h5py.File with no pre-loading
        return h5py.File(filepath, filemode)

    assert filemode == "r", "Compressed HDF5 files are read-only"
    assert (
        decompressor_fn is not None
    ), f"Unhandled suffix {suffix} in DataFile._open_file"
    with open(filepath, "rb") as inpf:
        stream = BytesIO(decompressor_fn(inpf.read()))

    return h5py.File(stream, filemode)


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

    - ``mjd_range``: a pair of ``float`` numbers representing the
          MJD of the first and last sample in the file. To initialize
          this field, you must call ``DataFile.read_file_metadata``
          first.

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

    def __init__(self, filepath, filemode="r"):
        self.filepath = Path(filepath)
        self.filemode = filemode

        self.mjd_range = None
        self.hdf5_groups = []
        self.tags = None
        self.hdf5_file = None

    def __str__(self):
        return f'striptease.DataFile("{self.filepath}")'

    def read_file_metadata(self, force=False):
        """Open the file and retrieve some basic metadata

        This function opens the HDF5 file and retrieves the following information:

        - List of groups under the root node

        - List of boards for whom some data was saved in the file

        - List of polarimeters that have some data saved in the file

        - List of tags

        - MJD of the first and last scientific/housekeeping sample in the file

        This function is *idempotent*, in the sense that calling it twice will not force
        a re-read of the metadata. To override this behavior, pass ``force=True``: the
        function will re-open the file and read all the metadata again.
        """

        if self.hdf5_file:
            if not force:
                return
            else:
                self.hdf5_file.close()
                del self.hdf5_file

        self.hdf5_file = _open_file(self.filepath, self.filemode)

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

        self.mjd_range = find_first_and_last_samples_in_hdf5(self.hdf5_file)

    def __enter__(self):
        # Force opening the file and reading the metadata
        self.read_file_metadata()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.hdf5_file.close()
        del self.hdf5_file

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

        hk_name_to_parameter = {"VPIN": "vphsw", "IPIN": "iphsw"}
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

        parameter_to_hk_name = {"vgate": "vg", "vdrain": "vd", "idrain": "id"}
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
