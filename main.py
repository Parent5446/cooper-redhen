
import os
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp.util import users
import backend

class MainHandler(webapp.RequestHandler):
    def get(self):
	name = users.get_current_user()
	greeting = 'Hello'
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
