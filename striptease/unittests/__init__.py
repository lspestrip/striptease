# -*- encoding: utf-8 -*-

"Functions to download and retrieve data from the Strip unit tests."


from dataclasses import dataclass, field
from datetime import date
from enum import Enum
import json
from pathlib import Path
import sqlite3
from shutil import copyfileobj
from typing import Any, Dict, Union
import urllib.request as urlreq
from urllib.parse import urljoin

import h5py
import numpy as np

DEFAULT_UNIT_TEST_SERVER = "https://striptest.fisica.unimi.it"
DEFAULT_UNIT_TEST_CACHE_PATH = Path.home() / ".strip" / "unittests" / "unittests.db"


class UnitTestType(Enum):
    DC_CHARACTERIZATION = 1
    SHORT_ACQUISITION = 2
    BANDPASS_MEASUREMENT = 3
    NOISE_TEMPERATURE_MEASUREMENT = 4
    STABLE_ACQUISITION = 5


__STRING_TO_UNIT_TEST_TYPE = {
    "DC characterization": UnitTestType.DC_CHARACTERIZATION,
    "Bandpass characterization": UnitTestType.BANDPASS_MEASUREMENT,
    "Y-factor test": UnitTestType.NOISE_TEMPERATURE_MEASUREMENT,
    "Long acquisition": UnitTestType.STABLE_ACQUISITION,
    "Short acquisition with HEMTs turned off": UnitTestType.SHORT_ACQUISITION,
}


@dataclass
class UnitTest:
    """Information about a polarimetric unit test

    This class hold some information about the data of a polarimetric
    unit test ran in Bologna, and it is returned by the function
    :func:`.get_unit_test`. It contains the following fields:

    - ``url``: a string containing the base URL of the test

    - ``metadata``: a dictionary containing the JSON record downloaded
      from the web server. This dictionary contains many details about
      the test itself: the name of the operators that actually
      executed the test, the date when the data was acquired, etc.

    - ``hdf5_file_path``: a ``pathlib.Path`` object pointing to the
      HDF5 file saved in the local cache. Instead of accessing this
      file directly, you should instead call
      :func:`.load_unit_test_data`.

    """

    url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    hdf5_file_path: Path = Path()

    @property
    def polarimeter_number(self) -> int:
        "Return the number of the polarimeter that was tested (e.g., 2 for ``STRIP02``)"
        return int(self.metadata["polarimeter_number"])

    @property
    def polarimeter_name(self) -> str:
        "Return the name of the polarimeter that was tested (e.g., ``STRIP02``)"
        return f"STRIP{self.polarimeter_number:02d}"

    @property
    def is_cryogenic(self) -> bool:
        "Return ``True`` if the test was done in cryogenic conditions"
        return bool(self.metadata["cryogenic"])

    @property
    def acquisition_date(self) -> date:
        "Return a ``datetime.date`` object containing the date of the acquisition"
        return date.fromisoformat(self.metadata["acquisition_date"])

    @property
    def test_type(self) -> UnitTestType:
        "Return a :class:`UnitTestType` instance specifying the kind of test"
        return __STRING_TO_UNIT_TEST_TYPE[self.metadata["test_type"]]


def unit_test_url(test_num: int, server=DEFAULT_UNIT_TEST_SERVER) -> str:
    "Return a string containing the URL of a unit-level test"
    return urljoin(server, f"/unittests/tests/{int(test_num)}")


def unit_test_json_url(test_num: int, server=DEFAULT_UNIT_TEST_SERVER) -> str:
    "Return a string containing the URL of the JSON record for a unit-level test"
    return unit_test_url(test_num, server) + "/json"


def unit_test_download_url(test_num: int, server=DEFAULT_UNIT_TEST_SERVER) -> str:
    "Return a string containing the URL used to download the HDF5 file of a test"
    return unit_test_url(test_num, server) + "/download"


def __unit_test_file_local_path(
    test_num: int, local_cache=DEFAULT_UNIT_TEST_CACHE_PATH
):
    return local_cache.parent / f"{test_num:05d}.h5"


