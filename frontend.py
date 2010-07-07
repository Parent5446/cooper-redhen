
import os
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from google.appengine.api import users
#import backend

class MainHandler(webapp.RequestHandler):
    def get(self):
		user = users.get_current_user()
		name = 'Red Hen User'
		#testdata = '<h2> This is a test <i> is this good </i> </h2> <br />poooop'
		if user is not None: name = user.nickname()
		greeting = 'elcome!'
			template_values = {
				'greeting': greeting,
				'userName': name
				}
			path = os.path.join(os.path.dirname(__file__), 'index.html')
			self.response.out.write(template.render(path, template_values))

def main():
    application = webapp.WSGIApplication([('/', MainHandler)], debug=True)
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
