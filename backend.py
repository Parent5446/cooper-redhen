'''This is a program for identifying spectra'''

import re # re.finditer (regex searches)
import pickle # pickle.loads, pickle.dumps (data serialization)
import bisect # bisect.bisect (binary search of a list)
import operator # operator.attrgetter, operator.itemgetter
from google.appengine.ext import db # import database
from google.appengine.api import memcache # import memory cache

#Testing:
import time
from google.appengine.api import quota
import logging

#Spectrum database entries and voting data structures will be preloaded
def search(file):
    """Search for a spectrum based on a given file descriptor."""
    # Load the user's spectrum into a Spectrum object.
    spectrum = Spectrum()
    spectrum.parseFile(file)
    # Check cache for the Matcher. If not, get from database.
    matcher = memcache.get(spectrum.type+'_matcher')
    if matcher is None:
        matcher = Matcher.get_by_key_name(spectrum.type)
    # Get the candidates for similar spectra.
    candidates = matcher.get(spectrum)
    # Do one-to-one on candidates and sort by error.
    for candidate in candidates:
        candidate.error = Matcher.bove(spectrum, candidate)
    list.sort(candidates, key=operator.attrgetter('error'), reverse=True)
    # Let frontend do the rest
    return candidates

def add(file):
    """Add a new spectrum to the database from a given file descriptor."""
    # Load the user's spectrum into a Spectrum object.
    spectrum = Spectrum()
    spectrum.parseFile(file)
    # Check cache for the Matcher. If not, get from database. If it's not there,
    # make a new one.
    matcher = memcache.get(spectrum.type+'_matcher')
    if matcher is None:
        matcher = Matcher.get_by_key_name(spectrum.type)
    if not matcher:
        matcher = Matcher(key_name=spectrum.type)
    # Add the spectrum to the database and Matcher.
    spectrum.put()
    matcher.add(spectrum)
    # Update the Matcher to the database and the cache.
    matcher.put()
    memcache.add(spectrum.type+'_matcher', matcher)
    
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
        self.type = 'Infrared' # Later this will be variable
        x = float(self.get_field('##FIRSTX=')) # The first x-value
        deltaX = float(self.get_field('##DELTAX=')) # The Space between adjacent x values
        xFactor = float(self.get_field('##XFACTOR=')) # for our purposes it's 1, but if not use this instead
        yFactor = float(self.get_field('##YFACTOR=')) # some very small number, but if not use this instead
        self.xy = []
        # Process the XY data from JCAMP's (X++(Y..Y)) format.
        raw_xy = self.contents[self.contents.index('##XYDATA=(X++(Y..Y))') + 20:]
        for match in re.finditer(r'(\D)([\d.-]+)', raw_xy):
            if match.group(1) == '\n':
                # Number is the first on the line and is an x-value
                x = float(match.group(2)) * xFactor
            else:
                # Number is a relative y-value.
                self.xy.append((x, float(match.group(2))*yFactor))
                x += deltaX
        # Keep the data in ascending order. It will be descending in the file
        # if our delta X is negative.
        if deltaX < 0:
            self.xy.reverse()
        # Integrate self.xy numerically over a fixed range.
        range = (700.0, 3900.0)
        # Initialize the data and find the interval of integration.
        self.data = [0.0 for i in xrange(1000)]
        interval = (range[1] - range[0]) / len(self.data)
        # Find index in self.xy where integrals start
        start = 0
        while self.xy[start][0] < range[0]:
            start+=1
        # oldX = start of range, oldY = linear interpolation of corresponding y
        xy = self.xy
        oldX, oldY = range[0], (self.xy[start - 1][1] +
             (xy[start][1] - xy[start - 1][1]) * (range[0] - xy[start][0]) /
             (xy[start - 1][0] - xy[start][0]))
        for x, y in self.xy[start:]: #Iterate over self.xy from start
            newIndex = int((x - range[0]) / interval)
            oldIndex = int((oldX - range[0]) / interval)
            if newIndex != oldIndex:
                # We're starting a new integral.
                boundary = newIndex * interval,\
                           ((y - oldY) * (newIndex * interval - oldX) /
                           (x - oldX) + oldY) #Linear interpolation
                self.data[oldIndex] += (boundary[1] + oldY) * (boundary[0] - oldX) / 2 #Add area
                if newIndex < len(self.data): # if data isn't filled 
                    self.data[newIndex] += (boundary[1] + y) * (x - boundary[0]) / 2 #Add area
            else:
                self.data[newIndex] += (y + oldY) * (x - oldX) / 2 #Add area
            if x > range[1]:
                break #If finished, break
            oldX, oldY = x, y #Otherwise keep going
        self.chemical_type = 'Unknown' # We will find this later
        # FIXME: Assumes chemical name is in TITLE label.
        self.chemical_name = self.get_field('##TITLE=')
        # Reference: http://www.jcamp-dx.org/
        
    def get_field(self, name):
        """Get a specific data label from the file."""
        index = self.contents.index(name) + len(name) # means find where the field name ends 
        return self.contents[index:self.contents.index('\n', index)] #Does not handle Windows format

