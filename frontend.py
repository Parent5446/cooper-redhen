from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class MainPage(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            self.response.out.write('<html style=text-align:center><h1>Hello, '+user.nickname()+'</h1></html>')
        else:
            self.redirect(users.create_login_url(self.request.uri))

application = webapp.WSGIApplication( [('/', MainPage)], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()