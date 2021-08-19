#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="Striptease",
    version="0.1.0",
    description="Bindings to the Strip control software",
    author="Stefano Sartor, Maurizio Tomasi",
    author_email="",
    url="https://github.com/lspestrip/striptease",
    packages=find_packages(),
    data_files=[
        (
            "data",
            [
                "data/bias1_cal.xlsx",
                "data/bias2_cal.xlsx",
                "data/bias3_cal.xlsx",
                "data/bias4_cal.xlsx",
                "data/bias5_cal.xlsx",
                "data/bias6_cal.xlsx",
                "data/bias7_cal.xlsx",
                "data/bias8_cal.xlsx",
                "data/bias9_cal.xlsx",
                "data/cold_bias_table.json",
                "data/default_biases_warm_nominal_you_want_to_use_this_when_everything_will_be_fixed.xlsx",
                "data/default_biases_warm.xlsx",
                "data/hk_pars_BOARD_BIAS.csv",
                "data/hk_pars_BOARD_DAQ.csv",
                "data/hk_pars_POL_BIAS.csv",
                "data/hk_pars_POL_DAQ.csv",
                "data/input_bias_IVtest.xlsx",
            ],
        )
    ],
)