class DictProperty(db.Property):
    """Store a dictionary object in the Google Data Store."""
    
    data_type = dict
    
    def get_value_for_datastore(self, model_instance):
        """Use pickle to serialize a dictionary for database storage."""
        value = super(DictProperty, self).get_value_for_datastore(model_instance)
        return db.Blob(pickle.dumps(value))
    
    def make_value_from_datastore(self, value):
        """Use pickle to deserialize a dictionary from the database."""
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
        """Check if the value is actually a dictionary."""
        if not isinstance(value, dict):
            raise db.BadValueError('Property %s needs to be convertible to a dict instance (%s)' % (self.name, value))
        # Have db.Property validate it as well.
        return super(DictProperty, self).validate(value)
    
    def empty(self, value):
        """Check if the value is empty."""
        return value is None
        
class GenericListProperty(db.Property):
    """Store a list object in the Google Data Store."""
    
    data_type = list
    
    def get_value_for_datastore(self, model_instance):
        """Use pickle to serialize a list for database storage."""
        value = super(GenericListProperty, self).get_value_for_datastore(model_instance)
        return db.Blob(pickle.dumps(value))
    
    def make_value_from_datastore(self, value):
        """Use pickle to deserialize a list from the database."""
        if value is None:
            # Make a new list if it does not exist.
            return []
        return pickle.loads(value)
    
    def default_value(self):
        """Get the default value for the property."""
        if self.default is None:
            return []
        else:
            return super(GenericListProperty, self).default_value().copy()
    
    def validate(self, value):
        """Check if the value is actually a list."""
        if not isinstance(value, list):
            raise db.BadValueError('Property %s needs to be convertible to a list instance (%s)' % (self.name, value))
        # Have db.Property validate it as well.
        return super(GenericListProperty, self).validate(value)
    
    def empty(self, value):
        """Check if the value is empty."""
        return value is None

