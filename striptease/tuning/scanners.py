# -*- encoding: utf-8 -*-

from abc import ABC, abstractmethod
from copy import copy
from typing import Dict, List, Union

import numpy as np

from . import scanners

# One dimensional scanners


class Scanner1D(ABC):
    """An abstract class representing a one dimensional scanner.

    Args:
    - `label` (`str`): the label of the x variable."""

    def __init__(self, label: str = "x"):
        self.label = label

    @abstractmethod
    def next(self) -> bool:
        """Advance the scanning to the next parameter: if the return value is True, the next parameter can be found in self.x,
        otherwise the scan has ended."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset the scanner to the initial state."""
        ...

    @property
    @abstractmethod
    def index(self) -> int:
        ...


class LinearScanner(Scanner1D):
    """A 1D scanner that explore the parameters linearly.

    Args:
    - `start` (`Union[float, np.ndarray]`): the starting value (or array).
    - `stop` (`Union[float, np.ndarray]`): the last value (or array).
    - `nsteps` (`int`): the number of steps.
    - `label` (`str`): the label of the x variable."""

    def __init__(
        self,
        start: Union[float, np.ndarray],
        stop: Union[float, np.ndarray],
        nsteps: int,
        label: str = "x",
    ):
        super().__init__(label)
        self.start = start
        self.stop = stop
        self.nsteps = nsteps
        self._delta = (stop - start) / nsteps

        self.x = copy(start)

        self._current_step = 0

    def next(self) -> bool:
        if self._current_step >= self.nsteps:
            return False

        self.x += self._delta
        self._current_step += 1
        return True

    def reset(self) -> None:
        self.x = copy(self.start)
        self._current_step = 0

    @property
    def index(self) -> int:
        return self._current_step


class IrregularScanner(Scanner1D):
    def __init__(self, *args: List):
        super().__init__()
        self._nscanners = len(args)
        self._scanners = []
        for current_arg in args:
            assert (
                len(current_arg) == 3
            )  # Each argument is a list of three elements: start, stop, nsteps
            self._scanners.append(
                LinearScanner(
                    start=current_arg[0], stop=current_arg[1], nsteps=current_arg[2]
                )
            )
        self._current_scanner = 0
        self.x = self._scanners[self._current_scanner].x

    def next(self) -> bool:
        while self._scanners[self._current_scanner].next() is False:
            self._current_scanner += 1
            if self._current_scanner >= self._nscanners:
                self._current_scanner -= 1  # Make sure that the next call to next() does not raise an exception but just returns False
                return False

        self.x = self._scanners[self._current_scanner].x
        return True

    def reset(self) -> None:
        for scanner in self._scanners:
            scanner.reset()
        self._current_scanner = 0
        self.x = self._scanners[self._current_scanner].x

    @property
    def index(self) -> int:
        index = 0
        for i in range(self._current_scanner):
            index += self._scanners[i].nsteps
        index += self._scanners[self._current_scanner].index
        return index


# Two dimensional scanners


class Scanner2D(ABC):
    """Abstract base class representing a scanning strategy to explore a 2D plane.

    Args:
    -`x_label`/`y_label` (`str`): the names of the x, y variables, to be used in the plot."""

    def __init__(self, x_label: str = "x", y_label: str = "y"):
        self.x_label = x_label
        self.y_label = y_label

    @abstractmethod
    def next(self) -> bool:
        """Return True if there is still a parameter pair to be tested, and set self.x and self.y accordingly.
        Return False otherwise."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset the scanner by setting `self.x` and `self.y` to the initial values."""
        ...

    @property
    @abstractmethod
    def index(self) -> List[int]:
        ...

    def plot(self):
        """Show a plot of the scanning strategy."""
        from matplotlib import pyplot as plt
        import numpy as np

        res = []
        while self.next() is True:
            res.append((self.x, self.y))

        res = np.asarray(res)
        plt.plot(res[:, 0], res[:, 1], "-o")
        plt.xlabel(self.x_label)
        plt.ylabel(self.y_label)
        plt.show()
        self.reset()


