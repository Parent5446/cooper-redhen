import cgi
import datetime
import logging
import backend

from google.appengine.ext import blobstore
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import quota

class Test(webapp.RequestHandler):
    def get(self):
        self.response.out.write('<html>Testing backend...<br>')
        file = open('jcamp-test.jdx')
        if 0:
            backend.add(file)
        else:
            response = backend.search(file)
            text = '<pre>' + '\n'.join( [str(r)[1:-1] for r in response] ) + '</pre>'
            self.response.out.write(text)
        self.response.out.write('<form action="/test" method="POST" enctype="multipart/form-data">')
        self.response.out.write('Upload File: <input type="file" name="file"><br> <input type="submit" name="submit" value="Submit"> </form>')
        self.response.out.write('<br>CPU megacycles: ' + str(quota.get_request_cpu_usage()) + '</body></html>')
        
    def post(self):
        file_contents = self.request.POST.get('file').file.read()
        self.response.out.write(file_contents)

application = webapp.WSGIApplication([
	('/', Test)
], debug=True)

def main():
	run_wsgi_app(application)

if __name__ == '__main__':
	main()