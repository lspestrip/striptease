#!/bin/bash

set -e

readonly pre_acquisition_time_proc1_s=120
readonly pre_acquisition_time_proc2_s=1800

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
	python3 program_phsw_curves.py \
		--pre-acquisition-time $pre_acquisition_time_proc1_s \
		--output "${output_dir}/phsw_curves_${board}_1.json" \
		1 $board

	python3 program_phsw_curves.py \
		--pre-acquisition-time $pre_acquisition_time_proc2_s \
		--turn-on \
		--output "${output_dir}/phsw_curves_${board}_2_turnon.json" \
		2 $board

	python3 program_phsw_curves.py \
		--pre-acquisition-time $pre_acquisition_time_proc2_s \
		--output "${output_dir}/phsw_curves_${board}_2_no_turnon.json" \
		2 $board
done

python3 program_phsw_curves1.py \
	--pre-acquisition-time $pre_acquisition_time_proc1_s \
	--output "${output_dir}/phsw_curves_all_1.json" \
	1

python3 program_phsw_curves2.py \
	--pre-acquisition-time $pre_acquisition_time_proc2_s \
	--turn-on \
	--output "${output_dir}/phsw_curves_all_2_turnon.json" \
	2

python3 program_phsw_curves2.py \
	--pre-acquisition-time $pre_acquisition_time_proc2_s \
	--output "${output_dir}/phsw_curves_all_2_no_turnon.json" \
	2
