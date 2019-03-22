# StripTEASE - Strip TEst Analysis for System Evaluation

[Online documentation](https://lspestrip.github.io/striptease/)

This repository contains the code used to perform tests and anlyze results for
the STRIP system level tests. It uses Python 3.6.x and Qt 5.

## Installation

The code is under developement. In order to install it, you must have
[Filt](https://pypi.org/project/flit/) installed.

Run the following command to

```bash
git clone git@github.com:lspestrip/striptease.git
flit install --symlink [--python path/to/python]
```

You must install PyQt5 separately, using the following command:

```bash
pip install PyQt5
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
