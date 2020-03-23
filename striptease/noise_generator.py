# coding=utf-8


class NoiseGenerator:
    """ This class generates noise datastreams characterized by white_noise only or 
        white_noise + 1/f spectrum"""

    def __init__(self):

        import numpy as np

        self.fmin = [1.0e-30, "%sfmin = %s%s: Minimum frequency to be considered\n"]
        self.fmax = [1.0e30, "%sfmin = %s%s: Maximum frequency to be considered\n"]
        self.A = [
            1.5e-5,
            "%sA = %s%s: constant defining amplifier fluctuations. "
            "Typical value for 30 GHz is A = 1.5e-5(default), and "
            "for 70 GHz is A = 2.8e-5)\n",
        ]
        self.Ns = [4, "%sNs = %s%s: number of amplifier stages.\n"]
        self.corr = [
            True,
            "%scorr = %s%s: whether to consider correlated DG/G and DTn/Tn\n",
        ]
        self.add_offset = [
            True,
            "%sadd_offset = %s%s: whether to add the signal level to "
            "the generated noise\n",
        ]
        self.iseed_1overf = [
            np.random.uniform() * 1e6,
            "%siseed_1overf = %s%s: seed for 1/f noise generation\n",
        ]
        self.iseed_wn = [
            np.random.uniform() * 1e6,
            "%siseed_wn = %s%s: seed for white noise generation\n",
        ]
        self.wn_only = [
            False,
            "%swn_only = %s%s: whether to consider white noise only\n",
        ]
        self.total_power = [
            False,
            "%stotal_power = %s%s: whether to generate a total power or "
            "a differential noise stream\n",
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

    def set_default(self):
        self.__init__()

    def generate_noise(
        self, frequency, bandwidth, parameters, slope, samp_freq, time_length
    ):
        """
        This pogram generates a white noise + 1/f stream according to 
        the code of Maino and Burigana it is tailored to simulate a noise
        data stream from a total power receiver. So the parameters are not
        defined in terms of white noise and 1/f characteristics, but in terms
        of the amplifier characteristics
        ;
        CALL
        generate_total_power_noise(frequency, bandwidth, T_signal, T_noise, 
        slope, samp_freq, time_length)
        ;
        INPUTS
        frequency (channel frequency in GHz)
        bandwidth (bandwidth in GHz)
        parameters: 
            if self.mode == total_power  => parameters = [Tsignal, Tnoise]
            if self.mode == differential => parameters = [wn_level, fknee]
        T_noise (noise temperature)
        slope (slope of 1/f -1 < slope < 0)
        samp_freq (sampling frequency in Hz)
        time_length (in seconds)
        ;


        OUTPUTS
        noise_out (noise stream)
        """

        import numpy as np

        freq9 = np.double(frequency * 1.0e9)
        beta9 = np.double(bandwidth * 1.0e9)
        fmin = np.double(self.fmin[0])
        fmax = np.double(self.fmax[0])
        iseed_1overf = int(self.iseed_1overf[0])
        iseed_wn = int(self.iseed_wn[0])

        # Generate seeds
        seed_gain = iseed_1overf
        seed_wn = iseed_wn
        seed_Tn = seed_gain

        if self.corr[0]:
            seed_Tn = int(np.random.uniform() * 1.0e6)

        # Calculate the number of samples
        n_samples = time_length * samp_freq

        # Check if n_samples is even or odd
        check = np.double(n_samples) / 2.0 - n_samples / 2.0

        # If n_samples is odd then subtract 1 and recalculate time_length
        if check > 0.0:
            n_samples = n_samples - 1
        time_length = np.double(n_samples) / samp_freq
        n_samples = int(n_samples)

        if self.total_power[0]:
            T_signal = parameters[0]
            T_noise = parameters[1]
            T_signal_ant = self.tant(T_signal, freq9)
            wn_rms = (T_signal_ant + T_noise) / np.sqrt(beta9 / samp_freq)
            C = 2.0 * np.sqrt(np.double(self.Ns[0])) * self.A[0]

            # Generate gain fluctuations
            sqrtA = np.sqrt(2.0) * (T_signal_ant + T_noise) * C * np.sqrt(samp_freq)
            noise_G = np.zeros(n_samples)
            if not self.wn_only[0]:
                noise_G = self.noise_kernel(
                    1.0, sqrtA, samp_freq, slope, n_samples, seed_gain
                )

            # Generate noise temperature fluctuations
            sqrtA = np.sqrt(2.0) * T_noise * self.A[0] * np.sqrt(samp_freq)
            noise_Tn = np.zeros(n_samples)
            if not self.wn_only[0]:
                noise_Tn = self.noise_kernel(
                    1, sqrtA, samp_freq, slope, n_samples, seed_Tn
                )
        else:
            wn_rms = parameters[0]
            sqrtA = wn_rms * np.sqrt(samp_freq)
            noise_G = np.zeros(n_samples)
            noise_Tn = np.zeros(n_samples)
            if not self.wn_only[0]:
                noise_G = self.noise_kernel(
                    parameters[1], sqrtA, samp_freq, slope, n_samples, seed_gain
                )
        # Add white noise
        np.random.seed(seed_wn)
        wn = np.random.normal(0.0, wn_rms, n_samples)
        noise_out = noise_G + noise_Tn + wn

        if self.add_offset[0]:
            noise_out = noise_out + T_signal + T_noise

        return noise_out

    #########################################################

    def noise_kernel(self, fknee, sqrtA, samp_freq, slope, n_samples, seed):

        import numpy as np

        rms_wn_norm = 1.0 / np.sqrt(2.0 * n_samples)
        creal = np.zeros(n_samples)
        cimg = np.zeros(n_samples)
        n_half = int(n_samples / 2.0)

        newknee = fknee * n_samples / samp_freq
        new_f_min = self.fmin[0] * n_samples / samp_freq
        new_f_max = self.fmax[0] * n_samples / samp_freq

        #       --------- spectral dependency ---------

        sqr_spectrum = np.zeros(n_half) + 1.0

        indexarr = np.array(range(n_half)) + 1
        funphi = (
            2.0
            / np.pi
            * (
                np.arctan(np.double(indexarr) / new_f_min)
                - np.arctan(np.double(indexarr) / new_f_max)
            )
        )
        sqr_spectrum = np.sqrt((newknee / indexarr * funphi) ** (-slope))

        #   ---------- creates fourier components --------

        creal[0] = 0.0
        cimg[0] = 0.0

        np.random.seed(seed)
        noise = np.random.normal(0.0, 1.0, n_half)

        creal[1:n_half] = noise[1:n_half] * rms_wn_norm * sqr_spectrum[0 : n_half - 1]

        noise = np.random.normal(0.0, 1.0, n_half)
        cimg[1:n_half] = noise[1:n_half] * rms_wn_norm * sqr_spectrum[0 : n_half - 1]

        dr = creal[1:n_half]
        di = cimg[1:n_half]
        creal[n_half + 1 : n_samples] = dr[::-1]
        cimg[n_half + 1 : n_samples] = -di[::-1]
        creal[n_half] = (
            np.random.normal(0.0, 1.0) * rms_wn_norm * sqr_spectrum[n_half - 1]
        )
        cimg[n_half] = 0.0

        result = (creal + 1j * cimg) * sqrtA
        # ;    noise_G = 2d * np.double(n_samples) / sqrt(samp_freq) * np.double(fft(result,/inverse))
        noise = 2.0 * n_samples * np.double(np.fft.ifft(result)) / np.sqrt(samp_freq)

        return noise

    def tant(self, Tthermo, freq):

        """
        NAME:
        Tant

        PURPOSE:
        Convert a signal from thermodynamic to antenna temperature

        CALLING SEQUENCE:
        result = Tant(Tin, freq)

        INPUTS:
        Tin = input thermodynamic temperature
        freq = signal frequency

        NOTES
        this function converts an input thermodynamic temperature to
        antenna temperature according to the following formula:
        Tout = eta Tin /(exp(eta)-1) where eta = h nu/(K Tin)

        MODIFICATION HISTORY:
        May 10    first python
        """

        import numpy as np

        K = 1.38066e-23  # Boltzmann constant
        h = 6.62608e-34  # Planck constant
        K = np.double(K)
        h = np.double(h)
        Tthermo = np.double(Tthermo)
        freq = np.double(freq)
        rj1 = h * freq / K / Tthermo
        rj2 = rj1 / (np.exp(rj1) - 1.0)
        return Tthermo * rj2

    ##################################################
