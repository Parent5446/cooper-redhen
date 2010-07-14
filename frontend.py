import cgi
import datetime
import logging
import backend

from google.appengine.ext import blobstore, db, webapp
from google.appengine.api import users, quota
from google.appengine.ext.webapp import template, blobstore_handlers
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache

class MyHandler(webapp.RequestHandler):
    def get(self): pass
    '''
        user = users.get_current_user()
        if user and users.is_current_user_admin():
            greeting = ("Welcome, Administrator %s! (<a href=\"%s\">sign out</a>)" % (user.nickname(), users.create_logout_url("/")))
        elif user and !users.is_current_user_admin():
            greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>)" % (user.nickname(), users.create_logout_url("/")))
        else:
            greeting = ("<a href=\"%s\">Sign in or register</a>." % users.create_login_url("/"))

        self.response.out.write("<html><body>%s</body></html>" % greeting)
    '''

class Test(webapp.RequestHandler):
    def get(self):
        self.response.out.write('<html>Testing backend...<br>')
        file = open('jcamp-test.jdx')
        if 1:
            for s in backend.Spectrum.all(): s.delete()
            for m in backend.Matcher.all(): m.delete()
            memcache.flush_all()
            import os
            fileNames = []
            for count, entry in enumerate(os.listdir('library')):
                if count > 10: break
                fileNames.append(entry)
                if entry[-4:]=='.jdx':
                    backend.add(open(os.path.join('library', entry)))
            self.response.out.write('<pre>' + '\n'.join( [s for s in fileNames] ) + '</pre>')
            #backend.add(file)
        else:
            response = backend.search(file)
            self.response.out.write('<pre>' + '\n'.join( [r.chemical_name for r in response] ) + '</pre>')

        self.response.out.write('<form action="/test" method="POST" enctype="multipart/form-data">')
        self.response.out.write('Upload File: <input type="file" name="file"><br> <input type="submit" name="submit" value="Submit"> </form>')
        self.response.out.write('<br>CPU megacycles: ' + str(quota.get_request_cpu_usage()) + '</body></html>')

    def post(self):
        file_contents = self.request.POST.get('file').file.read()
        self.response.out.write(file_contents)

application = webapp.WSGIApplication([
    ('/', MyHandler),
    ('/test', Test)
], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
