Polarimeters
============

This section explains some general-purpose functions and constants
that are useful to manipulate polarimeters.

Boards
------

If you need to iterate over all the board names, or if you want to
check if the board name provided as input by the user is valid, you
can use :data:`.STRIP_BOARD_NAMES`. The following example mocks a
processing script that needs to iterate over all the boards but one;
it shows how ``STRIP_BOARD_NAME`` can make the code more elegant::

  from striptease import STRIP_BOARD_NAMES

  while True:
      board_to_skip = input("Enter the board to skip: ")
      if board_to_skip in STRIP_BOARD_NAMES:
          break
      else:
          print(f"'{board_to_skip}' is not a valid board, retry")
          
  for cur_board_name in STRIP_BOARD_NAMES:
      if cur_board_name == board_to_skip:
          continue
          
      print(f"Processing board {cur_board_name}")
      # …

      
The output of the code is the following, assuming that the user
entered ``R`` at the prompt:

.. code-block:: none

   Enter the board to skip: R
   Processing board V
   Processing board G
   Processing board B
   Processing board Y
   Processing board O
   Processing board I


Polarimeter names
-----------------

Switching between modules and polarimeters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each «module» (e.g., I0) is associated with a «polarimeter»
(``STRIP34``), and it is often the case that procedures and data
analysis codes need to jump from one representation to another.

The association is stored in the file
``data/default_biases_warm.xlsx``, and it can be accessed using the
class :class:`.InstrumentBiases`::

  from striptease.biases import InstrumentBiases

  biases = InstrumentBiases()
  print(biases.module_name_to_polarimeter("W3"))
  # Output:
  # STRIP70

  print(biases.polarimeter_to_module_name("STRIP34"))
  # Output:
  # I0


W-band polarimeters
~~~~~~~~~~~~~~~~~~~

The convention used to name the Strip polarimeters is rather
unfortunate, as it follows a different convention for Q and W-band
polarimeters. While the former are indicated by a letter identifying
the *board* and a positive number indicating the polarimeter index in
the board, W-band polarimeters always use the letter ``W``, regardless
of the board.

The constant :data:`.BOARD_TO_W_BAND_POL` is a dictionary that
associates the uppercase letter of each board to the name of the
W-band polarimeter, or ``None`` in the case of board ``I``::

  from striptease import STRIP_BOARD_NAMES, BOARD_TO_W_BAND_POL
  
  for cur_board in STRIP_BOARD_NAMES:
      w_pol = BOARD_TO_W_BAND_POL[cur_board]

      if w_pol:
          print(f"{w_pol} is connected to board {cur_board}")
      else:
          print(f"Board {cur_board} has no W-band polarimeters")

          
The output of the script is the following:

.. code-block:: none

   W3 is connected to board R
   W4 is connected to board V
   W6 is connected to board G
   W5 is connected to board B
   W1 is connected to board Y
   W2 is connected to board O
   Board I has no W-band polarimeters


In some contexts, a saner naming convention is used for W-band
polarimeters: they are referred using the name of the board they
belong to, followed by the index ``7``. For instance, the name ``R7``
can be used to refer to polarimeter ``W3``, as this polarimeter is
connected to board ``R``. The function
:func:`.normalize_polarimeter_name` can be used to turn the name ``W3``
into the R-based name::

  print(normalize_polarimeter_name("W1")) # Prints Y7


Polarimeter index within a board
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The function :func:`.get_polarimeter_index` returns a zero-based index
of a polarimeter in a board, given the name of the polarimeter. W-band
polarimeters always use index ``7``:

.. code-block:: none

  print(get_polarimeter_index("R0")) # Print 0
  print(get_polarimeter_index("G4")) # Print 4
  print(get_polarimeter_index("W1")) # Print 7


Amplifiers
----------

Indexing
~~~~~~~~

The official naming convention enumerates the amplifiers according to
the line exiting the phase switch (``A`` or ``B``) and their order
within the line (``1``, ``2``, ``3``). Therefore, amplifier ``HA1`` is
the first stage of amplification in line ``A``, and it's followed by
``HA2``, which is in turn followed by ``HA3`` (the last amplification
stage).

However, there have been two other ways to enumerate the LNAs in a
QUIET/Strip polarimeter:

1. The indexes used by JPL for the QUIET experiment (e.g., ``Q5``);
2. The indexes used when designing the electronic boards (e.g.,
   ``H4``).

The web server used to operate Strip in Bologna and in Tenerife uses
the indexes understood by the **electronic board**, which neglects the
official naming convention. The function :func:`.get_lna_num` computes
the zero-based index of an LNA from its full name in one of the three
conventions named above::

  # All these examples refer to the same LNA
  print(get_lna_num("HA3"))  # Print 4
  print(get_lna_num("H4"))   # Print 4
  print(get_lna_num("Q5"))   # Print 4


 

Modes of operation
~~~~~~~~~~~~~~~~~~

A Strip amplifier can operate either in *open loop* or *closed loop*
mode, depending on how the gate and drain are set:

1. In *open loop mode*, the drain voltage :math:`V_d` and gate voltage
   :math:`V_g` are set by the user, while the drain current
   :math:`I_d` is set free to adapt to the voltages.

2. In *closed loop mode*, the drain current :math:`I_d` and drain
   voltage :math:`V_d` are set by the user, and a retro-feedback
   circuit in the electronics adapts the gate voltage :math:`V_g` to
   make sure that the drain current $I_d$ is kept at the level
   specified by the user.

The following figure depicts the difference between the two modes,
representing the three bias parameters :math:`I_d`, :math:`V_d`, and
:math:`V_g` as knobs; only green knobs can be manipulated by the user,
while the blue knob responds automatically to variations in the green
knobs.
   
.. figure:: _static/open-closed-loop-mode.svg
            :align: center
            :alt: Open/closed loop modes

The way an amplifier operates can be set using the ``POL_MODE``
command, through the method :meth:`.StripConnection.set_pol_mode`. You
can use the enumeration class :class:`.PolMode` to specify the flags
to be used, but usually you can stick to the two constants
:data:`.OPEN_LOOP_MODE` and :data:`.CLOSED_LOOP_MODE`::

        import striptease as st

        conn = st.StripConnection()
        conn.set_pol_mode("I0", OPEN_LOOP_MODE)
