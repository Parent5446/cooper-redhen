"""
RedHen API v0.2

Any request that requires a file upload must be a POST request. Only the
update, projects, data, and browse actions are allowed in a GET request.
The GET/POST variables below may be passed. If uploading files, make sure
to set enctype to multipart/form-data, or they will not be processed properly.

General Options:
 - action (required):
     - "compare" - Compare two targets, either from file upload or database.
     - "add" - Add a spectrum to a project or the public database.
     - "delete" - Add a spectrum to a project or the public database.
     - "update" - Clear all heuristic data and rebuild the Matcher (admin-only).
     - "browse" - Browse either the public database or a specific project.
     - "projects" - List all projects the user can access.
     - "bulkadd" - Add a mass amount of spectra to the database as once.
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
 - offset: Where to start listing spectra from (used for pagination).
 - type (used for search suggestions): What type of spectrum (infrared or raman)
 - guess (used only search suggestions): What the user has typed already and
   what we are giving suggestions for.

Comparing Options:
 - algorithm (defaults to "bove"): Which linear algorithm to compare spectra with

@organization: The Cooper Union for the Advancement of the Science and the Arts
@license: http://opensource.org/licenses/lgpl-3.0.html GNU Lesser General Public License v3.0
@copyright: Copyright (c) 2010, Cooper Union (Some Right Reserved)
"""
from google.appengine.api import users, memcache, quota
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.runtime.apiproxy_errors import CapabilityDisabledError

import common
import backend

class ApiHandler(webapp.RequestHandler):
    """Handle any API requests and return a JSON response."""
    
    def get(self):
        if self.request.get("action") in ("update", "projects", "data", "browse"):
            self.post()
        else:
            self.help()
    
    def post(self):
        """
        Handle a POST request to the API.
        
        Take a list of actions from a POST request, and do the appropriate
        action. See the documentation for this module for more information.
        
        @raise common.InputError: If no search targets are given in the target
        POST variable or if an invalid action is given.
        """
        cpu_start = quota.get_request_cpu_usage()
        
        action = self.request.get("action")
        target = self.request.get("targt", "public")
        spectra = filter(lambda x: x, self.request.get_all("spectrum"))
        offset = self.request.get("offset", 0)
        algorithm = self.request.get("algorithm", "bove")
        guess = self.request.get("guess")
        spectrum_type = self.request.get("type")
        raw = self.request.get("raw", False)
        user = users.get_current_user()
        
        # Just for testing
        '''
        [db.delete(m) for m in backend.Matcher.all(keys_only=True)]
        [db.delete(s) for s in backend.Spectrum.all(keys_only=True)]
        [db.delete(s) for s in backend.Project.all(keys_only=True)]
        [db.delete(s) for s in backend.GenericData.all(keys_only=True)]
        memcache.flush_all()
        import os
        for s in os.listdir('infrared'):
            if s[0]!='.': backend.add( open('infrared/'+s).read(), 'public', False)   
        #spectra = [ open('infrared/iodobenzene1.jdx').read() ]
        '''

        # If not operating on the main project, try getting the private one.
        # But abort if target is not supposed to be a project.
        if target and target != "public" and target != "others":
            target = backend.Project.get(target)
            if target is None:
                raise common.InputError(targets, "Invalid project ID.")
        # Start doing the request
        if action == "compare" and target == "public":
            # Search the database for something.
            result = backend.search(spectra, algorithm)
            response = ([(str(spec.key()), spec.chemical_name, spec.error, [d*300.0/65535 for d in spec.data]) for spec in result])
        elif action == "compare":
            # Compare multiple spectra uploaded in this session.
            result = backend.compare(spectra, algorithm)
            response = [("NULL", spec.chemical_name, spec.error, [d*300.0/65535 for d in spec.data]) for spec in result]
        elif action == "browse":
            # Get a list of spectra from the database for browsing
            backend.auth(user, target, "view")
            # Return the database key, name, and chemical type.
            response = backend.browse(target, offset, guess, spectrum_type) #a list of names and keys
        elif action == "add":
            # Add a new spectrum to the database. Supports multiple spectra.
            backend.auth(user, target, "spectrum")
            backend.add(spectra, target, False)
        elif action == "bulkadd":
            # Add a new spectrum to the database. Supports multiple spectra.
            backend.add(spectra, target, True)
        elif action == "delete":
            # Delete a spectrum from the database.
            backend.auth(user, target, "spectrum")
            backend.delete(spectra, target)
        elif action == "update":
            backend.auth(user, "public", "spectrum")
            backend.update()
        elif action == "projects":
            query = "WHERE :1 IN owners OR :1 IN collaborators OR :1 in viewers"
            response = [(proj.key(), proj.name) for proj in Project.gql(query, user)]
        else:
            # Invalid action. Raise an error.
            raise common.InputError(action, "Invalid API action.")
        # Pass it on to self.output for processing.
        self._output(response)
    
    def _output(self, response):
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
            self._output(["ServerError", exception.msg])
        elif isinstance(exception, common.InputError):
            # Input error: in normal cases, Google would send a 500 error code
            # for all exception, but we want a 400 for an invalid request.
            self.error(400)
            self._output(["InputError", exception.expr, exception.msg])
        elif isinstance(exception, common.AuthError):
            # Authorization error: the user tried to do something disallowed.
            self.error(401)
            url = users.create_login_url("/")
            self._output(["AuthError", exception.expr, exception.msg, url])
        elif isinstance(exception, CapabilityDisabledError):
            # Maintenance error: AppEngine is down for maintenance.
            self.error(503)
            self._output(["AppEngine is down for maintenance."])
        else:
            # Send all else to Google.
            super(ApiHandler, self).handle_exception(exception, True)

    def help(self):
        """Print help information for the API."""
        self.response.out.write("<pre>%s</pre>" % __doc__)
    
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

application = webapp.WSGIApplication([
    ('/api', ApiHandler)
], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
