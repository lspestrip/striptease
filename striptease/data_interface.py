def load_sci_data(fname_or_data, polarimeter, detector, data_type):
    """
    Loads scientific data from one detector of a given polarimeter
    CALL time, data = load_sci_data(fname_or_data, module, polarimeter, detector, data_type)

    INPUTS
    fname_or_data MIXED       if string then complete path to the filename, if h5py._hl.dataset.Dataset 
                              then it contains the actual data loaded externally
    polarimeter   STRING      string of the polarimeter (of the type XY, where X in [O,B,R,I,Y,G,W] and Y in [0, 1, 2, 3, 4, 5, 6])
    detector      STRING      detector to be displayed (Q1, Q2, U1, U2)
    data_type     STRING      type of data to be retreived (DEM, PWR)

    OUTPUTS
    time, data   INT or NUMPY_ARRAY     In case of error time, data = -1, 1. Otherwise they 
                                        contain the time stream and the scientific data stream
    """

    import h5py
    import numpy as np
    import matplotlib.pylab as plt
    import astropy.time
    import datetime
    import os.path

    # Test inputs

    # File exists?
    try:
        f = open(fname_or_data)
    except IOError as e:
        if str(type(fname_or_data)) != "<class 'h5py._hl.dataset.Dataset'>":
            raise ValueError(f"File can't be accessed")

    # # fname of correct type?
    # if (type(fname_or_data) != str) and (
    #     str(type(fname_or_data)) != "<class 'h5py._hl.dataset.Dataset'>"
    # ):
    #     msg = "ERROR: type(fname) %s is wrong" % str(type(fname_or_data))
    #     print(msg)
    #     return -1, -1

    # # Module exists?
    # modules = ["O", "Y", "R", "G", "B", "R", "W", "o", "y", "r", "g", "b", "r", "w"]
    # if not module in modules:
    #     raise ValueError(f"Module {module} does not exist")

    # module = module.upper()

    # Polarimeter exists?
    modules = ["O", "Y", "R", "G", "B", "R", "W"]
    polarimeters = ["0", "1", "2", "3", "4", "5", "6"]
    module = polarimeter[0]
    pol    = polarimeter[1]

    if (not module.upper() in modules) or (not pol.upper() in polarimeters):
        raise ValueError(f"ERROR: Polarimeter {polarimeter} does not exist")

    if polarimeter.upper() == "W0":
        raise ValueError(f"ERROR: Polarimeter {polarimeter} does not exist")

    polarimeter = polarimeter.upper()
    
    # Detector exists?
    detectors = ["Q1", "Q2", "U1", "U2"]
    if not detector.upper() in detectors:
        raise ValueError(f"ERROR: Detector %s does not exist")

    detector = detector.upper()
    
    # Data type exists?
    data_types = ["PWR", "DEM"]
    if not data_type.upper() in data_types:
        raise ValueError(f"ERROR: Data type %s does not exist")

    data_type = data_type.upper()

    channel = "POL_%s" % (polarimeter)
    if type(fname_or_data) == str:
        f = h5py.File(fname_or_data, "r")
        scidata = f[channel]["pol_data"]
    else:
        scidata = fname_or_data

    scitime = astropy.time.Time(scidata["m_jd"], format="mjd").unix  # time SCI in sec

    return scitime, scidata[data_type + detector]
