'''
Provide functions for identifying a spectrum for an unknown substance using
various methods of database searching.
 
@organization: The Cooper Union for the Advancement of the Science and the Arts
@license: http://opensource.org/licenses/lgpl-3.0.html GNU Lesser General Public License v3.0
@copyright: Copyright (c) 2010, Cooper Union (Some Right Reserved)
'''

import re # re.finditer (regex searches)
import bisect # bisect.bisect (binary search of a list)
import operator # operator.attrgetter, operator.itemgetter

from google.appengine.ext import db # import database
from google.appengine.api import memcache, users # import memory cache and user

import common

def search(spectrum_data):
    '''
    Search for a spectrum based on a given file descriptor.
    
    Parse the given file and create a Spectrum object for it. Use the Matcher
    object to find candidates for similar spectra in the database and compare
    all candidates to the original spectrum using linear comparison algorithms.
    
    @param spectrum_data: String containing spectrum information
    @type  spectrum_data: C{str}
    @return: List of candidates similar to the input spectrum
    @rtype: C{list} of L{backend.Spectrum}
    @raise common.InputError: If a non-string is given as spectrum_data
    '''
    if not isinstance(spectrum_data, str) or isinstance(spectrum_data, unicode):
        raise common.InputError(spectrum_data, "Invalid spectrum data.")
    # Load the user's spectrum into a Spectrum object.
    spectrum = Spectrum()
    spectrum.parse_string(spectrum_data)
    # Check cache for the Matcher. If not, get from database.
    matcher = memcache.get(spectrum.spectrum_type + '_matcher')
    if matcher is None:
        matcher = Matcher.get_by_key_name(spectrum.spectrum_type)
    # Get the candidates for similar spectra.
    candidates = matcher.get(spectrum)
    # Do one-to-one on candidates and sort by error
    for candidate in candidates:
        candidate.error = Matcher.bove(spectrum, candidate)
    candidates.sort(key=operator.attrgetter('error'))
    # Let frontend do the rest
    return candidates

def compare(data1, data2, algorithm="bove"):
    '''
    Compare two spectra using the given algorithm.
    
    @param data1: String containing spectrum information
    @type  data1: C{str}
    @param data2: String containing spectrum information
    @type  data2: C{str}
    @return: Calculated error between the two spectra
    @rtype: C{int}
    @raise common.InputError: If a non-string is given as spectrum_data or if
    an invalid algorithm is given.
    '''
    # First check for invalid spectrum data (if they are not strings).
    if not isinstance(data1, str) or isinstance(spectrum_data, unicode):
        raise common.InputError(data1, "Invalid spectrum data.")
    if not isinstance(data2, str) or isinstance(spectrum_data, unicode):
        raise common.InputError(data2, "Invalid spectrum data.")
    # Load spectrum either as a database key or a file.
    if data1[0:3] == "db:":
        spectrum1 = Spectrum(data1[3:])
    else:                        
        spectrum1 = Spectrum()
        spectrum1.parse_string(data1)
    if data2[0:3] == "db:":
        spectrum2 = Spectrum(data2[3:])
    else:                        
        spectrum1 = Spectrum()
        spectrum1.parse_string(data2)
    # Start comparing
    if algorithm == "bove":
        return Matcher.bove(spectrum1, spectrum2)
    elif algorithm == "leastsquares":
        return Matcher.leastsquares(spectrum1, spectrum2)
    else:
        raise common.InputError(algo, "Invalid algorithm selection.")

def browse(target="public", limit=10, offset=0):
    '''
    Get a list of spectrum for browsing.
    
    @param target: Where to list spectrum from ("public" or "private")
    @type  target: C{str} or L{google.appengine.api.users.User}
    @param limit: Number of spectra to list
    @type  limit: C{int}
    @param offset: Where to start listing from (for pagination)
    @type  offset: C{int}
    @return: List of spectra
    @rtype: C{list} of L{backend.Spectrum}
    @raise common.InputError: If the user tries to retrieve too many spectra
    at once, the user is not logged in and tries to access a private database,
    or if an invalid database choice is given.
    
    '''
    if limit > 50:
        raise common.InputError(limit, "Number of spectra to retrieve is too big.")
    if target == "public":
        target = Project.get_or_insert("public")
    return Spectrum.gql("WHERE project = :1", target).fetch(limit, offset)