class GridScanner(Scanner2D):
    """A scanner that explores parameters on a grid from down to up and from left to right

    Args:
    - `x_start`/`y_start` (`float | np.ndarray`): the starting parameters
    - `x_stop`/`y_stop` (`float | np.ndarray`): the parameters at which the grid ends
    - `x_nsteps`/`y_nsteps` (`int`): the number of steps
    - `x_label`/`y_label` (`str`): the names of the x, y variables, to be used in the plot."""

    def __init__(
        self,
        x_start: Union[float, np.ndarray],
        x_stop: Union[float, np.ndarray],
        x_nsteps: int,
        y_start: Union[float, np.ndarray],
        y_stop: Union[float, np.ndarray],
        y_nsteps: int,
        x_label: str = "x",
        y_label: str = "y",
    ):
        super().__init__(x_label, y_label)
        self.x_start = x_start
        self.x_stop = x_stop
        self.x_nsteps = x_nsteps
        self.delta_x = (x_stop - x_start) / x_nsteps
        self.y_start = y_start
        self.y_stop = y_stop
        self.y_nsteps = y_nsteps
        self.delta_y = (y_stop - y_start) / y_nsteps

        self.x = copy(x_start)
        self.y = copy(y_start)

        self.x_current_step = 0
        self.y_current_step = 0

    def next(self) -> bool:
        if self.y_current_step >= self.y_nsteps:  # Last column in the row
            if self.x_current_step >= self.x_nsteps:  # Last row in the grid
                return False
            else:  # Not last row in the grid
                self.x += self.delta_x
                self.x_current_step += 1
                self.y = copy(self.y_start)
                self.y_current_step = 0
                return True
        else:  # Not last row in the column
            self.y += self.delta_y
            self.y_current_step += 1
            return True

    def reset(self) -> None:
        self.x = copy(self.x_start)
        self.y = copy(self.y_start)

        self.x_current_step = 0
        self.y_current_step = 0

    @property
    def index(self) -> List[int]:
        return [self.x_current_step, self.y_current_step]


class IrregularGridScanner(Scanner2D):
    def __init__(self, x: List, y: List):
        super().__init__()
        self._x_scanner = IrregularScanner(*x)
        self._y_scanner = IrregularScanner(*y)
        self.x = self._x_scanner.x
        self.y = self._y_scanner.x

    def next(self) -> bool:
        if self._y_scanner.next() is False:  # Last column in the row
            if self._x_scanner.next() is False:  # Last row in the grid
                return False
            else:  # Not last column in the grid
                self._y_scanner.reset()
        self.x = self._x_scanner.x
        self.y = self._y_scanner.x
        return True

    def reset(self) -> None:
        self._x_scanner.reset()
        self._y_scanner.reset()

        self.x = self._x_scanner.x
        self.y = self._y_scanner.x

    @property
    def index(self) -> List[int]:
        return [self._x_scanner.index, self._y_scanner.index]


class RasterScanner(Scanner2D):
    """A scanner that explores parameters on a grid "boustrophedically",
    from down to up and viceversa alternating at every column.

    Args:
    - `x_start`/`y_start` (`float | np.ndarray`): the starting parameters
    - `x_stop`/`y_stop` (`float | np.ndarray`): the parameters at which the grid ends
    - `x_nsteps`/`y_nsteps` (`int`): the number of steps
    """

    def __init__(
        self,
        x_start: Union[float, np.ndarray],
        x_stop: Union[float, np.ndarray],
        x_nsteps: int,
        y_start: Union[float, np.ndarray],
        y_stop: Union[float, np.ndarray],
        y_nsteps: int,
        x_label: str = "x",
        y_label: str = "y",
    ):
        super().__init__(x_label, y_label)
        self.x_start = x_start
        self.x_stop = x_stop
        self.x_nsteps = x_nsteps
        self.delta_x = (x_stop - x_start) / x_nsteps
        self.y_start = y_start
        self.y_stop = y_stop
        self.y_nsteps = y_nsteps
        self.delta_y = (y_stop - y_start) / y_nsteps

        self.x = copy(x_start)
        self.y = copy(y_start)

        self.x_current_step = 0
        self.y_current_step = 0
        self.y_direction = +1

    def next(self) -> bool:
        if self.y_current_step >= self.y_nsteps:  # Last row in the column
            if self.x_current_step >= self.x_nsteps:  # Last column in the grid
                return False
            else:  # Not last column in the grid
                self.x += self.delta_x
                self.x_current_step += 1
                self.y_direction *= -1  # Invert the direction of the y scan
                self.y_current_step = 0
                return True
        else:  # Not last row in the column
            self.y += self.y_direction * self.delta_y
            self.y_current_step += 1
            return True

    def reset(self) -> None:
        self.x = copy(self.x_start)
        self.y = copy(self.y_start)

        self.x_current_step = 0
        self.y_current_step = 0
        self.y_direction = +1

    @property
    def index(self) -> List[int]:
        return [self.x_current_step, self.y_current_step]


class SpiralScanner(Scanner2D):
    """A scanner that explores parameters on a grid "spirally",
    starting from a center and expanding step by step.

    Args:
    - `x_start`/`y_start` (`float | np.ndarray`): the starting parameters
    - `x_step`/`y_step` (`float | np.ndarray`): the distance between two steps
    - `n_arms` (`int`): the number of spiral arms to explore
    """

    def __init__(
        self,
        x_start: Union[float, np.ndarray],
        x_step: Union[float, np.ndarray],
        y_start: Union[float, np.ndarray],
        y_step: Union[float, np.ndarray],
        n_arms: int,
        x_label: str = "x",
        y_label: str = "y",
    ):
        super().__init__(x_label, y_label)
        self.x_start = x_start
        self.x_step = x_step
        self.y_start = y_start
        self.y_step = y_step
        self.idrain = x_start
        self.x = copy(x_start)
        self.y = copy(y_start)

        self.n_arm = 1
        self.n_arms = n_arms
        self.step = 1
        self.steps = 1

    def next(self) -> bool:
        if self.n_arm > self.n_arms:  # End of the spiral
            return False

        # match-case would be useful (python 3.10)
        if self.n_arm % 4 == 1:
            self.y += self.y_step  # Up
        elif self.n_arm % 4 == 2:
            self.x += self.x_step  # Right
        elif self.n_arm % 4 == 3:
            self.y -= self.y_step  # Down
        elif self.n_arm % 4 == 0:
            self.x -= self.x_step  # Left

        self.step += 1
        if self.step > self.steps:  # End of the arm
            self.step = 1
            self.n_arm += 1
            if self.n_arm % 2 == 1:
                self.steps += 1

        return True

    def reset(self) -> None:
        self.x = copy(self.x_start)
        self.y = copy(self.y_start)

        self.n_arm = 1
        self.step = 1
        self.steps = 1

    @property
    def index(self) -> List[int]:
        self.index = [self.n_arm, self.step]


