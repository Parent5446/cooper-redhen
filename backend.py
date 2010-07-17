'''
Provide functions for identifying a spectrum for an unknown substance using
various methods of database searching.
 
@organization: The Cooper Union for the Advancement of the Science and the Arts
@license: http://opensource.org/licenses/lgpl-3.0.html GNU Lesser General Public License v3.0
@copyright: Copyright (c) 2010, Cooper Union (Some Right Reserved)
'''

import re # re.finditer (regex searches)
import pickle # pickle.loads, pickle.dumps (data serialization)
import bisect # bisect.bisect (binary search of a list)
import operator # operator.attrgetter, operator.itemgetter
from google.appengine.ext import db # import database
from google.appengine.api import memcache # import memory cache

# Testing:
import time
from google.appengine.api import quota
import logging

import common

def search(file_obj):
    """
    Search for a spectrum based on a given file descriptor.
    
    Parse the given file and create a Spectrum object for it. Use the Matcher
    object to find candidates for similar spectra in the database and compare
    all candidates to the original spectrum using linear comparison algorithms.
    
    @param file_obj: File descriptor containing spectrum information
    @type  file_obj: C{file} or L{google.appengine.ext.blobstore.BlobReader}
    
    @return: List of candidates similar to the input spectrum
    @rtype: C{list} of L{backend.Spectrum}
    """
    # Load the user's spectrum into a Spectrum object.
    spectrum = Spectrum()
    spectrum.parse_file(file_obj)
    # Check cache for the Matcher. If not, get from database.
    matcher = memcache.get(spectrum.type + '_matcher')
    if matcher is None:
        matcher = Matcher.get_by_key_name(spectrum.type)
    # Get the candidates for similar spectra.
    candidates = matcher.get(spectrum)
    # Do one-to-one on candidates and sort by error
    candidates = [Matcher.bove(spectrum, candidate) for candidate in candidates]
    list.sort(candidates, key=operator.attrgetter('error'))
    # Let frontend do the rest
    return candidates

def add(file_obj):
    """
    Add a new spectrum to the database from a given file descriptor.
    
    Parse the given file and create a Spectrum object for it. If the Matcher
    object does not yet exist, create it. Then store the spectrum in the database
    and add any necessary sorting data to the Matcher object.
    
    @param file_obj: File descriptor containing spectrum information
    @type  file_obj: C{file} or L{google.appengine.ext.blobstore.BlobReader}
    """
    # Load the user's spectrum into a Spectrum object.
    spectrum = Spectrum()
    spectrum.parse_file(file_obj)
    # Check cache for the Matcher. If not, get from database. If it's not there,
    # make a new one.
    matcher = memcache.get(spectrum.type + '_matcher')
    if matcher is None:
        matcher = Matcher.get_by_key_name(spectrum.type)
    if not matcher:
        matcher = Matcher(key_name=spectrum.type)
    # Add the spectrum to the database and Matcher.
    spectrum.put()
    matcher.add(spectrum)
    # Update the Matcher to the database and the cache.
    matcher.put()
    memcache.set(spectrum.type + '_matcher', matcher)


class Spectrum(db.Model):
    """
    Store a spectrum, its related data, and any algorithms necessary
    to compare the spectrum to the DataStore.
    """
    
    chemical_name = db.StringProperty()
    """The chemical name associated with the spectrum
    @type: C{str}"""
    
    chemical_type = db.StringProperty()
    """The chemical type of the substance the spectrum represents
    @type: C{str}"""
    
    data = db.ListProperty(float)
    """A list of integrated X,Y points for the spectrum's graph
    @type: C{list}"""
    
    def parse_file(self, file_obj):
        """
        Parse a string of JCAMP file data and extract all needed data.
        
        Search a JCAMP file for the chemical's name, type, and spectrum data.
        Then integrate the X, Y data and store alGet a specific data label from the file.l variables in the object.
        
        @warning: Does not handle Windows-format line breaks.
        @param file_obj: File descriptor containing spectrum information
        @type  file_obj: C{file} or L{google.appengine.ext.blobstore.BlobReader}
        """
        self.contents = file_obj.read()
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
        start = bisect.bisect_left(self.xy, (range[0], 0))
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
        """
        Get a specific data label from the file.
        
        @param name: Name of data label to retrieve
        @type  name: C{str}
        @return: Value of the data label
        @rtype: C{str}
        """
        index = self.contents.index(name) + len(name) # means find where the field name ends 
        return self.contents[index:self.contents.index('\n', index)] #Does not handle Windows format


