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
import struct
import array
import StringIO

from google.appengine.ext import db # import database
from google.appengine.api import memcache, users # import memory cache and user

import common
    
def search(spectra_data, algorithm="bove"):
    '''
    Search for spectra in the database which are similar to the given spectra_data.
    Use fast heuristics first, then linear comparison algorithms.
    
    @param spectrum_data: String containing spectrum information
    @type  spectrum_data: C{str}
    @param algorithm: Algorithm to do one-to-one comparisons with
    @type  algorithm: "bove" or "leastsquares"
    @return: List of candidates similar to the input spectrum
    @rtype: C{list} of L{backend.Spectrum}
    @raise common.InputError: If a non-string is given as spectrum_data or if
    an invalid algorithm is given
    '''
    if not isinstance(spectra_data, list):
        spectra_data = [spectra_data]

    if algorithm == "bove":
        algorithm = bove
    elif algorithm == "leastsquares":
        algorithm = least_squares
    else:
        raise common.InputError(algorithm, "Invalid algorithm.")
    
    results = []
    for spectrum_data in spectra_data:
        # Load the user's spectrum into a Spectrum object.
        if spectrum_data[0:3] == "db:":
            spectrum = Spectrum.get(db.Key(spectrum_data[3:]))
            spectrum.error = 0 #This is the original - no error
            results.append(spectrum) #Add to results
            continue #Don't try to parse as a file
        else:
            spectrum = Spectrum()
            try:
                spectrum.parse_string(spectrum_data)
            except NameError:
                raise common.InputError(spectrum_data, "Invalid spectrum data.")
        # Do one-to-one on candidates and sort by error
        candidates = spectrum.find_similar()
        for candidate in candidates:
            candidate.error = algorithm(spectrum, candidate)
        candidates.sort(key=operator.attrgetter('error'))
        results.extend(candidates)
        
    # Let frontend do the rest
    return results

def compare(data_list, algorithm="bove"):
    '''
    Compare multiple spectra using the given algorithm.
    
    @param dataList: A list of spectra strings to compare
    @type  dataList: [C{str}]
    @return: Calculated error between the two spectra
    @rtype: C{int}
    @raise common.InputError: If a non-string is given as spectrum_data or if
    an invalid algorithm is given.
    '''
    # First check for invalid spectrum data (if they are not strings).
    spectra = []
    for spectrum_data in data_list:
        if not (isinstance(spectrum_data, str) or isinstance(spectrum_data, unicode)):
            raise common.ServerError("Backend was given invalid spectrum data.")
        if spectrum_data[0:3] == "db:":
            spectra.append(Spectrum.get(spectrum_data[3:]))
        else:
            spectrum = Spectrum()
            try:
                spectrum.parse_string(spectrum_data)
            except NameError:
                raise common.InputError(spectrum_data, "Invalid spectrum data.")
            spectra.append(spectrum)
    # Start comparing
    if algorithm == "bove":
       algorithm = bove
    elif algorithm == "leastsquares":
        algorithm = least_squares
    else:
        raise common.InputError(algo, "Invalid algorithm selection.")
    for spectrum in spectra:
            spectrum.error = algorithm(spectra[0], spectrum)

    return spectra
    
def browse(target="public", offset=0, guess=False, spectrum_type="infrared"):
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
    if guess: #If the user has guessed the first 4 chars
        spectra = memcache.get(spectrum_type + '_browse_' + guess[0:4])
        if spectra is None:
            query = "WHERE prefixes = :1 AND spectrum_type = :2"
            query = Spectrum.gql(query, guess, spectrum_type)
            spectra = [(str(spectrum.key()), spectrum.chemical_name)
                       for spectrum in query]
            memcache.set(spectrum_type + '_browse_' + guess[0:4], spectra)
        return spectra
    else: #Browse the whole project
        target = Project.get_or_insert(target, owners=[users.get_current_user()], name=target)
        return [(str(spectrum.key()), spectrum.chemical_name) for spectrum in Spectrum.get(target.spectra)]
        
