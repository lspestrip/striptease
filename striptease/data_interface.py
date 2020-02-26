def load_sci_data(fname_or_data, module, polarimeter, detector, data_type):
    '''
    Loads scientific data from one detector of a given polarimeter
    CALL time, data = load_sci_data(fname_or_data, module, polarimeter, detector, data_type)

    INPUTS
    fname_or_data MIXED       if string then complete path to the filename, if h5py._hl.dataset.Dataset 
                              then it contains the actual data loaded externally
    module        STRING      string of the module (O, Y, R, G, B, R, W)
    polarimeter   STRING      string of the polarimeter (0, 1, 2, 3, 4, 5, 6)
    detector      STRING      detector to be displayed (Q1, Q2, U1, U2)
    data_type     STRING      type of data to be retreived (DEM, PWR)

    OUTPUTS
    time, data   INT or NUMPY_ARRAY     In case of error time, data = -1, 1. Otherwise they 
                                        contain the time stream and the scientific data stream
    '''

    import h5py
    import numpy as np
    import matplotlib.pylab as plt
    import astropy.time
    import datetime
    import os.path

    
    # Test inputs
    
    # File exists?
    if type(fname_or_data) == str:
        if os.path.exists(fname_or_data) == False:
            msg = 'ERROR: File %s does not exist' % fname_or_data
            print(msg)
            return -1, -1
        
    # fname of correct type?
    if ((type(fname_or_data) != str) and (str(type(fname_or_data)) != "<class 'h5py._hl.dataset.Dataset'>")):
        msg = 'ERROR: type(fname) %s is wrong' % str(type(fname_or_data))
        print(msg)
        return -1, -1
        
    
    # Module exists?
    modules = ['O', 'Y', 'R', 'G', 'B', 'R', 'W', 'o', 'y', 'r', 'g', 'b', 'r', 'w']
    if (module in modules) == False:
        msg = 'ERROR: Module %s does not exist' % module
        print(msg)
        return -1, -1
    module = module.upper()
    
    # Polarimeter exists?
    polarimeters = ['0','1','2','3','4','5','6']
    if (polarimeter in polarimeters) == False:
        msg = 'ERROR: Polarimeter %s does not exist' % polarimeter
        print(msg)
        return -1, -1
    
    if (module+polarimeter) == 'W0':
        msg = 'ERROR: Polarimeter %s does not exist' % module+polarimeter
        print(msg)
        return -1, -1
    
    # Detector exists?
    detectors = ['Q1', 'Q2', 'U1', 'U2']
    if (detector in detectors) == False:
        msg = 'ERROR: Detector %s does not exist' % detector
        print(msg)
        return -1, -1
    
    # Data type exists?
    data_types = ['PWR', 'DEM', 'pwr', 'dem']
    if (data_type in data_types) == False:
        msg = 'ERROR: Data type %s does not exist' % data_type
        print(msg)
        return -1, -1
    data_type.upper()
    
    channel = 'POL_%s%s' % (module, polarimeter)       
    if type(fname_or_data) == str:
        f = h5py.File(fname_or_data,"r")
        scidata = f[channel]["pol_data"]
    else:
        scidata = fname_or_data
        
    scitime = astropy.time.Time(scidata["m_jd"], format="mjd").unix  #time SCI in sec
    
    return scitime, scidata[data_type+detector]