def add(spectrum_data, target="public"):
    '''
    Add a new spectrum to the database from a given file descriptor.
    
    Parse the given file and create a Spectrum object for it. If the Matcher
    object does not yet exist, create it. Then store the spectrum in the database
    and add any necessary sorting data to the Matcher object.
    
    @param spectrum_data: String containing spectrum information
    @type  spectrum_data: C{str}
    @param target: Where to store the spectrum
    @type  target: C{"public"} or L{google.appengine.api.users.User}
    @raise common.InputError: If a non-string is given as spectrum_data
    '''
    if isinstance(spectrum_data, file):
        spectrum_data = spectrum_data.read()
    elif not isinstance(spectrum_data, str) or isinstance(spectrum_data, unicode):
        raise common.InputError(spectrum_data, "Invalid spectrum data.")
    # If project does not exist, make a new one.
    target = Project.get_or_insert(target, owners=[users.get_current_user()])
    # Load the user's spectrum into a Spectrum object.
    spectrum = Spectrum()
    spectrum.parse_string(spectrum_data)
    if isinstance(target, Project):
        spectrum.project = target
    spectrum.put()
    if target == "public":
        # Check cache for the Matcher. If not, get from database. If it's
        # not there, make a new one.
        matcher = memcache.get(spectrum.spectrum_type + '_matcher')
        if matcher is None:
            matcher = Matcher.get_by_key_name(spectrum.spectrum_type)
        if not matcher:
            matcher = Matcher(key_name=spectrum.spectrum_type)
        matcher.add(spectrum)
        # Update the Matcher to the database and the cache.
        matcher.put()
        memcache.set(spectrum.spectrum_type + '_matcher', matcher)

def delete(spectrum_data, target="public"):
    '''
    Delete a spectrum from the database and Matcher.
    
    @param spectrum_data: String containing database keys
    @type  spectrum_data: C{str}
    @param target: Where to store the spectrum
    @type  target: C{"public"} or L{backend.Project} key
    @raise common.AuthError: If a user tries to delete a spectrum outside
    of his or her projects.
    '''
    # Load the spectrum into a Spectrum object.
    spectrum = Spectrum(spectrum_data)
    # Remove it from the Matcher if in a public database.
    if target == "public":
        # Check cache for the Matcher. If not, get from database. If it's
        # not there, make a new one.
        matcher = memcache.get(spectrum.spectrum_type + '_matcher')
        if matcher is None:
            matcher = Matcher.get_by_key_name(spectrum.spectrum_type)
        if not matcher:
            matcher = Matcher(key_name=spectrum.spectrum_type)
        matcher.delete(spectrum)
        # Update the Matcher to the database and the cache.
        matcher.put()
        memcache.set(spectrum.spectrum_type + '_matcher', matcher)
    else:
        # If private, check if it is indeed the user's database.
        if not spectrum.project == target:
            raise common.AuthError(target, "Spectrum does not belong to targeted project.")
    # Delete the spectrum to the database.
    spectrum.delete()

def auth(user, project, action):
    '''
    Check if user is allowed to do action on project.
    
    @param user: User trying to access the project
    @type  user: L{google.appengine.api.users.User}
    @param project: Project action is being done on
    @type  project: "public" or L{backend.Project}
    @param action: Action to be done. "View" means view the project. "Spectrum"
    means add, edit, or delete spectra in the project. "Project" means change
    the project itself and its permissions.
    @type  action: "view", "spectrum", "project"
    @return: Whether the user is allowed
    @rtype: C{bool}
    '''
    # The main project has separate permissions
    if project == "public":
        # Only app admins can change the public project.
        if action in ("spectrum", "project"):
            return users.is_current_user_admin()
        else:
            # Everybody can view the main project
            return True
    # Owners can do anything.
    if user in project.owners:
        return True
    # Uploaders can spectrum and view
    if user in project.collaborators and action in ("spectrum", "view"):
        return True
    # Viewers can only view
    if user in project.viewers and action == "view":
        return True
    # Otherwise, not allowed
    return False


