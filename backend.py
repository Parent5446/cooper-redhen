import os.path, re, pickle, bisect, operator
from google.appengine.ext import db
from google.appengine.api import memcache

#Testing:
import time
from google.appengine.api import quota
import logging

#Spectrum database entries and voting data structures will be preloaded
def search(file):
    spectrum_type = 'Infrared'
    matcher = memcache.get(spectrum_type+'_matcher')
    if matcher is None: matcher = Matcher.get_by_key_name(spectrum_type)
    spectrum = Spectrum() # Load the user's spectrum into a Spectrum object.
    spectrum.parseFile(file)
    candidates = matcher.get(spectrum)
    for candidate in candidates: candidate.error = Matcher.bove(spectrum, candidate)
    list.sort(candidates, key = operator.attrgetter('error'), reverse=True)
    #Then return the candidates, and let frontend do the rest
    return candidates

def add(file):
    spectrum = Spectrum() # Load the user's spectrum into a Spectrum object.
    spectrum.parseFile(file)
    spectrum_type = 'Infrared'
    matcher = memcache.get(spectrum_type+'_matcher')
    if matcher is None: matcher = Matcher.get_by_key_name(spectrum_type)
    if not matcher: matcher = Matcher(key_name=spectrum_type)
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
    
    def parseFile(self, file):
        """Parse a string of JCAMP file data and extract all needed data."""
        self.contents = file.read()
        x = float(self.get_field('##FIRSTX='))
        deltaX = float(self.get_field('##DELTAX='))
        xFactor = float(self.get_field('##XFACTOR='))
        yFactor = float(self.get_field('##YFACTOR='))
        self.xy = [] # list of (x,y) pairs
        for match in re.finditer(r'(\D)([\d.-]+)', self.contents[self.contents.index('##XYDATA=(X++(Y..Y))')+20:]):
            if match.group(1) == '\n': x = float(match.group(2))*xFactor
            else: self.xy.append( (x, float(match.group(2))*yFactor) ); x += deltaX
        if deltaX < 0: self.xy.reverse() #Keep in ascending order of x
        #Integrate self.xy numerically over a fixed range:
        range = (700.0, 3900.0) #Define range to integrate
        self.data = [0.0 for i in xrange(1000)] # Intialize data to zero
        interval = (range[1]-range[0])/len(self.data) #Find width of each integral
        start = 0
        while self.xy[start][0] < range[0]: start+=1 #Find index in self.xy where integrals start
        oldX, oldY = range[0], self.xy[start-1][1] + (self.xy[start][1]-self.xy[start-1][1])*(range[0]-self.xy[start][0])/(self.xy[start-1][0] - self.xy[start][0]) #x = start of range, y = linear interpolation of corresponding y
        for x,y in self.xy[start:]: #Iterate over self.xy from start
            newIndex, oldIndex = int((x-range[0])/interval), int((oldX-range[0])/interval)
            if newIndex != oldIndex: #If we're starting a new integral
                boundary = newIndex*interval, (y-oldY)*(newIndex*interval-oldX)/(x-oldX) + oldY #Linear interpolation
                self.data[oldIndex] += (boundary[1]+oldY)*(boundary[0]-oldX)/2 #Add area
                if newIndex < len(self.data):
                    self.data[newIndex] += (boundary[1]+y)*(x-boundary[0])/2 #Add area
            else: self.data[newIndex] += (y+oldY)*(x-oldX)/2 #Add area
            if x > range[1]: break #If finished, break
            oldX,oldY = x,y #Otherwise keep going
        self.chemical_type = 'Unknown'
        self.chemical_name = self.get_field('##TITLE=')
        # Reference: http://www.jcamp-dx.org/
        
    def get_field(self, name):
        index = self.contents.index(name) + len(name)
        return self.contents[index:self.contents.index('\n', index)] #Does not handle Unix format

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
        """Add new spectrum data to the various Matcher data structures. Find the heavyside
        index, peaks, and other indices and add them to the data structures."""
        # Get the spectrum's key, peaks, and other heuristic data:
        
        #Flat heavyside: hash table of heavyside keys
        stack = [(0,0,0,len(spectrum.data))] #List of (key, whichBit, leftEdge, width)
        MAX_BITS = 8
        while len(stack) > 0:
            key, whichBit, leftEdge, width = stack.pop()
            if whichBit == MAX_BITS: #We're done with this key, so add it to the table
                if key in self.flat_heavyside: self.flat_heavyside[key].add(spectrum.key())
                else: self.flat_heavyside[key] = set([spectrum.key()])
            else:
                left = sum(spectrum.data[leftEdge:leftEdge+width/2]) #Sum integrals
                right = sum(spectrum.data[leftEdge+width/2:leftEdge+width]) #on both sides
                if leftEdge+width == len(spectrum.data): leftEdge = 0; width = width/2 #Adjust boundaries
                else: leftEdge += width #for next iteration
                if abs(left-right) < left*0.03: #If too close to call add twice
                    stack.append( (key, whichBit+1, leftEdge, width) ) #Once, leave key unchanged
                    stack.append( (key+(1<<(MAX_BITS-whichBit)), whichBit+1, leftEdge, width) ) #and once change key
                else: stack.append( (key+((left<right)<<(MAX_BITS-whichBit)), whichBit+1, leftEdge, width) )
        raise Exception(self.flat_heavyside)
        
        #peak_list - positions of highest peaks:
        xy = sorted(spectrum.xy, key = operator.itemgetter(1), reverse = True)
        peaks = []
        for x,y in xy:
            if y < xy[0][1]*0.95: break
            add = True
            for peak in peaks:
                if abs(peak-x) < 1: add = False #Must be more than 1 cm-1 from other peaks
            if add: peaks.append(x)
        for peak in peaks:
            index = bisect.bisect( [item[1] for item in self.peak_list], peak) #Find place in the sorted list
            self.peak_list.insert( index, (spectrum.key(),peak) ) #Insert in the right place
    
    def get(self, spectrum):
        """Find spectra that may represent the given Spectrum object by sorting
        the database using different heuristics, having them vote, and returning only
        the spectra deemed similar to the given spectrum."""
        # Get the reference values
        flatHeavysideKey = 21 # Calculate for real later later
        peak = max(spectrum.xy, key=operator.itemgetter(1))[0] # Find x with highest y
        
        # Get the candidates in a hash table
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
                
        keys = sorted(keys.iteritems(), key = operator.itemgetter(1))
        return Spectrum.get([k[0] for k in keys])
    
    @staticmethod
    def bove(a, b):
        return max([abs(a.data[i]-b.data[i]) for i in xrange(len(a.data))])
    
    @staticmethod
    def least_squares(a, b):
        return sum([(a.data[i]-a.b[i])**2 for i in xrange(len(a.data))])
