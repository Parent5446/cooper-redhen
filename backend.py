import os.path
import re
from google.appengine.ext import db
from google.appengine.api import memcache

#Spectrum database entries and voting data structures will be preloaded
def search(file):
    spectrum_type = 'Infrared'
    matcher = memcache.get(spectrum_type+'_matcher')
    if matcher is None: matcher = Matcher.all()[0]
    
    # Load the user's spectrum into a Spectrum object.
    user_spectrum = Spectrum()
    user_spectrum.parse_string(file_contents)
    # Get necessary data from spectrum.
    user_peaks = user_spectrum.find_peaks()
    
    #Once all the data structures are loaded, they vote on their keys
    #and the winners are fetched from the database by key
    spectrum = Spectrum(file)
    candidates = matcher.get(spectrum)
    findError(candidates)
    candidates = sorted(candidates, key=lambda k: k.error)
    #Then return the candidates, and let frontend do the rest
    return "It's me, the backend! Let's do this!\n"

def add(file):
    spectrum = Spectrum(file)
    spectrum_type = 'Infrared'
    matcher = memcache.get(spectrum_type+'_matcher')
    if matcher is None: matcher = Matcher.get_by_key_name(spectrum_type)
    if not matcher: matcher = Matcher(key_name=spectrum_type)
    spectrum.put() #Add to database
    matcher.add(spectrum) #Add to matcher
    
class Spectrum(db.Model):
    """Store a spectrum, its related data, and any algorithms necessary
    to compare the spectrum to the DataStore."""
    # Variables to be stored in the Google DataStore.
    chemical_name = db.StringProperty(required=True)
    chemical_type = db.StringProperty(required=True)
    data = db.ListProperty(float, required=True)
    
    def __init__(self, file):
        """Parse a string of JCAMP file data and extract all needed data."""
        contents = file.read()
        self.data = [ float(match.group(1)) for match in re.finditer('[^\r\n]([d.-]+)', contents[contents.find('##XYDATA=(X++(Y..Y))')+20:]) ]
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
    
    def add(self):
        """Add the spectrum to the data store and put its relevant heuristic data in
        the Matcher object."""
        spectrum_type = 'Infrared'
        # Get the Matcher, or make a new one if it does not exist.
        matcher = memcache.get(spectrum_type+'_matcher')
        if matcher is None:
            matcher = Matcher.all()
        if matcher:
            matcher = matcher[0] #Change this when there is more than one
        else:
            matcher = Matcher()
        # Put to the data store, then to the Matcher.
        key = self.put()
        matcher.add(self)
        memcache.set(spectrum_type+'_matcher', matcher)
        matcher.put()
    
    def bove(self, other):
        self.error = Matcher().bove(self, other)
    
    def least_squares(self, other):
        self.error = Matcher().least_squares(self, other)
    
    def find_peaks(self): 
        """Check memcache then the Data Store for the peaks in this Spectrum.
        If they are not found, calculate them and store them."""
        # Check memcached first.
        spectrum_type = 'Infrared'
        key = str(self.key())
        peaks_memcached = memcache.get(spectrum_type+'_peak_table')
        peaks_datastore = Matcher.all()[0].peak_table
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
    """Store spectra data necessary for searching the database, then search the database
    for candidates that may represent a given spectrum."""
    
    # Variables to be stored in the Google Data Store
    heavyside1 = DictProperty()
    heavyside2 = DictProperty()
    peak_table = DictProperty()
    high_low = DictProperty()
    chem_types = DictProperty()
    
    def add(self, spectrum):
        """Add new spectrum data to the various Matcher dictionaries. Find the heavyside
        index, peaks, and other indices and add them to the dictionaries."""
        # Get the spectrum's key, peaks, and other heuristic data.
        key = str(spectrum.key())
        heavyside = spectrum.find_heavyside()
        peaks = self.find_peaks()
        # Add it to the dictionaries.
        self.heavyside1[heavyside] = key
        for peak in peaks:
            self.peak_table[peak].append(key)
        return True
    
    def get(self, spectrum):
        """Find spectra that may represent the given Spectrum object by sorting
        the database using different heuristics, having them vote, and returning only
        the spectra deemed similar to the given spectrum."""
        # Get the reference values
        peaks = spectrum.find_peaks()
        heavyside = spectrum.find_heavyside()
        # Get the set of relevant spectra. The keys list should be a zipped pair
        # of lists with a spectra and and a vote in each.
        keys = []
        for peak in peaks:
            keys.extend([(spec, 10) for spec in self.peak_table if peak - 5 < spec < peak + 5])
        keys.extend([(spec, 10) for spec in self.heavyside1 if heavyside - 5 < spec < heavyside + 5])
        keys += [(spec, 10) for spec in high_low_dict[spectrum.highLowKey]]
        keys += [(spec, 10) for spec in chemical_types[spectrum.chemical_type]]
        # Add together all the votes.
        keys.sort()
        return keys
    
    @staticmethod
    def bove(one, other):
        return max([abs(one.data[i]-other.data[i]) for i in len(one.data)])
    
    @staticmethod
    def least_squares(one, other):
        return sum([(one.data[i]-one.other[i])**2 for i in len(one.data)])