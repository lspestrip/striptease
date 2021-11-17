#!/bin/bash

set -e

readonly output_dir="$1"

if [ "$output_dir" == "" ]; then
	echo "Usage: $(basename $0) OUTPUT_DIR"
	echo ""
	echo "Create the set of JSON files to run the PH/SW test for each board"
	exit 1
fi

# Create the directory, if it does not exist
mkdir -p "$output_dir"

for board in R O Y G B V I; do
	python3 program_phsw_curves1.py $board > "${output_dir}/phsw_curves_${board}_1.json"
	python3 program_phsw_curves2.py $board > "${output_dir}/phsw_curves_${board}_2.json"
done

python3 program_phsw_curves1.py > "${output_dir}/phsw_curves_all_1.json"
python3 program_phsw_curves2.py > "${output_dir}/phsw_curves_all_2.json"
