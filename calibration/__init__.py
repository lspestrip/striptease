# calibration/__init__.py --- class handling the conversion from ADU to phisical units and viceversa
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it



class Calibration(object):
    def __init__(self):
        ## TODO: load calibration curves
        pass

    def calibrate(self,pol,hk,value):
        ## TODO: given the polarimeter name, the housekeeping and the ADU value
        ## return the value in phisical units
        return value

    def reverse(self,pol,hk,value):
        ## TODO: given the polarimeter name, the housekeeping and the value in
        ## phisical units return the ADU value
        return value