class Project(db.Model):
    owners = db.ListProperty(users.User)
    '''The owners of the Project
    @type: L{google.appengine.ext.db.UserProperty}'''
    
    collaborators = db.ListProperty(users.User)
    '''People who can only change spectra in this project. They cannot change
    the project or permissions.
    @type: L{google.appengine.ext.db.UserProperty}'''
    
    viewers = db.ListProperty(users.User)
    '''People who can only view the data (cannot add, change, etc.)
    @type: L{google.appengine.ext.db.UserProperty}'''


class Spectrum(db.Model):
    '''
    Store a spectrum, its related data, and any algorithms necessary
    to compare the spectrum to the DataStore.
    '''
    
    chemical_name = db.StringProperty()
    '''The chemical name associated with the spectrum
    @type: C{str}'''
    
    chemical_type = db.StringProperty()
    '''The chemical type of the substance the spectrum represents
    @type: C{str}'''

    spectrum_type = db.StringProperty()
    '''The spectrum type of the substance the spectrum represents
    @type: C{str}'''

    xvalues = db.ListProperty(int, indexed=False)
    '''A list of X points for the spectrum's graph
    @type: C{list}'''
    
    yvalues = db.ListProperty(float, indexed=False)
    '''A list of integrated Y points for the spectrum's graph
    @type: C{list}'''
    
    project = db.ReferenceProperty(Project)
    '''The project this spectrum belongs to.
    @type: L{google.appengine.db.ReferenceProperty}'''
    
    notes = db.StringProperty()
    '''Notes on the spectrum if in a private database
    @type: C{str}'''
    
    def parse_string(self, contents):
        '''
        Parse a string of JCAMP file data and extract all needed data.
        
        Search a JCAMP file for the chemical's name, type, and spectrum data.
        Then integrate the X, Y data and store alGet a specific data label from
        the file.l variables in the object.
        
        @warning: Does not handle Windows-format line breaks.
        @param contents: String containing spectrum information
        @type  contents: C{unicode} or C{str}
        '''
        self.contents = contents
        self.spectrum_type = 'Infrared' # Later this will be variable
        x = float(self.get_field('##FIRSTX=')) # The first x-value
        delta_x = float(self.get_field('##DELTAX=')) # The Space between adjacent x values
        x_factor = float(self.get_field('##XFACTOR=')) # for our purposes it's 1, but if not use this instead
        y_factor = float(self.get_field('##YFACTOR=')) # some very small number, but if not use this instead
        xy = []
        # Process the XY data from JCAMP's (X++(Y..Y)) format.
        raw_xy = self.contents[self.contents.index('##XYDATA=(X++(Y..Y))') + 20:]
        pattern = re.compile(r'(\D+)([\d.-]+)')
        for match in re.finditer(pattern, raw_xy):
            if '\n' in match.group(1):
                # Number is the first on the line and is an x-value
                x = float(match.group(2)) * x_factor
            else:
                # Number is a relative y-value.
                xy.append((x, float(match.group(2)) * y_factor))
                x += delta_x
        # Keep the data in ascending order. It will be descending in the file
        # if our delta X is negative.
        if delta_x < 0:
            xy.reverse()
        # Integrate xy numerically over a fixed range.
        xvalue_range = (700.0, 3900.0)
        # Initialize the data and find the interval of integration.
        data = [0.0 for i in xrange(1000)]
        interval = (xvalue_range[1] - xvalue_range[0]) / len(data)
        # Find index in xy where integrals start
        start = bisect.bisect_left(xy, (xvalue_range[0], 0))
        # oldX = start of range, oldY = linear interpolation of corresponding y
        oldX, oldY = xvalue_range[0], (xy[start - 1][1] +
             (xy[start][1] - xy[start - 1][1]) * (xvalue_range[0] - xy[start][0]) /
             (xy[start - 1][0] - xy[start][0]))
        for x, y in xy[start:]: #Iterate over xy from start
            newIndex = int((x - xvalue_range[0]) / interval)
            oldIndex = int((oldX - xvalue_range[0]) / interval)
            if newIndex != oldIndex:
                # We're starting a new integral.
                boundary = newIndex * interval,\
                           ((y - oldY) * (newIndex * interval - oldX) /
                           (x - oldX) + oldY) #Linear interpolation
                data[oldIndex] += (boundary[1] + oldY) * (boundary[0] - oldX) / 2
                if newIndex < len(data): # if data isn't filled 
                    data[newIndex] += (boundary[1] + y) * (x - boundary[0]) / 2
            else:
                data[newIndex] += (y + oldY) * (x - oldX) / 2
            if x > xvalue_range[1]:
                break #If finished, break
            oldX, oldY = x, y #Otherwise keep going
        self.xvalues = range(int(xvalue_range[0]), int(xvalue_range[0]) + len(data))
        self.yvalues = data
        self.chemical_type = 'Unknown' # We will find this later
        # FIXME: Assumes chemical name is in TITLE label.
        self.chemical_name = self.get_field('##TITLE=')
        # Reference: http://www.jcamp-dx.org/
    
    def get_field(self, name):
        '''
        Get a specific data label from the file.
        
        @param name: Name of data label to retrieve
        @type  name: C{str}
        @return: Value of the data label
        @rtype: C{str}
        
        @warning: Does not support Windows-style line breaks.
        '''
        # Find where the field ends.
        # FIXME: Does not support Windows format.
        index = self.contents.index(name) + len(name)
        return self.contents[index:self.contents.index('\n', index)]
     
    def calculate_peaks(self, one=False):
        '''
        Calculate the peaks for a spectrum.
        
        @param one: Whether to get all the peaks or just the first one
        @type  one: C{bool}
        @return: Either a list of peaks or one peak, depending on the parameter
        @rtype: C{list} or C{float}
        '''
        data = zip(self.xvalues, self.yvalues)
        if one:
            return max(data, key=operator.itemgetter(1))[0]
        data = sorted(data, key=operator.itemgetter(1), reverse=True)
        peaks = []
        peaks = [x for x, y in data
                   if y >= data[0][1]*0.95
                   and not [peak for peak in peaks if abs(peak - x) < 1]]
        return peaks
    
    def calculate_heavyside(self):
        '''
        Calculate the heavyside index for a spectrum.
        
        @return: The heavyside index
        @rtype: C{int}
        '''
        data = zip(self.xvalues, self.yvalues)
        key, left_edge, width = 0, 0, len(data) # Initialize variables
        for bit in xrange(Matcher.FLAT_HEAVYSIDE_BITS):
            left = sum([i[1] for i in data[left_edge:left_edge + width / 2]])
            right = sum([i[1] for i in data[left_edge + width / 2:left_edge + width]])
            if left_edge + width == len(data):
                left_edge = 0
                width = width / 2 #Adjust boundaries
            else:
                left_edge += width #for next iteration
            key += (left < right) << (Matcher.FLAT_HEAVYSIDE_BITS - bit)
        return key


