from __future__ import with_statement
import cgi
import pickle
import os

if not os.environ.get("APPLICATION_ID", False):
    import httplib
    import urllib
    import os.path
    
    def main_client(dir, recursive=False):
        if not os.path.exists(dir) or not os.path.isdir(dir):
            raise Exception("Not a directory.")
        files = os.listdir(dir)
        for file_name in files:
            if os.path.isdir(file_name):
                if recursive:
                    main_client(file_name)
                else:
                    continue
            with open(file_name) as file_obj:
                transfer(file_obj)
    
    def transfer(file_obj):
        # Generate a SpectrumTransfer object
        spectrum = SpectrumTransfer()
        spectrum.parse_file(file_obj)
        # Serialize into a string
        data = pickle.dumps(spectrum)
        
        # Set up HTTP connection
        host = "cooper-redhen.appspot.com"
        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}
        params = urllib.encode({"spectrum": data})
        conn = HTTPConnection("cooper-redhen.appspot.com", strict=True)
        conn.request("POST", "/upload", params, headers)
        
        # Process response
        response = conn.getresponse()
        if int(response.status) != 200:
            raise Exception("Upload error: %s" % response.read())
        return True

if os.environ.get("APPLICATION_ID", False):
    from google.appengine.ext import webapp
    from google.appengine.ext.webapp.util import run_wsgi_app
    import backend
    
    class Uploader(webapp.RequestHandler):
        def post(self):
            data = self.request.POST.get('file').file.read()
            obj = pickle.loads(data)
            spectrum = Spectrum(chemical_name=obj.chemical_name,
                                chemical_type=obj.chemical_type,
                                data=obj.data)
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

class SpectrumTransfer():
    """Store a spectrum, its related data, and any algorithms necessary
    to compare the spectrum to the DataStore."""
    
    ## The chemical name associated with the spectrum.
    chemical_name = ""
    
    ## The chemical type of the substance the spectrum represents.
    chemical_type = ""
    
    ## A list of integrated X,Y points for the spectrum's graph.
    data = []
    
    ## Parse a string of JCAMP file data and extract all needed data.
    # 
    # Search a JCAMP file for the chemical's name, type, and spectrum data.
    # Then integrate the X, Y data and store alGet a specific data label from the file.l variables in the object.
    # @warning Does not handle Windows-format line breaks.
    # 
    # @param file_obj File descriptor for the JCAMP file.
    def parse_file(self, file_obj):
        """Parse a string of JCAMP file data and extract all needed data."""
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
    
    ## Get a specific data label from the file.
    # @param name Name of the data label to retrieve
    # @return Value of the data label
    def get_field(self, name):
        """Get a specific data label from the file."""
        index = self.contents.index(name) + len(name) # means find where the field name ends 
        return self.contents[index:self.contents.index('\n', index)] #Does not handle Windows format

if __name__ == '__main__':
    if os.environ.get("APPLICATION_ID", False):
        application = webapp.WSGIApplication([
            ('/', MainHandler)
        ], debug=True)
        run_wsgi_app(application)
    else:
        main_client(os.getcwd())