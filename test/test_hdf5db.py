# -*- encoding: utf-8 -*-

from dataclasses import dataclass
from typing import Tuple

from striptease import (
    DataStorage,
)


@dataclass
class MockDataFile:
    mjd_range: Tuple[float, float]


def test_hdf5db(tmp_path: str):
    # We pass an empty path, so we are sure that the list of files will be empty
    ds = DataStorage(tmp_path)

    # Fill the list with some mock objects
    ds.file_list = [
        MockDataFile(mjd_range=(0.0, 1.0)),
        MockDataFile(mjd_range=(1.1, 2.0)),
        MockDataFile(mjd_range=(2.1, 5.0)),  # There is a gap after this file
        MockDataFile(mjd_range=(8.1, 9.0)),
    ]

    assert ds._files_in_range((0.2, 0.8)) == [0]
    assert ds._files_in_range((0.2, 1.8)) == [0, 1]
    assert ds._files_in_range((0.2, 2.0)) == [0, 1]
    assert ds._files_in_range((1.0, 1.9)) == [0, 1]
    assert ds._files_in_range((8.4, 8.5)) == [3]
    assert ds._files_in_range((0.0, 10.0)) == [0, 1, 2, 3]

    # Out-of-bounds times
    assert not ds._files_in_range((-3.0, -1.0))
    assert not ds._files_in_range((11.0, 12.0))

    # A time falling within the gap in ]5.0, 8.0[
    assert not ds._files_in_range((6.0, 7.0))
