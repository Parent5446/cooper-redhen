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


class Greeting(db.Model):
    author = db.UserProperty()
    content = db.StringProperty(multiline=True)
    avatar = db.BlobProperty()
    date = db.DateTimeProperty(auto_now_add=True)

class MainPage(webapp.RequestHandler):
    def get(self):
        self.response.out.write('<html><body>')
        query_str = "SELECT * FROM Greeting ORDER BY date DESC LIMIT 10"
        greetings = db.GqlQuery (query_str)

        for greeting in greetings:
            if greeting.author:
                self.response.out.write('<b>%s</b> wrote:' % greeting.author.nickname())
            else:
                self.response.out.write('An anonymous person wrote:')
            self.response.out.write("<div><img src='img?img_id=%s'></img>" %
                                    greeting.key())
            self.response.out.write(' %s</div>' %
                                  cgi.escape(greeting.content))

        self.response.out.write("""
              <form action="/sign" enctype="multipart/form-data" method="post">
                <div><label>Message:</label></div>
                <div><textarea name="content" rows="3" cols="60"></textarea></div>
                <div><label>Avatar:</label></div>
                <div><input type="file" name="img"/></div>
                <div><input type="submit" value="Sign Guestbook"></div>
              </form>
            </body>
          </html>""")

class Image (webapp.RequestHandler):
    def get(self):
        greeting = db.get(self.request.get("img_id"))
        if greeting.avatar:
            self.response.headers['Content-Type'] = "image/png"
            self.response.out.write(greeting.avatar)
        else:
            self.response.out.write("No image")

class Guestbook(webapp.RequestHandler):
    def post(self):
        greeting = Greeting()
        if users.get_current_user():
            greeting.author = users.get_current_user()
        greeting.content = self.request.get("content")
        avatar = images.resize(self.request.get("img"), 32, 32)
        greeting.avatar = db.Blob(avatar)
        greeting.put()
        self.redirect('/')

class Test(webapp.RequestHandler):
	def get(self):
		self.response.out.write('Testing backend...')
		file = open('jcamp-test.jdx')
		response = backend.search(file)
		self.response.out.write('Done')


application = webapp.WSGIApplication([
    ('/', MainPage),
    ('/img', Image),
    ('/sign', Guestbook)
], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()