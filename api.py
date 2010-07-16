﻿'''Take a POST request with JSON data and process it through the back end.'''

## Take a POST request with JSON data and process it. If it contains a spectrum
# file, send it to the back end to search the database.
#
# In order for the request to be handled properly, a POST request should be
# submitted to this script with a JSON object as the body of the request.
# File uploads are handled automatically by Google's Blob Store. Note that
# the purpose of this script is because Pyjamas will compile static HTML,
# Javascript, and CSS files that cannot have App Engine Python in them. This
# script allows the user to still interact dynamically with the server through
# an HTTP request.
# 
# @package backend
# @author The Cooper Union for the Advancement of the Science and the Arts
# @license http://opensource.org/licenses/lgpl-3.0.html GNU Lesser General Public License v3.0
# @copyright Copyright (c) 2010, Cooper Union (Some Right Reserved)

import json

from google.appengine.ext import blobstore, webapp
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp.util import run_wsgi_app

import backend
import common

## Handle any API requests and return a JSON response.
class ApiHandler(webapp.RequestHandler, blobstore_handlers.BlobstoreUploadHandler):
    '''Handle any API requests and return a JSON response.'''
    
    ## Handle a POST request to the API.
    #
    # Load the JSON object in the request and hand it off to self.process_request.
    # Then put the response back in JSON format and give back to the user.
    def post(self):
        '''Handle a POST request to the API.'''
        request = json.loads(self.request.body)
        # The script needs a dictionary with an action key to continue.
        if not isinstance(request, dict):
            raise common.InputError(request, "JSON object must be an indexed array.")
        # Pop action and send the rest to the process_request function.
        action = request.pop("action", False)
        result = self.process_request(action, request)
        # Put back into JSON and send to user.
        response = json.dumps(result)
        self.response.out.write(response)
    
    ## Handle any exceptions raised by the handler.
    #
    # This is called by App Engine if an exception is raised. If there is a
    # server error, let Google handle it appropriately. If there is an input
    # error, print a custom error message.
    # 
    # @param exception The exception that was raised
    # @param debug_mode Whether to print debugging information or not
    def handle_exception(exception, debug_mode):
        '''Handle any exceptions raised by the handler.'''
        if isinstance(exception, ServerError):
            # Server error: let Google handle this the usual way.
            super(ApiHandler, self).handle_exception(exception, True)
        elif isinstance(exception, InputError):
            # Input error: in normal cases, Google would send a 500 error code
            # for all exception, but we want a 400 for an invalid request.
            self.error(400)
            response = "Invalid user input.\nInput: %s\nReason: %s"
            self.response.out.write(response % exception.expr, expression.msg)
        else:
            # Send all else to Google.
            super(ApiHandler, self).handle_exception(exception, True)
    
    ## Process an API request.
    #
    # Take a given action and args and process an API request. If the action
    # is 'search', search the database for any spectrum files uploaded.
    #
    # @param action What to do
    # @param args List of arguments for the action
    def process_request(action, args):
        '''Process an API request.'''
        response = []
        if action == "search":
            # Send each file upload to the back end for searching.
            for upload in self.get_uploads('spectrum'):
                file_obj = blobstore.BlobReader(upload.key())
                result = backend.search(file_obj)
                # Delete the file afterward so it does not become orphaned.
                upload.delete()
                # Extract relevant information and add to the response.
                info = result.chemical_name, result.error
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
