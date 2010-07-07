
import os
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from google.appengine.api import users
#import backend

class MainHandler(webapp.RequestHandler):
    def get(self):
<<<<<<< .mine
	user = users.get_current_user()
	name = 'Red Hen User'
	if user is not None: name = user.nickname()
<<<<<<< .mine
	greeting = 'How u doin? :)'
=======
	greeting = 'How u doin my friend?'
>>>>>>> .r19
        template_values = {
            'greeting': greeting,
            'userName': name
            }
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))
=======
		user = users.get_current_user()
		name = 'Red Hen User'
		testdata = '<h2> This is a test <i> is this good </i> </h2> <br />poooop'
		if user is not None: name = user.nickname()
		greeting = 'elcome!'
		template_values = {'greeting': greeting, 'userName': name, 'testdata':testdata }
		path = os.path.join(os.path.dirname(__file__), 'index.html')
		self.response.out.write(template.render(path, template_values))
>>>>>>> .r22

def main():
    application = webapp.WSGIApplication([('/', MainHandler)], debug=True)
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
