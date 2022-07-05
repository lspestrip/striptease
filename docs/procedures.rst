Writing test procedures
=======================

To create a new script that builds a sequence of JSON commands, the
easiest way is to create a new class derived from
:class:`striptease.procedures.StripProcedure`::

  from striptease import StripProcedure
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

Pretty-printing test procedures
-------------------------------

When debugging a procedure, it is useful to have a quick look of the
commands it contains. Striptease provides a program,
``pretty_print_procedure.py``, that outputs the list of commands in a
procedure using colors. The following demo shows how to use it:

.. asciinema:: pretty-print-table-94x26.cast
   :preload: 1
   :cols: 118
   :rows: 26


Sending messages with Telegram
------------------------------

The program ``program_batch_runner.py`` has the ability to send
messages through Telegram whenever a test is
started/stopped/completed. To use this feature, you must first
configure the service ``telegram-send`` (which is installed
automatically with Striptease) so that it knows where messages should
be sent.

You should run the following command to send messages to a group::

  telegram-send --configure-group

and follow the instructions; this requires you to add the bot
``StripSystemLevelTests`` to the group.

If you want to send the same messages to more than one
group/chat/channel, you can call ``telegram-send`` with the flag
``--config FILENAME`` and save each time a new configuration file::

  telegram-send --config conf1.txt --configure-group
  telegram-send --config conf2.txt --configure-group

When you call ``program_batch_runner.py``, you can use the switch
``--telegram-conf`` more than once to specify the configuration for
each group/channel/chat::

  ./program_batch_runner.py --telegram-conf=conf1.txt --telegram-conf=conf2.txt script.json

If you want to prevent the program from sending messages to Telegram,
use the switch ``--no-telegram``. Messages will *not* be sent in
«dry-run» mode (see above).


Module contents
----------------------------------

.. automodule:: striptease.procedures
    :members:
    :undoc-members:
    :show-inheritance:

