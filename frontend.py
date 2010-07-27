"""
Take a POST request with JSON data and process it. If it contains a spectrum
file, send it to the back end to search the database.

All request must be POST requests. Any GET requests will just print these
instructions, and all others will be ignored. The POST variables below
may be passed. If uploading files, make sure to set enctype to
multipart/form-data, or they will not be processed properly.

General Options:
 - action (required):
     - "compare" - Compare two targets, either from file upload or database.
     - "add" - Add a spectrum to a project or the public database.
     - "delete" - Add a spectrum to a project or the public database.
     - "update" - Clear all heuristic data and rebuild the Matcher (admin-only).
     - "projects" - List all projects the user can access.
     - "data" - Get the X,Y data for a spectrum graph. NOTE: This gives a list
       with the first x value, delta x, and then the y values.
 - spectrum (required): The spectrum (either file or database key) to do the
   action on. Depending on the action, multiple spectra can be uploaded here.
 - target (optional, defaults to "public"):
    - When action is "compare": Can be either "public" to search the spectrum
      against the public database or it can be another file upload if comparing
      two spectra against each other.
    - When action is "browse": Can be either "public" for browsing the public
      library or a database key referring to the project being browsed.
 - output (optional, defaults to "pickle"): Can be "xml", "json", "python", or
   "pickle" depending on what output format you want.

Browsing Options:
 - limit: How many spectra to get when browsing (maximum is 50).
 - offset: Where to start listing spectra from (used for pagination).
 - type (used for search suggestions): What type of spectrum (infrared or raman)
 - guess (used only search suggestions): What the user has typed already and
   what we are giving suggestions for.

Comparing Options:
 - algorithm (defaults to "bove"): Which linear algorithm to compare spectra with

Adding Options:
 - raw (defaults to False): Whether the uploaded spectrum is in a standard JCAMP
   or SPC file format, or if it has been pre-processed and integrated. This is
   used primarily for bulk uploading spectra.

@organization: The Cooper Union for the Advancement of the Science and the Arts
@license: http://opensource.org/licenses/lgpl-3.0.html GNU Lesser General Public License v3.0
@copyright: Copyright (c) 2010, Cooper Union (Some Right Reserved)
"""
from google.appengine.api import users, memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.util import run_wsgi_app

import common
import backend

class ApiHandler(webapp.RequestHandler):
    """Handle any API requests and return a JSON response."""
    
    def get(self):
        """
        Handle a GET request to the API. Print instructions on how to use
        the API.
        """
        self.response.out.write("""<pre>
RedHen API v0.2

All request must be POST requests. Any GET requests will just print these
instructions, and all others will be ignored. The POST variables below
may be passed. If uploading files, make sure to set enctype to
multipart/form-data, or they will not be processed properly.

General Options:
 - action (required):
     - "compare" - Compare two targets, either from file upload or database.
     - "add" - Add a spectrum to a project or the public database.
     - "delete" - Add a spectrum to a project or the public database.
     - "update" - Clear all heuristic data and rebuild the Matcher (admin-only).
     - "projects" - List all projects the user can access.
     - "data" - Get the X,Y data for a spectrum graph. NOTE: This gives a list
       with the first x value, delta x, and then the y values.
 - spectrum (required for some actions): The spectrum (either file or database
   key) to do the action on. Depending on the action, multiple spectra can be
   uploaded here.
 - target (optional, defaults to "public"):
    - When action is "compare": Can be either "public" to search the spectrum
      against the public database or it can be another file upload if comparing
      two spectra against each other.
    - When action is "browse": Can be either "public" for browsing the public
      library or a database key referring to the project being browsed.
 - output (optional, defaults to "pickle"): Can be "xml", "json", "python", or
   "pickle" depending on what output format you want.

Browsing Options:
 - limit: How many spectra to get when browsing (maximum is 50).
 - offset: Where to start listing spectra from (used for pagination).
 - type (used for search suggestions): What type of spectrum (infrared or raman)
 - guess (used only search suggestions): What the user has typed already and
   what we are giving suggestions for.

Comparing Options:
 - algorithm (defaults to "bove"): Which linear algorithm to compare spectra with

Adding Options:
 - raw (defaults to False): Whether the uploaded spectrum is in a standard JCAMP
   or SPC file format, or if it has been pre-processed and integrated. This is
   used primarily for bulk uploading spectra.
        </pre>""")
    
    def post(self):
        """
        Handle a POST request to the API.
        
        Take a list of actions from a POST request, and do the appropriate
        action. See the documentation for this module for more information.
        
        @raise common.InputError: If no search targets are given in the target
        POST variable or if an invalid action is given.
        """
        action = self.request.get("action")
        target = self.request.get("target", "public")
        spectra = self.request.get_all("spectrum") #Some of these will be in session data
        limit = self.request.get("limit", 10)
        offset = self.request.get("offset", 0)
        algorithm = self.request.get("algorithm", "bove")
        guess = self.request.get("guess")
        type = self.request.get("type")
        raw = self.request.get("raw", False)
        session = Session.get_or_insert(self.request.get("session")) #Get (or create) the session
        user = users.get_current_user()
        response = []
        
        # If not operating on the main project, try getting the private one.
        # But abort if target is not supposed to be a project.
        if target and target != "public":
            target = backend.Project.get(target)
            if target is None:
                raise common.InputError(targets, "Invalid project ID.")
        # Start doing the request
        if action == "compare" and target == "public":
            # Search the database for something.
            for spectrum in spectra:
                # User wants to commit a new search with a file upload.
                result = backend.search(spectrum)
                # Extract relevant information and add to the response.
                info = [(str(i.key()), i.chemical_name,
                         i.chemical_type, i.error) for i in result]
                response.append(info)
        elif action == "compare":
            # Compare two pre-uploaded spectra.
            response.append(backend.compare(spectra[0], target, algorithm))
        elif action == "browse":
            # Get a list of spectra from the database for browsing
            if not backend.auth(user, target, "view"):
                raise common.AuthError(user, "Need to be viewer or higher.")
            # Return the database key, name, and chemical type.
            results = [(str(spectrum.key()), spectrum.chemical_name,
                        spectrum.chemical_type)
                       for spectrum in backend.browse(target, limit, offset, guess, type)]
            response.extend(results)
        elif action == "add":
            # Add a new spectrum to the database. Supports multiple spectra.
            if not backend.auth(user, target, "spectrum"):
                raise common.AuthError(user, "Need to be collaborator or higher.")
            for spectrum_data in spectra:
                backend.add(spectrum_data, target, raw)
        elif action == "delete":
            # Delete a spectrum from the database.
            if not backend.auth(user, target, "spectrum"):
                raise common.AuthError(user, "Need to be collaborator or higher.")
            for spectrum_data in spectra:
                backend.delete(spectrum_data, target)
        elif action == "update":
            if not backend.auth(user, "public", "spectrum"):
                raise common.AuthError(user, "Need to be collaborator or higher.")
            backend.update()
        elif action == "projects":
            query = "WHERE :1 IN owners OR :1 IN collaborators OR :1 in viewers"
            response.extend([(proj.key(), proj.name) for proj in Project.gql(query, user)])
        elif action == "data":
            for spectrum in spectra:
                spectrum = backend.Spectrum.get(spectrum)
                data = [spectrum.xvalues[0], spectrum.xvalues[1] - spectrum.xvalues[0]]
                data.extend(spectrum.yvalues)
                response.append(data)
        else:
            # Invalid action. Raise an error.
            raise common.InputError(action, "Invalid API action.")
        # Pass it on to self.output for processing.
        self.output(response)
    
    def output(self, response):
        """
        Take a response from the script and process it for returning to the
        user. Output formats include a serialized pickle object, JSON, XML,
        or Python (simply running str() on the response.
        
        @param response: Server response to encode
        @type  response: Mixed
        @raise common.InputError: If an invalid output format is given.
        """
        format = self.request.get("output", "json")
        if format == "pickle":
            import pickle
            response = pickle.dumps(response)
        elif format == "json":
            from django.utils import simplejson
            response = simplejson.dumps(response)
        elif format == "xml":
            response = self._convert_to_xml(response)
        elif format == "python":
            response = str(response)
        else:
            raise common.InputError(format, "Invalid output format.")
        self.response.out.write(response)
    
    def handle_exception(self, exception, debug_mode):
        """
        Handle any exceptions raised by the handler.
        
        This is called by App Engine if an exception is raised. If there is a
        server error, let Google handle it appropriately. If there is an input
        error, print a custom error message.
        
        @param exception: The Exception that was raised
        @type  exception: C{Exception} or one of its children
        @param debug_mode: Whether to print deubgging information or not
        @type  debug_mode: C{bool}
        """
        # TODO: Convert errors into a JSON response so the front end can handle
        #       them easily.
        if isinstance(exception, common.ServerError):
            # Server error: notify user.
            self.error(500)
            self.output(["ServerError", exception.msg])
        elif isinstance(exception, common.InputError):
            # Input error: in normal cases, Google would send a 500 error code
            # for all exception, but we want a 400 for an invalid request.
            self.error(400)
            self.output(["InputError", exception.expr, exception.msg])
        elif isinstance(exception, common.AuthError):
            self.error(401)
            url = users.create_login_url("/")
            self.output(["AuthError", exception.expr, exception.msg, url])
        else:
            # Send all else to Google.
            super(ApiHandler, self).handle_exception(exception, True)

    def _convert_to_xml(self, item):
        """
        Convert a given item to XML.
        
        @param item: Item to convert
        @type  item: Mixed
        @return: Response in XML format
        @rtype: C{str}
        """
        xml = "<?xml version=\"1.0\"?>\n<response>"
        xml += self._convert_to_xml_internal(item)
        return xml + "</response>"
    
    def _convert_to_xml_internal(self, item):
        """
        Internal function for processing output into XML format.
        
        While the main function sets up the XML header, this actually converts
        to XML. If item is a string, int, etc., just return it. If it is a
        list, enclose each value in an <item></item> tag and run this function
        recursively on whatever the value is. Do the same for dictionaries
        except use the key as the tag name instead of <item>.
        
        @param item: Item to convert
        @type  item: Mixed
        @return: Response in XML format
        @rtype: C{str}
        """
        if   (isinstance(item, str) or
              isinstance(item, unicode) or
              isinstance(item, int) or
              isinstance(item, float)):
            # Item is a string, unicode, integer, or float. Just return it.
            return str(item)
        elif (isinstance(item, list) or
              isinstance(item, tuple)):
            # Item is a list or tuple. Enclose each item in <item></item> and
            # run this function recursively on each item.
            xml = ""
            for value in item:
                xml += "<item>" + self._convert_to_xml_internal(value) + "</item>"
            return xml
        elif isinstance(item, dict):
            # Item is a dictionary. Do the same as is done above for a list,
            # except use the keys as tag names.
            for key, value in item.iteritems():
                xml += "<" + key + ">" + self._convert_to_xml_internal(item) + "</" + key + ">"
            return xml

class Session(db.Model):
    '''
    Store a session on the site.
    '''
    user = db.UserProperty()
    '''The user logged on for this session (can be blank).
    @type: L{google.appengine.ext.db.UserProperty}'''
    
    spectra = db.ListProperty(db.Key)
    '''The list of active spectra uploaded by the user in this session.
    @type: L{backend.Spectrm}'''
    
            
application = webapp.WSGIApplication([
    ('/api', ApiHandler)
], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
