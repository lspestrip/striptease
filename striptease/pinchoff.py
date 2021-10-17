class PinchOffAnalysis:
    def __init__(self, data, output_folder="./"):
        data.read_file_metadata()
        self.data = data
        self.tags = data.tags
        self.amps = ["H%s%s" % (leg, n) for leg in ["A", "B"] for n in ["1", "2", "3"]]
        self.verification_tags = self.get_subtags(
            "PINCHOFF_VERIFICATION_1"
        ) + self.get_subtags("PINCHOFF_IDSET")
        self.configuration = {}
        self.output_folder = output_folder
        self.amp_tag_translation = {
            "HA1": 0,
            "HA2": 2,
            "HA3": 4,
            "HB1": 1,
            "HB2": 3,
            "HB3": 5,
        }
        self.tag_amp_translation = {
            "0": "HA1",
            "2": "HA2",
            "4": "HA3",
            "1": "HB1",
            "3": "HB2",
            "5": "HB3",
        }
        self.quad = lambda x, a, b, c: a * x ** 2 + b * x + c
        self.lin = lambda x, a, b: a * x + b

    #        self.verification_tags = ['STABLE_ACQUISITION_%s' % p for p in self.get_tested_polarimeters()] + \
    #        ['PINCHOFF_IDSET_%s_%s' % (p,a) for p in self.get_tested_polarimeters() for a in self.amps]

    ##########################
    # Add a tag
    ##########################
    def add_tag(self, mjd_start, mjd_end, name, start_comment, end_comment):
        """
        This function add a tag into self.tags. THE FILE IS NOT MODIFIED, so any modification is
        lost when the instance is destroyed
        """
        import striptease

        last_id = self.tags[-1].id
        newtag = striptease.hdf5files.Tag(
            last_id, mjd_start, mjd_end, name, start_comment, end_comment
        )

        # append tag
        self.tags.append(newtag)
        self.verification_tags = self.get_subtags(
            "PINCHOFF_VERIFICATION_1"
        ) + self.get_subtags("PINCHOFF_IDSET")
        print("TAGS UPDATED: ", newtag)

    ##########################
    # Get times of a given tag
    ##########################
    def get_times(self, polarimeter, tag):
        """
        This function extracts start and end times for the first verification point of a given
        polarimeter in a given module
        """
        curname = "%s%s" % (tag, polarimeter)
        curtag = [t for t in self.tags if (t.name in curname)]
        try:
            curtag = curtag[0]
        except IndexError:
            print("Polarimeter %s is not present in data" % polarimeter)
            return None, None

        tstart = curtag.mjd_start
        tend = curtag.mjd_end
        return tstart, tend

    #################################
    # Get HK in a given time interval
    #################################
    def get_hk(self, group, subgroup, parameter, tstart, tend):
        """
        This functions extracts HK data given a certain time interval
        """

        time_obj, values = self.data.load_hk(group, subgroup, parameter)
        mjd = time_obj.mjd  # Convert to Julian date
        mask = (mjd >= tstart) & (mjd <= tend)

        return time_obj[mask].unix, values[mask]

    ##################################
    # Get SCI in a given time interval
    ##################################
    def get_sci(self, polarimeter, data_type, detector, tstart, tend):
        """
        This function extract scientific data from a polarimeter
        given a certain time interval
        """
        time_obj, values = self.data.load_sci(polarimeter, data_type, detector)
        mjd = time_obj.mjd  # Convert to Julian date
        mask = (mjd >= tstart) & (mjd <= tend)

        return time_obj[mask].unix, values[mask]

    ##################################
    # Calculate r^2
    ##################################
    def rsquare(self, xvalues, yvalues, parameters, function):
        import numpy as np

        residuals = yvalues - function(xvalues, *parameters[0])
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((yvalues - np.mean(yvalues)) ** 2)
        return 1.0 - (ss_res / ss_tot)

    #########################################
    # Plot IV curves
    #########################################
    def plot_IV(self, polarimeters="All", filename=None, image="png"):
        import striptease
        import numpy as np
        from scipy.optimize import curve_fit
        import pickle
        from datetime import datetime

        """
        This function plots IV curves given a certain configuration stored into self.configuration.
        If self.configuration is empty the function first extracts the configuration for all tested
        polarimeters

        It also fits the IV curves with quadratic and linear functions

        Inputs
        polarimeters  STRING or LIST of strings. If polarimeters = 'All' (default)  then all the
                                                 polarimeter are tested. Otherwise it contains a
                                                 list of strings identifying the polarimeters to
                                                 be tested


        filename      STRING  The filename where to save the output dictionary in a pickle file
                              It defaults to None. In this case the filename is generated automatically

        image         STRING  The format of the saved plots ('png' (Default), 'pdf', 'svg')

        Output
        output   DICT   a dictionary containing the results of the linear and quadradic fits

        """
        if len(self.configuration) == 0:
            print("Generating instrument configuration")
            configuration = self.get_configuration(self.get_tested_polarimeters())
        else:
            configuration = self.configuration

        main_tags = list(configuration.keys())
        if polarimeters == "All":
            polarimeters = self.get_tested_polarimeters(tags=main_tags)

        amps = np.reshape(self.amps, (2, 3))

        output = {}

        for pol in polarimeters:
            # Initialize matrices
            vgate = [[j for j in [1, 2, 3]] for i in [0, 1]]
            idrain = [[j for j in [1, 2, 3]] for i in [0, 1]]
            fitquad = [[j for j in [1, 2, 3]] for i in [0, 1]]
            fitlin = [[j for j in [1, 2, 3]] for i in [0, 1]]
            rsquared = [[j for j in [1, 2, 3]] for i in [0, 1]]
            rsquared2 = [[j for j in [1, 2, 3]] for i in [0, 1]]
            highlight = [
                [[j for j in [1, 2, 3]] for i in [0, 1]],
                [[j for j in [1, 2, 3]] for i in [0, 1]],
            ]

            output[pol] = {}

            for row in [0, 1]:
                for col in [0, 1, 2]:
                    # Get current values
                    currents = self.get_currents(pol, amps[row, col])

                    # Remove repeats
                    currents = list(dict.fromkeys(currents))

                    # Get measured Voltage and current values
                    dumv = []
                    dumi = []

                    # Add first point from configuration
                    amp_id = self.amp_tag_translation[amps[row, col]]

                    cur_hk = "VG%s_HK" % (str(amp_id))
                    cur_tag = "PINCHOFF_VERIFICATION_1"
                    if cur_tag in self.configuration.keys():
                        vg_value = self.configuration[cur_tag][pol][cur_hk]
                        vstart = vg_value
                        dumv.append(vg_value)

                        cur_hk = "ID%s_HK" % (str(amp_id))
                        id_value = self.configuration[cur_tag][pol][cur_hk]
                        dumi.append(id_value)

                    #                    print(pol, amps[row,col], amp_id, vg_value,id_value)

                    for current in currents:
                        curtag = "PINCHOFF_IDSET_%s_%s_%smuA" % (
                            pol,
                            amps[row, col],
                            str(current),
                        )
                        tstart, tend = self.get_times(pol, curtag)

                        amp_id = self.amp_tag_translation[amps[row, col]]
                        cur_hk = "VG%s_HK" % (str(amp_id))
                        group, subgroup = striptease.hdf5files.get_group_subgroup(
                            cur_hk
                        )
                        subgroup = "%s_%s" % (subgroup, pol)
                        t, vg_values = self.get_hk(
                            group, subgroup, cur_hk, tstart, tend
                        )

                        cur_hk = "ID%s_HK" % (str(amp_id))
                        group, subgroup = striptease.hdf5files.get_group_subgroup(
                            cur_hk
                        )
                        subgroup = "%s_%s" % (subgroup, pol)
                        t, id_values = self.get_hk(
                            group, subgroup, cur_hk, tstart, tend
                        )

                        dumv.append(np.mean(vg_values))
                        dumi.append(np.mean(id_values))

                    # Sort values according to Vgate
                    dumi = np.array(dumi)
                    dumv = np.array(dumv)

                    dumi = dumi[np.argsort(dumv)]
                    dumv = np.sort(dumv)

                    vgate[row][col] = dumv
                    idrain[row][col] = dumi

                    # Fit curve
                    try:
                        fitquad[row][col] = curve_fit(self.quad, dumv, dumi)
                        rsquared2[row][col] = self.rsquare(
                            dumv, dumi, fitquad[row][col], self.quad
                        )
                    except KeyError:
                        fitquad[row][col] = None
                        rsquared2[row][col] = None

                    try:
                        fitlin[row][col] = curve_fit(self.lin, dumv, dumi)
                        rsquared[row][col] = self.rsquare(
                            dumv, dumi, fitlin[row][col], self.lin
                        )
                    except KeyError:
                        fitlin[row][col] = None
                        rsquared[row][col] = None

                    highlight[0][row][col] = np.where(dumv == vstart)[0]
                    highlight[1][row][col] = "Stable acquisition before pinchoff"

                    output[pol][amps[row, col]] = {}
                    output[pol][amps[row, col]]["quadratic"] = (
                        fitquad[row][col],
                        rsquared2[row][col],
                    )
                    output[pol][amps[row, col]]["linear"] = (
                        fitlin[row][col],
                        rsquared[row][col],
                    )

            self.plot_IV_single(
                pol,
                vgate,
                idrain,
                fitquad,
                fitlin,
                rsquared2,
                rsquared,
                highlight,
                image,
            )

        if not filename:
            now = str(datetime.now())
            filename = self.output_folder + "strip_pinchoff_analysis_" + now + ".pickle"

        file_id = open(filename, "wb")
        pickle.dump(output, file_id)
        file_id.close()

        return output

    #        return polarimeters

    def plot_IV_single(
        self, polarimeter, V, I, fitquad, fitlin, rq, rlin, highlight, image
    ):
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as pl
        import matplotlib.colors as mcolors
        import numpy as np

        """
        This function makes a IV plot for a single polarimeter

        Inputs
        polarimeter STRING      the id of the polarimeter
        V           FLOAT ARRAY an array of floats containing the voltage values
        I           FLOAT ARRAY an array of floats containing the current values
        fitquad     LIST        results of quadratic fits
        fitlin      LIST        results of linear fits
        rq          LIST        rsquared of quadratic fits
        rlin        lIST        rsquared of linear fits
        highlight   MIXED       indicates if one or more points need be highlighted
                                with a different color. In this case highlight contains
                                two 2x3 lists: the first one is the list of indices of the points
                                to be highlighted, the second one is a list of descriptions
                                appearing in a legend
        image       STRING      Image format for the plots ('png', 'svg', 'pdf')
        """
        colors = list(mcolors.CSS4_COLORS.values())

        amps = np.reshape(self.amps, (2, 3))
        fig, axes = pl.subplots(2, 3, figsize=(20, 20))
        plot_title = "Polarimeter " + polarimeter
        fig.suptitle(plot_title)
        for row in [0, 1]:
            for col in [0, 1, 2]:
                # Plot data
                axes[row, col].plot(V[row][col], I[row][col])
                axes[row, col].plot(
                    V[row][col], I[row][col], "o", markersize=10, label="PINCHOFF TEST"
                )
                xarr = np.linspace(min(V[row][col]), max(V[row][col]), 100)

                # Plot fits
                if fitquad[row][col] is not None:
                    equation = (
                        r"$y = %3.4f\,x^2 + %3.4f\,x + %3.4f\,\,\, r^2 = %3.4f$"
                        % (
                            fitquad[row][col][0][0],
                            fitquad[row][col][0][1],
                            fitquad[row][col][0][2],
                            rq[row][col],
                        )
                    )
                    axes[row, col].plot(
                        xarr, self.quad(xarr, *fitquad[row][col][0]), label=equation
                    )

                if fitlin[row][col] is not None:
                    equation = r"$y = %3.4f\,x + %3.4f\,\,\, r^2 = %3.4f$" % (
                        fitlin[row][col][0][0],
                        fitlin[row][col][0][1],
                        rlin[row][col],
                    )
                    axes[row, col].plot(
                        xarr, self.lin(xarr, *fitlin[row][col][0]), label=equation
                    )

                # Labels
                axes[row, col].set(
                    xlabel="Gate voltage [mV]", ylabel="Drain current [µA]"
                )

                if highlight:
                    indices = highlight[0][row][col]
                    labels = highlight[1][row][col]
                    j = -1
                    for index in indices:
                        j = j + 1
                        if type(labels) == str:
                            lab = labels
                        else:
                            lab = labels[j]

                        axes[row, col].plot(
                            V[row][col][index],
                            I[row][col][index],
                            "o",
                            markersize=10,
                            color=colors[20 + j],
                            label=lab,
                        )

                title = "Amplifier " + amps[row, col]
                axes[row, col].set_title(title)
                axes[row, col].legend()

        filename = "%sIVplot_%s.%s" % (self.output_folder, polarimeter, image)
        pl.savefig(filename)
        pl.close()

    #########################################
    # Plot Vg and Id curves versus time #####
    #########################################

    def bias_plot(self, polarimeters="All", image="png"):
        import striptease
        import numpy as np

        """
        This function plots Vg and Id versus time given a certain configuration stored into self.configuration.
        If self.configuration is empty the function first extracts the configuration for all tested
        polarimeters

        Inputs
        polarimeters LIST of STRING values  List of polarimeters to plot ('All' plots all polarimeters)
        image        STRING         the format of the output plot ('svg, 'png', 'pdf')

        Output
        None (plots are saved as pdf files)

        """
        vg_col = {
            "black": "#000000",
            "blue": "#0000FF",
            "blueviolet": "#8A2BE2",
            "brown": "#A52A2A",
            "burlywood": "#DEB887",
            "cadetblue": "#5F9EA0",
            "chartreuse": "#7FFF00",
            "chocolate": "#D2691E",
            "coral": "#FF7F50",
            "cornflowerblue": "#6495ED",
            "cornsilk": "#FFF8DC",
            "crimson": "#DC143C",
            "darkblue": "#00008B",
            "darkcyan": "#008B8B",
            "darkgoldenrod": "#B8860B",
            "darkgray": "#A9A9A9",
            "darkgreen": "#006400",
            "darkgrey": "#A9A9A9",
            "darkkhaki": "#BDB76B",
            "darkmagenta": "#8B008B",
            "darkolivegreen": "#556B2F",
            "darkorange": "#FF8C00",
            "darkorchid": "#9932CC",
            "darkred": "#8B0000",
            "darksalmon": "#E9967A",
            "darkseagreen": "#8FBC8F",
            "darkslateblue": "#483D8B",
            "darkslategray": "#2F4F4F",
            "darkslategrey": "#2F4F4F",
            "darkturquoise": "#00CED1",
            "darkviolet": "#9400D3",
            "deeppink": "#FF1493",
            "deepskyblue": "#00BFFF",
            "dimgray": "#696969",
            "dimgrey": "#696969",
            "dodgerblue": "#1E90FF",
            "firebrick": "#B22222",
            "floralwhite": "#FFFAF0",
            "forestgreen": "#228B22",
            "fuchsia": "#FF00FF",
            "gainsboro": "#DCDCDC",
            "ghostwhite": "#F8F8FF",
            "gold": "#FFD700",
            "goldenrod": "#DAA520",
            "green": "#008000",
            "greenyellow": "#ADFF2F",
            "grey": "#808080",
            "honeydew": "#F0FFF0",
            "hotpink": "#FF69B4",
            "indianred": "#CD5C5C",
            "indigo": "#4B0082",
            "ivory": "#FFFFF0",
            "khaki": "#F0E68C",
            "lavender": "#E6E6FA",
            "lavenderblush": "#FFF0F5",
            "lawngreen": "#7CFC00",
        }

        id_col = {
            "magenta": "#FF00FF",
            "maroon": "#800000",
            "mediumblue": "#0000CD",
            "mediumorchid": "#BA55D3",
            "mediumpurple": "#9370DB",
            "mediumseagreen": "#3CB371",
            "mediumslateblue": "#7B68EE",
            "mediumspringgreen": "#00FA9A",
            "mediumturquoise": "#48D1CC",
            "mediumvioletred": "#C71585",
            "midnightblue": "#191970",
            "mintcream": "#F5FFFA",
            "mistyrose": "#FFE4E1",
            "moccasin": "#FFE4B5",
            "navajowhite": "#FFDEAD",
            "navy": "#000080",
            "oldlace": "#FDF5E6",
            "olive": "#808000",
            "olivedrab": "#6B8E23",
            "orange": "#FFA500",
            "orangered": "#FF4500",
            "orchid": "#DA70D6",
            "palegoldenrod": "#EEE8AA",
            "palegreen": "#98FB98",
            "paleturquoise": "#AFEEEE",
            "palevioletred": "#DB7093",
            "papayawhip": "#FFEFD5",
            "peachpuff": "#FFDAB9",
            "peru": "#CD853F",
            "pink": "#FFC0CB",
            "plum": "#DDA0DD",
            "powderblue": "#B0E0E6",
            "purple": "#800080",
            "rebeccapurple": "#663399",
            "red": "#FF0000",
            "rosybrown": "#BC8F8F",
            "royalblue": "#4169E1",
            "saddlebrown": "#8B4513",
            "salmon": "#FA8072",
            "sandybrown": "#F4A460",
            "seagreen": "#2E8B57",
            "seashell": "#FFF5EE",
            "sienna": "#A0522D",
            "silver": "#C0C0C0",
            "skyblue": "#87CEEB",
            "slateblue": "#6A5ACD",
            "springgreen": "#00FF7F",
            "steelblue": "#4682B4",
            "tan": "#D2B48C",
            "teal": "#008080",
            "thistle": "#D8BFD8",
            "tomato": "#FF6347",
            "turquoise": "#40E0D0",
            "violet": "#EE82EE",
            "wheat": "#F5DEB3",
            "yellowgreen": "#9ACD32",
        }

        vg_colors = list(vg_col.values())
        id_colors = list(id_col.values())
        id_colors = list(reversed(id_colors))

        if len(self.configuration) == 0:
            print("Generating instrument configuration")
            configuration = self.get_configuration(self.get_tested_polarimeters())
        else:
            configuration = self.configuration

        main_tags = list(configuration.keys())

        if polarimeters == "All":
            polarimeters = self.get_tested_polarimeters(tags=main_tags)

        amps = np.reshape(self.amps, (2, 3))

        for pol in polarimeters:

            # Initialize matrices
            vgate = [[j for j in [1, 2, 3]] for i in [0, 1]]
            idrain = [[j for j in [1, 2, 3]] for i in [0, 1]]
            timev = [[j for j in [1, 2, 3]] for i in [0, 1]]
            timei = [[j for j in [1, 2, 3]] for i in [0, 1]]

            for row in [0, 1]:
                for col in [0, 1, 2]:
                    # Get current values
                    currents = self.get_currents(pol, amps[row, col])

                    # Remove repeats

                    # Get measured Voltage, current and time values
                    dumv = []
                    dumi = []
                    dumvt = []
                    dumit = []

                    # Add first point from configuration
                    amp_id = self.amp_tag_translation[amps[row, col]]

                    cur_vghk = "VG%s_HK" % (str(amp_id))
                    cur_idhk = "ID%s_HK" % (str(amp_id))
                    cur_tag = "PINCHOFF_VERIFICATION_1"
                    tags = []
                    col_id = 0
                    vg_col = []
                    id_col = []
                    if cur_tag in self.configuration.keys():

                        tags.append("Verif. point")
                        vg_col.append(vg_colors[col_id])
                        id_col.append(id_colors[col_id])
                        col_id = col_id + 1

                        tstart, tend = self.get_times(pol, cur_tag)

                        # VG data
                        group, subgroup = striptease.hdf5files.get_group_subgroup(
                            cur_vghk
                        )
                        subgroup = "%s_%s" % (subgroup, pol)
                        t, values = self.get_hk(group, subgroup, cur_vghk, tstart, tend)
                        dumv.append(values[-10:])
                        dumvt.append(t[-10:])

                        # ID data
                        group, subgroup = striptease.hdf5files.get_group_subgroup(
                            cur_idhk
                        )
                        subgroup = "%s_%s" % (subgroup, pol)
                        t, values = self.get_hk(group, subgroup, cur_idhk, tstart, tend)
                        dumi.append(values[-10:])
                        dumit.append(t[-10:])

                    for current in currents:
                        curtag = "PINCHOFF_IDSET_%s_%s_%smuA" % (
                            pol,
                            amps[row, col],
                            str(current),
                        )
                        vg_col.append(vg_colors[col_id])
                        id_col.append(id_colors[col_id])
                        col_id = col_id + 1
                        tags.append(str(current) + " muA")
                        tstart, tend = self.get_times(pol, curtag)

                        # VG data
                        group, subgroup = striptease.hdf5files.get_group_subgroup(
                            cur_vghk
                        )
                        subgroup = "%s_%s" % (subgroup, pol)
                        t, values = self.get_hk(group, subgroup, cur_vghk, tstart, tend)
                        dumv.append(values)
                        dumvt.append(t)

                        # ID data
                        group, subgroup = striptease.hdf5files.get_group_subgroup(
                            cur_idhk
                        )
                        subgroup = "%s_%s" % (subgroup, pol)
                        t, values = self.get_hk(group, subgroup, cur_idhk, tstart, tend)
                        dumi.append(values)
                        dumit.append(t)

                    # Sort values according to Vgate
                    #                    dumi = np.array(dumi)
                    #                    dumv = np.array(dumv)

                    #                    dumi = dumi[np.argsort(dumv)]
                    #                    dumv = np.sort(dumv)

                    vgate[row][col] = dumv
                    idrain[row][col] = dumi
                    timev[row][col] = dumvt
                    timei[row][col] = dumit

            self.bias_plot_single(
                pol, (timev, vgate), (timei, idrain), tags, vg_col, id_col, image=image
            )

    #        if filename == None:
    #            now = str(datetime.now())
    #            filename = self.output_folder + 'strip_pinchoff_analysis_' + now + '.pickle'

    #        file_id = open(filename,'wb')
    #        pickle.dump(output, file_id)
    #        file_id.close()

    #        return vgate, idrain, timev, timei

    def bias_plot_single(
        self, polarimeter, vgate, idrain, tags, vg_col, id_col, image="png"
    ):
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as pl
        import numpy as np

        """
        This function plots a given bias parameter versus time for a single polarimeter

        Inputs
        polarimeter STRING  the id of the polarimeter
        vgate       TUPLE   vgate[0] - FLOAT ARRAY an array of floats containing the time values
                            vgate[1] - FLOAT ARRAY an array of floats containing the vg values
        idrain      TUPLE   idrain[0] - FLOAT ARRAY an array of floats containing the time values
                            idrain[1] - FLOAT ARRAY an array of floats containing the id values
        tags        LIST    list of strings itentifying the various steps
        image       STRING  the format of the output plot ('svg', 'pdf', 'png')
        """

        amps = np.reshape(self.amps, (2, 3))
        fig, axes = pl.subplots(2, 3, figsize=(35, 30))
        plot_title = "Polarimeter " + polarimeter
        fig.suptitle(plot_title)
        newtime_v = [[[] for j in [1, 2, 3]] for i in [0, 1]]
        newtime_i = [[[] for j in [1, 2, 3]] for i in [0, 1]]
        startv = 0
        starti = 0

        # Produce a fake time vector that does not contain the gaps
        for row in [0, 1]:
            for col in [0, 1, 2]:
                for xv, xi in zip(vgate[0][row][col], idrain[0][row][col]):
                    dumv = list(np.arange(len(xv)) + startv)
                    startv = startv + len(xv)
                    newtime_v[row][col].append(dumv)

                    dumi = list(np.arange(len(xi)) + starti)
                    starti = starti + len(xi)
                    newtime_i[row][col].append(dumi)

        for row in [0, 1]:
            for col in [0, 1, 2]:
                # Plot data
                # tv = vgate[0]
                vg = vgate[1]
                # ti = idrain[0]
                idr = idrain[1]

                ax2 = axes[row, col].twinx()
                for x, y, x1, y1, t, vgc, idc in zip(
                    newtime_v[row][col],
                    vg[row][col],
                    newtime_i[row][col],
                    idr[row][col],
                    tags,
                    vg_col,
                    id_col,
                ):
                    axes[row, col].plot(x, y, color=vgc, label="Vg %s" % t)
                    axes[row, col].set_title(amps[row, col])
                    ax2.plot(x1, y1, color=idc, label="Id %s" % t)

                axes[row, col].legend(loc=2, bbox_to_anchor=(0, 1.15))
                axes[row, col].set(xlabel="time [sec]", ylabel="Vg [mV]")
                ax2.legend(loc=1, bbox_to_anchor=(1, 1.15))
                ax2.set(ylabel="Id [muA]")
                ax2.set(ylim=(0, 12000))

                # Labels
        #                axes[row,col].set(xlabel = 'time [s]', ylabel = label)

        filename = "%svg_id_timeplot_%s.%s" % (self.output_folder, polarimeter, image)
        pl.savefig(filename)
        pl.close()

    #########################################
    # Plot Sci curves versus time       #####
    #########################################

    def sci_plot(self, polarimeters="All", image="png"):
        import numpy as np

        """
        This function plots scientific data versus time given a certain configuration stored into self.configuration.
        If self.configuration is empty the function first extracts the configuration for all tested
        polarimeters

        Inputs
        polarimeters LIST of STRING values  List of polarimeters to plot ('All' plots all polarimeters)
        image        STRING         the format of the output plot ('svg, 'png', 'pdf')

        Output
        None (plots are saved as files)

        Notes
        The procedure produces for each polarimeter and for each tested amplifers one plot with
        eight subplots four for PWR data and four for DEM data.

        """

        diodes = ["Q1", "Q2", "U1", "U2"]
        data_types = ["PWR", "DEM"]

        if len(self.configuration) == 0:
            print("Generating instrument configuration")
            configuration = self.get_configuration(self.get_tested_polarimeters())
        else:
            configuration = self.configuration

        main_tags = list(configuration.keys())

        if polarimeters == "All":
            polarimeters = self.get_tested_polarimeters(tags=main_tags)

        amps = np.reshape(self.amps, (2, 3))

        for pol in polarimeters:

            # Initialize matrices
            data = {}
            time = {}

            for diode in diodes:
                for data_type in data_types:
                    key = "%s_%s" % (diode, data_type)
                    data[key] = [[j for j in [1, 2, 3]] for i in [0, 1]]
                    time[key] = [[j for j in [1, 2, 3]] for i in [0, 1]]

            # Now we cycle legs ([0,1]) and amps ([0,1,2]) for each element
            # we get all the available currents, the starting configuration point
            # and we store the scientific data in the data, time matrices
            for row in [0, 1]:
                for col in [0, 1, 2]:
                    # Get current values
                    currents = self.get_currents(pol, amps[row, col])

                    # Get measured Voltage, current and time values
                    dumv = {}
                    dumt = {}
                    for diode in diodes:
                        for data_type in data_types:
                            key = "%s_%s" % (diode, data_type)
                            dumv[key] = []
                            dumt[key] = []

                    cur_tag = "PINCHOFF_VERIFICATION_1"
                    tags = []
                    # col_id = 0
                    # vg_col = []
                    # id_col = []
                    if cur_tag in self.configuration.keys():

                        tags.append("Verif. point")
                        # vg_col.append(vg_colors[col_id])
                        # id_col.append(id_colors[col_id])
                        # col_id = col_id + 1

                        tstart, tend = self.get_times(pol, cur_tag)

                        for diode in diodes:
                            for data_type in data_types:
                                key = "%s_%s" % (diode, data_type)
                                dumv[key] = []
                                dumt[key] = []
                                t, values = self.get_sci(
                                    pol, data_type, diode, tstart, tend
                                )
                                dumv[key].append(values[-100:])
                                dumt[key].append(t[-100:])

                    for current in currents:
                        curtag = "PINCHOFF_IDSET_%s_%s_%smuA" % (
                            pol,
                            amps[row, col],
                            str(current),
                        )
                        # vg_col.append(vg_colors[col_id])
                        # id_col.append(id_colors[col_id])
                        # col_id = col_id + 1
                        tags.append(str(current) + " muA")
                        tstart, tend = self.get_times(pol, curtag)

                        for diode in diodes:
                            for data_type in data_types:
                                key = "%s_%s" % (diode, data_type)
                                t, values = self.get_sci(
                                    pol, data_type, diode, tstart, tend
                                )
                                dumv[key].append(values)
                                dumt[key].append(t)

                    #                     # Sort values according to Vgate
                    # #                    dumi = np.array(dumi)
                    # #                    dumv = np.array(dumv)

                    # #                    dumi = dumi[np.argsort(dumv)]
                    # #                    dumv = np.sort(dumv)
                    for diode in diodes:
                        for data_type in data_types:
                            key = "%s_%s" % (diode, data_type)
                            data[key][row][col] = dumv[key]
                            time[key][row][col] = dumt[key]

                    # Now data and time contain, for each key, the scientifica data for the various
                    # current steps of the six amplifiers

            self.sci_plot_single(pol, time, data, tags, image=image)

    # #        if filename == None:
    # #            now = str(datetime.now())
    # #            filename = self.output_folder + 'strip_pinchoff_analysis_' + now + '.pickle'

    # #        file_id = open(filename,'wb')
    # #        pickle.dump(output, file_id)
    # #        file_id.close()

    # return(tags, time, data)

    def sci_plot_single(self, polarimeter, time, data, tags, image="png"):
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as pl
        import numpy as np

        """
        This function plots a given bias parameter versus time for a single polarimeter

        Inputs
        polarimeter STRING  the id of the polarimeter
        time       DICT with FLOAT arrays containing the time values
        data       DICT with FLOAT arrays containing the data values
        tags        LIST    list of strings itentifying the various steps
        image       STRING  the format of the output plot ('svg', 'pdf', 'png')
        """

        amps = np.reshape(self.amps, (2, 3))
        keys = data.keys()
        keys1 = np.reshape(list(keys), (4, 2))

        # Produce a fake time vector that does not contain the gaps
        newtime = {}
        for key in keys:
            start = 0
            newtime[key] = [[[] for j in [1, 2, 3]] for i in [0, 1]]
            for row in [0, 1]:
                for col in [0, 1, 2]:
                    for xv in data[key][row][col]:
                        dumt = list(np.arange(len(xv)) + start)
                        start = start + len(xv)
                        newtime[key][row][col].append(dumt)

        for row in [0, 1]:
            for col in [0, 1, 2]:
                fig, axes = pl.subplots(4, 2, figsize=(35, 30))
                plot_title = "Polarimeter %s, Amp %s " % (polarimeter, amps[row, col])
                fig.suptitle(plot_title)

                for row1 in [0, 1, 2, 3]:
                    for col1 in [0, 1]:
                        key = keys1[row1][col1]
                        for (x, y, t) in zip(
                            newtime[key][row][col], data[key][row][col], tags
                        ):
                            axes[row1, col1].plot(x, y, label=t)
                            axes[row1, col1].set_title(key)

                            # axes[row,col].legend(loc = 2, bbox_to_anchor = (0, 1.15))
                            axes[row1, col1].set(xlabel="time [sec]", ylabel="Vg [mV]")
                            axes[row1, col1].legend()
                            # ax2.legend(loc = 1, bbox_to_anchor = (1, 1.15))
                            # ax2.set(ylabel = 'Id [muA]')
                            # ax2.set(ylim=(0,12000))

                    # Labels
                #                axes[row,col].set(xlabel = 'time [s]', ylabel = label)

                filename = "%ssciplot_%s_%s.%s" % (
                    self.output_folder,
                    polarimeter,
                    amps[row, col],
                    image,
                )
                pl.savefig(filename)
                pl.close()

    #########################################
    # Get the configuration of the instrument
    #########################################
    def get_configuration(self, polarimeters):
        import striptease
        import numpy as np

        """
        This function retrieves the configuration of a given set of polarimeters at the various
        verification points indicated by the tags
        The configuration is given by: start_time, end_time and the average value of
        ID_SET, VD_set, Vd_hk, Vg_hk, Id_hk in each time window

        Inputs
        polarimeters - Array of STRING - polarimeters to be checked

        Output
        out - DICT - Dictionary containing 'ID_SET', 'VD_SET', 'VD_HK', 'VG_HK', 'ID_HK'

        """
        hklist = ["ID_SET", "VD_SET", "VD_HK", "VG_HK", "ID_HK"]
        out = {}
        for curtag in self.verification_tags:
            out[curtag] = {}
            for pol in polarimeters:
                tstart, tend = self.get_times(pol, curtag)
                print(pol, curtag, tstart, tend)
                out[curtag][pol] = {}
                out[curtag][pol]["TIME_START"] = tstart
                out[curtag][pol]["TIME_END"] = tend
                for hk in hklist:
                    for index in np.arange(6):
                        cur_hk = "%s%s_%s" % (hk[0:2], str(index), hk[3:])
                        group, subgroup = striptease.hdf5files.get_group_subgroup(
                            cur_hk
                        )
                        subgroup = "%s_%s" % (subgroup, pol)
                        t, values = self.get_hk(group, subgroup, cur_hk, tstart, tend)
                        out[curtag][pol][cur_hk] = np.mean(values)

        self.configuration = out

        return out

    #####################################################
    # Save configuration into pickle and text file
    #####################################################
    def save_configuration(self, d, filename, save="both"):
        import csv

        """
        Saves the configuration present in the dictionary d into a pickle and a text
        file. The string "filename" must not have an extension
        """
        import pickle

        if save == "both" or save == "pickle":
            # This dumps the whole configuration into a pickle binary file
            file_id = open(self.output_folder + filename + ".pickle", "wb")
            pickle.dump(d, file_id)
            file_id.close()

        if save == "both" or save == "csv":
            # This generates a csv file to be opened with a spreadsheet
            with open(self.output_folder + filename + ".csv", mode="w") as file_id:
                writer = csv.writer(
                    file_id, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
                )

                header_top = [
                    "CHANNEL/STEP",
                    "ID_HA3",
                    "ID_HA2",
                    "ID_HA1",
                    "ID_HB3",
                    "ID_HB2",
                    "ID_HB1",
                    "VG_HA3",
                    "VG_HA2",
                    "VG_HA1",
                    "VG_HB3",
                    "VG_HB2",
                    "VG_HB1",
                    "VG4A_HK",
                    "VG5A_HK",
                ]

                writer.writerow(header_top)

                for pol in self.get_tested_polarimeters():
                    writer.writerow([pol])
                    # Save verification 1
                    try:
                        data = self.configuration["PINCHOFF_VERIFICATION_1"][pol]
                    except (TypeError, KeyError, IndexError):
                        print(
                            "Problem in configuration file. Either not present or wrong tag"
                        )

                    head = ["PINCHOFF_VERIFICATION_1"]
                    currents = self.get_currents(pol, "HA1")
                    id_list = [
                        data["ID%s_HK" % self.amp_tag_translation[h]]
                        for h in ["HA3", "HA2", "HA1", "HB3", "HB2", "HB1"]
                    ]
                    vg_list = [
                        data["VG%s_HK" % self.amp_tag_translation[h]]
                        for h in ["HA3", "HA2", "HA1", "HB3", "HB2", "HB1"]
                    ]
                    writer.writerow(head + id_list + vg_list)

                    # Save configuration during pinchoff test
                    currents = self.get_currents(pol, "HA1")
                    steps = ["Pinchoff_%s_uA" % cur for cur in currents]
                    for step, cur in zip(steps, currents):
                        #                        idvals = []
                        #                        vgvals = []
                        idvals = [
                            self.configuration[
                                "PINCHOFF_IDSET_%s_%s_%smuA" % (pol, amp, cur)
                            ][pol]["ID%s_HK" % self.amp_tag_translation[amp]]
                            for amp in ["HA3", "HA2", "HA1", "HB3", "HB2", "HB1"]
                        ]
                        vgvals = [
                            self.configuration[
                                "PINCHOFF_IDSET_%s_%s_%smuA" % (pol, amp, cur)
                            ][pol]["VG%s_HK" % self.amp_tag_translation[amp]]
                            for amp in ["HA3", "HA2", "HA1", "HB3", "HB2", "HB1"]
                        ]
                        #                        for amp in ['HA3','HA2','HA1','HB3','HB2','HB1']:
                        #                            tag = 'PINCHOFF_IDSET_%s_%s_%smuA' % (pol, amp, cur)
                        #                            idvals.append(self.configuration[tag][pol]['ID%s_HK' % self.amp_tag_translation[amp]])
                        #                            vgvals.append(self.configuration[tag][pol]['VG%s_HK' % self.amp_tag_translation[amp]])
                        writer.writerow([step] + idvals + vgvals)

                    writer.writerow([""])

    # Get list of tested polarimeters
    #################################
    def get_tested_polarimeters(self, search_tag="PINCHOFF_IDSET", tags=None):
        import numpy as np

        """
        Retrieves the list of the polarimeters tested in the data file
        """
        filtered = self.get_subtags(search_tag)
        pols = [o[15:17] for o in filtered]  # Extract the polarimeter string
        return np.array(list(dict.fromkeys(pols)))  # Remove duplicates

    ###################################
    # Get list of tags matching pattern
    ###################################
    def get_subtags(self, search_tag, tags=None):
        """
        Retrieves a list of tags matchina search_tag
        """
        if tags is None:
            tags = self.tags

        names = [t.name for t in tags]
        substr = [search_tag]
        return [
            str for str in names if any(sub in str for sub in substr)
        ]  # Filter tags according to the search_tag

    ##############################################
    # Get list of currents for a given pol and amp
    ##############################################
    def get_currents(self, pol, amp):
        import numpy as np

        """
        Retrieves the list of tested currents for a given pol and amp
        """
        pols = self.get_tested_polarimeters()
        if pol not in pols:
            print("Polarimeter %s does not exist in data" % pol)
            return None

        if amp not in self.amps:
            print("Amplifier %s does not exist" % amp)
            return None

        tag = "PINCHOFF_IDSET_%s_%s_" % (pol, amp)
        subtags = self.get_subtags(tag)
        return np.array([a[22:][:-3] for a in subtags])
