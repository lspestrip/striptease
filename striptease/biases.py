# -*- encoding: utf-8 -*-

import json
import pandas as pd
from pathlib import Path
import logging
from collections import namedtuple

BiasConfiguration = namedtuple(
    "BiasConfiguration",
    [
        "vd0",
        "vd1",
        "vd2",
        "vd3",
        "vd4",
        "vd5",
        "vg0",
        "vg1",
        "vg2",
        "vg3",
        "vg4",
        "vg5",
        "vg4a",
        "vg5a",
        "vpin0",
        "vpin1",
        "vpin2",
        "vpin3",
        "ipin0",
        "ipin1",
        "ipin2",
        "ipin3",
        "id0",
        "id1",
        "id2",
        "id3",
        "id4",
        "id5",
    ],
)

ChannelCalibration = namedtuple(
    "ChannelCalibration",
    [
        "vd0_set",
        "vd1_set",
        "vd2_set",
        "vd3_set",
        "vd4_set",
        "vd5_set",
        "vg0_set",
        "vg1_set",
        "vg2_set",
        "vg3_set",
        "vg4_set",
        "vg5_set",
        "vg4a_set",
        "vg5a_set",
        "vpin0_set",
        "vpin1_set",
        "vpin2_set",
        "vpin3_set",
        "ipin0_set",
        "ipin1_set",
        "ipin2_set",
        "ipin3_set",
        "id0_set",
        "id1_set",
        "id2_set",
        "id3_set",
        "id4_set",
        "id5_set",
        "vd0_hk",
        "vd1_hk",
        "vd2_hk",
        "vd3_hk",
        "vd4_hk",
        "vd5_hk",
        "vg0_hk",
        "vg1_hk",
        "vg2_hk",
        "vg3_hk",
        "vg4_hk",
        "vg5_hk",
        "vg4a_hk",
        "vg5a_hk",
        "vpin0_hk",
        "vpin1_hk",
        "vpin2_hk",
        "vpin3_hk",
        "ipin0_hk",
        "ipin1_hk",
        "ipin2_hk",
        "ipin3_hk",
        "id0_hk",
        "id1_hk",
        "id2_hk",
        "id3_hk",
        "id4_hk",
        "id5_hk",
    ],
)


class InstrumentBiases:
    """InstrumentBiases

    Query an Excel file containing the values for all the biases needed to turn on the
    Strip instrument.

    Once you have created an instance of `InstrumentBiases`, call `get_biases` to return
    the biases of one polarimeter.
    """

    def __init__(self, filename=None):
        if not filename:
            filename = str(
                Path(__file__).absolute().parent.parent
                / "data"
                / "default_biases_warm.xlsx"
            )

        logging.info("Loading default biases from file %s", filename)
        sheets = pd.read_excel(
            filename, header=0, index_col=0, sheet_name=["Biases", "Modules"]
        )
        self.biases = sheets["Biases"]
        self.modules = sheets["Modules"]

    def module_name_to_polarimeter(self, module_name: str) -> str:
        """Given a module name like ``V0``, return the name of the polarimeter (e.g., ``STRIP04``)

        See also :meth:`.module_name_to_polarimeter_number`.
        """
        return self.modules["Polarimeter"][module_name]

    def module_name_to_polarimeter_number(self, module_name: str) -> str:
        """Given a module name like ``V0``, return the number of the polarimeter (e.g., 4)

        See also :meth:`.module_name_to_polarimeter`.
        """
        return self.modules["Polarimeter"][module_name]

    def polarimeter_to_module_name(self, polarimeter_name: str) -> str:
        """Given a polarimeter name like ``STRIP04``, return the module name (e.g., ``V0``)

        See also :meth:`.polarimeter_number_to_module_name`."""
        mask = self.modules["Polarimeter"] == polarimeter_name
        entries = self.modules[mask].index.values
        assert len(entries) == 1
        return entries[0]

    def polarimeter_number_to_module_name(self, polarimeter_num: int) -> str:
        """Given a polarimeter name like 4 (for ``STRIP04``), return the module name (e.g., ``V0``)

        See also :meth:`.polarimeter_to_module_name`."""
        return self.polarimeter_to_module_name(f"STRIP{polarimeter_num:02d}")

    def get_biases(self, module_name=None, polarimeter_name=None,param_hk=None):
        """Return the biases needed to turn on a polarimeter.

        The return value is an instance of `BiasConfiguration`. You can specify either the name
        of the module (e.g., "I0") or the name of the polarimeter (e.g., "STRIP58").
        """
        if (not module_name) and (not polarimeter_name):
            raise ValueError(
                "You must provide either 'module_name' or 'polarimeter_name' to 'InstrumentBiases.read_biases'"
            )

        if module_name and polarimeter_name:
            raise ValueError(
                "You cannot provide both 'module_name' and 'polarimeter_name' to 'InstrumentBiases.read_biases'"
            )

        if module_name:
            polarimeter_name = self.module_name_to_polarimeter(module_name)

        if not (polarimeter_name in self.biases):
            valid_names = ", ".join(['"{0}"'.format(x) for x in self.biases.keys()])
            raise ValueError(
                f"Unknown polarimeter '{polarimeter_name}', valid values are {valid_names}"
            )
        if param_hk is not None:
            result = self.biases[polarimeter_name][param_hk]
        else:
            result = BiasConfiguration(
                vd0=self.biases[polarimeter_name]["VD0"],
                vd1=self.biases[polarimeter_name]["VD1"],
                vd2=self.biases[polarimeter_name]["VD2"],
                vd3=self.biases[polarimeter_name]["VD3"],
                vd4=self.biases[polarimeter_name]["VD4"],
                vd5=self.biases[polarimeter_name]["VD5"],
                vg0=self.biases[polarimeter_name]["VG0"],
                vg1=self.biases[polarimeter_name]["VG1"],
                vg2=self.biases[polarimeter_name]["VG2"],
                vg3=self.biases[polarimeter_name]["VG3"],
                vg4=self.biases[polarimeter_name]["VG4"],
                vg5=self.biases[polarimeter_name]["VG5"],
                vg4a=self.biases[polarimeter_name]["VG4A"],
                vg5a=self.biases[polarimeter_name]["VG5A"],
                vpin0=self.biases[polarimeter_name]["VPIN0"],
                vpin1=self.biases[polarimeter_name]["VPIN1"],
                vpin2=self.biases[polarimeter_name]["VPIN2"],
                vpin3=self.biases[polarimeter_name]["VPIN3"],
                ipin0=self.biases[polarimeter_name]["IPIN0"],
                ipin1=self.biases[polarimeter_name]["IPIN1"],
                ipin2=self.biases[polarimeter_name]["IPIN2"],
                ipin3=self.biases[polarimeter_name]["IPIN3"],
                id0=self.biases[polarimeter_name]["ID0"],
                id1=self.biases[polarimeter_name]["ID1"],
                id2=self.biases[polarimeter_name]["ID2"],
                id3=self.biases[polarimeter_name]["ID3"],
                id4=self.biases[polarimeter_name]["ID4"],
                id5=self.biases[polarimeter_name]["ID5"],
        )
        return result


