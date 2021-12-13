#!/bin/bash

set -e

readonly pre_acquisition_time_proc1_s=60
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

for ult_case in ult no_ult; do
    if [ "$ult_case" == "no_ult" ]; then
        ult_switch="--no-unit-level-tests"
    else
        ult_switch=""
    fi

    for board in R O Y G B V I; do
            python3 program_phsw_curves.py \
                    --pre-acquisition-time $pre_acquisition_time_proc1_s \
                    --output "${output_dir}/phsw_curves_${board}_1_${ult_case}.json" \
                    ${ult_switch} \
                    1 $board

            python3 program_phsw_curves.py \
                    --pre-acquisition-time $pre_acquisition_time_proc2_s \
                    --turn-on \
                    --output "${output_dir}/phsw_curves_${board}_2_${ult_case}_turnon.json" \
                    ${ult_switch} \
                    2 $board

            python3 program_phsw_curves.py \
                    --pre-acquisition-time $pre_acquisition_time_proc2_s \
                    --output "${output_dir}/phsw_curves_${board}_2_${ult_case}_no_turnon.json" \
                    ${ult_switch} \
                    2 $board
    done

    python3 program_phsw_curves.py \
            --pre-acquisition-time $pre_acquisition_time_proc1_s \
            --output "${output_dir}/phsw_curves_all_1_${ult_case}.json" \
            ${ult_switch} \
            1

    python3 program_phsw_curves.py \
            --pre-acquisition-time $pre_acquisition_time_proc2_s \
            --turn-on \
            --output "${output_dir}/phsw_curves_all_2_${ult_case}_turnon.json" \
            ${ult_switch} \
            2

    python3 program_phsw_curves.py \
            --pre-acquisition-time $pre_acquisition_time_proc2_s \
            --output "${output_dir}/phsw_curves_all_2_${ult_case}_no_turnon.json" \
            ${ult_switch} \
            2
done
