# coding=utf-8


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
            "the key welch = True\n"
        ]
        self.welch = [
            False,
            "%swelch = %s%s: Whether to use welch windowing and "
            "segmenting (True) or not (False)\n"
        ]
        self.fast = [
            False,
            "%sfast = %s%s: Whether to use fast FFT computation (True) "
            "or not (False). If ``fast = True`` "
            "only a number of elements equal to a "
            "power of two is taken in the data.\n"
        ]
        self.return_phase = [
            False,
            "%sreturn_phase = %s%s: Whether to return the phase values of "
            "the spectrum (True) or not (False)\n"
        ]
        self.remove_drift = [
            False,
            "%sremove_drift = %s%s: Whether to use remove a linear drift "
            "from the data (True) or not (False)\n"
        ]
        self.spectrum_type = [
            "ASD",
            "%sspectrum_type = %s%s: The type of spectrum requested by the "
            "user. It can be ``ASD``, ``PSD``, ``AS``, ``PS``\n"
        ]

    # METHODS

    def parameters(self):
        """ Prints the attributes of the class, corresponding to the values of
        the spectrum calculation parameters """

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
        import cmath as cm
        import math as m
        import string as strg
        import logging as log
        import scipy as sc

        arr = np.array(array2)
        nel = len(arr)

        if self.welch[0]:
            # The output is in V/rtHz
            if self.return_phase[0]:
                raise ValueError(
                    f"keyword RETURN_PHASE = True is incompatible with WELCH = True. RETURN_PHASE is set to FALSE"
                )
                self.return_phase[0] = False

            z = self.nps(array2, sampfreq)
            phases = np.zeros(2 * len(z[:, 0]))
            norm = 1.0

        else:
            if self.fast[0]:
                nel = long(2.0 ** (np.floor(np.log(nel) / np.log(2.0))))
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
                arr = self.lresid(arr)

            ft = np.fft.fft(arr)

            dummy = (
                norm * np.abs(ft) / nel
            )  # division by nel to be consistent with IDL definition
            z[:, 1] = dummy[0 : int(nel / 2 + 1)]  # z[*,1] is now in V/rtHz

            if self.return_phase[0]:
                phases = map(phase, ft)
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
        }

        return result

    ######################################################################

    def nps(self, array2, sampfreq):

        import numpy as np
        import pdb
        from scipy.signal import welch

        array1 = np.array(array2)
        if self.remove_drift[0] == 1:
            array1 = lresid(array1)

        nnn = len(array1)

        nlow = np.double((sampfreq / self.lowfreq[0]))

        # the thing that we have to do the fft on is nlow elements.
        # lets adjust lowest freq so that this is always a power of 2 if this
        # is requested by the user

        if self.fast[0]:
            nlow = 2.0 ** (np.floor(np.log(nlow) / np.log(2.0)))

        if not (nlow % 2 == 0):
            nlow = nlow + 1

        lowestfreq = sampfreq / nlow
        # log.debug('using lowest freq of %f' % lowestfreq)
        nlow = int(nlow)
        retsamp = 1.0 / sampfreq
        tlow = 1.0 / lowestfreq
        i = 0
        count = 1
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

        """ Unused - function used by the old implementation of nps function """

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

        upper_x = 10.0 ** (int(np.log10(sampfreq / 2.0)))
        duration = n / sampfreq  # duration of data in seconds
        sfactor = 10.0  # smoothing
        lower_x = 10.0 ** (int(np.log10(1.0 / (duration))))

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

    def cshift(self, l, offset):
        import numpy as np

        offset %= len(l)
        return np.concatenate((l[-offset:], l[:-offset]))

    #######################################
    ## Wrapper functions
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
        """

        if self.welch[0] and self.return_phase[0]:
            raise ValueError(
                f"keyword /RETURN_PHASE is incompatible with /WELCH. RETURN_PHASE is set to zero"
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
                f"keyword /RETURN_PHASE is incompatible with /WELCH. RETURN_PHASE is set to zero"
            )
            self.return_phase[0] = 0

        powerspectrum = self.fft_calculate(toi, sampfreq)

        return powerspectrum

    # Wrapper to fft_calculate for amplitude spectrum (spectrum_type == 'AS')
    def amplitude_spectrum(self, toi, sampfreq):

        if self.welch[0] and self.return_phase[0]:
            raise ValueError(
                f"keyword /RETURN_PHASE is incompatible with /WELCH. RETURN_PHASE is set to zero"
            )
            self.return_phase[0] = 0

        amplitude_spectrum = self.fft_calculate(toi, sampfreq)

        return amplitude_spectrum

    # Wrapper to fft_calculate for amplitude spectrum (spectrum_type == 'PSD')
    def power_spectral_density(self, toi, sampfreq):

        if self.welch[0] and self.return_phase[0]:
            raise ValueError(
                f"keyword /RETURN_PHASE is incompatible with /WELCH. RETURN_PHASE is set to zero"
            )
            self.return_phase[0] = 0

        power_spectral_density = self.fft_calculate(toi, sampfreq)

        return power_spectral_density

    # Wrapper to fft_calculate for amplitude spectrum (spectrum_type == 'ASD')
    def amplitude_spectral_density(self, toi, sampfreq):

        if self.welch[0] and self.return_phase[0]:
            raise ValueError(
                f"keyword /RETURN_PHASE is incompatible with /WELCH. RETURN_PHASE is set to zero"
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
