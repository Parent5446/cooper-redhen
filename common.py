import logging

## Base class for exceptions in this module.
class Error(Exception):
    """Base class for exceptions in this module."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    
    def log(self):
        logger.exception(self)

## Exception raised for errors in the input.
class InputError(Error):
    """Exception raised for errors in the input.

    Attributes:
        expr -- input expression in which the error occurred
        msg  -- explanation of the error
    """

    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg
        self.log()

## Exception raised for errors on the server side.
class ServerError(Error):
    """Exception raised for errors on the server side.
    
    Attributes:
        level -- level of the error
    """
    
    def __init__(self, msg):
        self.msg = msg
        self.log()