class Matcher(db.Model):
    """
    Store spectra data necessary for searching the database, then search the database
    for candidates that may represent a given spectrum.
    """
    
    FLAT_HEAVYSIDE_BITS = 8
    """Number of bits in the heavyside index
    @type: C{int}"""
    
    flat_heavyside = common.DictProperty()
    """@ivar: List of flat-heavyside indices
    @type: L{common.DictProperty}"""
    
    ordered_heavyside = common.DictProperty()
    """@ivar: List of ordered-heavyside indices
    @type: L{common.DictProperty}"""
    
    peak_list = common.GenericListProperty()
    """@ivar: List of x-values for peaks and their associated spectra
    @type: L{common.GenericListProperty}"""
    
    high_low = common.DictProperty()
    """@ivar: List of high-low table indices
    @type: L{common.DictProperty}"""
    
    chem_types = common.DictProperty()
    """@ivar: List of chemical types
    @type: L{common.DictProperty}"""
    
    def add(self, spectrum):
        """
        Add a new spectrum to the Matcher.
        
        Add new spectrum data to the various Matcher data structures. Find the
        heavyside index, peaks, and other indices and add them to the data
        structures.
        
        @param spectrum: The spectrum to add
        @type  spectrum: L{backend.Spectrum}
        """
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
        peaks = [x for x, y in xy if y >= xy[0][1]*0.95 and not [peak for peak in peaks if abs(peak - x) < 1]]
        for peak in peaks:
            bisect.insort(self.peak_list, (peak, spectrum.key()))

    def get(self, spectrum):
        """
        Find spectra similar to the given one.
        
        Find spectra that may represent the given Spectrum object by sorting
        the database using different heuristics, having them vote, and returning only
        the spectra deemed similar to the given spectrum.
        
        @param spectrum: The spectrum to search for
        @type  spectrum: L{backend.Spectrum}
        @return: List of similar spectra
        @rtype: C{list} of L{backend.Spectrum}
        """
        
        # Get flat heayside key.
        flatHeavysideKey, leftEdge, width = 0, 0, len(spectrum.data) # Initialize variables
        for whichBit in xrange(Matcher.FLAT_HEAVYSIDE_BITS): # Count from zero to number of bits
            left = sum(spectrum.data[leftEdge:leftEdge + width / 2]) #Sum integrals
            right = sum(spectrum.data[leftEdge + width / 2:leftEdge + width]) #on both sides
            if leftEdge + width == len(spectrum.data):
                leftEdge = 0
                width = width / 2 #Adjust boundaries
            else:
                leftEdge += width #for next iteration
            flatHeavysideKey += (left < right) << (Matcher.FLAT_HEAVYSIDE_BITS - whichBit) # Adds on to the key
        # Get x position of highest peak.
        peak = max(spectrum.xy, key=operator.itemgetter(1))[0] # Find x with highest y
        
        # Get the candidates in a hash table
        keys = {}
        # Give ten votes to each spectrum with the same heavyside key.
        if flatHeavysideKey in self.flat_heavyside:
            for key in self.flat_heavyside[flatHeavysideKey]:
                keys[key] = keys.get(key) + 10
        
        # If a spectrum has a peak within five indices of our given spectrum's
        # peaks in either direction, give it votes depending on how close it is.
        index = bisect.bisect(self.peak_list, peak)
        for offset in xrange(-5,5):
            if index+offset < 0 or index+offset >= len(self.peak_list):
                # If bisect gives us an index near the beginning or end of list.
                continue
            # Give the spectrum (5 - offest) votes
            index = self.peak_list[index+offset][1]
            keys[index] = keys.get(index, 0) + (5 - abs(offset))
        # Sort candidates by number of votes and return Spectrum objects.
        keys = sorted(keys.iteritems(), key=operator.itemgetter(1))
        return Spectrum.get([k[0] for k in keys])
    
    def bove(a, b):
        """
        Calculate the difference or error between two spectra using Bove's
        algorithm.
        
        @param a: Spectrum to compare
        @type  a: L{backend.Spectrum}
        @param b: Other Spectrum to compare
        @type  b: L{backend.Spectrum}
        @return: The difference or error between the spectra
        @rtype: C{int}
        """
        return max([abs(a.data[i]-b.data[i]) for i in xrange(len(a.data))]) # Do Bove's algorithm
    
    @staticmethod # Make a static method for faster execution
    def least_squares(a, b):
        """
        Calculate the difference or error between two spectra using Bove's
        algorithm.
        
        @param a: Spectrum to compare
        @type  a: L{backend.Spectrum}
        @param b: Other Spectrum to compare
        @type  b: L{backend.Spectrum}
        @return: The difference or error between the spectra
        @rtype: C{int}
        """
        return sum([(a.data[i]-a.b[i])**2 for i in xrange(len(a.data))]) # Compare to spectra with least squares
