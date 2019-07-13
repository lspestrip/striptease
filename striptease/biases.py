# -*- encoding: utf-8 -*-

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

ChannelCalibration = namedtuple("ChannelCalibration", [])


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

    def get_biases(self, module_name=None, polarimeter_name=None):
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
            polarimeter_name = self.modules["Polarimeter"][module_name]

        if not (polarimeter_name in self.biases):
            valid_names = ", ".join(['"{0}"'.format(x) for x in self.biases.keys()])
            raise ValueError(
                f"Unknown polarimeter '{polarimeter_name}', valid values are {valid_names}"
            )

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
    def __init__(self, filename=None):
        pass
