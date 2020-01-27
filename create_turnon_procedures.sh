#!/bin/bash

set -e

readonly output_dir="$1"

function create_board_script {
	board="$1"
	pol="$2"
	basename="$3"

	python3 program_turnon.py --board $board $board > "${basename}_turnon.json"
	python3 program_turnon.py --turnoff --board $board $board > "${basename}_turnoff.json"
}

if [ "$output_dir" == "" ]; then
	echo "Usage: $(basename $0) OUTPUT_DIR"
	echo ""
	echo "Create the set of JSON files to turn on and off the polarimeters"
	exit 1
fi

for pair in V_W4 R_W3 O_W2 Y_W1 G_W6 B_W5; do
	board=$(echo $pair | head -c 1)
	pol=$(echo $pair | tail -c 3)
	create_board_script $board $pol "$output_dir/$pair"
done

for board in R O Y G B V I; do
	create_board_script $board $board "$output_dir/${board}_all"
	for num in $(seq 0 6); do
		create_board_script $board $board "$output_dir/${board}${num}"
	done
done