class BoardCalibration:
    """InstrumentBiases

    Query an Excel file containing the values for all calibrations needed to turn on the
    Strip instrument.

    Once you have created an instance of `BoardCalibration`, call `get_channel_calibration` to return
    the calibration of one channel.
    """

    def __init__(self, filename):
        pass

    def get_channel_calibration(self, channel_no=None, channel_name=None):
        """Return the calibration needed to drive a channel.

        The return value is an instance of `ChannelCalibration`. You can specify either the name
        of the channel number (0:7) or the name of the channel ("Pol1" : "Pol8").
        """
        if channel_no is None and channel_name is None:
            raise ValueError(
                "You must provide either 'channel_no' or 'channel_name' to 'BoardCalibration.get_channel_calibration'"
            )

        if channel_no is not None and channel_name is not None:
            raise ValueError(
                "You cannot provide both 'channel_no' and 'channel_name' to 'BoardCalibration.get_channel_calibration'"
            )

        if channel_no is not None:
            if channel_no < 0 or channel_no > 7:
                raise ValueError("'channel_no' must be a value from 0 to 7")
            channel = "Pol" + str(channel_no + 1)
        else:
            # if channel_name not in ['Pol1',]
            raise Exception("Not implemented yet!")


RefBiasConfiguration = namedtuple(
    "RefBiasConfiguration",
    [
        "vd0",
        "vd1",
        "vd2",
        "vd3",
        "vd4",
        "vd5",
        "vg0",
        "vg1",
        "vg2",
        "vg3",
        "vg4",
        "vg5",
        "id0",
        "id1",
        "id2",
        "id3",
        "id4",
        "id5",
        "output_q1",
        "output_q2",
        "output_u1",
        "output_u2",
    ],
)


class ReferenceBiases:
    """ReferenceBiases

    Load the reference biases acquired during the unit tests.

    Once you have created an instance of `ReferenceBiases`, call
    `get_biases` to return the biases of one polarimeter.

    """

    def __init__(self, filename=None):
        if not filename:
            filename = str(
                Path(__file__).absolute().parent.parent
                / "data"
                / "cold_bias_table.json"
            )

        logging.info("Loading reference biases from file %s", filename)

        with open(filename, "rt") as inpf:
            self.data = json.load(inpf)

    def get_biases(self, polarimeter_name):
        """Return the reference biases for a polarimeter.

        The return value is a dictionary containing all the metadata
        related to the biases of the specified polarimeter (e.g.,
        `STRIP05`).

        """

        if not (polarimeter_name in self.data):
            values = ", ".join(self.data.keys())
            raise ValueError(
                f"Unknown polarimeter {polarimeter_name}, valid values are {values}"
            )

        return self.data[polarimeter_name]
