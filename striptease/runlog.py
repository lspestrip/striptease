from collections import namedtuple
from datetime import datetime
import json
from pathlib import Path
import pyzstd
import sqlite3
from typing import Any, List, Union

"""A ``Path`` object that represents the SQLite3 database
containing a log of all the procedures that have been ran.
"""
RUN_LOG_FILE_PATH = Path.home() / ".strip" / "run_log.db"

RUN_LOG_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

RunLogEntry = namedtuple(
    "RunLogEntry",
    [
        "id",
        "start_time",
        "end_time",
        "wait_time_s",
        "wait_cmd_time_s",
        "full_path",
        "number_of_commands",
        "zstd_json_procedure",
    ],
)


def connect_to_run_log() -> sqlite3.Connection:
    """Connect to the run log database or create one if it does not exist"""

    run_log_dir = RUN_LOG_FILE_PATH.parent
    run_log_dir.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(str(RUN_LOG_FILE_PATH))
    curs = db.cursor()
    curs.execute(
        """
CREATE TABLE IF NOT EXISTS run_log(
    start_time TEXT,
    end_time TEXT,
    wait_time_s NUMBER,
    wait_cmd_time_s NUMBER,
    full_path TEXT,
    number_of_commands NUMBER,
    zstd_json_procedure BLOB
)
"""
    )
    db.commit()

    return db


def append_to_run_log(
    start_time: datetime,
    end_time: datetime,
    wait_time_s: Union[int, float],
    wait_cmd_time_s: Union[int, float],
    full_path: str,
    procedure: List[Any],
):
    """Add a new entry to the log of procedures that have been executed.

    This function adds a new entry to the database that keeps track of all
    the JSON procedures that have been executed by this user. The procedure
    is saved in the database using the JSON format and the Zstandard
    compression, and it should not take too much space (the average
    compression ratio is ~10³).
    """

    json_proc = json.dumps(procedure)

    db = connect_to_run_log()
    curs = db.cursor()
    curs.execute(
        """
INSERT INTO run_log VALUES (
    :start_time,
    :end_time,
    :wait_time_s,
    :wait_cmd_time_s,
    :full_path,
    :number_of_commands,
    :zstd_json_procedure
)
        """,
        {
            "start_time": start_time.strftime(RUN_LOG_DATETIME_FORMAT),
            "end_time": end_time.strftime(RUN_LOG_DATETIME_FORMAT),
            "wait_time_s": wait_time_s,
            "wait_cmd_time_s": wait_cmd_time_s,
            "full_path": full_path,
            "number_of_commands": len(procedure),
            "zstd_json_procedure": pyzstd.compress(
                json_proc.encode("utf-8"), level_or_option=12
            ),
        },
    )
    db.commit()
