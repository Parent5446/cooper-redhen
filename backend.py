'''This is a program for identifying spectra'''

import re #regex(regular expressions)
import pickle #datastorage(converts variables into string form)
import bisect #binary search of a list
import operator #fast functions for getting data from objects (used for key methods)
from google.appengine.ext import db #import database
from google.appengine.api import memcache #import memory cache

#Testing:
import time
from google.appengine.api import quota
import logging

#Spectrum database entries and voting data structures will be preloaded
def search(file):
    """Search for a spectrum based on a given file descriptor."""
    spectrum = Spectrum() # Load the user's spectrum into a Spectrum object.
    spectrum.parseFile(file)
    matcher = memcache.get(spectrum.type+'_matcher') # Get Matcher from cache.
    if matcher is None: matcher = Matcher.get_by_key_name(spectrum.type) # If not in cache, get from database.
    candidates = matcher.get(spectrum) # Find similar spectra
    for candidate in candidates: candidate.error = Matcher.bove(spectrum, candidate) # Do one-to-one on candidates.
    list.sort(candidates, key = operator.attrgetter('error'), reverse=True) # Sort by error
    #Then return the candidates, and let frontend do the rest
    return candidates

def add(file):
    """Add a new spectrum to the database from a given file descriptor."""
    spectrum = Spectrum() # Load the user's spectrum into a Spectrum object.
    spectrum.parseFile(file)
    matcher = memcache.get(spectrum.type+'_matcher') # Get Matcher from cache.
    if matcher is None: matcher = Matcher.get_by_key_name(spectrum.type) # If not in cache, get from database.
    if not matcher: matcher = Matcher(key_name=spectrum.type) # If not in database, make new one.
    spectrum.put() #Add to database
    matcher.add(spectrum) #Add to matcher 
    matcher.put() # Update matcher to database.
    memcache.add(spectrum.type+'_matcher', matcher) # Put into the cache for easy access.
    
class Spectrum(db.Model):
    """Store a spectrum, its related data, and any algorithms necessary
    to compare the spectrum to the DataStore."""
    # Variables to be stored in the Google DataStore.
    chemical_name = db.StringProperty()  # stores the name of the chemical
    chemical_type = db.StringProperty() # stores the type of the chemical
    data = db.ListProperty(float)  # stores the data of the chemical
    
    def parseFile(self, file):
        """Parse a string of JCAMP file data and extract all needed data."""
        self.contents = file.read() # reading the string 
        self.type = 'Infrared' # Later this will be variable
        x = float(self.get_field('##FIRSTX=')) # just gets the float after first x 
        deltaX = float(self.get_field('##DELTAX='))   # space between adjacent x values
        xFactor = float(self.get_field('##XFACTOR=')) # for our purposes it's 1, but if not use this instead
        yFactor = float(self.get_field('##YFACTOR=')) # some very small number, but if not use this instead
        self.xy = [] # list of (x,y) pairs
        for match in re.finditer(r'(\D)([\d.-]+)', self.contents[self.contents.index('##XYDATA=(X++(Y..Y))')+20:]): # match whatever comes before the number and the whole number
            if match.group(1) == '\n': x = float(match.group(2))*xFactor # if thing before the number is a new line then it's a x value 
            else: self.xy.append( (x, float(match.group(2))*yFactor) ); x += deltaX # otherwise it's a y value 
        if deltaX < 0: self.xy.reverse() #Keep in ascending order of x
        #Integrate self.xy numerically over a fixed range:
        range = (700.0, 3900.0) #Define range to integrate 
        self.data = [0.0 for i in xrange(1000)] # Intialize data to zero
        interval = (range[1]-range[0])/len(self.data) #Find the horizontal distance between each integral 
        start = 0
        while self.xy[start][0] < range[0]: start+=1 #Find index in self.xy where integrals start
        oldX, oldY = range[0], self.xy[start-1][1] + (self.xy[start][1]-self.xy[start-1][1])*(range[0]-self.xy[start][0])/(self.xy[start-1][0] - self.xy[start][0]) #x = start of range, y = linear interpolation of corresponding y
        for x,y in self.xy[start:]: #Iterate over self.xy from start
            newIndex, oldIndex = int((x-range[0])/interval), int((oldX-range[0])/interval) # finds the positions in the data array 
            if newIndex != oldIndex: #If we're starting a new integral
                boundary = newIndex*interval, (y-oldY)*(newIndex*interval-oldX)/(x-oldX) + oldY #Linear interpolation
                self.data[oldIndex] += (boundary[1]+oldY)*(boundary[0]-oldX)/2 #Add area
                if newIndex < len(self.data): # if data isn't filled 
                    self.data[newIndex] += (boundary[1]+y)*(x-boundary[0])/2 #Add area
            else: self.data[newIndex] += (y+oldY)*(x-oldX)/2 #Add area
            if x > range[1]: break #If finished, break
            oldX,oldY = x,y #Otherwise keep going
        self.chemical_type = 'Unknown' # We will find this later 
        self.chemical_name = self.get_field('##TITLE=') # assuming chemical name is in title field 
        # Reference: http://www.jcamp-dx.org/
        
    def get_field(self, name):
        index = self.contents.index(name) + len(name) # means find where the field name ends 
        return self.contents[index:self.contents.index('\n', index)] #Does not handle Windows format

class DictProperty(db.Property):
    data_type = dict #data_type is dict
    def get_value_for_datastore(self, model_instance):
        value = super(DictProperty, self).get_value_for_datastore(model_instance) #get string for database
        return db.Blob(pickle.dumps(value)) #convert into a string and stores it
    def make_value_from_datastore(self, value):
        if value is None: #if there is no value
            return dict() #returns an empty dict
        return pickle.loads(value) #gets a value from a string
    def default_value(self):
        if self.default is None: #if there is no default
            return dict() #returns empty dict
        else:
            return super(DictProperty, self).default_value().copy() #returns default value
    def validate(self, value):
        if not isinstance(value, dict): #if it is not a dict
            raise db.BadValueError('Property %s needs to be convertible to a dict instance (%s)' % (self.name, value)) #sends error report back to user
        return super(DictProperty, self).validate(value) #parent class validates it
    def empty(self, value):
        return value is None #whether or not its empty
        
class GenericListProperty(db.Property):
    data_type = list #data type is list
    def get_value_for_datastore(self, model_instance):
        value = super(GenericListProperty, self).get_value_for_datastore(model_instance) #get string from database
        return db.Blob(pickle.dumps(value))#convert into a string and stores it
    def make_value_from_datastore(self, value):
        if value is None: return [] #if there is no value it returns an empty dict
        return pickle.loads(value) #gets a value from a string
    def default_value(self):
        if self.default is None: return [] #if there is no default it returns an empty dict
        else: return super(GenericListProperty, self).default_value().copy() #returns default value
    def validate(self, value):
        if not isinstance(value, list): #if it is not a dict
            raise db.BadValueError('Property %s needs to be convertible to a list instance (%s)' % (self.name, value)) #sends error report back to user
        return super(GenericListProperty, self).validate(value) #parent class validates it
    def empty(self, value):
        return value is None #whether or not its empty

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