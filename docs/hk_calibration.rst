Calibration of housekeeping parameters
======================================

One of the duty of the electronic boards used by Strip is to measure
instrument parameters like currents, voltages, temperatures, etc.
These parameters are called `housekeepings` and are vital to monitor
the status of the instrument. Like scientific samples, housekeeping
parameters are measured by digital units and are stored as integer
numbers, nicknamed `ADU` (analog-to-digital unit). Calibration curves
must be applied to ADU numbers to retrieve a physically meaningful
unit (e.g., milliampere, Kelvin, etc.). These calibration curves are
provided in the form of Excel spreadsheets, and `striptease` provides
a few utilities to ease the conversion between ADUs and physical
units.

Usage of calibration tables
---------------------------

The most basic functions to apply calibration tables are provided by
the class :class:`.CalibrationTables`. This class implements two
methods, named :meth:`.physical_units_to_adu` and
:meth:`.adu_to_physical_units`, which perform the two
conversions::

  from calibration import CalibrationTables

  cal = CalibrationTables()
  print(cal.physical_units_to_adu(
      polarimeter="R0",
      hk="idrain",
      component="HA1",
      value=1000,
  ))

A `CalibrationTable` object connects with the server when the
constructor is called, because it needs to know which is the
association between the board name (in the example above, ``R``) and
the board number used by the electronics. Once the object ``cal`` has
been constructed, the connection is no longer used. If you have
already instanced a :class:`Config` object, you can pass it
to the constructor and it will be reused::

  from calibration import CalibrationTables
  from config import Config
  from striptease import StripConnection

  conn = StripConnection()
  conn.login()

  config = Config()
  config.load(conn)

  # Use "conn" and "config"
  # …

  # Reuse the configuration object
  cal = CalibrationTables(config)


Low-level calibration functions
-------------------------------

A calibration curve is stored in a `CalibrationCurve` object, which
has the following fields:

1. ``slope`` (float)

2. ``intercept`` (float)

3. ``mul`` (int)

4. ``div`` (int)

5. ``add`` (int)

The operation carried out by the electronics to convert physical units
to ADU is the following (integer operations)::

  adu = value * mul / div + add

However, Striptease uses the following floating-point operation::

  adu = int(value * slope + intercept)

These operations are implemented by the functions
:meth:`calibration.physical_units_to_adu` and
:meth:`calibration.adu_to_physical_units`, which require a
`CalibrationCurve` object.


Module documentation
--------------------

.. automodule:: calibration
    :members:
    :undoc-members:
    :show-inheritance:
