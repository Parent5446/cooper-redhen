import cgi

from google.appengine.ext import db
from googlre.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import images

class JDXFile(db.Model):
	fileName = db.BlobProperty()

class MainPage(webapp.RequestHandler):
	def get(self): 
		self.response.out.write('<html><body>')
		query_str = "SELECT * FROM JDXFile DESC LIMIT 10"
		jdxFiles = db.GqlQuery (query_str)
			
		for jdxFile in jdxFiles:
			self.response.out.write("<a> File Name is: %s</a>" %
									jdxFile.key())
										
		self.response.out.write("""
			<form action="/upload" enctype="multipart/form-data" method="post">
				<div><label>Upload File:</label></div>
				<div><input type="file" name="file"/></div>					
				<div><input type="submit" value="Upload!"></div>
				</form>
				</body></html>""")

class UploadedFile(webapp.REquestHandler):
		def post(self):
			jdxFile = JDXFile()
			jdxFile.fileName = db.Blob(fileName)
			jdxFile.put()
			self.redirect('/')
application = webapp.WSGIApplication([
	('/', MainPage),
	('/sign', UploadedFile)
], debug=True)

def main():
	run_wsgi_app(application)

if __name__ == '__main__':
	main()