class Matcher(db.Model):
    '''
    Store spectra data necessary for searching the database, then search the
    database for candidates that may represent a given spectrum.
    '''
    
    FLAT_HEAVYSIDE_BITS = 8
    '''Number of bits in the heavyside index
    @type: C{int}'''
    
    flat_heavyside = common.DictProperty()
    '''@ivar: List of flat-heavyside indices
    @type: L{common.DictProperty}'''
    
    ordered_heavyside = common.DictProperty()
    '''@ivar: List of ordered-heavyside indices
    @type: L{common.DictProperty}'''
    
    peak_list = common.GenericListProperty()
    '''@ivar: List of x-values for peaks and their associated spectra
    @type: L{common.GenericListProperty}'''
    
    high_low = common.DictProperty()
    '''@ivar: List of high-low table indices
    @type: L{common.DictProperty}'''
    
    chem_types = common.DictProperty()
    '''@ivar: List of chemical types
    @type: L{common.DictProperty}'''
    
    def add(self, spectrum):
        '''
        Add a new spectrum to the Matcher.
        
        Add new spectrum data to the various Matcher data structures. Find the
        heavyside index, peaks, and other indices and add them to the data
        structures.
        
        @param spectrum: The spectrum to add
        @type  spectrum: L{backend.Spectrum}
        '''
        #Flat heavyside: hash table of heavyside keys
        key = spectrum.calculate_heavyside()
        if key in self.flat_heavyside:
            self.flat_heavyside[key].add(spectrum.key())
        else:
            self.flat_heavyside[key] = set([spectrum.key()])
        
        #peak_list - positions of highest peaks:
        for peak in spectrum.calculate_peaks():
            bisect.insort(self.peak_list, (peak, spectrum.key()))
    
    def delete(self, spectrum):
        '''
        Delete a spectrum to the Matcher.
        
        @param spectrum: The spectrum to add
        @type  spectrum: L{backend.Spectrum}
        '''
        # Remove it from the heavyside keys and peak lists.
        [key.discard(spectrum) for spectrum in self.flat_heavyside]
        [self.flat_heavyside.remove(peak) for peak in self.peak_list if x[1] == spectrum]
    
    def get(self, spectrum):
        '''
        Find spectra similar to the given one.
        
        Find spectra that may represent the given Spectrum object by sorting
        the database using different heuristics, having them vote, and 
        returning only the spectra deemed similar to the given spectrum.
        
        @param spectrum: The spectrum to search for
        @type  spectrum: L{backend.Spectrum}
        @return: List of similar spectra
        @rtype: C{list} of L{backend.Spectrum}
        '''
        
        # Get heavyside key and peaks.
        flatHeavysideKey = spectrum.calculate_heavyside()
        peak = spectrum.calculate_peaks(True)
        
        # Get the candidates in a hash table
        keys = {}
        # Give ten votes to each spectrum with the same heavyside key.
        if flatHeavysideKey in self.flat_heavyside:
            for key in self.flat_heavyside[flatHeavysideKey]:
                keys[key] = keys.get(key, 0) + 10
        
        # If a spectrum has a peak within five indices of our given spectrum's
        # peaks in either direction, give it votes depending on how close it is
        index = bisect.bisect(self.peak_list, peak)
        for offset in xrange(-5,5):
            if index + offset < 0 or index + offset >= len(self.peak_list):
                # If bisect gives us an index near the beginning or end of list
                continue
            # Give the spectrum (5 - offest) votes
            peak_index = self.peak_list[index+offset][1]
            keys[peak_index] = keys.get(peak_index, 0) + (5 - abs(offset))
        # Sort candidates by number of votes and return Spectrum objects.
        keys = sorted(keys.iteritems(), key=operator.itemgetter(1), reverse=True)
        return Spectrum.get([k[0] for k in keys])
    
    @staticmethod # Make a static method for faster execution
    def bove(a, b):
        '''
        Calculate the difference or error between two spectra using Bove's
        algorithm.
        
        @param a: Spectrum to compare
        @type  a: L{backend.Spectrum}
        @param b: Other Spectrum to compare
        @type  b: L{backend.Spectrum}
        @return: The difference or error between the spectra
        @rtype: C{int}
        @raise common.ServerError: If there are invalid spectra in the database
        '''
        length = min([len(a.yvalues), len(b.yvalues)])
        if length == 0 or a.yvalues is None or b.yvalues is None:
            raise common.ServerError("Invalid spectra in the database.")
        return max([abs(a.yvalues[i] - b.yvalues[i]) for i in xrange(length)])
    
    @staticmethod # Make a static method for faster execution
    def least_squares(a, b):
        '''
        Calculate the difference or error between two spectra using Bove's
        algorithm.
        
        @param a: Spectrum to compare
        @type  a: L{backend.Spectrum}
        @param b: Other Spectrum to compare
        @type  b: L{backend.Spectrum}
        @return: The difference or error between the spectra
        @rtype: C{int}
        @raise common.ServerError: If there are invalid spectra in the database
        '''
        length = min([len(a.yvalues), len(b.yvalues)])
        if length == 0 or a.yvalues is None or b.yvalues is None:
            raise common.ServerError("Invalid spectra in the database.")
        return sum([(a.yvalues[i] - a.yvalues[i])**2 for i in xrange(length)])