def __init_cache_db(db: sqlite3.Connection):
    curs = db.cursor()
    curs.execute(
        """
CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY,
        url STRING NOT NULL UNIQUE,
        metadata STRING,
        hdf5_file_path STRING
)
"""
    )


def __get_test_from_cache(
    db: sqlite3.Connection, test_num: int, server: str
) -> UnitTest:
    curs = db.cursor()
    url = unit_test_url(test_num, server)
    curs.execute(
        """
SELECT
    url,
    metadata,
    hdf5_file_path
FROM tests WHERE url = ?""",
        (url,),
    )

    entry = curs.fetchone()
    if not entry:
        return None

    (_, metadata_str, hdf5_file_path) = entry

    metadata = json.loads(metadata_str)
    return UnitTest(url=url, metadata=metadata, hdf5_file_path=Path(hdf5_file_path))


def __download_test(
    db: sqlite3.Connection, test_num: int, server: str, local_cache: Path
) -> UnitTest:
    # Download the metadata from the db (JSON record)
    response = urlreq.urlopen(unit_test_json_url(test_num, server))
    metadata_str = response.read().decode("utf-8")

    # This is for validation
    _ = json.loads(metadata_str)

    # Download a copy of the HDF5 file
    response = urlreq.urlopen(unit_test_download_url(test_num, server))
    hdf5_file_path = __unit_test_file_local_path(test_num, local_cache)
    with open(hdf5_file_path, "wb") as outf:
        copyfileobj(response, outf)

    # Add the entry to the cache database
    curs = db.cursor()
    curs.execute(
        """
INSERT INTO tests (
    url,
    metadata,
    hdf5_file_path
)
VALUES (?, ?, ?)
""",
        (unit_test_url(test_num, server), metadata_str, str(hdf5_file_path)),
    )
    db.commit()

    return __get_test_from_cache(db, test_num, server)


def get_unit_test(
    test_num: int,
    server=DEFAULT_UNIT_TEST_SERVER,
    local_cache=DEFAULT_UNIT_TEST_CACHE_PATH,
):
    """Return a :class:`UnitTest` object referring to a unit test.

    This function is used to access the data files acquired during the
    Strip Unit Tests done in Milano Bicocca. Each test is referenced
    by an unique number, which is passed in the parameter `test_num`.
    The parameter `server` must be a string containing the name of the
    web server hosting the test database. The parameter `local_cache`
    points to a file that will contain a local copy of each test
    downloaded from the webserver.

    The following code prints some information about test #354::

        from striptease.unittests import get_unit_test

        test = get_unit_test(354)
        print(f"The test was acquired on {test.acquisition_date}")

    Once you retrieve the information for a test, you can use
    :func:`.load_unit_test_data` to load the actual data acquired
    during the test.

    Args:

        test_num (int): the unique ID of the unit test to download

        server (str): the protocol+name/IP address of the web server
            that hosts the unit tests. The default is the variable
            ``DEFAULT_UNIT_TEST_SERVER``, and it should probably be ok
            for any situation.

        local_cache (Path): the path to a file that will contain a local
            copy of each test downloaded using this function. This speeds
            up subsequent queries to the same test.

    Return:

        An instance of :class:`UnitTest`.

    """

    # Ensure that the folder containing the cache database exists
    local_cache.parent.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(local_cache)
    __init_cache_db(db)

    test = __get_test_from_cache(db=db, test_num=test_num, server=server)
    if not test:
        test = __download_test(
            db=db, test_num=test_num, server=server, local_cache=local_cache
        )

    return test


