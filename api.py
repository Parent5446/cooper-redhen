"""
Take a POST request with JSON data and process it. If it contains a spectrum
file, send it to the back end to search the database.

The nature of this API depends on the type of request sent to it, and where
the request is sent to. It behaves as follows:

- /upload/*
    - GET: Returns a file upload URL
    - POST: Uploads a file (must be a valid upload URL)
- /serve/*
    - GET: Executes a request for an uploaded file.
- /*
    - POST: Executes a request not involving a file upload.

@organization: The Cooper Union for the Advancement of the Science and the Arts
@license: http://opensource.org/licenses/lgpl-3.0.html GNU Lesser General Public License v3.0
@copyright: Copyright (c) 2010, Cooper Union (Some Right Reserved)
"""

import urllib

from google.appengine.ext import blobstore, webapp
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache # import memory cache
from django.utils import simplejson

import common
import backend
import frontend

class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def get(self):
        self.response.out.write(blobstore.create_upload_url('/upload'))

    def post(self):
        upload_files = self.get_uploads('spectrum')
        blob_info = upload_files[0]
        self.redirect('/serve/%s' % blob_info.key())

class ApiHandler(blobstore_handlers.BlobstoreDownloadHandler):
    """Handle any API requests and return a JSON response."""
    
    def get(self, resource):
        resource = str(urllib.unquote(resource))
        response = self.handle_request(blobstore.BlobInfo.get(resource))
        self.response.out.write(simplejson.dumps(response))
    
    def post(self):
        """
        Handle a POST request to the API.
        
        Load the JSON object in the request and hand it off to self.process_request.
        Then put the response back in JSON format and give back to the user.
        """
        response = self.handle_request()
        self.response.out.write(simplejson.dumps(response))
        
    def handle_request(self, upload=False):
        action = self.request.get("action")
        response = []
        if upload is not False:
            # Search the database for something
            targets = self.request.get_all("target")
            if targets:
                # User wants to find an already completed search.
                # Get the targeted searches and extract relevant information.
                # TODO: Make script entirely re-do the search if the 'force'
                #       argument is set to True.
                searches = frontend.Search(targets)
                info = [(searches.spectrum_out[i].chemical_name, searches.error[i])
                        for i in len(searches.spectrum_out)]
                response.append(info)
            else:
                # User wants to commit a new search with a file upload.
                # Send file upload to the back end for searching.
                file_obj = blobstore.BlobReader(upload.key())
                result = backend.search(file_obj)
                # Extract relevant information and add to the response.
                info = [(i.chemical_name, i.error) for i in result]
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
        # Put back into JSON and send to user.
        return response
    
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
    ('/', ApiHandler),
    ('/upload', UploadHandler),
	('/serve/([^/]+)?', ApiHandler)
], debug=True)

def main():
	run_wsgi_app(application)

if __name__ == '__main__':
	main()
