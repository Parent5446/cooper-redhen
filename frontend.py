"""
Take a POST request with JSON data and process it. If it contains a spectrum
file, send it to the back end to search the database.

All request must be POST requests. Any GET requests will just print these
instructions, and all others will be ignored. The POST variables below
may be passed. If uploading files, make sure to set enctype to
multipart/form-data, or they will not be processed properly.

 - action (required):
     - "compare" - Compare two targets, either from file upload or database.
     - "analyze" - Does the same as compare, except instead of taking two
                  targets, it takes one and searches the database in an
                  attempt to find the other (good for unknown spectra).
     - "browse"  - Browse the database.
 - target (required):
    - When action is "search" or "compare": Can be either the text from a JCAMP
      file or "db:key", where key is the database key for a Spectrum object.
    - When action is "browse": Can be either "public" for browsing the public
      library or "private" for browsing your own private library.
 - limit (optional, used only when action is "browse"): How many spectra to get
  when browsing (maximum is 50).
 - offset (optional, used only when action is "browse"): Where to start listing
  spectra from (used for pagination).
 - output (optional): Can be "xml", "json", "python", or "pickle" depending on
                     what output format you want. Default is "pickle".

@organization: The Cooper Union for the Advancement of the Science and the Arts
@license: http://opensource.org/licenses/lgpl-3.0.html GNU Lesser General Public License v3.0
@copyright: Copyright (c) 2010, Cooper Union (Some Right Reserved)
"""
from google.appengine.api import users, memcache
from google.appengine.ext import webapp
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
RedHen API v0.1

All request must be POST requests. Any GET requests will just print these
instructions, and all others will be ignored. The POST variables below
may be passed. If uploading files, make sure to set enctype to
multipart/form-data, or they will not be processed properly.

- action (required):
    - "compare" - Compare two targets, either from file upload or database.
    - "analyze" - Does the same as compare, except instead of taking two
                  targets, it takes one and searches the database in an
                  attempt to find the other (good for unknown spectra).
    - "browse"  - Browse the database.
- target (required):
    - When action is "search" or "compare": Can be either the text from a JCAMP
      file or "db:key", where key is the database key for a Spectrum object.
    - When action is "browse": Can be either "public" for browsing the public
      library or "private" for browsing your own private library.
- limit (optional, used only when action is "browse"): How many spectra to get
  when browsing (maximum is 50).
- offset (optional, used only when action is "browse"): Where to start listing
  spectra from (used for pagination).
- output (optional): Can be "xml", "json", "python", or "pickle" depending on
                     what output format you want. Default is "pickle".
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
        targets = self.request.get_all("target")
        response = []
        if action == "analyze":
            # Search the database for something.
            for target in targets:
                # User wants to commit a new search with a file upload.
                # Send file upload to the back end for searching.
                result = backend.search(target)
                # Extract relevant information and add to the response.
                info = [(i.chemical_name, i.error) for i in result]
                response.append(info)
        elif action == "compare":
            # Compare two pre-uploaded spectra.
            if targets is None:
                raise common.InputError(targets, "No search targets given.")
            # Default to Bove's algorithm if not given
            algorithm = self.request.get("algorithm", "bove")
            response.append(backend.compare(targets[0], targets[1], algorithm))
        elif action == "browse":
            # Get a list of spectra from the database for browsing
            limit = self.request.get("limit", 10)
            offset = self.request.get("offset", 0)
            user = users.get_current_user()
            if targets[0] == "public":
                target = "public"
            elif user is None:
                # Must be logged in to access a private database.
                raise common.AuthError(user, "Not logged in.")
            else:
                target = user
            # Return the database key, name, and chemical type.
            results = [(str(spectrum.key()), spectrum.chemical_name, spectrum.chemical_type)
                       for spectrum in backend.browse(target, limit, offset)]
            response.extend(results)
        elif action == "add":
            # Add a new spectrum to the database. Supports multiple spectra.
            spectra = self.request.get_all("spectrum")
            user = users.get_current_user()
            if targets[0] == "public":
                if not users.is_current_user_admin():
                    # User must be admin to change public database.
                    raise AuthError(user, "Needs administrative privileges.")
                target = "public"
            elif user is None:
                # Must be logged in to access a private database.
                raise common.AuthError(user, "Not logged in.")
            else:
                target = user
            for spectrum_data in spectra:
                backend.add(spectrum_data, target)
        elif action == "delete":
            # Delete a spectrum from the database.
            spectra = self.request.get_all("spectrum")
            user = users.get_current_user()
            if targets[0] == "public":
                if not users.is_current_user_admin():
                    # User must be admin to change public database.
                    raise AuthError(user, "Needs administrative privileges.")
                target = "public"
            elif user is None:
                # Must be logged in to access a private database.
                raise common.AuthError(user, "Not logged in.")
            else:
                target = user
            for spectrum_data in spectra:
                backend.delete(spectrum_data, target)
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
        format = self.request.get("output", "pickle")
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


application = webapp.WSGIApplication([
    ('/api', ApiHandler)
], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