def add(spectra_data, target="public", preprocessed=False):
    '''
    Parse the given files and add new spectra to the database.
    Also store the hueristic data needed for fast searching.
    
    @param spectrum_data: String containing spectrum information
    @type  spectrum_data: C{str}
    @param target: Where to store the spectrum
    @type  target: "public" or the db key for a project
    @param preprocessed: Whether spectrum_data is already integrated or not
    @type  preprocessed: C{bool}
    '''
    if not isinstance(spectra_data, list):
        spectra_data = [spectra_data]    
    
    project = Project.get_or_insert(target, owners=[users.get_current_user()], name=target)
    for spectrum_data in spectra_data:
        # If project does not exist, make a new one.
        # Load the user's spectrum into a Spectrum object.
        if not preprocessed:
            spectrum = Spectrum()
            try:
                spectrum.parse_string(spectrum_data)
            except NameError:
                raise common.InputError(spectrum_data, "Invalid spectrum data.")
        else:
            if urllib is None:
                import urllib
            data = eval(urllib.unquote(spectrum_data))
            spectrum = Spectrum(**data)
        spectrum.put()
        project.spectra.append(spectrum.key())
    project.put()

def delete(spectra_data, target="public"):
    '''
    Delete a spectrum from the database
    
    @param spectrum_data: String containing database keys
    @type  spectrum_data: C{str}
    @param target: Where to store the spectrum
    @type  target: C{"public"} or L{backend.Project} key
    @raise common.AuthError: If a user tries to delete a spectrum outside
    of his or her projects.
    '''
    if not isinstance(spectra_data, list):
        spectra_data = [spectra_data]    
    
    project = Project.get_or_insert(target, owners=[users.get_current_user()], name=target)
    for spectrum_data in spectra_data:
        # Load the spectrum into a Spectrum object.
        spectrum = Spectrum.get(spectrum_data)
        if target == "public": raise Exception('Delete is not yet supported')
        else:
            # If private, check if it is indeed the user's database.
            if not spectrum.project == target:
                raise common.AuthError(target, "Spectrum does not belong to targeted project.")
        project.spectra.remove(spectrum.key())
        spectrum.delete()

def update():
    '''
    Purge the heuristic data and completely regenerate it.
    This should only be used when fixing a corrupt database.
    '''
    # Clear all spectra from the project.
    project = Project.get_by_key_name("public")
    project.spectra = []
    memcache.flush_all()
    # Regenerate heuristics data.
    for s in GenericData.all(keys_only=True): db.delete(s)
    for spectrum in Spectrum.all():
        add_public(spectrum)
        project.spectra.append(spectrum.key())
    # Put the project back in database
    project.put()

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
    if isinstance(project, unicode):
        return True
    # The main project has separate permissions
    if project == "public":
        # Only app admins can change the public project.
        if action in ("spectrum", "project"):
            if users.is_current_user_admin():
                return True
            else:
                raise common.AuthError(user, "Need to be app admin.")
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
    if action == "project":
        need = "owner"
    elif action == "spectrum":
        need = "collaborator"
    else:
        need = "viewer"
    raise common.AuthError(user, "Need to be %s or higher." % need)
    return False
    
def bove(a, b):
    '''
    Calculate the difference or error between two spectra using Bove's
    algorithm.
    
    @param a: Spectrum to compare
    @type  a: L{backend.Spectrum}
    @param b: Other Spectrum to compare
    @type  b: L{backend.Spectrum}
    @return: The difference or error between the spectra
    @rtype: C{float}
    @raise common.ServerError: If there are invalid spectra in the database
    '''
    length = min([len(a.data), len(b.data)])
    if length == 0 or a.data is None or b.data is None:
        raise common.ServerError("Invalid spectra in the database.")
    return max([abs(a.data[i] - b.data[i]) for i in xrange(length)])

