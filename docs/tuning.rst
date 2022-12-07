The tuning module
=================

This section explains the tuning module API and some procedures written using it.

Scanners
--------

A tuning procedure scans the parameter space according to a scanning
strategy. This strategy is encoded in a :class:`Scanner1D` or :class:`Scanner2D`
class. A scanner class is used initializing it with the constructor and
then calling the :func:`next` method, which returns ``True`` if there is
still a parameter to be scanned, or ``False`` if the scan is over.
If there is still a parameter, it can be read in the ``x`` (and ``y`` if
the scanner is 2D) variable of the class.
For example, a :class:`Scanner1D` can be used as follows::

  scanner = LinearScanner(start = 0, stop = 20, nsteps = 5)
  while True:
      do_something_with(scanner.x)
      if scanner.next() == False:
          break

Calling the :func:`reset` method brings the scanner to the initial state.
The ``index`` property returns a 1D or 2D index that can be used to identify
the current step of the scan.
:class:`Scanner2D` also have a :func:`plot` method that can be used to produce
a 2D plot of the scanning strategy.

Reding scanners form an Excel file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Scanners can be read from an Excel file, to make it easier to reuse them
in multiple tests and changing them if needed. The function to be used is
:func:`read_excel`, which returns a dictionary of dictionaries: each of them
refers to a polarimeter, and associates a scanner object to each test.

An example Excel file is like this:

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

The resulting dictionary will be as follows::

  >>> read_excel(filename="example.xlsx", tests=["HA1", "HA2"])
  {'O1': {'HA1': <tuning.scanners.GridScanner object at ...>,
          'HA2': <tuning.scanners.RasterScanner object at ...>},
   'O2': {'HA1': <tuning.scanners.GridScanner object at ...>,
          'HA2': <tuning.scanners.RasterScanner object at ...>}}

If the function is called with ``dummy_polarimeter=True``, all polarimeters
are assigned the scanners in the "DUMMY" row.

Tuning Procedures
-----------------

Now that we have a way to define our scanning strategy, we can write
a procedure to run the tests. To make our life easier, the :class:`TuningProcedure`
abstract class can be used. In addition to providing some useful methods
to set and reset some biases, it does two things:
1. It decorates the :func:`run` procedure of child classes adding a turnon
   and turnoff procedure if the start or end states are ``StripState.OFF``.
2. It provides a :func:`_test` function that child classes can use to run
   their tests. This function does something like the test example above,
   calling the function it recieves as an argument instead of :func:`do_something_with`
   for each ``test_polarimeters``, until the scan is over. It also adds some
   useful tags, hk_scan and wait commands here and there.

To write a tuning procedure, therefore, one needs only define a class
that inherits from :class:`TuningProcedure`, calls the constructor with
the appropriate parameters, write the functions that do something with the
scanned parameters (tipically, converting to ADU and setting the biases)
and pass them to the :func:`_test` method after setting the needed state.
 
Existing tuning procedures
~~~~~~~~~~~~~~~~~~~~~~~~~~

The module defines two tuning procedures: :class:`LNAPretuningProcedure`
and :class:`OffsetTuningProcedure`.
:class:`LNAPretuningProcedure` operates as follows:
1. Set leg HA biases to the default values;
2. Set leg HB vdrain (and igate if running in closed loop) to zero, and
   phsw status to ``PhswPinMode.STILL_NO_SIGNAL``;
3. Test HA1 scanning idrains or vgates (depending on mode) and offsets
   according to the scanner for each polarimeter;
4. Reset HA1 biases to default values;
5. Repeat steps 3 and 4 for LNAs HA2 and HA3;
6. Repeat steps 1-5 for leg HB.

:class:`OffsetTuningProcedure` operates as follows:
1. Set all polarimeters to zero bias;
2. Test offsets according to the scanning strategy specified by the scanner.