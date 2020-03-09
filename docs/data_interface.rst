Reading data saved in HDF5 files
================================

Introduction
------------

The module data_interface.py provides an interface to the data
acquired by the instrument and stored in HDF5 files

It allows the user to access both scientific and housekeepings data
returning them into time, data numpy arrays.

Here is an example that shows how to use it::

    from striptease.hdf5files import DataFile
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
of housekeeping parameter and detector outputs, the :class:`.DataFile`
class provides two methods:

- :meth:`.DataFile.load_hk`
- :meth:`.DataFile.load_sci`

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

Handling multiple HDF5 files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Acquiring Strip data is a continuous process, and HDF5 files are
continuously created once every `n` hours. It might happen that the
data you want to load span more than one file. Striptease provides the
function :func:`.scan_data_path` to ease the task of transversing the
list of HDF5 in chronological order; it returns a list of
:class:`.DataFile` objects found in a folder and any of its
subdirectories.

Here is an example::

  from pathlib import Path
  from striptease.hdf5files import scan_data_path

  basepath = Path("/storage/mydata/2020")
  all_files = scan_data_path(basepath)

  # "all_files" is a list of DataFile objects, sorted in chronological
  # order


Module contents
----------------------------------

.. automodule:: striptease.hdf5files
    :members:
    :undoc-members:
    :show-inheritance:
