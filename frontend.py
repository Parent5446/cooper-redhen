from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class MainPage(webapp.RequestHandler):
    def get(self):
	user = users.get_current_user()
	name = 'Red Hen User'
	if user is not None: name = user.nickname()
	greeting = 'How u doin my friend?'
    template_values = {'greeting': greeting,'userName': name}
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))
		user = users.get_current_user()
		name = 'Red Hen User'
		testdata = '<h2> This is a test <i> is this good </i> </h2> <br />poooop'
		if user is not None: name = user.nickname()
		greeting = 'elcome!'
		template_values = {'greeting': greeting, 'userName': name, 'testdata':testdata }
		self.redirect('http://www.google.com');
		path = os.path.join(os.path.dirname(__file__), 'index.html')
		self.response.out.write(template.render(path, template_values))

	template_values = { 'greeting': greeting, 'userName': name }
	
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))
        user = users.get_current_user()

        if user:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('Hello, ' + user.nickname())
        else:
            self.redirect(users.create_login_url('/'))

application = webapp.WSGIApplication([('/', MainPage)], debug=True)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()