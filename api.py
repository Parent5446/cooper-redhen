"""
Take a POST request with JSON data and process it. If it contains a spectrum
file, send it to the back end to search the database.

In order for the request to be handled properly, a POST request should be
submitted to this script with a JSON object as the body of the request.
File uploads are handled automatically by Google's Blob Store. Note that
the purpose of this script is because Pyjamas will compile static HTML,
Javascript, and CSS files that cannot have App Engine Python in them. This
script allows the user to still interact dynamically with the server through
an HTTP request.

@organization: The Cooper Union for the Advancement of the Science and the Arts
@license: http://opensource.org/licenses/lgpl-3.0.html GNU Lesser General Public License v3.0
@copyright: Copyright (c) 2010, Cooper Union (Some Right Reserved)
"""

import json

from google.appengine.ext import blobstore, webapp
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp.util import run_wsgi_app

import backend
import common

class ApiHandler(webapp.RequestHandler, blobstore_handlers.BlobstoreUploadHandler):
    """Handle any API requests and return a JSON response."""
    
    def post(self):
        """
        Handle a POST request to the API.
        
        Load the JSON object in the request and hand it off to self.process_request.
        Then put the response back in JSON format and give back to the user.
        """
        request = self.request.arguments()
        # Pop action and send the rest to the process_request function.
        action = request.pop("action", False)
        result = self.process_request(action, request)
        # Put back into JSON and send to user.
        self.response.out.write(json.dumps(result))
    
    def handle_exception(exception, debug_mode):
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
        if isinstance(exception, ServerError):
            # Server error: let Google handle this the usual way.
            super(ApiHandler, self).handle_exception(exception, True)
        elif isinstance(exception, InputError):
            # Input error: in normal cases, Google would send a 500 error code
            # for all exception, but we want a 400 for an invalid request.
            self.error(400)
            self.response.out.write(json.dumps([exception.expr, exception.msg]))
        else:
            # Send all else to Google.
            super(ApiHandler, self).handle_exception(exception, True)
    
    def process_request(action, args):
        """
        Process an API request.
        
        Take a given action and args and process an API request. If the action
        is 'search', search the database for any spectrum files uploaded or get
        any history items if they are provided as the 'target'. If the action is
        'history', get the history of searches for the current user.
        
        @param action: What to do
        @type  action: C{str}
        @param args: List of arguments for the action
        @type  args: C{dict}
        @return: Response to the request
        @rtype: C{list}
        """
        response = []
        if action == "search":
            # Search the database for something
            if isinstance(args.get("target", ""), str):
                # User wants to find an already completed search.
                # First validate the target. It should be a list.
                if not isinstance(args["target"], list):
                    raise common.InputError(args["target"], "Invalid search target.")
                # Get the targeted searches and extract relevant information.
                # TODO: Make script entirely re-do the search if the 'force'
                #       argument is set to True.
                searches = frontend.Search(args["target"])
                info = [(searches.spectrum_out[i].chemical_name, searches.error[i])
                        for i in len(searches.spectrum_out)]
                response.append(info)
            else:
                # User wants to commit a new search with a file upload.
                # Send each file upload to the back end for searching.
                for upload in self.get_uploads('spectrum'):
                    file_obj = blobstore.BlobReader(upload.key())
                    result = backend.search(file_obj)
                    # Extract relevant information and add to the response.
                    info = [(result.chemical_name, result.error) for i in result]
                    response.append(info)
                    # Add to search history
                    # FIXME: Find way to limit the number of stored searches
                    search = frontend.Search()
                    search.spectrum_in = upload
                    search.spectrum_out = [spectrum.key() for spectrum in result]
                    search.error = [spectrum.error for spectrum in result]
                    search.put()
        elif action == "history":
            # Get a list of previous searches for the current user.
            curr_user = users.get_current_user()
            history = frontend.Search.gql("WHERE user = :user", user=curr_user)
            for item in history:
                info = [item.key, item.datetime, list(item.spectrum_out)]
                response.append(info)
        else:
            # Invalid action. Raise an error.
            raise common.InputError(action, "Invalid API action.")
        return response

application = webapp.WSGIApplication([
	('/', MainHandler)
], debug=True)

def main():
	run_wsgi_app(application)

if __name__ == '__main__':
	main()
