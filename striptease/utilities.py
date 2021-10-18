# -*- encoding: utf-8 -*-

from enum import IntFlag

#: List of all the board names: handy if you need to iterate over them,
#: or if you need to validate user input
STRIP_BOARD_NAMES = ["R", "V", "G", "B", "Y", "O", "I"]

#: This dictionary associates the name of a board with the W-band
#: polarimeter associated with it.
BOARD_TO_W_BAND_POL = {
    "Y": "W1",
    "O": "W2",
    "R": "W3",
    "V": "W4",
    "B": "W5",
    "G": "W6",
    "I": None,
}


#: Used to set the operational mode of a polarimeter. See
#: :data:`CLOSED_LOOP_FLAGS` and :data:`OPEN_LOOP_FLAGS`.
class PolMode(IntFlag):
    # If this is not set, the electronics will ignore drain settings
    ENABLE_VDRAIN = 1
    # If this is set, the LNA works in open-loop mode
    ENABLE_IDRAIN_LOOP = 2
    # If enable, gate voltage is set to a constant value
    MANUAL_MODE = 4


#: Value to be passed to ``POL_MODE`` to use open-loop mode for LNAs
#: (constant drain voltage)
OPEN_LOOP_MODE = PolMode.ENABLE_VDRAIN

#: Value to be passed to ``POL_MODE`` to use closed-loop mode for LNAs
#: (constant drain current)
CLOSED_LOOP_MODE = PolMode.ENABLE_VDRAIN | PolMode.ENABLE_IDRAIN_LOOP


def normalize_polarimeter_name(name: str):
    """Translate the name of W-band polarimeters

    This function returns the name of a W-band polarimeter as if it
    were named as the Q-band polarimeters in its own board::

        >>> normalize_polarimeter_name("W2")
        "O7"

    """
    result = name.upper()
    if name[0] != "W":
        return result

    for board, w_pol in BOARD_TO_W_BAND_POL.items():
        if w_pol == result:
            return f"{board}7"

    raise KeyError(f"unknown polarimeter {result}")


def get_polarimeter_index(pol_name):
    """Return the progressive number of the polarimeter within the board (0…7)

    Args:
        pol_name (str): Name of the polarimeter, like ``R0`` or ``W3``.

    Returns:
        An integer from 0 to 7.
    """

    if pol_name[0] == "W":
        return 7
    else:
        return int(pol_name[1])


def get_lna_num(name):
    """Return the number of an LNA, in the range 0…5

    Valid values for the parameter `name` can be:
    - The official name, e.g., HA1
    - The UniMIB convention, e.g., H0
    - The JPL convention, e.g., Q1
    - An integer number, which will be returned identically
    """

    if type(name) is int or name in ["4A", "5A"]:
        # Assume that the index refers to the proper firmware register
        return name
    elif (len(name) == 3) and (name[0:2] in ["HA", "HB"]):
        # Official names
        d = {"HA1": 0, "HA2": 1, "HA3": 2, "HB1": 5, "HB2": 4, "HB3": 3}
        return d[name]
    elif name[0] == "H":
        # UniMiB
        d = {
            "H0": 0,
            "H1": 1,
            "H2": 2,
            "H3": 3,
            "H4": 4,
            "H4A": "4A",
            "H5": 5,
            "H5A": "5A",
        }
        return d[name]
    elif (len(name) == 2) and (name[0] == "Q"):
        # JPL
        d = {"Q1": 0, "Q2": 1, "Q3": 2, "Q4": 3, "Q5": 4, "Q6": 5}
        return d[name]
    else:
        raise ValueError(f"Invalid amplifier name '{name}'")


def get_lna_list(pol_name=None, module_name=None):
    """
    Return the LNA list of one polarimeter.
    In particular, W polarimeters have two type of LNA configurations.

    Args
    ----
    module_name (str): Name of the module, like ``I`` or ``V``. Use ``Wn`` for
        any of the W-band polarimeters
    pol_name (str): Name of the polarimeter, like ``R0`` or ``W3``

    Return
    ------
    lnaList (tuple): list of LNA in the polarimeter
    """
    if module_name is not None:
        if module_name[0].upper() in STRIP_BOARD_NAMES:
            lnaList = ("HA3", "HB3", "HA2", "HB2", "HA1", "HB1")
        elif module_name[0].upper() == "W":
            if module_name[1] in ["2", "4"]:
                lnaList = ("HA2", "HB2", "HA1", "HB1")
            if module_name[1] in ["1", "3", "5", "6"]:
                lnaList = ("HA3", "HB3", "HA2", "HB2", "HA1", "HB1")
        else:
            raise ValueError(f"Invalid polarimeter name '{pol_name}'")

    if pol_name is not None:
        lnaList = ("HA3", "HB3", "HA2", "HB2", "HA1", "HB1")
        if pol_name in ["STRIP71", "STRIP73"]:
            lnaList = ("HA2", "HB2", "HA1", "HB1")
        elif pol_name in ["STRIP76", "STRIP78", "STRIP81", "STRIP82"]:
            lnaList = ("HA2", "HB2", "HA1", "HB1")

    return lnaList


def polarimeter_iterator(
    boards=STRIP_BOARD_NAMES, include_q_band=True, include_w_band=True
):
    """Iterate over all the polarimeters/feed horns of one or more boards.

    Arguments:

      - boards (``str`` or list of strings): letters identifying the
        boards. You can either pass a string containing all the board
        letters (e.g., ``"BVI"``), or a list of strings (``["B", "V",
        "I"]``).

      - include_q_band (bool): whether to include Q-band polarimeters
        or not

      - include_w_band (bool): whether to include W-band polarimeters
        or not

    Returns: A sequence of tuples in the form ``(board_name,
      polarimeter_index, polarimeter_name)``, where ``board_name`` is
      a one-letter string containing the name of the board (e.g.,
      ``B``), ``polarimeter_index`` is a zero-based index of the
      polarimeter within the board, and ``polarimeter_name`` the name
      of the polarimeter/feed horn (e.g., ``B4``). W-band polarimeters
      use their official name, e.g., ``W4``.

    Example::

      for board_name, pol_idx, pol_name in polarimeter_iterator():
          print(f"- Polarimeter {pol_name} (#{pol_idx}), board {board_name}")

    """

    start_idx = 0 if include_q_band else 7
    stop_idx = 8 if include_w_band else 7

    for cur_board in boards:
        for pol_idx in range(start_idx, stop_idx):

            if cur_board == "I" and pol_idx == 7:
                continue

            if pol_idx != 7:
                pol_name = f"{cur_board}{pol_idx}"
            else:
                pol_name = BOARD_TO_W_BAND_POL[cur_board]

            yield cur_board, pol_idx, pol_name
