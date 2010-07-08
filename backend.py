import os.path, re, pickle
from google.appengine.ext import db
from google.appengine.api import memcache

#Spectrum database entries and voting data structures will be preloaded
def search(file):
    spectrum_type = 'Infrared'
    matcher = memcache.get(spectrum_type+'_matcher')
    if matcher is None: matcher = Matcher.get_by_key_name('__'+spectrum_type+'__')

    spectrum = Spectrum() # Load the user's spectrum into a Spectrum object.
    spectrum.parseFile(file)
    candidates = matcher.get(spectrum)
    candidates = [ (candidate, Matcher.bove(spectrum, candidate)) for candidate in candidates]
    candidates = sorted(candidates, key=lambda k: k[1])
    #Then return the candidates, and let frontend do the rest
    return "It's me, the backend! Let's do this!\n"

def add(file):
    spectrum = Spectrum() # Load the user's spectrum into a Spectrum object.
    spectrum.parseFile(file)
    spectrum_type = 'Infrared'
    matcher = memcache.get(spectrum_type+'_matcher')
    if matcher is None: matcher = Matcher.get_by_key_name(spectrum_type)
    if not matcher: matcher = Matcher(key_name='__'+spectrum_type+'__')
    spectrum.put() #Add to database
    matcher.add(spectrum) #Add to matcher
    matcher.put()
    memcache.add(spectrum_type+'_matcher', matcher)
    
class Spectrum(db.Model):
    """Store a spectrum, its related data, and any algorithms necessary
    to compare the spectrum to the DataStore."""
    # Variables to be stored in the Google DataStore.
    chemical_name = db.StringProperty()
    chemical_type = db.StringProperty()
    data = db.ListProperty(float)
    
    def parseFile(self, file): #Consider not using a constructor
        """Parse a string of JCAMP file data and extract all needed data."""
        contents = file.read()
        self.xy = [ float(match.group(1)) for match in re.finditer('[^\r\n]([d.-]+)', contents[contents.index('##XYDATA=(X++(Y..Y))')+20:]) ]
        self.data = [1.0, 2.0, 3.0]
        self.chemical_type = 'Unknown'
        self.chemical_name = self.get_field('##TITLE=', contents)
        # Reference: http://www.jcamp-dx.org/
        
    def get_field(self, name, data):
        index = data.index(name) + len(name)
        return data[index:data.index('\n', index)] #Does not handle Unix format

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
            raise db.BadValueError('Property %s needs to be convertible to a dict instance (%s)' % (self.name, value))
        return super(DictProperty, self).validate(value)
    
    def empty(self, value):
        return value is None


class Matcher(db.Model):
    """Store spectra data necessary for searching the database, then search the database
    for candidates that may represent a given spectrum."""
    
    # Variables to be stored in the Google Data Store
    flat_heavyside = DictProperty()
    ordered_heavyside = DictProperty()
    peak_table = DictProperty()
    high_low = DictProperty()
    chem_types = DictProperty()
    
    def add(self, spectrum):
        """Add new spectrum data to the various Matcher dictionaries. Find the heavyside
        index, peaks, and other indices and add them to the dictionaries."""
        # Get the spectrum's key, peaks, and other heuristic data.
        flatHeavysideKey = 21 # Calculate for real later later
        peaks = [1, 2] # Calculate for real later later
        # Add it to the dictionaries
        if flatHeavysideKey in self.flat_heavyside: self.flat_heavyside[flatHeavysideKey].add(spectrum.key())
        else: self.flat_heavyside[flatHeavysideKey] = set([spectrum.key()])
        for peak in peaks:
            self.peak_table[peak] = spectrum.key() #This will need to be sorted as a list later
    
    def get(self, spectrum):
        """Find spectra that may represent the given Spectrum object by sorting
        the database using different heuristics, having them vote, and returning only
        the spectra deemed similar to the given spectrum."""
        # Get the reference values
        flatHeavysideKey = 21 # Calculate for real later later
        peaks = [1, 2] # Calculate for real later later
        # Get the set of relevant spectra. The keys list should be a list of pairs with a spectrum and and a vote in each.
        keys = {}
        if flatHeavysideKey in self.flat_heavyside: 
            for key in self.flat_heavyside[flatHeavysideKey]:
                keys[key] = 10 #10 votes
        keys = sorted(keys.iteritems(), lambda k: k[1])
        keys = [k[0] for k in keys]
        return Spectrum.get(keys)
    
    @staticmethod
    def bove(a, b):
        return max([abs(a.data[i]-b.data[i]) for i in xrange(len(a.data))])
    
    @staticmethod
    def least_squares(a, b):
        return sum([(a.data[i]-a.b[i])**2 for i in xrange(len(a.data))])