# Excel-file functions


def _list_to_array(x):
    new_list = []
    for element in x:
        if isinstance(element, list):
            if any(
                isinstance(subelement, list) for subelement in element
            ):  # element contains a list
                element = _list_to_array(element)
            else:  # element is a list of atomics: we convert it to an array
                element = np.asarray(element, dtype="float")
        new_list.append(element)
    return new_list


def _read_test(excel_file, polarimeter: str, test: str) -> Union[Scanner2D, Scanner1D]:
    """Read the cells regarding one test in the excel file and return the corresponding scanner.

    Args:
    - `excel_file`: a dictionary representing the file as returned by pd.read_excel(...).to_dict(orient="index").
    - `polarimeter` (`str`): the row to read the test in.
    - `test` (`str`): the test to return.
    """
    from ast import literal_eval

    row = excel_file[polarimeter]
    scanner_class = getattr(
        scanners, row[(test, "Scanner")]
    )  # The "Scanner" column contains the name of the scanner class: get the class itself with getattr.
    arguments_str = row[
        (test, "Arguments")
    ]  # The "Arguments" column contains the arguments to use to instantiate an object of the class.
    arguments = _list_to_array(
        list(map(literal_eval, arguments_str.split(";")))
    )  # Evaluate the arguments and store them in a list, converting lists of atomics to arrays
    return scanner_class(
        *arguments
    )  # Return an instance of the scanner class with the specified parameters.


def read_excel(
    filename: str, tests: List[str], dummy_polarimeter: bool = False
) -> Dict[str, Dict[str, Union[Scanner1D, Scanner2D]]]:

    """Read an Excel file describing a set of scanners. The rows represent the polarimeters, the columns the scanners. For example:
    +------------+---------------+-----------------------------------------------+---------------+-----------------------------------------------+
    |Polarimeter | HA1           |                                               | HA2           |                                               |
    +------------+---------------+-----------------------------------------------+---------------+-----------------------------------------------+
    |            | Scanner       | Arguments                                     | Scanner       | Arguments                                     |
    +------------+---------------+-----------------------------------------------+---------------+-----------------------------------------------+
    |O1          | GridScanner   | 2000;7000;5;[0,0,0,0];[4095,4095,4095,4095];5 | RasterScanner | 2000;7000;5;[0,0,0,0];[4095,4095,4095,4095];5 |
    +------------+---------------+-----------------------------------------------+---------------+-----------------------------------------------+
    |O2          | GridScanner   | 3000;6000;5;[0,0,0,0];[4095,4095,4095,4095];5 | RasterScanner | 3000;6000;5;[0,0,0,0];[4095,4095,4095,4095];5 |
    +------------+---------------+-----------------------------------------------+---------------+-----------------------------------------------+
    |DUMMY       | RasterScanner | 2000;7000;5;[0,0,0,0];[4095,4095,4095,4095];5 | GridScanner   | 2000;7000;5;[0,0,0,0];[4095,4095,4095,4095];5 |
    +------------+---------------+-----------------------------------------------+---------------+-----------------------------------------------+
    The DUMMY row is used to configure all the polarimeters with the same scanners without changing the file.
    Return a dictionary of dictionaries of scanners (one for each polarimeters and for each test).

    Args:
    - `filename` (`str`): the name of the Excel file.
    - `tests` (`List[`str`]`): the list of the names of the tests to look up in the file.
    - `dummy_polarimeter` (`bool`): True if the DUMMY row is to be used for all plarimeters, False otherwise.
    """
    import pandas as pd

    excel_file = pd.read_excel(filename, header=(0, 1), index_col=0).to_dict(
        orient="index"
    )
    scanners = {}
    for polarimeter in set(excel_file) - {
        "DUMMY"
    }:  # Iterate over all polarimeters except the DUMMY one
        scanners[polarimeter] = {}
        for test in tests:
            if dummy_polarimeter:
                scanners[polarimeter][test] = _read_test(excel_file, "DUMMY", test)
            else:
                scanners[polarimeter][test] = _read_test(excel_file, polarimeter, test)
    return scanners
