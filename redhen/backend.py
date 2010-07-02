# The Python style guide is located here:
# http://www.python.org/dev/peps/pep-0008/

from google.appengine.ext import db
from error import Error
import os.path

def search():
	return "It's me, the backend! Let's do this!\n"


class Spectrum(db.model):
    chemical_name = db.StringProperty(required=True)
    chemical_type = db.StringProperty(required=True)
    options_jcamp = db.ListProperty(str)
    options_custom = db.ListProperty(str)
    xydata_normal = db.ListProperty(float, required=True)
    xydata_integrated = db.ListProperty(float, required=True)
    xydata_differentiated = db.ListProperty(float, required=True)
    
    def __init__(self, file_data = False):
        if not isinstance(file_data, bool):
            self.parseString(file_data)
    
    def parseFile(self, file_name):
        if not os.path.exists(file_name) or os.path.isdir(file_name):
            return Error("File error: File does not exist or is invalid.")
        fp = open(file_name)
        lines = fp.readlines()
        fp.close()
        return self.parseString(lines)
    
    def parseString(self, data):
        opt_list  =  {"TITLE":             True,  "JCAMP-DX":           True, \
                      "DATA TYPE":         True,  "ORIGIN":             True, \
                      "OWNER":             True,  "XUNITS":             True, \
                      "YUNITS":            True,  "XFACTOR":            True, \
                      "YFACTOR":           True,  "FIRSTX":             True, \
                      "LASTX":             True,  "NPOINTS":            True, \
                      "FIRSTY":            True,  "XYDATA":             True, \
                      "END":               True,  "CLASS":              False,\
                      "DATE":              False, "SAMPLE DESCRIPTION": False,\
                      "CAS NAME":          False, "MOLOFORM":           False,\
                      "CAS REGISTRY NO":   False, "WISWESSER":          False,\
                      "MP":                False, "BP":                 False,\
                      "SOURCE REFERENCE":  False, "SAMPLING PROCEDURE": False,\
                      "DATA PROCESSING":   False, "RESOLUTION":         False,\
                      "DELTAX":            False}

        # Note on JCAMP parsing syntax:
        # The file has a number of special characters to process:
        #   == - Denotes the start of a data label
        #   =  - Signals the end of a data label (and beginning of its value)
        #        NOTE: At the end of a line, the equals sign means continue
        #              to the next line without stopping.
        #   $$ - Indicates the rest of the line is a comment
        #   $  - Signifies a user-defined, nonstandard data label
        #   () - Used to delimit strings instead of quotes
        #        NOTE: Can also be used to delimit string-containing
        #              data groups.
        # Reference: http://www.jcamp-dx.org/
        if isinstance(data, str):
            data = data.splitlines()
        workingline = ""
        for line in data:
            workingline += line
            # Start by removing inline comments
            line = line.partition("$$")[0]
            # First check if combining with next line
            if line[-1] == "=":
                workingline = workingline[:-1]
                continue
            # Now check for special characters
            if workingline[0:2] == "==":
                # This line is a data label
                parts = workingline[2:].partition("=")
                key, value = parts[0], parts[1]
                if key[0] == "$":
                    # Put custom options in a separate list
                    self.options_custom[key] = value
                elif key in opt_list.keys():
                    opt_list[key] = value
            else:
                # This line is part of the xy data.
                # First validate the data labels before continuing.
                for key in opt_list.keys():
                    if opt_list[key] and isinstance(opt_list[key], bool):
                        # This means a required variable has not been set.
                        return Error("Parse error: Missing required options.")
                    # Now check how the XY data is sorted.
                if opt_list["XYDATA"] == "(X++(Y..Y))":
                    if not opt_list["DELTAX"]:
                        deltax = (opt_list["LASTX"] - opt_list["FIRSTX"]) / \
                                 (opt_list["NPOINTS"] - 1)
                    else:
                        deltax = opt_list["DELTAX"]
                    # TODO: Parse XY data
                elif opt_list["XYDATA"] == "(XY..XY)":
                    # TODO: Parse XY data
                    pass
                else:
                    return Error("Parse error: Invalid XY data.")
            # Reset the working line.
            workingline = ""
        return True