def least_squares(a, b):
    '''
    Calculate the difference or error between two spectra using Bove's
    algorithm.
    
    @param a: Spectrum to compare
    @type  a: L{backend.Spectrum}
    @param b: Other Spectrum to compare
    @type  b: L{backend.Spectrum}
    @return: The difference or error between the spectra
    @rtype: C{float}
    @raise common.ServerError: If there are invalid spectra in the database
    '''
    length = min([len(a.data), len(b.data)])
    if length == 0 or a.data is None or b.data is None:
        raise common.ServerError("Invalid spectra in the database.")
    return sum([(a.data[i] - a.data[i])**2 for i in xrange(length)])


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
    '''The spectrum type, eg infrared
    @type: C{str}'''
    
    peak = db.FloatProperty()
    '''The x location of the spectrum's highest peak
    @type: C{float}'''
    
    heavyside = db.IntegerProperty()
    '''The heavyside index for the spectrum.
    @type: C{float}'''
    
    prefixes = db.StringListProperty()
    '''Just the non-alphabetical prefix to the chemical_name.
    @type: C{str}'''
    
    FLAT_HEAVYSIDE_BITS = 8
    '''Number of bits in the heavyside index, should be a power of 2
    @type: C{int}'''
    
    data = common.ArrayProperty('H')
    '''A list of integrated y values for comparisons ('H' = unsigned short)
    @type: C{list}'''
    
    data_y_max = 65535
    
    notes = db.StringProperty(indexed=False)
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
        self.spectrum_type = 'infrared' # Later this will be variable
        
        '''
        The following block of code interprets GRAMS file types
        This block of code will only run if the GRAMS file is in old format or new, LSB format
        ***WHEN FILE EXTENSION SUPPORT IS ADDED IT SHOULD BE USED.  GRAMS FILES ARE .SPC.***
        Until then, this code block runs if and only if the file starts with "\0K" or "\0L"
        That's not the best way to do this, so it should be changed ASAP.  Fortunately, JCAMP files
        will never start with a null byte, and multi-file support hasn't been added, so it won't cause problems.
        This code block requires imports of StringIO, array, and struct
        '''
        f = StringIO.StringIO()
        f.write(contents)
        f.seek(0)
        ftflgs = f.read(1) #ftflgs == null means that the data is single-file, and is stored with evenly spaced x data
        fversn = f.read(1) #fversn determines if the file is MSB 1st, LSB 1st, or 'old-format' (L, K, M respectively)
        GRAMS = False #Is it a grams file?
        
        spectra_types = "General Spectra", "Gas Chromatogram", "Chromatogram", "HPLC", "FT-IR/FT-Raman", "NIR", "UV-VIS", "X-ray Diffraction", "Mass Spec", "NMR", "Raman Spectrum", "Fluorescence", "Atomic", "Chromatography Diode"
        if(ftflgs == '\0'):
            if(fversn == 'K'):
                GRAMS = True
                fexper = f.read(1)
                self.spectrum_type = spectra_types[fexper]
                #fexper tells the program what type of spectrum this is.
                #Below is a quote of the SPC.h header file defining fexper values.
                '''
                #define SPCGEN    0    /* General SPC (could be anything) */
                #define SPCGC    1    /* Gas Chromatogram */
                #define SPCCGM    2    /* General Chromatogram (same as SPCGEN with TCGRAM) */
                #define SPCHPLC 3    /* HPLC Chromatogram */
                #define SPCFTIR 4    /* FT-IR, FT-NIR, FT-Raman Spectrum or Igram (Can also be used for scanning IR.) */
                #define SPCNIR    5    /* NIR Spectrum (Usually multi-spectral data sets for calibration.) */
                #define SPCUV    7    /* UV-VIS Spectrum (Can be used for single scanning UV-VIS-NIR.) */
                #define SPCXRY    8    /* X-ray Diffraction Spectrum */
                #define SPCMS    9    /* Mass Spectrum  (Can be single, GC-MS, Continuum, Centroid or TOF.) */
                #define SPCNMR    10    /* NMR Spectrum or FID */
                #define SPCRMN    11    /* Raman Spectrum (Usually Diode Array, CCD, etc. use SPCFTIR for FT-Raman.) */
                #define SPCFLR    12    /* Fluorescence Spectrum */
                #define SPCATM    13    /* Atomic Spectrum */
                #define SPCDAD    14    /* Chromatography Diode Array Spectra */
                '''
                #Code executing here is for "LSB 1st" and "new format" files
                f.seek(1,1)
                (numpoints,) = struct.unpack('l',f.read(4))
                (firstx,) = struct.unpack('d',f.read(8))
                (lastx,) = struct.unpack('d',f.read(8))
                f.seek(544,0) #Skip the next 544 bytes, as they are the rest of the header
                a = array.array('f')
                a.fromstring(f.read(numpoints * 4))
                
            elif(fversn == 'L'):
                fexper = f.read(1)
                #Code executing here is for GRAMS files that are "MSB 1st" and "new format".
                #There are no MSB files to test, and I don't know what MSB means.
            else:
                pass #This code can be added back in once file extension support is added
                '''GRAMS = True
                #Code executing here is for GRAMS files that are in the "old format"
                #This code is UNTESTED
                self.spectrum_type = "Infrared" # Old format GRAMS files are always infrared
                f.seek(2,1)
                (numpoints,) = struct.unpack('f',f.read(4))
                (firstx,) = struct.unpack('f',f.read(4))
                (lastx,) = struct.unpack('f',f.read(4))
                f.seek(288,0) #Skip the next 288 bytes, as they are the rest of the header
                a = array.array('f')
                a.fromstring(f.read(numpoints * 4))'''
        else:
            pass
            #The GRAMS file is multi-file or something like that.
            #Until we add file-extension support, multi-file GRAMS will throw errors!!


        if GRAMS:
            delta_x = (lastx - firstx)/(numpoints - 1)
            x_factor = 1
            y_factor = 1
        else:
            # Get the spectrum type and other variables.
            self.spectrum_type = self.get_field("##DATA ?TYPE=")
            x = float(self.get_field('##FIRSTX='))
            delta_x = float(self.get_field('##DELTAX='))
            x_factor = float(self.get_field('##XFACTOR='))
            y_factor = float(self.get_field('##YFACTOR='))
        
        # Intuitively determine the spectrum type.
        if self.spectrum_type.upper().find("IR") >= 0 or \
           self.spectrum_type.upper().find("INFRARED") >= 0:
            self.spectrum_type = "infrared"
        elif self.spectrum_type.upper().find("RAMAN") >= 0:
            self.spectrum_type = "raman"

        xy = []
        if GRAMS:
            xy.extend([((i * deltax + firstx), a[i]) for i in xrange(0, numpoints - 1)])
        else:
            # Process the XY data from JCAMP's (X++(Y..Y)) format.
            regex = re.compile(r'(\D+)([\d.-]+)')
            for match in re.finditer(regex, self.contents[self.contents.index('##XYDATA=(X++(Y..Y))') + 20:]):
                if '\n' in match.group(1):
                    # Number is the first on the line and is an x-value
                    x = float(match.group(2)) * x_factor
                else:
                    # Number is a relative y-value.
                    xy.append((x, float(match.group(2)) * y_factor))
                    x += delta_x
        
        # Keep the points in ascending x order.
        if delta_x < 0:
            xy.reverse()
            
        # Integrate xy numerically over a fixed range.
        if self.spectrum_type == "infrared":
            x_range = (700.0, 3900.0)
        elif self.spectrum_type == "raman":
            x_range = (300.0, 2000.0)
        # Make a power of two number data points for use in heavyside.
        data = [0.0 for i in xrange(512)]
        interval = (x_range[1] - x_range[0]) / len(data)
        start = bisect.bisect_right(xy, (x_range[0], 0))
        # Get the start of the range (both X and Y values).
        old_x = x_range[0]
        old_y = (xy[start-1][1] + (xy[start-1][0]-old_x) *
                 (xy[start][1] - xy[start-1][1]) /
                 (xy[start-1][0] - xy[start][0]))
        # Start integrating.
        for x, y in xy[start:]:
            if x > x_range[1]:
                # We passed the range limit. We're done.
                break
            # Get the index in data for the past loop and this loop
            newIndex = int((x - x_range[0]) / interval)
            oldIndex = int((old_x - x_range[0]) / interval)
            if newIndex != oldIndex:
                # We're starting a new integral: find the boundary x and y.
                boundary_x = x_range[0] + newIndex * interval
                boundary_y = old_y + (y-old_y)*(boundary_x-old_x)/(x-old_x)
                # Finish the old integral then start the new one.
                data[oldIndex] += (boundary_x - old_x)*(boundary_y + old_y) / 2
                if newIndex < len(data):
                    data[newIndex] += (x-boundary_x) * (y+boundary_y) / 2
            else:
                # Continue the current integral
                data[newIndex] += (x-old_x)*(y+old_y) / 2
            old_x, old_y = x, y
        
        # Store all the variables
        this_max = max(data)
        self.data = array.array('H', [round((d/this_max)*Spectrum.data_y_max) for d in data])
        self.xy = xy
        self.peak = max(self.xy, key=operator.itemgetter(1))[0]
        self.heavyside = self.calculate_heavyside()
        self.chemical_type = 'Unknown' # We will find this later (maybe)
        # Determine the chemical name of the substance.
        if GRAMS:
            self.chemical_name = 'Unknown'
        else:
            # FIXME: Assumes chemical name is in TITLE label.
            match = re.search( '([^a-zA-Z]*)([a-zA-Z])(.*?)[ %,\+\-\d]*(.jdx)?$', self.get_field('##TITLE=') )
            self.chemical_name = match.group(1) + match.group(2).upper() + match.group(3)
            self.prefixes = [self.chemical_name.lower()[0:4],
                             "".join([match.group(2), match.group(3)]).lower()[0:4]]
        # Reference: http://www.jcamp-dx.org/
    
    def get_field(self, name):
        '''
        Get a specific data field from the file.
        
        @param name: Name of the field to retrieve (regex syntax allowed)
        @type  name: C{str}
        @return: Value of the field
        @rtype: C{str}
        '''
        match = re.search(name+'([^\\r\\n]+)', self.contents)
        if match is None: raise Exception(self.contents)
        return match.group(1)
    
    def find_similar(self, target="public"):
        '''
        Find spectra similar to the given one.
        
        Find spectra that may represent the given Spectrum object by sorting
        the database using different heuristics, having them vote, and 
        returning only the spectra deemed similar to the given spectrum.
        
        @return: List of similar spectra
        @rtype: C{list} of L{backend.Spectrum}
        '''
        project = Project.get_or_insert(target)
        # Get heavyside key and peaks.
        peaks = self.calculate_peaks()
        heavyside = self.calculate_heavyside()
        # Check memcached for the data.
        key = self.spectrum_type + '_heavyside_' + str(heavyside) #Get the heavyside key
        spectra = memcache.get(key)
        if spectra is None:
            # Data is not in memcached. Check database.
            spectra = set()
            data = Spectrum.gql("WHERE heavyside = :1", heavyside)
            spectra = set([(spectrum.peak, str(spectrum.key()))
                           for spectrum in data
                           if spectrum.key() in project.spectra])
            memcache.set(key, spectra)
        # Sort by smallest distance to peaks and return top 20.
        keys = sorted(spectra, key=lambda s: min([s[0] - peak for peak in peaks]))
        return Spectrum.get([k[1] for k in keys[:20]])
    
    def calculate_peaks(self):
        '''
        Find the x values of the highest peaks (those within 95% of the absolute highest)
        
        @return: A list of peaks
        @rtype: C{list}
        '''
        self.xy = sorted(self.xy, key=operator.itemgetter(1), reverse=True)
        peaks = []
        peaks = [x for x, y in self.xy
                   if y >= self.xy[0][1]*0.95
                   and not [peak for peak in peaks if abs(peak - x) < 1]]
        return peaks
    
    def calculate_heavyside(self):
        '''
        Calculate the heavyside index for a spectrum.
        
        @return: The heavyside index
        @rtype: C{int}
        '''
        key, left_edge, width = 0, 0, len(self.data) # Initialize variables

        for bit in xrange(self.FLAT_HEAVYSIDE_BITS):
            left = sum(self.data[left_edge:left_edge + width / 2])
            right = sum(self.data[left_edge + width / 2:left_edge + width])
            if left_edge + width == len(self.data):
                left_edge = 0
                width = width / 2 #Adjust boundaries
            else:
                left_edge += width #for next iteration
            key += (left < right) << (self.FLAT_HEAVYSIDE_BITS - bit)
        return key


class Project(db.Model):
    '''
    Store a user's spectrum project, where different users have
    different access levels and spectra are stored within the project.
    '''
    
    name = db.StringProperty()
    '''Name for the project. Does not need to be unique.
    @type: C{str}'''
    
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
    
    spectra = db.ListProperty(db.Key)
    '''Spectra included in this project.
    @type: L{backend.Spectrm}'''
