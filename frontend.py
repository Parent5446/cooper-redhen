import backend
import cgi
import datetime
import logging

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import images

logging.getLogger().setLevel(logging.DEBUG)


class JDXFile(db.Model):
    fileName = db.BlobProperty()
    date = db.DateTimeProperty(auto_now_add=True)

class MainPage(webapp.RequestHandler):
    def get(self):
        self.response.out.write('<html><body>')
        query_str = "SELECT * FROM JDXFile ORDER BY date DESC LIMIT 10"
        JDXFiles = db.GqlQuery (query_str)

        '''for JDXFile in JDXFiles:
            self.response.out.write("<div><img src='img?img_id=%s'></img>" %
                                    JDXFile.key())
            self.response.out.write('</div>')'''

        self.response.out.write("""
              <form action="/sign" enctype="multipart/form-data" method="post">
                <div><label>JDX File:</label></div>
                <div><input type="file" name="jdxFile"/></div>
                <div><input type="submit" value="Upload"></div>
              </form>
            </body>
          </html>""")

class JDX (webapp.RequestHandler):
    def get(self):
        JDXFile = db.get(self.request.get("jdxFile_id"))
        if JDXFile.fileName:
            self.response.headers['Content-Type'] = "image/png"
            self.response.out.write(JDXFile.fileName)
        else:
            self.response.out.write("Failed to Upload")

class Uploader(webapp.RequestHandler):
    def post(self):
        jdxFile = JDXFiles()
		jdxFile.fileName = db.Blob(fileName)
        jdxFile.put()
        self.redirect('/')

class Test(webapp.RequestHandler):
	def get(self):
		self.response.out.write('Testing backend...')
		file = open('jcamp-test.jdx')
		response = backend.search(file)
		self.response.out.write('Done')


application = webapp.WSGIApplication([
    ('/', MainPage),
    ('/img', JDX),
    ('/sign', Uploader)
], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()