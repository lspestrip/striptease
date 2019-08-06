# StripTEASE - Strip TEst Analysis for System Evaluation

[Online documentation](https://lspestrip.github.io/striptease/)

This repository contains the code used to perform tests and anlyze results for
the STRIP system level tests. It uses Python 3.6.x and Qt 5.

## Installation

You have two choices to install this program:

1. Install and use it as any other Python package; good if you are not
   a Python expert but just want to control the Strip instrument;

2. Install it with the aim to develop and improve it; good if you know
   some Python and do not want to prevent yourself from patching the
   code.
   
If you want to follow the first route, use the following commands:

```bash
git clone git@github.com:lspestrip/striptease.git
python setup.py install
```

If you are a developer, use these commands:

```bash
git clone git@github.com:lspestrip/striptease.git
python -m pip install -e .
```

Striptease includes a C++ program used to send long sequence of
commands to the Strip electronics. This program is written in C++ and
requires a separate compilation step:

```bash
cd TestRunner
qmake TestRunner.pro && make
```

## How to use the code

Once you have configured the library using the
[documentation](https://lspestrip.github.io/striptease/authentication.html),
you can happily use IPython or a Jupyter notebook to write your code.
Start with the following command:

```python
from striptease import Connection
c = Connection()
c.login()
```

## Running long scripts

Programs like `program_turnon.py` generate JSON files that can be fed
to `TestRunner`. To generate a JSON file that turns on board `G`, run
the following from the command line:

```bash
python program_turnon.py -o turnon.json G
```

Now start `TestRunner/TestRunner` and load file `turnon.json`, then
press the `Run` command to start the execution.

![demo](testrunner-demo.gif)
