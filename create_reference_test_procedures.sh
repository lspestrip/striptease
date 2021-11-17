#!/bin/bash

set -e

readonly output_dir="$1"

if [ "$output_dir" == "" ]; then
	echo "Usage: $(basename $0) OUTPUT_DIR"
	echo ""
	echo "Create the set of JSON files to run the reference test for each board"
	exit 1
fi

# Create the directory, if it does not exist
mkdir -p "$output_dir"

for board in R O Y G B V I; do
	python3 program_reference_test1.py $board > "${output_dir}/reftest_${board}_1.json"
	python3 program_reference_test2.py $board > "${output_dir}/reftest_${board}_2.json"
	python3 program_reference_test3.py $board > "${output_dir}/reftest_${board}_3.json"
	python3 program_reference_test4.py $board > "${output_dir}/reftest_${board}_4.json"
done

python3 program_reference_test1.py > "${output_dir}/reftest_all_1.json"
python3 program_reference_test2.py > "${output_dir}/reftest_all_2.json"
python3 program_reference_test3.py > "${output_dir}/reftest_all_3.json"
python3 program_reference_test4.py > "${output_dir}/reftest_all_4.json"