@dataclass
class UnitTestDCCurves:
    """Characterization of one component in a unit test acquisition

    This class is used to hold the data acquired during the unit-level
    tests for the characterization of the components (e.g., amplifier,
    phase-switch, etc.) in a Strip polarimeter.

    The class has two fields:

    - ``acquisition_date``: a ``datetime.date` object containing the
      date when the test was acquired.

    - ``band``: a string containing either ``Q`` or ``W``;

    - ``is_cryogenic``: a Boolean value indicating whether the test
      was done in cryogenic or warm conditions;

    - ``polarimeter_name``: the name of the polarimeter being tested
      (e.g., ``STRIP02``);

    - ``url``: a string containing the URL of the test page

    - ``components``: a dictionary associating the name of each test
      (e.g., ``IDVD`` for the drain voltage-to-drain current test of
      an amplifier) with a NumPy matrix containing the results of the
      test. The meaning of the columns in the matrix depend on the
      kind of test, and they can be retrieved using the property
      ``.dtype.names``.

    Here is an example::

        import striptease.unittests as u

        test = u.get_unit_test(354)
        data = u.load_unit_test_data(test)

        # Pick a component and get the data of the tests associated
        # with it
        ha1_data = data.components["HA1"]

        for test_name, test_data in ha1_data.curves.items():
            print(f'Test "{test_name}"')
            for name in test_data.dtype.names:
                print(f"- {name}, avg: {np.mean(test_data[name]):.2e}")

        # Output:
        # Test "IDVD"
        # - DrainI, avg: 2.22e-03
        # - DrainV, avg: 4.70e-01
        # - GateI, avg: 9.99e-06
        # - GateV, avg: 2.00e-01
        # Test "IDVG"
        # - DrainI, avg: 2.19e-03
        # - DrainV, avg: 4.70e-01
        # - GateI, avg: 9.99e-06
        # - GateV, avg: 2.00e-01
    """

    polarimeter_name: str
    component_name: str
    acquisition_date: date
    band: str
    is_cryogenic: bool
    url: str
    curves: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnitTestDC:
    """Detailed information about a unit-level DC test of a polarimeter.

    This class is created by the function :func:`.load_unit_test_data`
    whenever a DC test is requested. It contains the following fields:

    - ``acquisition_date``: a ``datetime.date` object containing the
      date when the test was acquired.

    - ``band``: a string containing either ``Q`` or ``W``;

    - ``is_cryogenic``: a Boolean value indicating whether the test
      was done in cryogenic or warm conditions;

    - ``polarimeter_name``: the name of the polarimeter being tested
      (e.g., ``STRIP02``);

    - ``url``: a string containing the URL of the test page

    - ``components``: a dictionary associating the name of each
      component of the polarimeter (e.g., ``HA1`` for the first
      amplifier of the first leg) with a :class:`.UnitTestDCCurves`
      object, which contains the data of the various curves
      characterizing the polarimetric component.

    """

    acquisition_date: date
    band: str
    is_cryogenic: bool
    polarimeter_name: str
    url: str
    components: Dict[str, UnitTestDCCurves] = field(default_factory=dict)


@dataclass
class UnitTestTimestream:
    """A time stream acquired from one polarimeter during the Unit Level tests in Bicocca.

    This class is created by the function :func:`.load_unit_test_data`
    whenever the caller asks to load a unit-level test where a
    timestream is acquired (e.g., bandpass measurement, noise
    temperature characterization, etc.). It contains the following
    fields:

    - ``acquisition_date``: a ``datetime.date` object containing the
      date when the test was acquired.

    - ``band``: a string containing either ``Q`` or ``W``;

    - ``is_cryogenic``: a Boolean value indicating whether the test
      was done in cryogenic or warm conditions;

    - ``polarimeter_name``: the name of the polarimeter being tested
      (e.g., ``STRIP02``);

    - ``url``: a string containing the URL of the test page

    - ``time_s``: A NumPy array containing the time in seconds

    - ``pctime``: A NumPy array containing the On-board time, in clock
      ticks

    - ``phb``: A NumPy array containing the phase of the slow phase
      switch

    - ``record``: A NumPy array containing an undocumented field

    - ``demodulated``: A 4×N NumPy matrix containing the output of
       DEM0, DEM1, DEM2, DEM3 channels

    - ``power``: A 4×N NumPy matrix containing the output of PWR0,
       PWR1, PWR2, PWR3 channels

    - ``rfpower_db``: A NumPy array containing the power of the
       -radiofrequency generator, in dB, or 1 if turned off

    - ``freq_hz``: A NumPy array containing the frequency of the
       signal injected by the radiofrequency generator, in Hertz. If
       the generator is turned off, this is -1.

    """

    acquisition_date: date
    band: str
    is_cryogenic: bool
    polarimeter_name: str
    url: str
    time_s: Any = None
    pctime: Any = None
    phb: Any = None
    record: Any = None
    demodulated: Any = None
    power: Any = None
    rfpower_db: Any = None
    freq_hz: Any = None


