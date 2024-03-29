# -*- encoding: utf-8 -*-

"""
Striptease
"""

from .unittests import (
    UnitTestType,
    UnitTest,
    unit_test_url,
    unit_test_json_url,
    unit_test_download_url,
    get_unit_test,
    UnitTestDCCurves,
    UnitTestDC,
    UnitTestTimestream,
    load_unit_test_data,
)
from .biases import (
    BiasConfiguration,
    ChannelCalibration,
    InstrumentBiases,
    BoardCalibration,
    RefBiasConfiguration,
    ReferenceBiases,
)
from .diagnostics import (
    TagEvent,
    script_to_tagevents,
    plot_tagevents,
)
from .hdf5db import (
    DataStorage,
    HDF5FileInfo,
)
from .hdf5files import (
    HDF5_GZIP_FILE_SUFFIXES,
    HDF5_BZIP2_FILE_SUFFIXES,
    HDF5_ZSTD_FILE_SUFFIXES,
    HDF5_XZ_FILE_SUFFIXES,
    HDF5_RAW_FILE_SUFFIXES,
    HDF5_FILE_SUFFIXES,
    Tag,
    HkDescriptionList,
    find_first_and_last_samples_in_hdf5,
    get_group_subgroup,
    get_hk_descriptions,
    DataFile,
)
from .procedures import (
    dump_procedure_as_json,
    StripProcedure,
)
from .runlog import (
    RUN_LOG_FILE_PATH,
    RUN_LOG_DATETIME_FORMAT,
    RunLogEntry,
    connect_to_run_log,
    append_to_run_log,
)
from .stripconn import (
    StripConnection,
    StripTag,
    wait_with_tag,
)
from .utilities import (
    STRIP_BOARD_NAMES,
    BOARD_TO_W_BAND_POL,
    PolMode,
    OPEN_LOOP_MODE,
    CLOSED_LOOP_MODE,
    PhswPinMode,
    normalize_polarimeter_name,
    get_polarimeter_board,
    get_polarimeter_index,
    get_lna_num,
    get_lna_list,
    parse_polarimeters,
    polarimeter_iterator,
)


__version__ = "0.1.0"

__all__ = [
    # unittests
    "UnitTestType",
    "UnitTest",
    "unit_test_url",
    "unit_test_json_url",
    "unit_test_download_url",
    "get_unit_test",
    "UnitTestDCCurves",
    "UnitTestDC",
    "UnitTestTimestream",
    "load_unit_test_data",
    # biases.py
    "BiasConfiguration",
    "ChannelCalibration",
    "InstrumentBiases",
    "BoardCalibration",
    "RefBiasConfiguration",
    "ReferenceBiases",
    # diagnostics.py
    "TagEvent",
    "script_to_tagevents",
    "plot_tagevents",
    # hdf5db.py
    "DataStorage",
    "HDF5FileInfo",
    # hdf5files.py
    "HDF5_GZIP_FILE_SUFFIXES",
    "HDF5_BZIP2_FILE_SUFFIXES",
    "HDF5_ZSTD_FILE_SUFFIXES",
    "HDF5_XZ_FILE_SUFFIXES",
    "HDF5_RAW_FILE_SUFFIXES",
    "HDF5_FILE_SUFFIXES",
    "Tag",
    "HkDescriptionList",
    "find_first_and_last_samples_in_hdf5",
    "get_group_subgroup",
    "get_hk_descriptions",
    "DataFile",
    "scan_data_path",
    # procedures.py
    "dump_procedure_as_json",
    "StripProcedure",
    # runlog.py
    "RUN_LOG_FILE_PATH",
    "RUN_LOG_DATETIME_FORMAT",
    "RunLogEntry",
    "connect_to_run_log",
    "append_to_run_log",
    # stripconn.py
    "StripConnection",
    "StripTag",
    "wait_with_tag",
    # utilities.py
    "STRIP_BOARD_NAMES",
    "BOARD_TO_W_BAND_POL",
    "PolMode",
    "OPEN_LOOP_MODE",
    "CLOSED_LOOP_MODE",
    "PhswPinMode",
    "normalize_polarimeter_name",
    "get_polarimeter_board",
    "get_polarimeter_index",
    "get_lna_num",
    "get_lna_list",
    "parse_polarimeters",
    "polarimeter_iterator",
]
