
from google.appengine.ext import db
import os.path

def search(spectrum):
	type = 'Infrared'
	heavysideDict = memcache.get(type+'heavysideDict')
	peakTable = memcache.get(type+'peakTable')
	
	if not heavysideDict: #Make new ones or get from database
		mem = { 'heavysideDict': {'keys':'data'}, 'peakTable': [1,2,3] }
		memcache.setMulti(mem, key_prefix=type)
	
	#Once all the data structures are loaded, they vote on their keys
	#and the winners are fetched from the database by key
	keys = []
	candidates = db.get(keys)
	candidates = sorted(candidates, key=lambda k: k.error)
	#Then return the candidates, and let frontend do the rest
	
	return "It's me, the backend! Let's do this!\n"

class Spectrum(db.Model):
    """Store a spectrum, its related data, and any algorithms necessary
    to compare the spectrum to the DataStore."""
    
    # Variables to be stored in the Google DataStore.
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
    
    def parse_file(self, file_name):
        """Parse a JCAMP file and extract all options and XY data."""
        # Check if file is a directory or does not exist.
        if not os.path.exists(file_name) or os.path.isdir(file_name):
            return Error("File error: File does not exist or is invalid.")
        fp = open(file_name)
        lines = fp.readlines()
        fp.close()
        # Pass the string on to self.parse_string.
        return self.parse_string(lines)
    
    def parse_string(self, data):
        """Parse a string of JCAMP file data and extract all options
        and XY data."""
        opt_list  =  {"TITLE":             True,  "JCAMP-DX":           True,
                      "DATA TYPE":         True,  "ORIGIN":             True,
                      "OWNER":             True,  "XUNITS":             True,
                      "YUNITS":            True,  "XFACTOR":            True,
                      "YFACTOR":           True,  "FIRSTX":             True,
                      "LASTX":             True,  "NPOINTS":            True,
                      "FIRSTY":            True,  "XYDATA":             True,
                      "END":               True,  "CLASS":              False,
                      "DATE":              False, "SAMPLE DESCRIPTION": False,
                      "CAS NAME":          False, "MOLOFORM":           False,
                      "CAS REGISTRY NO":   False, "WISWESSER":          False,
                      "MP":                False, "BP":                 False,
                      "SOURCE REFERENCE":  False, "SAMPLING PROCEDURE": False,
                      "DATA PROCESSING":   False, "RESOLUTION":         False,
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
    
    def find_peaks(self, thres):
        """Looks at the x and y values and finds peaks in the spectrum's
        graph that are higher than the given numeric threshold."""
        # Get XY data and set temporary variables
        x, y = self.x, self.y
        peaks = []
        prev = ypeak = end = xpeak = 0
        start = y[1]
        # This variable is true when ascending a peak and false when
        # descending a peak.
        searching = True
        for k in x:
            if y[k] < prev and searching:
                # Found the peak itself
                ypeak = y[k - 1]
                xpeak = k
                searching = False
            elif y[k] > prev and not searching:
                # Found the end of the peak
                end = y[k]
                if ypeak - start < int(thres):
                    # Peak not high enough, keep searching
                    xpeak = ypeak = 0
                    searching = True
                elif ypeak - end < int(thres):
                    # End not low enough, keep looking
                    end = 0
                else:
                    # Peak confirmed, add it to the list
                    peaks.append(xpeak)
                    start = end
                    end = xpeak = ypeak = 0
                    searching = True
            prev = y[k]
        return peaks
