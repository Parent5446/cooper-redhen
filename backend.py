﻿import os.path, re, pickle
from google.appengine.ext import db
from google.appengine.api import memcache

#Spectrum database entries and voting data structures will be preloaded
def search(file):
    spectrum_type = 'Infrared'
    matcher = memcache.get(spectrum_type+'_matcher')
    if matcher is None: matcher = Matcher.get_by_key_name('__'+spectrum_type+'__')

    spectrum = Spectrum(file) # Load the user's spectrum into a Spectrum object.
    candidates = matcher.get(spectrum)
    candidates = [ (candidate, Matcher.bove(spectrum, candidate)) for candidate in candidates]
    candidates = sorted(candidates, key=lambda k: k[1])
    #Then return the candidates, and let frontend do the rest
    return "It's me, the backend! Let's do this!\n"

def add(file):
    spectrum = Spectrum(file)
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
    flat_heavyside = DictProperty()
    ordered_heavyside = DictProperty()
    peak_table = DictProperty()
    high_low = DictProperty()
    chem_types = DictProperty()
    
    def add(self, spectrum):
        """Add new spectrum data to the various Matcher dictionaries. Find the heavyside
        index, peaks, and other indices and add them to the dictionaries."""
        db.Model.__init__(self)
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
        # Get the set of relevant spectra. The keys list should be a zipped pair
        # of lists with a spectra and and a vote in each.
        keys = []
        for peak in peaks:
            keys.extend([(spec, 10) for spec in self.peak_table if peak - 5 < spec < peak + 5])
        keys.extend([(spec, 10) for spec in self.flat_heavyside if heavyside - 5 < spec < heavyside + 5])
        keys += [(spec, 10) for spec in high_low_dict[spectrum.highLowKey]]
        keys += [(spec, 10) for spec in chemical_types[spectrum.chemical_type]]
        # Add together all the votes.
        keys.sort()
        return Spectrum.get(keys)
    
    @staticmethod
    def bove(a, b):
        return max([abs(a.data[i]-b.data[i]) for i in len(a.data)])
    
    @staticmethod
    def least_squares(a, b):
        return sum([(a.data[i]-a.b[i])**2 for i in len(a.data)])
