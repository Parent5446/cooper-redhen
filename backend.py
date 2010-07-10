import os.path, re, pickle, bisect
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
    for candidate in candidates: candidate.error = Matcher.bove(spectrum, candidate)
    candidates = sorted(candidates, key=lambda k: k.error)
    #Then return the candidates, and let frontend do the rest
    return candidates

def add(file):
    spectrum = Spectrum() # Load the user's spectrum into a Spectrum object.
    spectrum.parseFile(file)
    spectrum_type = 'Infrared'
    matcher = memcache.get(spectrum_type+'_matcher')
    if matcher is None: matcher = Matcher.get_by_key_name(spectrum_type)
    if not matcher: matcher = Matcher(key_name='__'+spectrum_type+'__')
    spectrum.put() #Add to database
    matcher.add(spectrum) #Add to matcher
    #raise Exception(str(list(matcher.flat_heavyside[21])[0]) + ' - ' + str(spectrum.key()))
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
        
class GenericListProperty(db.Property):
    data_type = list
    def get_value_for_datastore(self, model_instance):
        value = super(GenericListProperty, self).get_value_for_datastore(model_instance)
        return db.Blob(pickle.dumps(value))
    def make_value_from_datastore(self, value):
        if value is None: return []
        return pickle.loads(value)
    def default_value(self):
        if self.default is None: return []
        else: return super(GenericListProperty, self).default_value().copy()
    def validate(self, value):
        if not isinstance(value, list):
            raise db.BadValueError('Property %s needs to be convertible to a list instance (%s)' % (self.name, value))
        return super(GenericListProperty, self).validate(value)
    def empty(self, value):
        return value is None

class Matcher(db.Model):
    """Store spectra data necessary for searching the database, then search the database
    for candidates that may represent a given spectrum."""
    
    # Variables to be stored in the Google Data Store
    flat_heavyside = DictProperty()
    ordered_heavyside = DictProperty()
    peak_list = GenericListProperty()
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
            index = bisect.bisect( [item[1] for item in self.peak_list], peak) #Find place in teh sorted list
            self.peak_list.insert( index, (spectrum.key(),peak) ) #Insert in the right place
    
    def get(self, spectrum):
        """Find spectra that may represent the given Spectrum object by sorting
        the database using different heuristics, having them vote, and returning only
        the spectra deemed similar to the given spectrum."""
        # Get the reference values
        flatHeavysideKey = 21 # Calculate for real later later
        peak = 1 # Calculate for real later later
        # Get the set of relevant spectra. The keys list should be a list of pairs with a spectrum and and a vote in each.
        keys = {}
        #Add flat heavyside votes
        if flatHeavysideKey in self.flat_heavyside: 
            for key in self.flat_heavyside[flatHeavysideKey]:
                keys[key] = 10 #10 votes
                
        #Add peak list votes
        index = bisect.bisect( [item[1] for item in self.peak_list], peak)
        for offset in xrange(10):
            if index+offset-5 < 0 or index+offset-5 >= len(self.peak_list): continue
            if self.peak_list[index+offset-5][0] in keys:
                keys[self.peak_list[index+offset-5][0]] += abs(offset-5)
            else:
                keys[self.peak_list[index+offset-5][0]] = abs(offset-5)
        
        keys = sorted(keys.iteritems(), lambda k: k[1])
        keys = [k[0] for k in keys]
        return Spectrum.get(keys)
    
    @staticmethod
    def bove(a, b):
        return max([abs(a.data[i]-b.data[i]) for i in xrange(len(a.data))])
    
    @staticmethod
    def least_squares(a, b):
        return sum([(a.data[i]-a.b[i])**2 for i in xrange(len(a.data))])
