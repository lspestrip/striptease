#!/bin/bash

set -e

readonly output_dir="$1"

readonly short_wait_time_s=120
readonly proc3_long_wait_time_s=1800
readonly proc4_long_wait_time_s=7200

if [ "$output_dir" == "" ]; then
	echo "Usage: $(basename $0) OUTPUT_DIR"
	echo ""
	echo "Create the set of JSON files to run the reference test for each board"
	exit 1
fi

# Create the directory, if it does not exist
mkdir -p "$output_dir"

for board in R O Y G B V I; do
    python3 program_reference_test1.py \
            --wait-time-s=$short_wait_time_s \
            $board > "${output_dir}/reftest_${board}_1.json"
    python3 program_reference_test2.py \
            --wait-time-s=$short_wait_time_s \
            $board > "${output_dir}/reftest_${board}_2.json"
    python3 program_reference_test3.py \
            --wait-time-s=$short_wait_time_s \
            --long-wait-time-s=$proc3_long_wait_time_s \
            $board > "${output_dir}/reftest_${board}_3.json"
    python3 program_reference_test4.py \
            --wait-time-s=$short_wait_time_s \
            --long-wait-time-s=$proc4_long_wait_time_s \
            $board > "${output_dir}/reftest_${board}_4.json"
done

python3 program_reference_test1.py \
        --wait-time-s=$short_wait_time_s \
        > "${output_dir}/reftest_all_1.json"
python3 program_reference_test2.py \
        --wait-time-s=$short_wait_time_s \
        > "${output_dir}/reftest_all_2.json"
python3 program_reference_test3.py \
        --wait-time-s=$short_wait_time_s \
        --turn-on \
        --long-wait-time-s=$proc3_long_wait_time_s \
        > "${output_dir}/reftest_all_3.json"
python3 program_reference_test4.py \
        --wait-time-s=$short_wait_time_s \
        --turn-on \
        --long-wait-time-s=$proc4_long_wait_time_s \
        > "${output_dir}/reftest_all_4.json"
