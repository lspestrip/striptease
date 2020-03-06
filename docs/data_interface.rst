Tutorial on module "data_interface.py"
=============================================

Objective
----------------------------------------

The module data_interface.py provides an interface to the data acquired
by the instrument and stored in HDF5 files

It allows the user to access both scientific and housekeepings data returning
them into time, data numpy arrays
       
Module contents
----------------------------------

Class: **LoadData**

*Call to instance the class*
``mydata = LoadData(filename)``, where ``filename`` is the complete path to the HDF5 file containing the data

*Attributes*
Assuming that ``mydata`` is the class instance, these are the attributes

* ``mydata.fname``: filename of the HDF5 file containing data (passed by the user)
* ``mydata.hklist_fname``: basename of the files containing the lists of HK parameters. These files are searched for in the local directory also containing the module
* ``mydata.groups = ["POL", "BOARD"]``:  strings identifying the top groups of the HK parameters
* ``mydata.subgroups = ["BIAS", "DAQ"]``: strings identifying the subgroups of the HK parameters
* ``mydata.polarimeters = ["O", "R", "B", "G", "Y", "I", "V", "W"]``: strings identifying the polarimeter groups
* ``mydata.boards = ["O", "R", "B", "G", "Y", "I", "V"]``: string identifying the boards
* ``mydata.data``: object pointing to the data contained in the HDF5 file

*Methods*

* ``mydata.read_hk_list`` :  reads the list of housekeeping parameters with their own description and returns it into a dictionary
* ``mydata.print_hk_list`` :  prints at video the list of housekeeping parameters with their own description
* ``load_sci``: loads scientific data
* ``load_hk``: loads housekeepings data

Methods description
----------------------------------

Method **read_hk_list**

*CALL* 

``instance.read_hk_list(group, subgroup)``, where ``instance`` is the instance of the class
        
*INPUTS*

============   ==========  ==============================================
Variable       Type        Description
============   ==========  ==============================================
``group``      ``STRING``  the main group (either ``"POL`` or ``"BOARD"``
``subgroup``   ``STRING``  the subgroup (either ``"BIAS"`` or ``"DAQ"``)
============   ==========  ==============================================
        
*OUTPUTS*

=========== =========  ======================================================
Variable    Type       Description
=========== =========  ======================================================
``hk_list`` ``DICT``   The dictionary containing the housekeeping parameters
                       and description strings
=========== =========  ======================================================

*EXAMPLE*

``import data_interface``

``fname = '/path_to/data.h5'``

``my_data = LoadData(fname)``

``pars = my_data.read_hk_list("POL", "BIAS")``
   
Method **print_hk_list**

*CALL* 

``instance.print_hk_list(group, subgroup)``, where ``instance`` is the instance of the class
        
*INPUTS*

============ ==========   ==============================================
Variable     Type         Description
============ ==========   ==============================================
``group``    ``STRING``   the main group (either ``"POL`` or ``"BOARD"``
``subgroup`` ``STRING``   the subgroup (either ``"BIAS"`` or ``"DAQ"``)
============ ==========   ==============================================
        
*OUTPUTS*

None

*EXAMPLE*

``import data_interface``

``fname = '/path_to/data.h5'``

``my_data = LoadData(fname)``

``my_data.print_hk_list("POL", "BIAS")``

Method **load_sci**

*CALL* 

``time, data = instance.load_sci(polarimeter, detector, data_type)``, where ``instance`` is the instance of the class
        
*INPUTS*

=============== ==========  ================================================
Variable        Type        Description
=============== ==========  ================================================
``polarimeter`` ``STRING``  string of the polarimeter (of the type ``XY``, 
                            where ``X`` in ``["O","B","R","I","Y","G","W"]``
                            and ``Y`` in ``[0, 1, 2, 3, 4, 5, 6]``)
``detector``    ``STRING``  detector to be displayed 
                            (``"Q1", "Q2", "U1", "U2"``)
``data_type``   ``STRING``  type of data to be retrieved (``"DEM"`` or 
                            ``"PWR"`` )
=============== ==========  ================================================
        
*OUTPUTS*

============== ================  ======================================================
Variable       Type              Description
============== ================  ======================================================
``time, data`` ``NUMPY_ARRAY``   The time stream and the scientific data stream
============== ================  ======================================================

*EXAMPLE*

``import data_interface``

``fname = '/path_to/data.h5'``

``my_data = LoadData(fname)``

``time, data = my_data.load_sci("Y6", "Q1","DEM")``

Method **load_hk**

*CALL* 

``time, data = instance.load_hk(group, subgroup, par)``, where ``instance`` is the instance of the class
        
*INPUTS*

============= ==========  =======================================
Variable      Type        Description
============= ==========  =======================================
``group``     ``STRING``  string of the HK group (of the type ``"POL_XY"``, 
                          where ``X`` in ``["O","B","R","I","Y","G","W"]``
                          and ``Y`` in ``[0, 1, 2, 3, 4, 5, 6]``) or ``"BOARD_X"``
``subgroup``  ``STRING``  either ``"BIAS"`` or ``"DAQ"``
``par``       ``STRING``  HK parameter
============= ==========  =======================================
        
*OUTPUTS*

============== ================  ======================================================
Variable       Type              Description
============== ================  ======================================================
``time, data`` ``NUMPY_ARRAY``   The time stream and the housekeepings data stream
============== ================  ======================================================

*EXAMPLE*

``import data_interface``

``fname = '/path_to/data.h5'``

``my_data = LoadData(fname)``

``time, data = my_data.load_hk("POL_Y6", "BIAS","VG4A_SET")``

