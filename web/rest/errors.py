# web/rest/errors.py --- Base Exceptions
#
# Copyright (C) 2018 Stefano Sartor - stefano.sartor@inaf.it


class RestError(Exception):
    """Base class for exceptions in this module."""

    pass


class InputLogin(RestError):
    """Exception raised when infufficient login credentials are provided"""

    def __init__(self):
        self.message = "No login credentials provided"
