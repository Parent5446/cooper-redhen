import os.path, re
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
    matcher.put()
    
class Spectrum(db.Model):
    """Store a spectrum, its related data, and any algorithms necessary
    to compare the spectrum to the DataStore."""
    # Variables to be stored in the Google DataStore.
    chemical_name = db.StringProperty()
    chemical_type = db.StringProperty()
    data = db.ListProperty(float)
    
    def __init__(self, file):
        """Parse a string of JCAMP file data and extract all needed data."""
        contents = file.read()
        self.xy = [ float(match.group(1)) for match in re.finditer('[^\r\n]([d.-]+)', contents[contents.index('##XYDATA=(X++(Y..Y))')+20:]) ]
        self.chemical_type = 'Unknown'
        self.chemicalName = self.get_field('##TITLE=', contents)
        db.Model.__init__(self)
        # Reference: http://www.jcamp-dx.org/
        
    def get_field(self, name, data):
        index = data.index(name) + len(name)
        return data[index:data.index('\n')] #Does not handle Unix format
    
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
        db.Model.__init__(self)
        # Get the spectrum's key, peaks, and other heuristic data.
        heavyside = 21 # Fix this later
        peaks = [1, 2] # Fix this later
        # Add it to the dictionaries
        if heavyside in self.heavyside1: self.heavyside1[heavyside].add(spectrum.key())
        else: self.heavyside1[heavyside] = set([spectrum.key()])
        for peak in peaks:
            self.peak_table[peak].append(spectrum.key())
    
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