
import os
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from google.appengine.api import users
#import backend


class MainPage(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('Hello, webapp World!')
		
application = webapp.WSGIApplication([('/', MainPage)] , debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
	main()
