import logging

from google.appengine.ext import db

## Provide functions and class definitions for use in both the front end and
# back end.
# 
# @package common
# @author The Cooper Union for the Advancement of the Science and the Arts
# @license http://opensource.org/licenses/lgpl-3.0.html GNU Lesser General Public License v3.0
# @copyright Copyright (c) 2010, Cooper Union (Some Right Reserved

## Store a dictionary object in the Google Data Store.
class DictProperty(db.Property):
    """Store a dictionary object in the Google Data Store."""
    
    data_type = dict
    
    ## Serialize the dictionary for storage in the database.
    # @param model_instance An instance of this class
    # @return String with the serialized dictionary
    def get_value_for_datastore(self, model_instance):
        """Use pickle to serialize a dictionary for database storage."""
        value = super(DictProperty, self).get_value_for_datastore(model_instance)
        return db.Blob(pickle.dumps(value))
    
    ## Unserialize a dictionary retrieved from the database.
    # @param value String with the serialized dictionary
    # @return Dictionary (dict) with the unserialized value
    def make_value_from_datastore(self, value):
        """Use pickle to deserialize a dictionary from the database."""
        if value is None:
            # Make a new dictionary if it does not exist.
            return dict()
        return pickle.loads(value)
    
    ## Get the default value for the property.
    def default_value(self):
        """Get the default value for the property."""
        if self.default is None:
            return dict()
        else:
            return super(DictProperty, self).default_value().copy()
    
    ## Check if the value is actually a dictionary.
    # @param value Value to be validated
    # @return True for valid, false for invalid
    def validate(self, value):
        """Check if the value is actually a dictionary."""
        if not isinstance(value, dict):
            raise db.BadValueError('Property %s needs to be convertible to a dict instance (%s)' % (self.name, value))
        # Have db.Property validate it as well.
        return super(DictProperty, self).validate(value)
    
    ## Check if the dictionary is empty.
    # @param value Dictionary to be checked
    # @return True for empty, false for not empty
    def empty(self, value):
        """Check if the value is empty."""
        return value is None

## Store a list object in the Google Data Store.
class GenericListProperty(db.Property):
    """Store a list object in the Google Data Store."""
    
    data_type = list
    
    ## Serialize the list for storage in the database.
    # @param model_instance An instance of this class
    # @return String with the serialized list
    def get_value_for_datastore(self, model_instance):
        """Use pickle to serialize a list for database storage."""
        value = super(GenericListProperty, self).get_value_for_datastore(model_instance)
        return db.Blob(pickle.dumps(value))
    
    ## Unserialize a list retrieved from the database.
    # @param value String with the serialized list
    # @return List with the unserialized value
    def make_value_from_datastore(self, value):
        """Use pickle to deserialize a list from the database."""
        if value is None:
            # Make a new list if it does not exist.
            return []
        return pickle.loads(value)
    
    ## Get the default value for the property.
    def default_value(self):
        """Get the default value for the property."""
        if self.default is None:
            return []
        else:
            return super(GenericListProperty, self).default_value().copy()
    
    ## Check if the value is actually a list.
    # @param value Value to be validated
    # @return True for valid, false for invalid
    def validate(self, value):
        """Check if the value is actually a list."""
        if not isinstance(value, list):
            raise db.BadValueError('Property %s needs to be convertible to a list instance (%s)' % (self.name, value))
        # Have db.Property validate it as well.
        return super(GenericListProperty, self).validate(value)
    
    ## Check if the list is empty.
    # @param value List to be checked
    # @return True for empty, false for not empty
    def empty(self, value):
        """Check if the value is empty."""
        return value is None
    

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
