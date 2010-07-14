import cgi
import datetime
import logging
import backend

from google.appengine.ext import blobstore, db, webapp
from google.appengine.api import users, quota
from google.appengine.ext.webapp import template, blobstore_handlers
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from google.appengine.ext.webapp import template

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
        file = open('jcamp-test.jdx')
        if 0:
            for s in backend.Spectrum.all(): s.delete()
            for m in backend.Matcher.all(): m.delete()
            memcache.flush_all()
            import os
            fileNames = []
            for count, entry in enumerate(os.listdir('short_library')):
                #if count > 10: break
                fileNames.append(entry)
                if entry[-4:]=='.jdx':
                    backend.add(open(os.path.join('short_library', entry)))
            self.response.out.write('<pre>' + '\n'.join( [s for s in fileNames] ) + '</pre>')
            
        #self.response.out.write('<form action="/test" method="POST" enctype="multipart/form-data">')
        #self.response.out.write('Upload File: <input type="file" name="file"><br> <input type="submit" name="submit" value="Submit"> </form>')
        self.response.out.write(template.render('index.html', {}))
        
    def post(self):
        file = self.request.POST.get('file').file
        response = backend.search(file)
        search_results = '\n'.join( [r.chemical_name+' - '+str(100/(r.error+1)**0.1)[:5]+'%' for r in response] )
        '''
        self.response.out.write('<html style="background-color:#CCFFCC; margin-left:50px"><div style="border-style:solid; padding-left:50px"><h1>Redhen Search Results</h1><div style="background-color:#FFF; width:600px"')
        self.response.out.write('<pre style="line-height:2em">' + '\n'.join( [r.chemical_name+' - '+str(100/(r.error+1)**0.1)[:5]+'%' for r in response] ) + '</pre>')
        self.response.out.write('</div><p>&copy Cooper Union for the Advancement of Science and Art, 2010</p></div></html>')
        '''
        self.response.out.write(template.render('index.html', {'search_results':search_results}))

application = webapp.WSGIApplication([
	('/', MyHandler),
	('/test', Test)
], debug=True)

def main():
	run_wsgi_app(application)

if __name__ == '__main__':
	main()
