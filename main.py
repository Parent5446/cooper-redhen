
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
import redhen.backend

class MainHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write("I'm the frontend. Let me go get the backend for you...<br />")
	answer = backend.search()
	self.response.out.write(answer)

def main():
    application = webapp.WSGIApplication([('/', MainHandler)], debug=True)
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
