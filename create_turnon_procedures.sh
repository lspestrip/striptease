#!/bin/bash

readonly output_dir="$1"

function create_board_script {
	board="$1"
	pol="$2"
	basename="$3"

        echo "Creating turnon/turnoff procedures for $pol"
        for condition in warm cryo; do
            biases="./data/default_biases_${condition}.xlsx"
            python3 program_turnon.py \
                --bias-table-file "$biases" \
                --output "${basename}_turnon_${condition}.json" \
                --board $board \
                $pol
            python3 program_turnon.py \
                --bias-table-file "$biases" \
                --output "${basename}_turnoff_${condition}.json" \
                --board $board \
                --turnoff \
                $pol
        done
}

if [ "$output_dir" == "" ]; then
	echo "Usage: $(basename $0) OUTPUT_DIR"
	echo ""
	echo "Create the set of JSON files to turn on and off the polarimeters"
	exit 1
fi

# Create the directory, if it does not exist
mkdir -p "$output_dir"

for pair in V_W4 R_W3 O_W2 Y_W1 G_W6 B_W5; do
	board=$(echo $pair | head -c 1)
	pol=$(echo $pair | tail -c 3)
	create_board_script $board $pol "$output_dir/$pair"
done

for board in R O Y G B V I; do
	for num in $(seq 0 6); do
		create_board_script $board "$board$num" "$output_dir/${board}${num}"
	done
	create_board_script $board $board "$output_dir/${board}_all"
done

for condition in cryo warm; do
    ./join_scripts.py $(ls "$output_dir"/*_all_turnon_${condition}.json | sort) \
                      > "$output_dir"/all_turnon_${condition}.json
    ./join_scripts.py $(ls "$output_dir"/*_all_turnoff_${condition}.json | sort) \
                      > "$output_dir"/all_turnoff_${condition}.json
end
