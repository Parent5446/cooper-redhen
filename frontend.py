import cgi

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import images

class JDXFile(db.Model):
	fileName = db.BlobProperty()

class MainPage(webapp.RequestHandler):
	def get(self): 
		self.response.out.write('<html><body>')
		query_str = "SELECT * FROM JDXFile"
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

class UploadedFile(webapp.RequestHandler):
		def post(self):
			jdxFile = JDXFile()
			#jdxFile.fileName = db.Blob(fileName)
			jdxFile.put()
			self.redirect('/')

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
	('/', MainPage),
	('/upload', UploadedFile),
	('/test', Test)
], debug=True)

def main():
	run_wsgi_app(application)

if __name__ == '__main__':
	main()