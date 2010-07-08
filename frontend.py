import cgi

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

class MainPage(webapp.RequestHandler):
    def get(self):
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

class Greeting(db.Model):
    author = db.UserProperty()
    content = db.StringProperty(multiline=True)
    avatar = db.BlobProperty()
    date = db.DateTimeProperty(auto_now_add=True)
	
class Guestbook(webapp.RequestHandler):
    def post(self):
        greeting = Greeting()
        if users.get_current_user():
            greeting.author = users.get_current_user()
        greeting.content = self.request.get("content")
        avatar = self.request.get("img")
        greeting.avatar = db.Blob(avatar)
        greeting.put()
        self.redirect('/')

application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ('/sign', Guestbook)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()