# StripTEASE - Strip TEst Analysis for System Evaluation

[![Documentation Status](https://readthedocs.org/projects/striptease/badge/?version=latest)](https://striptease.readthedocs.io/en/latest/?badge=latest)
[![Tests](https://github.com/lspestrip/striptease/workflows/Tests/badge.svg?branch=master&event=push)](https://github.com/lspestrip/striptease/actions?query=workflow%3ATests+branch%3Amaster)


This repository contains the code used to perform tests and anlyze results for
the STRIP system level tests. It uses Python 3.7.x and Qt 5.

## Installation

This package is peculiar, because at the moment it is not supposed to be installed using `pip install`. Instead, you should clone the repository and always work within it.

Run the following commands to clone this repository on your computer (you must have `git`):

    git clone git@github.com:lspestrip/striptease.git
    cd striptease
    pip install --user -r requirements.txt

You can drop `--user` if you are working in a virtual environment (as you should!).

If you plan to modify the source code and make pull requests, run the following command as well:

    pre-commit install

## How to use the code

Once you have configured the library using the
[documentation](https://striptease.readthedocs.io/en/latest/authentication.html),
you can happily use IPython or a Jupyter notebook to write your code.
Start with the following command:

```python
from striptease import Connection
c = Connection()
c.login()
```

## Contributing

See file
[CONTRIBUTING.md](https://github.com/lspestrip/striptease/blob/master/CONTRIBUTING.md).

## Running long scripts

Programs like `program_turnon.py` generate JSON files that can be fed either to `program_batch_runner.py` or TestRunner`. To generate a JSON file that turns on all the polarimeters in board `G`, run the following from the command line:

```bash
python program_turnon.py -o turnon.json G
```

Now you can use the command-line utility `program_batch_runner.py` to run it:

```bash
./program_batch_runner.py turnon.json
```

While the program is running, you can use the following keys:

- `SPACE` or `p` pauses the execution (press any key to resume);
- `l` enters a log message;
- `q` prompt the users if it is necessary to quit the script.


## Description of the available programs

### Turn-on procedure

To produce a JSON file that contains the turn-on procedure for one or more radiometers, run

```bash
./program_turnon.py [args] POLARIMETER [POLARIMETER...]
```

Use the switch `--help` to get a full list of the available parameters. The procedure is written to the terminal, so you surely want to save it in a file; either use the syntax `> JSON_FILE` or the `-o` flag to do this.

The specification for `POLARIMETER` can be one of the following:

- A module name, like `G` or `R`: in this case, all the polarimeters belonging to that module will be turned on in sequence.

- A horn name, like `G0` or `Y3`: in this case, the polarimeter that should be connected to the horn will be turned on. (The nominal correspondence between horns and polarimeters is provided in file `data/default_warm_biases.xlsx`.)

- A string like `G0:STRIP33`: in this case, the default association between horns and polarimeters can be overridden. This can be useful when running debugging tests on the hardware.