class Matcher(db.Model):
    """Store spectra data necessary for searching the database, then search the database
    for candidates that may represent a given spectrum."""
    
    FLAT_HEAVYSIDE_BITS = 8 #number of bits in the heavyside index
    
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
        while len(stack) > 0: #keep going while there is stuff on the stack
            key, whichBit, leftEdge, width = stack.pop() #stack holds key, whichBit, leftEdge, width
            if whichBit == Matcher.FLAT_HEAVYSIDE_BITS: #We're done with this key, so add it to the table
                if key in self.flat_heavyside: self.flat_heavyside[key].add(spectrum.key()) #add it to table
                else: self.flat_heavyside[key] = set([spectrum.key()]) #add it to table
            else:
                left = sum(spectrum.data[leftEdge:leftEdge+width/2]) #Sum integrals
                right = sum(spectrum.data[leftEdge+width/2:leftEdge+width]) #on both sides
                if leftEdge+width == len(spectrum.data): leftEdge = 0; width = width/2 #Adjust boundaries
                else: leftEdge += width #for next iteration
                if abs(left-right) < left*0.03: #If too close to call add twice
                    stack.append( (key, whichBit+1, leftEdge, width) ) #Once, leave key unchanged
                    stack.append( (key+(1<<(Matcher.FLAT_HEAVYSIDE_BITS-whichBit)), whichBit+1, leftEdge, width) ) #and once change key
                else: stack.append( (key+((left<right)<<(Matcher.FLAT_HEAVYSIDE_BITS-whichBit)), whichBit+1, leftEdge, width) ) #if its easy to tell which side is heavier
        
        #peak_list - positions of highest peaks:
        xy = sorted(spectrum.xy, key = operator.itemgetter(1), reverse = True) #sort xy data by y value
        peaks = [] #make peaks empty list
        for x,y in xy: #go through all the points in xy
            if y < xy[0][1]*0.95: break #if y is less than 95% of the previous peak, stop
            add = True #add starts as true
            for peak in peaks: 
                if abs(peak-x) < 1: add = False #Must be more than 1 cm-1 from other peaks
            if add: peaks.append(x) #add peak to peaks
        for peak in peaks:
            index = bisect.bisect( [item[1] for item in self.peak_list], peak) #Find place in the sorted list
            self.peak_list.insert( index, (spectrum.key(),peak) ) #Insert in the right place
    
    def get(self, spectrum):
        """Find spectra that may represent the given Spectrum object by sorting
        the database using different heuristics, having them vote, and returning only
        the spectra deemed similar to the given spectrum."""
        # Get the reference values
        
        #Get flat heayside key:
        flatHeavysideKey, leftEdge, width = 0, 0, len(spectrum.data) # Initialize variables
        for whichBit in xrange(Matcher.FLAT_HEAVYSIDE_BITS): # Count from zero to number of bits
            left = sum(spectrum.data[leftEdge:leftEdge+width/2]) #Sum integrals
            right = sum(spectrum.data[leftEdge+width/2:leftEdge+width]) #on both sides
            if leftEdge+width == len(spectrum.data): leftEdge = 0; width = width/2 #Adjust boundaries
            else: leftEdge += width #for next iteration
            flatHeavysideKey += (left<right)<<(Matcher.FLAT_HEAVYSIDE_BITS-whichBit) # Adds on to the key
        #Get x position of highest peak:
        peak = max(spectrum.xy, key=operator.itemgetter(1))[0] # Find x with highest y
        
        # Get the candidates in a hash table
        keys = {}
        #Add flat heavyside votes
        if flatHeavysideKey in self.flat_heavyside: # if the key is in the pre-determined dictionary
            for key in self.flat_heavyside[flatHeavysideKey]: # for every spectrum with that key
                keys[key] = 10 #10 votes
                
        #Add peak list votes
        index = bisect.bisect( [item[1] for item in self.peak_list], peak) # Find nearest location for item[1] in peak_list
        for offset in xrange(10): # From one to ten
            if index+offset-5 < 0 or index+offset-5 >= len(self.peak_list): continue # If bisect gives us an index too near the beginning or end of list
            if self.peak_list[index+offset-5][0] in keys: # if the spectrum is already in the list of candidtes
                keys[self.peak_list[index+offset-5][0]] += abs(offset-5) # Add offset-5 votes
            else:
                keys[self.peak_list[index+offset-5][0]] = abs(offset-5) # Set it to offset-5 votes
                
        keys = sorted(keys.iteritems(), key = operator.itemgetter(1)) # Sort by number of votes
        return Spectrum.get([k[0] for k in keys]) # Return Spectrum objects for each one.
    
    @staticmethod # Make a static method for faster execution
    def bove(a, b):
        return max([abs(a.data[i]-b.data[i]) for i in xrange(len(a.data))]) # Do Bove's algorithm
    
    @staticmethod # Make a static method for faster execution
    def least_squares(a, b):
        return sum([(a.data[i]-a.b[i])**2 for i in xrange(len(a.data))]) # Compare to spectra with least squares