def __load_unit_test_timestream(h5_file):
    attrs = dict(h5_file.attrs.items())
    dataset = h5_file["time_series"]
    return UnitTestTimestream(
        acquisition_date=date.fromisoformat(attrs["acquisition_date"]),
        band=attrs["band"],
        is_cryogenic=attrs["cryogenic"],
        polarimeter_name=attrs["polarimeter"],
        url=attrs["url"],
        time_s=dataset["time_s"].astype(np.float),
        pctime=dataset["pctime"].astype(np.float),
        phb=dataset["phb"].astype(np.int),
        record=dataset["record"].astype(np.int),
        demodulated=np.vstack(
            [
                dataset[x].astype(np.float)
                for x in ("dem_Q1_ADU", "dem_U1_ADU", "dem_U2_ADU", "dem_Q2_ADU")
            ]
        ).transpose(),
        power=np.vstack(
            [
                dataset[x].astype(np.float)
                for x in ("pwr_Q1_ADU", "pwr_U1_ADU", "pwr_U2_ADU", "pwr_Q2_ADU")
            ]
        ).transpose(),
        rfpower_db=dataset["rfpower_dB"].astype(np.float),
        freq_hz=dataset["freq_Hz"].astype(np.float),
    )


def __load_unit_test_dc(h5_file):
    attrs = dict(h5_file.attrs.items())

    test = UnitTestDC(
        acquisition_date=date.fromisoformat(attrs["acquisition_date"]),
        band=attrs["band"],
        is_cryogenic=attrs["cryogenic"],
        polarimeter_name=attrs["polarimeter"],
        url=attrs["url"],
    )

    for component_name in h5_file:
        component_datasets = h5_file[component_name]
        test.components[component_name] = UnitTestDCCurves(
            acquisition_date=test.acquisition_date,
            band=test.band,
            polarimeter_name=test.polarimeter_name,
            is_cryogenic=test.is_cryogenic,
            url=test.url,
            component_name=component_name,
            curves={
                test_name: np.array(component_datasets[test_name])
                for test_name in component_datasets
            },
        )

    return test


def load_unit_test_data(
    input_file: Union[str, Path, UnitTest]
) -> Union[UnitTestTimestream, UnitTestDC]:
    """Load an HDF5 file into a Timestream object

    Return either an instance of the class
    :class:`.UnitTestTimestream` or :class:`.UnitTestDC`. The choice
    between the two types depends on the type of the test (i.e., the
    value of the key ``test_type`` in the ``metadata`` of the test):

    1. DC tests return a :class:`.UnitTestDc`; these tests were
       acquired by directly sampling the biases at the components of
       the polarimeters, and no proper time streams were recorded.

    2. All other types of tests return a :class:`UnitTestTimestream`.

    The typical usage for this function is to call it on the result of
    a call to :func:`.get_unit_test`, as in the following example::

        import striptease.unittests as u

        test = u.get_unit_test(354)
        data = load_unit_test_data(test)

    Args:

        input_file: Either a string containing the path to a HDF5
            file, a ``pathlib.Path`` object, or a :class:`.UnitTest`
            object.

    Return:

        A pair containing two elements: (1) a dictionary containing a
        set of attributes read from the root object of the HDF5 file,
        and (2) either an instance of the class
        :class:`.UnitTestTimestream` or :class:`.UnitTestDC`,
        depending on the type of the test.

    """

    if isinstance(input_file, UnitTest):
        file_name = input_file.hdf5_file_path
    else:
        file_name = input_file

    with h5py.File(file_name, "r") as h5_file:
        if "time_series" in h5_file:
            return __load_unit_test_timestream(h5_file)
        else:
            return __load_unit_test_dc(h5_file)
