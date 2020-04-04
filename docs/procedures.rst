Writing test procedures
=======================

To create a new script that builds a sequence of JSON commands, the
easiest way is to create a new class derived from
:class:`striptease.procedures.StripProcedure`::
  
  from striptease.procedures import StripProcedure
  from calibration import CalibrationTables
  
  class MyProcedure(StripProcedure):
      def __init__(self):
          super(MyProcedure, self).__init__()
          self.calibr = CalibrationTables()

      def run(self):
          # Run all your commands using "self.conn": it is a
          # StripConnection object that writes command to a JSON
          # buffer, instead of sending them to the server

          # Here is an example: set the drain current of one
          # amplifier to some value (in ADU)
          self.conn.set_id(
              polarimeter="R0",
              lna="HA1",
              value_adu=1345,
          )

          # A more complex example: set the drain current of
          # another amplifier to a *physical* value in μA
          self.conn.set_id(
              polarimeter="B3",
              lna="HB2",
              value_adu=self.calibr.physical_units_to_adu(
                  polarimeter="B3",
                  hk="idrain",
                  component="HB2",
                  value=11_000,
              ),
          )

  if __name__ == "__main__":
     proc = MyProcedure()
     proc.run()
     proc.output_json()

The procedure above will simply set the drain currents of two
amplifiers in polarimeters ``R0`` and ``B3`` to some hard-coded value,
using :meth:`.StripConnection.set_id`. Finally, the test procedure
will be written to ``stdout`` as a JSON object:

.. code-block:: json
                
    [
        {
            "path": "/rest/slo",
            "kind": "command",
            "command": {
                "board": "R",
                "pol": "R0",
                "base_addr": "ID0_SET",
                "type": "BIAS",
                "method": "SET",
                "size": 1,
                "timeout": 500,
                "data": [
                    1345
                ]
            }
        },
        {
            "path": "/rest/slo",
            "kind": "command",
            "command": {
                "board": "B",
                "pol": "B3",
                "base_addr": "ID3_SET",
                "type": "BIAS",
                "method": "SET",
                "size": 1,
                "timeout": 500,
                "data": [
                    1919
                ]
            }
        }
    ]  

Note that the names of the LNAs (``HA1`` and ``HB2``) have been
converted in the naming scheme used by the electronics (the indexes
``0`` and ``3`` used in the names ``ID0_SET`` and ``ID3_SET``), and
that the value 11,000 μA has been converted into 1919 ADU using the
appropriate calibration curve for amplifier ``HB2`` in polarimeter
``B3``. You must always instantiate a :class:`.CalibrationTables`
object, if you want to use physical units for biases.

For a real-world example of test procedure, have a look at
`program_pinchoff.py
<https://github.com/lspestrip/striptease/blob/master/program_pinchoff.py>`_.

Module contents
----------------------------------

.. automodule:: striptease.procedures
    :members:
    :undoc-members:
    :show-inheritance:


