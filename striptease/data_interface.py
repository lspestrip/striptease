###########################################################################################################


class load_data:
    """
    Class to load housekeepings data
    Instance creation
    mydata = hk_data(fname)

    INPUT
    fname    STRING    filename pointing to the datafile

    Methods:
    read_hklist: - reads the list of housekeepings and stores it into a dictionary
    print_hklist: - prints the list of housekeepings with its description
    """

    import h5py
    import numpy as np
    import matplotlib.pylab as plt
    import astropy.time
    import datetime
    import os.path

    def __init__(self, fname):

        import h5py
        import numpy as np

        self.fname = fname
        self.hklist_fname = "hk_pars"
        self.groups = ["POL", "BOARD"]
        self.subgroups = ["BIAS", "DAQ"]

        # Define polarimeters and boards
        self.polarimeters = []
        for module in ["O", "R", "B", "G", "Y", "I", "V"]:
            for pol in np.arange(6):
                self.polarimeters.append("POL_" + module + str(pol))
        for pol in np.arange(1, 7):
            self.polarimeters.append("POL_W" + str(pol))

        self.boards = []
        for module in ["O", "R", "B", "G", "Y", "I", "V"]:
            self.boards.append("BOARD_" + module)

        # Read data from H5 file
        # File exists?
        try:
            f = open(self.fname)
        except IOError as e:
            if str(type(self.fname)) != "<class 'h5py._hl.dataset.Dataset'>":
                raise ValueError(f"File can't be accessed")

        self.data = h5py.File(self.fname, "r")

    def read_hklist(self, group, subgroup):
        """
        Reads the list of housekeeping parameters with their own description
        CALL hk_data.red_hklist(group, subgroup)
        
        INPUTS
        group      STRING    the main group (either POL_XY or BOARD_X, where X is the module string
                             and Y is the polarimeter number
        subgroup   STRING    the subgroup (either "BIAS" or "DAQ")
        
        OUTPUTS
        hk_list  DICT   the dictionary containing the housekeeping parameters and description strings
        """
        import csv

        # Check inputs
        if not group.upper() in self.groups:
            raise ValueError(f"ERROR: Group %s does not exist" % group)

        if not subgroup.upper() in self.subgroups:
            raise ValueError(f"ERROR: Subgroup %s does not exist" % subgroup)

        par_fname = "%s_%s_%s.csv" % (
            self.hklist_fname,
            group.upper(),
            subgroup.upper(),
        )

        hklist = {}
        with open(par_fname, mode="r") as csv_file:
            csv_reader = csv.DictReader(csv_file)
            line_count = 0
            for row in csv_reader:
                line_count += 1
                hklist[row["HK_PAR"]] = row["Description"]

        return hklist

    def print_hklist(self, group, subgroup):
        """
        Prints the list of housekeeping parameters with their own description
        CALL hklist = hk_data.print_hklist(group, subgroup)
        
        INPUTS
        group      STRING    the main group (either POL_XY or BOARD_X, where X is the module string
                             and Y is the polarimeter number
        subgroup   STRING    the subgroup (either "BIAS" or "DAQ")
        
        OUTPUTS
        None
        """

        # Check inputs
        if not group.upper() in self.groups:
            raise ValueError(f"ERROR: Group %s does not exist")

        if not subgroup.upper() in self.subgroups:
            raise ValueError(f"ERROR: Subgroup %s does not exist")

        par_fname = "%s_%s_%s.csv" % (self.hklist_fname, group, subgroup)

        hklist = self.read_hklist(group.upper(), subgroup.upper())
        keys = hklist.keys()

        print("Parameters for group %s and subgroup %s" % (group, subgroup))
        for key in keys:
            if len(key) < 8:
                spacer = "\t\t"
            else:
                spacer = "\t"
            outstring = "%s%s%s" % (key, spacer, hklist[key])
            print(outstring)

    # ---------------------------------------------------------------------------------------------------------------

    def load_hk(self, group, subgroup, par):
        """
        Add description here
        """
        import h5py
        import astropy

        # Check inputs
        if (group.upper() not in self.boards) and (
            group.upper() not in self.polarimeters
        ):
            raise ValueError(f"ERROR: Group %s does not exist" % group)

        if not subgroup.upper() in self.subgroups:
            raise ValueError(f"ERROR: Subgroup %s does not exist" % subgroup)

        if group[0] == "P":
            grp = "POL"
        else:
            grp = "BOARD"

        pars = self.read_hklist(grp, subgroup)
        if not par.upper() in pars:
            raise ValueError(f"ERROR: Parameter %s does not exist" % par)

        # Check inputs

        datahk = self.data[group.upper()][subgroup.upper()][par.upper()]
        hk_time = astropy.time.Time(
            datahk["m_jd"], format="mjd"
        ).unix  # Julian time in sec
        hk_data = datahk["value"]
        return hk_time, hk_data

    # ---------------------------------------------------------------------------------------------------------------

    def load_sci(self, polarimeter, detector, data_type):
        """
        Loads scientific data from one detector of a given polarimeter

        CALL time, data = instance.load_sci(fname_or_data, polarimeter, detector, data_type), where instance is the instance
             of the class

        INPUTS
             polarimeter   STRING      string of the polarimeter (of the type XY, where X in [O,B,R,I,Y,G,W] and Y in [0, 1, 2, 3, 4, 5, 6])
             detector      STRING      detector to be displayed (Q1, Q2, U1, U2)
             data_type     STRING      type of data to be retreived (DEM, PWR)

        OUTPUTS
             time, data    NUMPY_ARRAY The time stream and the scientific data stream
        """

        import numpy as np
        import matplotlib.pylab as plt
        import astropy.time
        import datetime
        import os.path

        # Test inputs

        # Polarimeter exists?
        modules = ["O", "Y", "R", "G", "B", "R", "W"]
        polarimeters = ["0", "1", "2", "3", "4", "5", "6"]
        module = polarimeter[0]
        pol = polarimeter[1]

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

        channel = f"POL_{polarimeter}"
        scidata = self.data[channel]["pol_data"]

        scitime = astropy.time.Time(
            scidata["m_jd"], format="mjd"
        ).unix  # time SCI in sec

        return scitime, scidata[data_type + detector]
