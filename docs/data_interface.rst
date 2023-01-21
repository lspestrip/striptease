Reading data saved in HDF5 files
================================

Introduction
------------

Striptease provides an interface to the data acquired by the
instrument and stored in HDF5 files which allows the user to access
both scientific and housekeepings data returning them into time, data
numpy arrays.

Before reading this chapter, you should be aware of the way data are
saved to disk when LSPE/Strip operates. The instrument sends all the
scientific (``PWR`` and ``DEM`` timelines) and housekeeping (biases,
temperatures…) timelines to a computer, where a software called *data
server* takes them and writes them in HDF5 files. The stream of data
is usually continuous, but occasionally the *data server* stops
writing in a file and opens a new one. This ensures that files do not
get too big and that you can grab one of them for analysis while the
instrument is still running. These files are usually saved in a
hierarchical structure of directories, grouped according to the
year/month of acquisition. So, assuming that these data files are
stored in ``/storage/strip``, you might find the following files in
the Strip data storage:

.. code-block:: text

  /storage/strip/2021/10
      2021_10_31_15-42-44.h5
      2021_10_31_19-42-44.h5
      2021_10_31_23-42-44.h5
  /storage/strip/2021/11
      2021_11_01_03-42-44.h5
      2021_11_01_07-42-44.h5
      2021_11_01_11-42-44.h5

It is now time to see the kind of tools that Striptease provides to
access these files. The interface is based on two classes:

- :class:`.DataFile` provides a high-level access to a **single** HDF5
  file.

- :class:`.DataStorage` provides a high-level access to a
  **directory** containing several HDF5 files, like the one above. It
  basically abstracts over the concept of a «file» and instead
  considers the data as being acquired continuously.


Accessing one file
------------------

Let's begin with a small example that shows how to use the class
:class:`.DataFile`::

    from striptease import DataFile
    fname = '/path_to/data.h5'

    with DataFile(fname) as my_data:
        # Load a HK time series
        time, data = my_data.load_hk("POL_Y6", "BIAS","VG4A_SET")

        # Load some scientific data
        time, data = my_data.load_sci("POL_G0", "DEM", "Q1")

The class :class:`.DataFile` assumes that the name of the file follows
the convention used by the acquisition software used in the
system-level tests in Bologna and during nominal data acquisition in
Tenerife. Be sure not to mess with HDF5 file names!

Since the kind of HDF5 file used in Strip has a complex structure,
Striptease provides a few facilities to handle them. To load timelines
of housekeeping parameter, temperature sensors, and detector outputs,
the :class:`.DataFile` class provides two methods:

- :meth:`.DataFile.load_hk`
- :meth:`.DataFile.load_sci`
- :meth:`.DataFile.load_cryo`

Moreover, a method :meth:`.DataFile.get_average_biases` can be used
to retrieve the average level of biases within some time frame.

.. autoclass:: striptease.DataFile
   :members:


Accessing the list of tags
~~~~~~~~~~~~~~~~~~~~~~~~~~

Every :class:`.DataFile` object keeps the list of tags in the ``tags``
attribute, which is a list of object of type :class:`.Tag`. Here is a
code that searches for all the tags containing the string
``STABLE_ACQUISITION`` in their name::

  from striptease import DataFile

  with DataFile("test.h5") as inpf:
      list_of_tags = [
          t
          for t in inpf.tags
          if "STABLE_ACQUISITION" in t.name
      ]

  for cur_tag in list_of_tags:
      print("Found a tag: ", cur_tag.name)

  # Possible output:
  #
  # Found a tag: STABLE_ACQUISITION_R0
  # Found a tag: STABLE_ACQUISITION_B0
  # Found a tag: STABLE_ACQUISITION_R1
  # Found a tag: STABLE_ACQUISITION_B1


.. autoclass:: striptease.Tag



Information about housekeeping parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As there are hundreds of housekeeping parameters used in Strip HDF5
files, Striptease provides the function :func:`.get_hk_descriptions`.
You pass the name of a group and a subgroup to it, and it returns a
`dict`-like object of type :class:`.HkDescriptionList` that associates
the name of each housekeeping in the group/subgroup with a textual
description. The object can be printed using ``print``: it will
produce a (long!) table containing all the housekeeping parameters and
descriptions in alphabetic order.


.. autoclass:: striptease.HkDescriptionList
   :members:

.. autofunction:: striptease.get_hk_descriptions


Handling multiple HDF5 files
----------------------------

It is often the case that the data you are looking for spans more than
one HDF5 file. In this case, it is a tedious process to read chunks of
data from several files and knit them together. Luckly, Striptease
provides the :class:`.DataStorage` class, which implements a database
of HDF5 files and provides methods for accessing scientific and
housekeeping data without bothering of which files should be read.

Here is an example::

  from striptease import DataStorage

  # This call might take some time if you have never used DataStorage
  # before, as it needs to build an index of all the files
  ds = DataStorage("/storage/strip")

  # Wow! We are reading one whole day of housekeeping data!
  times, data = ds.load_hk(
      mjd_range=(59530.0, 59531.0),
      group="BIAS",
      subgroup="POL_R0",
      par="VG1_HK",
  )

Note that the script provides the range of times as a MJD range; the
:class:`.DataStorage` object looks in the list of files and decides
which files contain this information and reads them. The return value
is the same as for a call to :meth:`.DataFile.load_hk`.

For the class :class:`.DataStorage` to work, a database of the HDF5
files in the specified path must be already present. You can create
one using the command-line script ``build_hdf5_database.py``:

.. code-block:: text

  ./build_hdf5_database.py /storage/strip

Accessing data in a storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :class:`.DataStorage` provides the following methods to access
tags, scientific data and housekeeping parameters:

- :meth:`.DataStorage.get_tags` retrieves a list of tags;
- :meth:`.DataStorage.load_sci` retrieves scientific timelines;
- :meth:`.DataStorage.load_hk` retrieves housekeeping timelines;
- :meth:`.DataStorage.load_cryo` retrieves the timelines measured
  by temperature sensors.

All these functions accept either a 2-tuple containing the start and
end MJD or a :class:`.Tag` object that specifies the time range.

.. autoclass:: striptease.DataStorage
   :members:

You can access a list of the files indexed by a :class:`.DataStorage`
object using the method :meth:`.DataStorage.get_list_of_files()`,
which returns a list of :`.HDF5FileInfo` objects.

.. autoclass:: striptease.HDF5FileInfo


