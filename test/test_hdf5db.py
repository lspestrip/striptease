# -*- encoding: utf-8 -*-

from dataclasses import dataclass
import sqlite3
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

    ds.db = sqlite3.connect(":memory:")
    ds.db.execute(
        """
CREATE TABLE IF NOT EXISTS files(
    path TEXT,
    size_in_bytes NUMBER,
    first_sample REAL,
    last_sample REAL
)
    """
    )
    ds.db.executemany(
        "INSERT INTO files VALUES (:path, 0, :first_sample, :last_sample)",
        [
            ("a", 0.0, 1.0),
            ("b", 1.1, 2.0),
            ("c", 2.1, 5.0),  # There is a gap after this file
            ("d", 8.1, 9.0),
        ],
    )
    ds.db.commit()

    def get_file_names(file_entries):
        # ds._files_in_range returns a FileEntry type, but for these
        # tests we are only interested in the name (first field)
        return [x[0] for x in file_entries]

    assert get_file_names(ds._files_in_range((0.2, 0.8))) == ["a"]
    assert get_file_names(ds._files_in_range((0.2, 1.8))) == ["a", "b"]
    assert get_file_names(ds._files_in_range((0.2, 2.0))) == ["a", "b"]
    assert get_file_names(ds._files_in_range((1.0, 1.9))) == ["a", "b"]
    assert get_file_names(ds._files_in_range((8.4, 8.5))) == ["d"]
    assert get_file_names(ds._files_in_range((0.0, 10.0))) == ["a", "b", "c", "d"]

    # Out-of-bounds times
    assert not ds._files_in_range((-3.0, -1.0))
    assert not ds._files_in_range((11.0, 12.0))

    # A time falling within the gap in ]5.0, 8.0[
    assert not ds._files_in_range((6.0, 7.0))
