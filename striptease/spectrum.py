# coding=utf-8
# Change track
""" 
2025-03-26: added degrees of freedom in noise fitting routine. Now with the linear fitting
            routine one can choose how many points to choose for start and nfirst. There is also the 
            degree of freedom to choose a max frequency rather than the number of points to fit for
            the 1/f part. The values of start = 5 and nfirst = 15 are maintained by default
"""


class Spectrum:
    def __init__(self):
        """
        *KEYWORDS*

        +-------------------+------------+-----------------------------------------+---------------+
        | Name              | Type       | Description                             | Default value |
        +===================+============+=========================================+===============+
        | ``lowfreq``   `   | Double     | Minimum frequency to be considered in   | 1e-3          |
        |                   | precision  | Welch windowing and segmenting. It is   |               |
        |                   |            | used only if the key welch = True       |               |
        +-------------------+------------+-----------------------------------------+---------------+
        | ``welch``     `   | Boolean    | Whether to use welch windowing and      | False         |
        |                   |            | segmenting (True) or not (False)        |               |
        +-------------------+------------+-----------------------------------------+---------------+
        | ``fast``      `   | Boolean    | Whether to use fast FFT computation (Tr | False         |
        |                   |            | ue) or not (False). If ``fast = True``  |               |
        |                   |            | only a number of elements equal to a    |               |
        |                   |            | power of two is taken in the data.      |               |
        +-------------------+------------+-----------------------------------------+---------------+
        | ``remove_drift``  | Boolean    | Whether to use remove a linear drift    | False         |
        |                   |            | from the data (True) or not (False)     |               |
        +-------------------+------------+-----------------------------------------+---------------+
        | ``spectrum_type`` | String     | The type of spectrum requested by the   | "ASD"         |
        |                   |            | user. It can be 'ASD', 'PSD', 'AS', 'PS'|               |
        +-------------------+------------+-----------------------------------------+---------------+
        | ``return_phase``  | Boolean    | Whether to return the phase values of   | False         |
        |                   |            | the spectrum (True) or not (False)      |               |
        +-------------------+------------+-----------------------------------------+---------------+
        """

        self.lowfreq = [
            1.0e-3,
            "%slowfreq = %s%s: Minimum frequency to be considered in Welch "
            "windowing and segmenting. It is  used only if "
            "the key welch = True\n",
        ]
        self.welch = [
            False,
            "%swelch = %s%s: Whether to use welch windowing and "
            "segmenting (True) or not (False)\n",
        ]
        self.fast = [
            False,
            "%sfast = %s%s: Whether to use fast FFT computation (True) "
            "or not (False). If ``fast = True`` "
            "only a number of elements equal to a "
            "power of two is taken in the data.\n",
        ]
        self.return_phase = [
            False,
            "%sreturn_phase = %s%s: Whether to return the phase values of "
            "the spectrum (True) or not (False)\n",
        ]
        self.remove_drift = [
            False,
            "%sremove_drift = %s%s: Whether to use remove a linear drift "
            "from the data (True) or not (False)\n",
        ]
        self.spectrum_type = [
            "ASD",
            "%sspectrum_type = %s%s: The type of spectrum requested by the "
            "user. It can be ``ASD``, ``PSD``, ``AS``, ``PS``\n",
        ]
        self.noise_fit = [
            False,
            "%snoise_fit = %s%s: Whether to use a three parameters fit or just fit linearly "
            "1/f noise in log space\n",
        ]

    # METHODS

    def parameters(self):
        """Prints the attributes of the class, corresponding to the values of
        the spectrum calculation parameters"""

        items = list(self.__dict__.items())
        CRED = "\033[91m"
        CEND = "\033[0m"

        for item in items:
            print(item[1][1] % (CRED, item[1][0], CEND))

    def fft_calculate(self, array2, sampfreq):

        """Low-level function for amplitude or power spectrum calculation.

        Determine the amplitude or power spectrum of the data stream in *array2*.
        The parameter *sampfreq* specifies the sampling frequency of *array2*.

        fft_parameters DICT parameters for fft calculation. Default values defined in __init__
        function

        .. note::

        The implementation is based on the functions ``nps.pro``, ``psq.pro``
        and ``lresid.pro`` initially developed by M. Seiffert.

        In this version the following options have been added:

        * Possibility to choose whether to add a welch windowing function or not.
        * Possibility to choose whether to display the amplitude or the power
        spectrum.
        * Possibility to choose whether to calculate the absolute
        spectrum or the spectral density (i.e. amp/rt Hz or pw/rtHz).

        Original version by Michael Seiffert, implemented in LIFE by A. Mennella
        and ported to Python by A. Mennella."""

        import numpy as np

        arr = np.array(array2)
        nel = len(arr)

        if self.welch[0]:
            # The output is in V/rtHz
            if self.return_phase[0]:
                raise ValueError(
                    "keyword RETURN_PHASE = True is incompatible with WELCH = True. RETURN_PHASE is set to FALSE"
                )
                self.return_phase[0] = False

            z = self.nps(array2, sampfreq)
            phases = np.zeros(2 * len(z[:, 0]))
            norm = 1.0

        else:
            if self.fast[0]:
                nel = int(2.0 ** (np.floor(np.log(nel) / np.log(2.0))))
                arr = np.array(array2[0:nel])

            # 1.2 is a normalisation factor to make the fft level similar
            # to what is  obtained with welch windowing

            #   Fix by T. Poutanen / 5 Feb, 2009 - start
            if self.spectrum_type[0] in ["AS", "ASD"]:
                #                norm = np.sqrt (2. * nel / sampfreq)*1.2* 0.943142  # AS/ASD normalization
                norm = np.sqrt(nel / sampfreq) * 1.2 * 0.943142  # AS/ASD normalization
            if self.spectrum_type[0] in ["PS", "PSD"]:
                #                norm = np.sqrt (2. * nel / sampfreq)                # PS/PSD normalization
                norm = np.sqrt(nel / sampfreq)  # PS/PSD normalization
            #   Fix - end

            z = np.zeros((int(nel / 2 + 1), 2))
            dummy = np.arange(nel, dtype="float") / nel * sampfreq
            z[:, 0] = dummy[0 : int(nel / 2 + 1)]

            if self.remove_drift[0]:
                # raise Exception("lresid was not properly imported")
                arr = self.lresid(arr)

            ft = np.fft.fft(arr)

            dummy = (
                norm * np.abs(ft) / nel
            )  # division by nel to be consistent with IDL definition
            z[:, 1] = dummy[0 : int(nel / 2 + 1)]  # z[*,1] is now in V/rtHz

            if self.return_phase[0]:
                phases = map(phases, ft)
            else:
                phases = np.zeros(len(ft))

        #   Fix by T. Poutanen / 5 Feb, 2009 - start
        if self.spectrum_type[0] in ["PS", "PSD"]:
            z[:, 1] = z[:, 1] ** 2  # the output is in V^2/Hz

        if self.spectrum_type[0] == "PS":
            z[:, 1] = z[:, 1] * sampfreq  # the output is in V^2

        if self.spectrum_type[0] == "AS":
            z[:, 1] = z[:, 1] * np.sqrt(sampfreq)  # the output is in V
        # Fix - end

        result = {
            "frequencies": z[:, 0],
            "amplitudes": z[:, 1],
            "norm": norm,
            "phases": phases,
            "welch": self.welch[0],
        }

        return result

    ######################################################################

    def nps(self, array2, sampfreq):

        import numpy as np
        from scipy.signal import welch

        if self.remove_drift[0] == 1:
            # raise Exception("lresid was not properly imported")
            array2 = self.lresid(array2)

        nlow = np.double((sampfreq / self.lowfreq[0]))

        # the thing that we have to do the fft on is nlow elements.
        # lets adjust lowest freq so that this is always a power of 2 if this
        # is requested by the user

        if self.fast[0]:
            nlow = 2.0 ** (np.floor(np.log(nlow) / np.log(2.0)))

        if not (nlow % 2 == 0):
            nlow = nlow + 1

        nlow = int(nlow)
        j = np.arange(nlow)
        welch_window = (
            1 - ((j - (nlow / 2.0)) / (nlow / 2.0)) ** 2
        )  # welch windowing fnc

        # the following is the old implementation based on M. Seiffert code
        # ---- Starts here
        # timeseg      = array1[0:nlow]
        # timeseg      = timeseg * welch_window

        # z = (self.psq(timeseg, sampfreq))**2 # same as ps.pro but doesn't display

        # for i in np.arange(nlow, (nnn-nlow)+1, (nlow/2.)):
        #     timeseg = array1[int(i):(int(i) + nlow)]
        #     timeseg = timeseg * welch_window
        #     z = z + (self.psq(timeseg, sampfreq))**2
        #     count = count + 1

        # newfr = np.array(list(map(np.sqrt,z[:,0]/count)))
        # newamp = np.array(list(map(np.sqrt,z[:,1]/count)))
        # z[:,1] = newamp * 1.374/np.sqrt(2)   # renormalization is necessary after the
        #                       # segmenting and windowing.
        # z[:,0] = newfr
        # ----- Ends here

        sp = welch(array2, sampfreq, window=welch_window)
        norm = 1.0 / 2.0

        z = np.zeros((len(sp[0]) - 4, 2))
        z[:, 1] = np.sqrt(sp[1][2:-2] * norm)
        # segmenting and windowing.
        z[:, 0] = sp[0][2:-2]

        return z

    ######################################################################

    def psq(self, array1, sampfreq):

        """Unused - function used by the old implementation of nps function"""

        import numpy as np

        n = len(array1)
        t = 1.0 / float(sampfreq)

        n21 = int(n / 2 + 1.0)
        f = np.arange(n, dtype="float")

        f[n21:n] = n21 - n + np.arange(n21 - 2)
        f = f / (n * t)
        if f[n - 1] > 0.0:
            f[n - 1] = f[n - 2] + (f[1] - f[0])

        spec = (np.abs(np.fft.fft(array1)) / n) ** 2

        z = np.zeros((n, 2))
        z[:, 1] = self.cshift(spec, -n21)
        z[:, 0] = self.cshift(f, -n21)

        norm = n * (1.0 / (sampfreq / 2.0))  # this is the power normalization

        z[:, 1] = z[:, 1] * norm

        # the 1/n is needed by IDL, the sampfreq/2 is the resolution bandwidth

        amp = np.sqrt(z[:, 1])

        freq = z[:, 0]

        amp = amp[np.where(freq > 0.0)[0]]
        freq = freq[np.where(freq > 0.0)[0]]

        z = np.zeros((len(freq), 2))
        z[:, 0] = freq
        z[:, 1] = amp

        return z

    ######################################

    def cshift(self, arr, offset):
        import numpy as np

        offset %= len(arr)
        return np.concatenate((arr[-offset:], arr[:-offset]))

    #######################################
    # Wrapper functions
    #######################################

    def spectrum(self, toi, sampfreq):

        """
        **Function to calculate the Fourier spectrum of a datastream**

        This function calculates the spectrum of a timestream. It can calculate
        four different types of spectra:

        * Amplitude spectrum (AS)
        * Power spectrum (PS)
        * Amplitude spectral density (ASD)
        * Power spectral density (PSD)

        *CALL*

        ``result = spectrum(self, toi, sampfreq)

        *INPUTS*

        +-------------------------+------------------+-----------------------------------+
        | Name                    | Type             | Description                       |
        +=========================+==================+===================================+
        | ``toi``                 | Double precision | Array containing the timestream   |
        |                         | array            |                                   |
        +-------------------------+------------------+-----------------------------------+
        | ``sampfreq``            | Double precision | Sampling frequency in Hz          |
        +-------------------------+------------------+-----------------------------------+


        *OUTPUT*

        +-------------------------+------------------+-----------------------------------+
        | Name                    | Type             | Description                       |
        +=========================+==================+===================================+
        | ``result``              | Dictionary       | Dictionary containing the spectrum|
        |                         |                  | data. The dictionary has the      |
        |                         |                  | following elements:               |
        +-------------------------+------------------+-----------------------------------+
        | ``result.frequencies``  | Double precision | Array of frequencies in Hz        |
        |                         | array            |                                   |
        +-------------------------+------------------+-----------------------------------+
        | ``result.amplitudes``   | Double precision | Array of amplitudes               |
        |                         | array            |                                   |
        +-------------------------+------------------+-----------------------------------+
        | ``result.phases``       | Double precision | Array of phases. If               |
        |                         | array            | ``return_phase = 0`` then an      |
        |                         |                  | array of zeros is returned        |
        +-------------------------+------------------+-----------------------------------+
        | ``result.norm``         | Double precision | Used normalisation constant       |
        +-------------------------+------------------+-----------------------------------+
        | ``result.welch``        | Boolean          | Wether windowing is used          |
        +-------------------------+------------------+-----------------------------------+
        """

        if self.welch[0] and self.return_phase[0]:
            raise ValueError(
                "keyword /RETURN_PHASE is incompatible with /WELCH. RETURN_PHASE is set to zero"
            )
            self.return_phase[0] = 0

        st = self.spectrum_type[0].upper()

        if st == "ASD":
            sp = self.amplitude_spectral_density(toi, sampfreq)

        elif st == "PSD":
            sp = self.power_spectral_density(toi, sampfreq)

        elif st == "AS":
            sp = self.amplitude_spectrum(toi, sampfreq)

        elif st == "PS":
            sp = self.power_spectrum(toi, sampfreq)

        return sp

    ##################################

    # Wrapper to fft_calculate for amplitude spectrum (spectrum_type == 'PS')
    def power_spectrum(self, toi, sampfreq):

        if self.welch[0] and self.return_phase[0]:
            raise ValueError(
                "keyword /RETURN_PHASE is incompatible with /WELCH. RETURN_PHASE is set to zero"
            )
            self.return_phase[0] = 0

        powerspectrum = self.fft_calculate(toi, sampfreq)

        return powerspectrum

    # Wrapper to fft_calculate for amplitude spectrum (spectrum_type == 'AS')
    def amplitude_spectrum(self, toi, sampfreq):

        if self.welch[0] and self.return_phase[0]:
            raise ValueError(
                "keyword /RETURN_PHASE is incompatible with /WELCH. RETURN_PHASE is set to zero"
            )
            self.return_phase[0] = 0

        amplitude_spectrum = self.fft_calculate(toi, sampfreq)

        return amplitude_spectrum

    # Wrapper to fft_calculate for amplitude spectrum (spectrum_type == 'PSD')
    def power_spectral_density(self, toi, sampfreq):

        if self.welch[0] and self.return_phase[0]:
            raise ValueError(
                "keyword /RETURN_PHASE is incompatible with /WELCH. RETURN_PHASE is set to zero"
            )
            self.return_phase[0] = 0

        power_spectral_density = self.fft_calculate(toi, sampfreq)

        return power_spectral_density

    # Wrapper to fft_calculate for amplitude spectrum (spectrum_type == 'ASD')
    def amplitude_spectral_density(self, toi, sampfreq):

        if self.welch[0] and self.return_phase[0]:
            raise ValueError(
                "keyword /RETURN_PHASE is incompatible with /WELCH. RETURN_PHASE is set to zero"
            )
            self.return_phase[0] = 0

        amplitude_spectral_density = self.fft_calculate(toi, sampfreq)

        return amplitude_spectral_density

    #############

    def white_noise_level(self, spectrum):

        """
        **Function to calculate white noise level from a spectrum**

        This function calculates the white noise level from an input spectrum. The
        white noise level is calculated by averaging the right-most portion of the
        amplitude values in the spectrum.

        *CALL*

        ``result = white_noise_level(spectrum)``

        *INPUTS*

        +-------------------------+------------------+-----------------------------------+
        | Name                    | Type             | Description                       |
        +=========================+==================+===================================+
        | ``spectrum``            | Dictionary       | Dictionary containing frequencies |
        |                         |                  | and amplitudes. The dictionary    |
        |                         |                  | must be as follows (other entries |
        |                         |                  | are simply neglected)             |
        +-------------------------+------------------+-----------------------------------+
        | ``spectrum.frequencies``| Double precision | Array of frequencies in Hz        |
        |                         | array            |                                   |
        +-------------------------+------------------+-----------------------------------+
        | ``spectrum.amplitudes`` | Double precision | Array of amplitudes               |
        |                         | array            |                                   |
        +-------------------------+------------------+-----------------------------------+

        *OUTPUT*

        +-------------------------+------------------+-----------------------------------+
        | Name                    | Type             | Description                       |
        +=========================+==================+===================================+
        | ``result``              | Double precision | White noise value in the same     |
        |                         |                  | units of the input spectrum       |
        +-------------------------+------------------+-----------------------------------+
        """

        import numpy as np

        sp = np.zeros((len(spectrum["frequencies"]), 2))
        sp[:, 0] = spectrum["frequencies"]
        sp[:, 1] = spectrum["amplitudes"]

        whitenoiselevel = self.wn_level(sp[:, 0], sp[:, 1])

        return whitenoiselevel

    ##################

    def wn_level(self, freqs, power_spectrum):

        import numpy as np

        freqs = np.array(freqs)
        power_spectrum = np.array(power_spectrum)
        nel = len(freqs)

        # Here I calculate the number of elements in the white noise part
        # of the power spectrum by means of the function
        # fft_wn_freqs. The variable wn_freqs contains the number of
        # elements
        wn_freq = self.wn_freqs(freqs)

        # If the wn_freqs is equal to -1 then exit
        if wn_freq == -1.0:
            wn_level = -1.0
            return wn_level

        # Calculate white noise level
        wn_level = np.mean(power_spectrum[nel - wn_freq : nel])

        return wn_level

    def wn_freqs(self, freqs):

        import numpy as np

        freqs = np.array(freqs)
        nel = -1
        perc = 1.0
        nfreq = len(freqs)
        fsamp = freqs[nfreq - 1]
        fmin = fsamp
        while (fmin > 0) and (nel < 10):
            # Decrease perc by 0.1 and calculate the fmin
            perc = perc - 0.1
            fmin = perc * fsamp

            # Select the indices where the frequencies are greater than
            # fmin
            wn_index = np.where(freqs > fmin)
            wn_index = wn_index[0]

            # If a selection cannot be made then return -1.
            if wn_index[0] == -1:
                return wn_index[0]

            # Update nel
            nel = len(wn_index)

        return len(wn_index)

    def lresid(self, data):
        """Remove any linear trend from DATA.

        Assuming that DATA is a 1D NumPy array, it returns an array of the same
        size with any linear trend removed."""

        import numpy as np

        x = np.arange(data.size)
        fit = np.polyfit(x, data, 1)
        return data - fit[1] - fit[0] * x

    #######################################

    def get_noise_parameters(self, spectrum):

        """
        Function to calculate the noise parameters from a spectrum. It assumes that
        the input spectrum is a power spectrum, but the function can work with any kind
        of spectrum

        *CALL*

        ``result = .noise_parameters(spectrum, guess)``

        *INPUTS*

        +-------------------------+------------------+-----------------------------------+
        | Name                    | Type             | Description                       |
        +=========================+==================+===================================+
        | ``spectrum``            | Dictionary       | Dictionary containing frequencies |
        |                         |                  | and amplitudes. The dictionary    |
        |                         |                  | must be as follows (other entries |
        |                         |                  | are simply neglected)             |
        +-------------------------+------------------+-----------------------------------+
        | ``spectrum.frequencies``| Double precision | Array of frequencies in Hz        |
        |                         | array            |                                   |
        +-------------------------+------------------+-----------------------------------+
        | ``spectrum.amplitudes`` | Double precision | Array of amplitudes               |
        |                         | array            |                                   |
        +-------------------------+------------------+-----------------------------------+


        *OUTPUT*

        +-------------------------+------------------+-----------------------------------+
        | Name                    | Type             | Description                       |
        +=========================+==================+===================================+
        | ``result``              | Double precision | White noise value in the same     |
        |                         |                  | units of the input spectrum       |
        +-------------------------+------------------+-----------------------------------+
        """

        result = -1
        return result

    class FitNoise:
        """
        Class that fits a noise spectrum to extract the noise parameters. There are two methods:

        linear_fit - fits the 1/f part with a straight line in log-log space and finds the slope
        and frequency where the 1/f part equals white noise

        full_fit - fits the whole spectrum with a 3 parameters model
        """

        def __init__(self):

            self.guess = [1.0e-1, -1.0]
            self.spect = Spectrum()
            self.fkguess = 1.0e-1
            self.slopeguess = -1.0

        def fit(self, spectrum, start=5, nfirst=15, fmax=-1):
            """
            This function is a wrapper to linear_fit or full_fit. The choice is done by checking spectrum['welch'].
            If windowing is used (welch = True) then the full_fit is called, otherwise the linear_fit is used
            *CALL*

            ``result = .fit(spectrum)``

            *INPUTS*

            +-------------------------+------------------+-----------------------------------+
            | Name                    | Type             | Description                       |
            +=========================+==================+===================================+
            |   spectrum              | Dictionary       | Dictionary containing frequencies |
            |                         |                  | and amplitudes. The dictionary    |
            |                         |                  | must be as follows (other entries |
            |                         |                  | are simply neglected)             |
            +-------------------------+------------------+-----------------------------------+
            |  spectrum['frequencies']| Double precision | Array of frequencies in Hz        |
            |                         | array            |                                   |
            +-------------------------+------------------+-----------------------------------+
            |  spectrum['amplitudes'] | Double precision | Array of amplitudes               |
            |                         | array            |                                   |
            +-------------------------+------------------+-----------------------------------+
            | spectrum['welch']       | Boolean          | Whether windowing was used        |
            |                         |                  | If welch==True then the full fit  |
            |                         |                  | is performed by default           |
            +-------------------------+------------------+-----------------------------------+
            | start                   | Int              | How many points to discard in the |
            |                         |                  | 1/f noise part of the spectrum    |
            |                         |                  | (Default is start = 5)            |
            +-------------------------+------------------+-----------------------------------+
            | nfirst                  | Int              | How many points to select in the  |
            |                         |                  | 1/f noise part of the spectrum    |
            |                         |                  | (Default is nfirst = 15)          |
            +-------------------------+------------------+-----------------------------------+
            | fmax                    | Double precision | This is in alternative to nfirst  |
            |                         |                  | it is the maximum frequency to    |
            |                         |                  | consider to select the 1/f noise  |
            |                         |                  | part of the spectrum. If fmax is  |
            |                         |                  | positive then nfirst is ignored,  |
            |                         |                  | if fmax is negative then nfirst   |
            |                         |                  | is used                           |
            +-------------------------+------------------+-----------------------------------+


            *OUTPUT*

            +-------------------------+------------------+-----------------------------------+
            | Name                    | Type             | Description                       |
            +=========================+==================+===================================+
            | ``result``              | Double precision | Array of fit parameters           |
            |                         | array            | [sigma, f_knee, slope]            |
            +-------------------------+------------------+-----------------------------------+
            """
            if spectrum["welch"]:
                return self.full_fit(spectrum, start, nfirst, fmax)
            else:
                return self.linear_fit(spectrum, start, nfirst, fmax)

        def linear_fit(self, spectrum, start, nfirst, fmax):

            """
            This function calculates noise properties using a linear fit in log-log space

            *CALL*

            ``result = .linear_fit(spectrum)``

            *INPUTS*

            +-------------------------+------------------+-----------------------------------+
            | Name                    | Type             | Description                       |
            +=========================+==================+===================================+
            |   spectrum              | Dictionary       | Dictionary containing frequencies |
            |                         |                  | and amplitudes. The dictionary    |
            |                         |                  | must be as follows (other entries |
            |                         |                  | are simply neglected)             |
            +-------------------------+------------------+-----------------------------------+
            |  spectrum['frequencies']| Double precision | Array of frequencies in Hz        |
            |                         | array            |                                   |
            +-------------------------+------------------+-----------------------------------+
            |  spectrum['amplitudes'] | Double precision | Array of amplitudes               |
            |                         | array            |                                   |
            +-------------------------+------------------+-----------------------------------+
            | spectrum['welch']       | Boolean          | Whether windowing was used        |
            +-------------------------+------------------+-----------------------------------+
            | start                   | Int              | How many points to discard in the |
            |                         |                  | 1/f noise part of the spectrum    |
            |                         |                  | (Default is start = 5)            |
            +-------------------------+------------------+-----------------------------------+
            | nfirst                  | Int              | How many points to select in the  |
            |                         |                  | 1/f noise part of the spectrum    |
            |                         |                  | (Default is nfirst = 15)          |
            +-------------------------+------------------+-----------------------------------+
            | fmax                    | Double precision | This is in alternative to nfirst  |
            |                         |                  | it is the maximum frequency to    |
            |                         |                  | consider to select the 1/f noise  |
            |                         |                  | part of the spectrum. If fmax is  |
            |                         |                  | positive then nfirst is ignored,  |
            |                         |                  | if fmax is negative then nfirst   |
            |                         |                  | is used                           |
            +-------------------------+------------------+-----------------------------------+


            *OUTPUT*

            +-------------------------+------------------+-----------------------------------+
            | Name                    | Type             | Description                       |
            +=========================+==================+===================================+
            | ``result``              | Double precision | Array of fit parameters           |
            |                         | array            | [sigma, f_knee, slope]            |
            +-------------------------+------------------+-----------------------------------+
            """

            import numpy as np
            import bisect

            freqs = spectrum["frequencies"]
            power = spectrum["amplitudes"]

            # select the 1/f part of the spectrum
            if spectrum["welch"]:
                start = 0

            if fmax > 0:  # count how many frequencies are less than fmax
                nfirst = bisect.bisect_left(freqs, fmax)

            freq1f = freqs[start:nfirst]
            power1f = power[start:nfirst]
            freq1flog = np.log10(freq1f)
            power1flog = np.log10(power1f)
            linearfit = np.polyfit(freq1flog, power1flog, 1)
            slope = linearfit[0]
            intercept = linearfit[1]

            wnl = self.spect.white_noise_level(spectrum)
            avwhite = 2.0 * wnl
            avwhitelog = np.log10(avwhite)
            fklog = (avwhitelog - intercept) / slope
            fk = 10**fklog

            result = [wnl, fk, slope, intercept]

            return result

        ##

        def full_fit(self, spectrum):

            """
            This function calculates noise properties using a three parameters fit of the input
            spectrum against a function σ(1+ (fk/f)^(-slope)). This function is used only
            if windowing was used in the spectrum computation. In case welch = 0 the linear_fit
            is called instead

            *CALL*

            ``result = .full_fit(spectrum)``

            *INPUTS*

            +-------------------------+------------------+-----------------------------------+
            | Name                    | Type             | Description                       |
            +=========================+==================+===================================+
            |   spectrum              | Dictionary       | Dictionary containing frequencies |
            |                         |                  | and amplitudes. The dictionary    |
            |                         |                  | must be as follows (other entries |
            |                         |                  | are simply neglected)             |
            +-------------------------+------------------+-----------------------------------+
            |  spectrum['frequencies']| Double precision | Array of frequencies in Hz        |
            |                         | array            |                                   |
            +-------------------------+------------------+-----------------------------------+
            |  spectrum['amplitudes'] | Double precision | Array of amplitudes               |
            |                         | array            |                                   |
            +-------------------------+------------------+-----------------------------------+
            | spectrum['welch']       | Boolean          | Whether windowing was used        |
            +-------------------------+------------------+-----------------------------------+


            *OUTPUT*

            +-------------------------+------------------+-----------------------------------+
            | Name                    | Type             | Description                       |
            +=========================+==================+===================================+
            | ``result``              | Double precision | Array of fit parameters           |
            |                         | array            | [sigma, f_knee, slope]            |
            +-------------------------+------------------+-----------------------------------+
            """

            from scipy.optimize import curve_fit

            # Check if windowing was used. Otherwise fall back on linear_fit
            if not spectrum["welch"]:
                return self.linear_fit(spectrum)

            wn_guess = self.spect.white_noise_level(spectrum)
            guess = [wn_guess, self.fkguess, self.slopeguess]

            freqs = spectrum["frequencies"]
            power = spectrum["amplitudes"]

            resfit = curve_fit(
                lambda x, sig, fk, sl: sig * (1.0 + (fk / x) ** (-sl)),
                freqs,
                power,
                p0=guess,
            )

            return resfit[0]
