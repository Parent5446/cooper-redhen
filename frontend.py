import cgi
import datetime
import logging

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

logging.getLogger().setLevel(logging.DEBUG)


class JDX(db.Model):
	fileName = db.BlobProperty()
	date = db.DateTimeProperty(auto_name_add=True)

class MainPage(webapp.RequestHandler):
	def get(self):
		self.response.out.write('<html><body>')
		query_str = "SELECT * FROM JDX ORDER BY date DESC LIMIT 10"
		JDXs = db.GqlQuery(query_str)
		
		for jdx in JDXs:
			self.response.out.write("<a>file uploaded: %s</a>" %
									jdx.key())
		self.response.out.write("""
			 <form action="/uploader" enctype="multipart/form-data" method="post">
                <div><input type="file" name="jdxFile"/></div>
                <div><input type="submit" value="Upload"></div>
              </form>
            </body>
          </html>""")
		  
class JDXFile(webapp.RequestHandler):
	def get(self):
		jdx = db.get(self.request.get("jdxFile_id"))
		if jdx.fileName:
			self.response.out.write(jdx.fileName)
		else:
			self.response.out.write("Failed to Upload")

class uploadedPage(webapp.RequestHandler):
	def post(self):
		jdx = JDX()
		jdx.fileName = db.Blob(fileName)
		jdx.put()
		self.redirect('/')

		
class Test(webapp.RequestHandler):
	def get(self):
		self.response.out.write('Testing backend...')
		file = open('jcamp-test.jdx')
        backend.add(file)
		#response = backend.search(file)
		self.response.out.write('Done')

application = webapp.WSGIApplication([
    ('/', MainPage),
    ('/uploader', uploadedPage)
], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()
		