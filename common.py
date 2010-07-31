"""
Provide functions and class definitions for use in both the front end and
back end.

@organization: The Cooper Union for the Advancement of the Science and the Arts
@license: http://opensource.org/licenses/lgpl-3.0.html GNU Lesser General Public License v3.0
@copyright: Copyright (c) 2010, Cooper Union (Some Right Reserved)
"""

import logging
import pickle
import array

from google.appengine.ext import db
from google.appengine.api import datastore_errors


class DictProperty(db.Property):
    """Store a dictionary object in the Google Data Store."""
    
    data_type = dict
    """Data type for this property, which is a dictionary since this is the
    DictProperty class."""
    
    def get_value_for_datastore(self, model_instance):
        """
        Use pickle to serialize a dictionary for database storage.
        
        @param model_instance: An instance of this class
        @type  model_instance: L{common.DictProperty}
        @return: The serialized dictionary
        @rtype: C{str}
        """
        value = super(DictProperty, self).get_value_for_datastore(model_instance)
        return db.Blob(pickle.dumps(value))
    
    def make_value_from_datastore(self, value):
        """
        Use pickle to deserialize a dictionary from the database.
        
        @param value: Database value to deserialize
        @type  value: C{str}
        @return: The unserialized dictionary
        @rtype: C{dict}
        """
        if value is None:
            # Make a new dictionary if it does not exist.
            return dict()
        return pickle.loads(value)
    
    def default_value(self):
        """Get the default value for the property."""
        if self.default is None:
            return dict()
        else:
            return super(DictProperty, self).default_value().copy()
    
    def validate(self, value):
        """
        Check if the value is actually a dictionary.
        
        @param value: Value to be validated
        @type  value: Anything
        @return: Whether the value is valid
        @rtype: C{bool}
        """
        if not isinstance(value, dict):
            raise db.BadValueError('Property %s needs to be convertible to a dict instance (%s)' % (self.name, value))
        # Have db.Property validate it as well.
        return super(DictProperty, self).validate(value)
    
    def empty(self, value):
        """
        Check if the value is empty.
        
        @param value: Value to be checked
        @type  value: Anything
        @return: Whether the value is empty
        @rtype: C{bool}
        """
        return value is None


class GenericListProperty(db.Property):
    """Store a list object in the Google Data Store."""
    
    data_type = list
    """Data type for this property, which is a list since this is the
    GenericListProperty class."""
    
    def get_value_for_datastore(self, model_instance):
        """
        Use pickle to serialize a list for database storage.
        
        @param model_instance: An instance of this class
        @type  model_instance: L{common.GenericListProperty}
        @return: The serialized list
        @rtype: C{str}
        """
        value = super(GenericListProperty, self).get_value_for_datastore(model_instance)
        return db.Blob(pickle.dumps(value))
    
    def make_value_from_datastore(self, value):
        """
        Use pickle to deserialize a list from the database.
        
        @param value: Database value to deserialize
        @type  value: C{str}
        @return: The unserialized list
        @rtype: C{list}
        """
        if value is None:
            # Make a new list if it does not exist.
            return []
        return pickle.loads(str(value))
    
    def default_value(self):
        """Get the default value for the property."""
        if self.default is None:
            return []
        else:
            return super(GenericListProperty, self).default_value().copy()
    
    def validate(self, value):
        """
        Check if the value is actually a list.
        
        @param value: Value to be validated
        @type  value: Anything
        @return: Whether the value is valid
        @rtype: C{bool}
        """
        if not isinstance(value, list):
            raise db.BadValueError('Property %s needs to be convertible to a list instance (%s)' % (self.name, value))
        # Have db.Property validate it as well.
        return super(GenericListProperty, self).validate(value)
    
    def empty(self, value):
        """
        Check if the value is empty.
        
        @param value: Value to be checked
        @type  value: Anything
        @return: Whether the value is empty
        @rtype: C{bool}
        """
        return value is None

class ArrayProperty(db.Property):
    def __init__(self, typecode, default=None, **kwargs):
        self.typecode = typecode
        if default is None: default = array.array(typecode)
        super(ArrayProperty, self).__init__(default=default, **kwargs)
    
    def validate(self, value):
        if not isinstance(value, array.array) or value.typecode != self.typecode:
            raise datastore_errors.BadValueError("Property %s must be an array instance with typecode %s" % (self.name, self.typecode))
        value = super(ArrayProperty, self).validate(value)
        return value
    
    def get_value_for_datastore(self, model_instance):
        value = self.__get__(model_instance, model_instance.__class__)
        return db.Blob(value.tostring())
    
    def make_value_from_datastore(self, value):
        a = array.array(self.typecode)
        if value is None: return a
        a.fromstring(value)
        return a
    
    data_type=db.Blob        

class Error(Exception):
    """Base class for exceptions in this module."""
    
    DEBUG = logging.DEBUG
    """Constant for debug-level messages."""
    
    INFO = logging.INFO
    """Constant for info-level messages."""
    
    WARNING = logging.WARNING
    """Constant for warning-level messages."""
    
    ERROR = logging.ERROR
    """Constant for error-level messages."""
    
    CRITICAL = logging.CRITICAL
    """Constant for critical-level messages."""
    
    def log(self):
        """Create a log message when an exception is raised."""
        logging.exception(self)


class InputError(Error):
    """Exception raised for errors in the input."""

    def __init__(self, expr, msg):
        """
        Initialize the exception variables.
        
        @param expr: The input that was invalid
        @type  expr: C{str}
        @param msg: Explanation of why it was invalid
        @type  msg: C{str}
        """
        self.expr = expr
        self.msg = msg
        self.log()


class ServerError(Error):
    """Exception raised for errors on the server side."""
    
    def __init__(self, msg):
        """
        Initialize the exception variables.
        
        @param msg: Explanation of what went wrong
        @type  msg: C{str}
        """
        self.msg = msg
        self.log()


class AuthError(Error):
    """Exception raised for authorization errors."""
    
    def __init__(self, user, msg):
        """
        Initialize the exception variables.
        
        @param user: The user, or None if not logged in
        @type  user: L{google.appengine.api.users.User}
        @param msg: Explanation of what permissions were needed
        @type  msg: C{str}
        """
        if user is not None:
            self.expr = user.nickname
        else:
            self.expr = "Anonymous"
        self.msg = msg
        self.log()

class GenericDataProperty(db.Property):
    """Store arbitrary data in the datastore."""
    
    data_type = object
    """Data type for this property, which is any."""
    
    def get_value_for_datastore(self, model_instance):
        """
        Use pickle to serialize for database storage.
        
        @param model_instance: An instance of this class
        @type  model_instance: L{common.Data}
        @return: The serialized data
        @rtype: C{str}
        """
        value = super(GenericDataProperty, self).get_value_for_datastore(model_instance)
        return db.Blob(pickle.dumps(value))
    
    def make_value_from_datastore(self, value):
        """
        Use pickle to deserialize data from the database.
        
        @param value: Database value to deserialize
        @type  value: C{str}
        @return: The unserialized data
        @rtype: C{object}
        """
        if value is None:
            return None
        return pickle.loads(value)
    
    def default_value(self):
        """Get the default value for the property."""
        if self.default is None:
            return None
        else:
            return super(GenericDataProperty, self).default_value().copy()
    
    def empty(self, value):
        """
        Check if the value is empty.
        
        @param value: Value to be checked
        @type  value: Anything
        @return: Whether the value is empty
        @rtype: C{bool}
        """
        return value is None