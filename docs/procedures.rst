Writing test procedures
=======================

To create a new script that builds a sequence of JSON commands, the
easiest way is to create a new class derived from
:class:`striptease.procedures.StripProcedure`::
  
  from striptease.procedures import StripProcedure

  class MyProcedure(StripProcedure):
      def __init__(self):
          super(MyProcedure, self).__init__()

      def run(self):
          # Run all your commands using "self.conn": it is a
          # StripConnection object that writes command to a JSON
          # buffer, instead of sending them to the server

          # Here is an example: set the drain current of one amplifier
          # to some value (in ADU)
          conn.set_id(polarimeter="R0", lna="HA1", value_adu=1345)

   if __name__ == "__main__":
       proc = MyProcedure()
       proc.run()
       proc.output_json()

The procedure above will simply set the drain current of polarimeter
``R0`` to some hard-coded value, using
:meth:`.StripConnection.set_id`, and the test procedure will be
written to ``stdout``.

For a real-world example of test procedure, have a look at
`program_pinchoff.py
<https://github.com/lspestrip/striptease/blob/master/program_pinchoff.py>`_.

Module contents
----------------------------------

.. automodule:: striptease.procedures
    :members:
    :undoc-members:
    :show-inheritance:


