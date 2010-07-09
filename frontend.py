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

logging.getLogger().setLevel(logging.DEBUG)

class JDX(db.Model):
    fileName = db.BlobProperty()
    date = db.DateTimeProperty(auto_now_add=True)

class MainHandler(webapp.RequestHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/upload')
        self.response.out.write('<html><body>')
        self.response.out.write('<form action="%s" method="POST" enctype="multipart/form-data">' % upload_url)
        self.response.out.write("""Upload File: <input type="file" name="file"><br> <input type="submit" 
            name="submit" value="Submit"> </form></body></html>""")
					
          
class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
		upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
		blob_info = upload_files[0]
		self.redirect('/serve/%s' % blob_info.key())

		
class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, resource):
		resource = str(urllib.unquote(resource))
		blob_info = blobstore.BlobInfo.get(resource)
		backend.search(blob_info)

        
class Test(webapp.RequestHandler):
    def get(self):
        self.response.out.write('<html>Testing backend...<br>')
        file = open('jcamp-test.jdx')
        if 0:
            backend.add(file)
        else:
            response = backend.search(file)
            text = '<br>'.join( [str(r.data) for r in response] )
            self.response.out.write(text)
        self.response.out.write('<form action="/test" method="POST" enctype="multipart/form-data">')
        self.response.out.write('Upload File: <input type="file" name="file"><br> <input type="submit" name="submit" value="Submit"> </form></body></html>')
        
    def post(self):
        file_contents = self.request.POST.get('file').file.read()
        self.response.out.write(file_contents)

def main():
    application = webapp.WSGIApplication(
          [('/', MainHandler),
           ('/upload', UploadHandler),
           ('/serve/([^/]+)?', ServeHandler),
		   ('/test', Test)
          ], debug=True)
    run_wsgi_app(application)

if __name__ == '__main__':
  main()