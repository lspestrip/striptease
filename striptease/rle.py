# -*- encoding: utf-8 -*-

from dataclasses import dataclass

import astropy.time as astrotime
import numpy as np
from numba import njit


def _get_default_delta_time_s(time: astrotime.Time) -> float:
    "Estimate the average time interval between consecutive samples"
    return float(np.median((time[1:] - time[0:-1]).to("s").value))


@njit
def _find_consecutive_chunks(
    arr, expected_increment: float, output_runs, relative_tolerance: float = 0.1
):
    """
    Find the length of each run of uniformly-sampled values in `arr`

    This function detects runs of values in `arr` whose consecutive differences is approximately
    the same. The relative tolerance in the comparison is set through the `tolerance_factor`;
    setting it to 0 means that
    """
    output_idx = 0
    run_length = 1

    for i in range(1, len(arr)):
        if (arr[i] - arr[i - 1]) > ((1.0 + relative_tolerance) * expected_increment):
            # We got a time jump
            output_runs[output_idx] = run_length
            output_idx += 1
            run_length = 1
        else:
            run_length += 1

    output_runs[output_idx] = run_length
    output_idx += 1

    return output_idx


@dataclass
class RunLengthTime:
    """An array of astropy.time.Time values, compressed using the Run-Length Encoding algorithm

    Objects of this type are created using the :func:`.compress_times_rle`. They can be decompressed
    back using :func:`.decompress_times_rle`.

    The original Run-Length Encoding (RLE) algorithm works by finding sequences of repeated values and compressing
    them into a pair ``(value, count)``. If there are many repetitions in the sequence, the compression factor
    can be excellent.

    When compressing array of *times*, we consider repetitions in the interval between consecutive samples,
    so it's not strictly a RLE algorithm.

    The stream of times is encoded as a sequence of “chunks”; within each chunk, the sampling frequency is
    constant and free of gaps, so that it is enough to encode the value of the first (`start_times`) and
    last sample (`end_times`) in the chunk as well as the number of samples (`run_lengths`).

    For instance, consider the following sequence of times, acquired once every second::

        0, 1, 2, 3,    7, 8,    10, 11,    15,    21, 22, 23

    (Spaces have been added to highlight where the sequence has a discontinuity). The representation of this
    sequence using the class :`RunLengthTime` is the following::

        start_times = [0, 7, 11, 15, 21]
        end_times = [3, 8, 11, 15, 23]
        run_lengths = [4, 2, 2, 1, 3]
    """

    start_times: astrotime.Time
    end_times: astrotime.Time
    run_lengths: np.array


def compress_times_rle(
    time: astrotime.Time, dtype="int32", relative_tolerance: float = 0.1
) -> RunLengthTime:
    "Compress an array of times in a :class:`.RunLengthTime` object"

    time_s = (time - time[0]).to("s").value
    output_runs = np.empty(len(time), dtype=dtype)
    default_delta_time_s = _get_default_delta_time_s(time)
    num_of_chunks = _find_consecutive_chunks(
        time_s,
        expected_increment=default_delta_time_s,
        output_runs=output_runs,
        relative_tolerance=relative_tolerance,
    )
    output_runs = output_runs[0:num_of_chunks]

    result = RunLengthTime(
        start_times=astrotime.Time(np.zeros(len(output_runs)), format="mjd"),
        end_times=astrotime.Time(np.zeros(len(output_runs)), format="mjd"),
        run_lengths=output_runs,
    )
    result.start_times[0] = time[0]
    cur_idx = 0
    for idx, cur_run_length in enumerate(output_runs):
        result.start_times[idx] = time[cur_idx]
        result.end_times[idx] = time[cur_idx + cur_run_length - 1]
        cur_idx += cur_run_length

    return result


def decompress_times_rle(rle: RunLengthTime) -> astrotime.Time:
    assert len(rle.run_lengths) == len(rle.end_times)
    assert len(rle.end_times) == len(rle.start_times)

    num_of_samples = np.sum(rle.run_lengths)
    result = astrotime.Time(np.zeros(num_of_samples), format="mjd")

    cur_sample_idx = 0
    for cur_chunk_len, cur_start_time, cur_end_time in zip(
        rle.run_lengths, rle.start_times, rle.end_times
    ):
        result[cur_sample_idx : (cur_sample_idx + cur_chunk_len)] = np.linspace(
            cur_start_time, cur_end_time, num=cur_chunk_len
        )
        cur_sample_idx += cur_chunk_len

    return result
