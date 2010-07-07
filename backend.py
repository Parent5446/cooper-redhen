import os.path
from google.appengine.ext import db, memcache

#Spectrum database entries and voting data structures will be preloaded
def search(file):
    spectrum_type = 'Infrared'
    heavyside_dict = memcache.get(spectrum_type+'_heavyside_dict')
    peak_table = memcache.get(spectrum_type+'_peak_table')
    
    # Load the user's spectrum into a Spectrum object.
    user_spectrum = Spectrum()
    user_spectrum.parse_string(file_contents)
    # Get necessary data from spectrum.
    user_peaks = user_spectrum.find_peaks()
    
    #Once all the data structures are loaded, they vote on their keys
    #and the winners are fetched from the database by key
    spectrum = Spectrum(file)
    keys = [ (spec, 10) for spec in heavyside_dict[spectrum.heavySideKey]]
    keys += peak_table[spectrum.peak-5:spectrum.peak+5]
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
    data = db.ListProperty(float, required=True)
    
    def __init__(self, file_data = None):
        if file_data is not None:
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
    
    def find_peaks(self):
        """Check memcache then the Data Store for the peaks in this Spectrum.
        If they are not found, calculate them and store them."""
        # Check memcached first.
        spectrum_type = 'Infrared'
        key = str(self.key())
        peaks_memcached = memcache.get(spectrum_type+'_peak_table')
        peaks_datastore = Matcher.peak_table
        peaks_local = []
        if peaks_memcached is not None:
            # Peak table is a dictionary where the keys are x-values and the
            # values are dictionaries with Spectrum keys.
            for peak in peaks_memcached.keys():
                # Check if there is a peak for this spectrum
                if key in peaks_memcached[peak]:
                    peaks_local.append(peak)
                if len(peaks_local) != 0:
                    # If we got any peaks, return them.
                    return peaks_local
        # Function did not return, so nothing is in memcached. Check data store.
        if len(peaks_datastore) != 0:
            # Data store has something, so get the values and return.
            for peak in peaks_datastore:
                if key in peak:
                    peaks_local.append(peak.value)
            if len(peaks_local) != 0:
                return peaks_local
        else:
            # Now we have to get the peaks ourselves and store them.
            # FIXME: Find way to define threshold.
            peaks_local = self._calculate_peaks(thres)
            if peaks_memcached is None:
                # Set a default peak table if memcached does not exist
                peaks_memcached = {}
            for peak in peaks_local:
                # Data Store: Add the value to the dictionary.
                if peaks_datastore[peak] is None:
                    peaks_datastore[peak] = [key]
                else:
                    peaks_datastore[peak].append(key)
                # Memcached: Add the value to the dictionary.
                if peaks_memcached[peak] is None:
                    peaks_memcached[peak] = [key]
                else:
                    peaks_memcached[peak].append(key)
            # Store the final dictionaries.
            memcache.set(spectrum_type+'_peak_table', peaks_memcached)
            Matcher.peak_table = peaks_datastore
            Matcher.put()
        return peaks_local
    
    def find_integrals(self):
        """Get the integrated XY dat for this spectrum, or calculate it if
        it does not exist."""
        if not len(self.xydata_integrated):
            self.xydata_integrated = self._calculate_integrals()
        return self.xydata_integrated
    
    def find_heavyside(self):
        """Get the heavyside index for this spectrum, or calculate it if
        it does not exist."""
        # FIXME: Need storage for heavyside so it does not have to be
        #        calculated every time.
        return self._calculate_heavyside(self, 8)
    
    def _calculate_integrals(self):
        """Integrate the XY data for the spectrum."""
        x, y = self.x, self.y
        deltax = x[2] - x[1]
        return [deltax * yvalue for yvalue in y]
    
    def _calculate_peaks(self, thres):
        """Looks at the x and y values and finds peaks in the spectrum's
        graph that are higher than the given numeric threshold."""
        # Get XY data and set temporary variables
        x, y = self.x, self.y
        peaks = []
        prev = ypeak = end = xpeak = 0
        start = y[1] # The spectra has to be within the range of 600-3900
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
    
    def _calculate_heavyside(self, bits):
        """Calculate the heavyside index for this spectrum."""
        # Get the intgrated data for calculation.
        integrals = self.find_integrals()
        index = ""
        # Only run for a user-defined number of bits.
        for k in range(bits):
            # Separate the data and find the total area.
            separator = len(integrals) / 2
            sum1 = reduce(add, integrals[:separator])
            sum2 = reduce(add, integrals[separator:])
            if sum1 > sum2:
                # The left is bigger, add a zero bit.
                index += "0"
                integrals = integrals[:separator]
            else:
                # The right is bigger, add a one bit.
                index += "1"
                integrals = integrals[separator:]
        # Convert to binary and return.
        return int(index, 2)

class DictProperty(db.Property):
    data_type = dict
    
    def get_value_for_datastore(self, model_instance):
        value = super(DictProperty, self).get_value_for_datastore(model_instance)
        return db.Blob(pickle.dumps(value))
    
    def make_value_from_datastore(self, value):
        if value is None:
            return dict()
        return pickle.loads(value)

    def default_value(self):
        if self.default is None:
            return dict()
        else:
            return super(DictProperty, self).default_value().copy()

    def validate(self, value):
        if not isinstance(value, dict):
            raise db.BadValueError('Property %s needs to be convertible '
                                   'to a dict instance (%s) of class dict' % (self.name, value))
        return super(DictProperty, self).validate(value)
    
    def empty(self, value):
        return value is None


class Matcher(db.Model):
    heavyside1 = DictProperty()
    heavyside2 = DictProperty()
    peak_table = ListProperty()
    high_low = DictProperty()
    chem_types = DictProperty()
	