Run log database
================

It is handy to keep track of all the test procedures that are executed
on the Strip instrument. The Striptease library supports the creation
and update of a database that can be used whenever a :ref:`JSON
procedure <Writing test procedures>` is issued.

The program ``program_batch_runner.py`` makes use of the function
:func:`.append_to_run_log` to update the database, which is stored in
``~/.strip/run_log.db``. The database can be queried using the program
``dump_run_log.py``; use the ``--help`` command to learn how to use
it. It can print the contents of the database or save them in the JSON
or CSV format; it can also dump the commands for a specific log in a
JSON file.


.. automodule:: striptease.runlog
    :members:
    :undoc-members:
    :show-inheritance:

