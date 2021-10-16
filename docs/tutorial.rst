Tutorial
========

In this tutorial, we will show how to connect to the Strip webserver
and run simple commands that drive the electronics and the instrument.

(Before reading this part, be sure to follow the instructions in the
page :ref:`Authentication`, otherwise the commands in this page will
not work. You need to be authenticated if you are going to send
commands to the real electronics.)


Establising a connection with the server
----------------------------------------

The Python interface provided by Striptease revolves around the object
:class:`striptease.StripConnection`, which derives from
:class:`web.rest.base.Connection`. It handles authentication, measure
unit conversion, and validation of commands. If you properly
configured the credentials in file ``~/.strip/conf.json`` (see the
page :ref:`Authentication`), you can create a new object with no
parameters::

  import striptease as st
  conn = st.StripConnection()

These commands create a connection but do not authenticate, as shown
by the :meth:`web.rest.base.Connection.is_connected`::

  >>> conn.is_connected()
  False
  >>> conn.login()
  >>> conn.is_connected()
  True

To disconnect, you must call the method
:meth:`web.rest.base.StripConnection.logout`::

  >>> conn.logout()
  >>> conn.is_connected()
  False
  >>> conn.login()  # Log back in

Using the `login` and `logout` commands is handy when running a REPL;
if you are writing automatic script, it's better to rely to the fact
that :class:`striptease.StripConnection` can be used as a context
manager::

   with st.StripConnection() as conn:
       # Use "conn" freely here, as the login has already been done
       pass

       
Sending commands to the instrument
----------------------------------

Once you have a working connection to the server, you can use the
method :meth:`striptease.StripConnection.slo_command` to send «slow»
commands to the server. This kind of commands is the most common, and
you are going to use it 95% of the time. The following command
retrieves the drain voltage for HEMT #0 from detector `R0`::

  vd0_hk = conn.slo_command(
      method="GET",
      board="R",
      pol=0,
      kind="BIAS",
      base_addr="VD0_HK",
  )

The example above retrieved a value from the electronic board and
saved it into ``vd0_hk``. Changing the method from ``GET`` to ``SET``
permits to set new values in the board; in this case, we must change
the name of the parameter as well, because of the way the Strip
electronics works::

  conn.slo_command(
      method="SET",
      board="R",
      pol=0,
      kind="BIAS",
      base_addr="VD0_SET",
      data=vd0_hk,
  )

The class :class:`.StripConnection` has more high-level methods that
rely on :meth:`.slo_command`: refer to its documentation for more
details.

How data are saved and accessed
-------------------------------

The web server acquiring data from the instrument distinguishes
between «fast» and «slow» timestreams; the scientific output of each
polarimeter belongs to the first category, while housekeeping
parameters like currents, biases, and temperatures are slow
timestreams. This distinction is kept in Striptease, as it acts as a
middleware library between the user and the web server.

Scientific and housekeeping data are saved by the web server in HDF5
files; no more than 6 hours of data are saved in a file, for the fear
of data loss. When a HDF5 file is closed, the web server immediately
creates a new one and continues saving data in it. It is possible to
force the web server to close the current HDF5 file and to create a
new one; this can be useful before running a long test script, for
instance::

  conn.round_all_files()


Tags
----

In long tests, it is often useful to mark some events happening: for
instance, a time span where the state of the instrument is considered
«stable», or the moment when a polarimeter is being turned off.

The web server implement «tags» to mark specific events during a
test. A tag is defined by a start and an end, and it must therefore be
opened and closed::

  conn.tag_start("MY_TAG", comment="My comment")

  # Do whatever you want, send your commands, etc.

  conn.tag_stop("MY_TAG", comment="Another comment")


To ease the use of tags, Striptease implements the
:class:`striptease.StripTag` class, which acts as a context manager::

  with StripTag(conn, name="MY_TAG",
      start_comment="Start", stop_comment="End"):
      
      # Do whatever you want, send your commands, etc.
      pass


The main purpose of tags is to ease the implementation of analysis
scripts. You can query tags using the method
:meth:`striptease.StripConnection.tag_query`::

  from astropy.time import Time
  
  tags = conn.tag_query("MY_TAG",
      start_mjd=Time("2019-12-20").mjd,
      end_mjd=Time("2019-12-30").mjd)
  for cur_tag in tags:
      # "cur_tag" is a dictionary
      print(cur_tag)
  

Running complex automatic scripts
---------------------------------

To run a test on the hardware, one needs to carefully plan the
sequence of commands to be sent before the real hardware be exercised.
Once the list of commands is prepared, they can be sent to the
electronics and be ran automatically, one by one. Therefore, to run a
test, Striptease require users to follow a two-step process:

1. A Python script builds the sequence of commands (the so-called
   *test procedure*) and save it into a file (written in the `JSON
   format <https://en.wikipedia.org/wiki/JSON>`_;
2. The user runs the sequence of commands using a command-line tool.
   Striptease provides the file ``program_batch_runner.py`` for this
   purpose.

This approach ensures reproducibility and allows the user to inspect
the test procedure (in the JSON file) before actually running it.

The JSON file saved by Python scripts contains an ordered list of
dictionaries, each providing the parameters for a single command sent
to the electronics.


How to create test procedures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


A *test procedure* is a sequence of commands written in a JSON file
that can be used to automatically run a test of the Strip hardware.
See the chapter :ref:`Writing test procedures`.
