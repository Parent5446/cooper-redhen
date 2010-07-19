"""
Take a POST request with JSON data and process it. If it contains a spectrum
file, send it to the back end to search the database.

Usage:
- All requests to the API must be POST.
- Pass the API one or more POST variables all with the name "request". Any
  POST variable that is not named "request" will be ignored.
- All requests must be serialized dictionaries with the request information,
  and must follow the format below.

Requests:
{ action: <action>
  target: [<target>, <target>, ...]
  limit: <limit>
  offset: <offset> }

- action (required): Can be "search", "compare", or "browse"
- target (required):
    - When action is "search" or "compare": Can be either the text from a JCAMP
      file or "db:key", where key is the database key for a Spectrum object.
    - When action is "browse": Can be either "public" for browsing the public
      library or "private" for browsing your own private library.
- limit (optional, used only when action is "browse"): How many spectra to get
  when browsing (maximum is 50).
- offset (optional, used only when action is "browse"): Where to start listing
  spectra from (used for pagination).

@organization: The Cooper Union for the Advancement of the Science and the Arts
@license: http://opensource.org/licenses/lgpl-3.0.html GNU Lesser General Public License v3.0
@copyright: Copyright (c) 2010, Cooper Union (Some Right Reserved)
"""

import pickle

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
        system.response.out.write("""
RedHen API v0.1

Usage:
- All requests to the API must be POST.
- Pass the API one or more POST variables all with the name "request". Any
  POST variable that is not named "request" will be ignored.
- All requests must be serialized dictionaries with the request information,
  and must follow the format below.

Requests:
{ action: <action>
  target: [<target>, <target>, ...]
  limit: <limit>
  offset: <offset> }

- action (required): Can be "search", "compare", or "browse"
- target (required):
    - When action is "search" or "compare": Can be either the text from a JCAMP
      file or "db:key", where key is the database key for a Spectrum object.
    - When action is "browse": Can be either "public" for browsing the public
      library or "private" for browsing your own private library.
- limit (optional, used only when action is "browse"): How many spectra to get
  when browsing (maximum is 50).
- offset (optional, used only when action is "browse"): Where to start listing
  spectra from (used for pagination).
        """)
    
    def post(self):
        """
        Handle a POST request to the API.
        
        Take a list of actions from a POST request, and do the appropriate
        action. See the documentation for this module for more information.
        """
        requests = [pickle.loads(req) for req in self.request.get_all("request")]
        output = []
        for request in requests:
            response = []
            actions = request.get("action", False)
            if action == "analyze":
                # Search the database for something.
                targets = request.get("target", [])
                for target in targets:
                    # User wants to commit a new search with a file upload.
                    # Send file upload to the back end for searching.
                    result = backend.search(target)
                    # Extract relevant information and add to the response.
                    info = [(i.chemical_name, i.error) for i in result]
                    response.append(info)
            elif action == "compare":
                targets = request.get("target", None)
                if targets is None:
                    raise common.InputError(targets, "No search targets given.")
                algorithm = request.get("algorithm", "bove")
                response.append(backend.compare(targets[0], targets[1], algorithm))
            elif action == "browse":
                target = request.get("target", "public")
                limit = request.get("limit", 10)
                offset = request.get("offset", 0)
                response.append(backend.browse(target, limit, offset))
            else:
                # Invalid action. Raise an error.
                raise common.InputError(action, "Invalid API action.")
            # Put back into JSON and send to user.
            output.append(response)
        self.response.out.write(pickle.dumps(output))
    
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
            # Server error: let Google handle this the usual way.
            super(ApiHandler, self).handle_exception(exception, True)
        elif isinstance(exception, common.InputError):
            # Input error: in normal cases, Google would send a 500 error code
            # for all exception, but we want a 400 for an invalid request.
            self.error(400)
            self.response.out.write(simplejson.dumps([exception.expr, exception.msg]))
        else:
            # Send all else to Google.
            super(ApiHandler, self).handle_exception(exception, True)

application = webapp.WSGIApplication([
    ('/', ApiHandler)
], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
