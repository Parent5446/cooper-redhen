import cgi
import datetime
import logging
import backend

from google.appengine.ext import blobstore, db, webapp
from google.appengine.api import users, quota, memcache
from google.appengine.ext.webapp import template, blobstore_handlers
from google.appengine.ext.webapp.util import run_wsgi_app

class MainHandler(webapp.RequestHandler):
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
            
        self.response.out.write(template.render('index.html', {}))

    def post(self):
        file = self.request.POST.get('file').file
        response = backend.search(file)
        search_results = '\n'.join( [r.chemical_name+' - '+str(100/(r.error+1)**0.1)[:5]+'%' for r in response] )
        self.response.out.write(template.render('index.html', {'search_results':search_results}))

class Search(db.Model):
    """Store a user's search for a certain spectrum."""
    
    spectrum_in = blobstore.BlobReferenceProperty()
    """The Spectrum that was searched for
    @type: L{google.appengine.ext.blobstore.BlobReferenceProperty}"""
    
    spectrum_out = db.ListProperty(db.Key)
    """The Spectra that were returned
    @type: C{list}"""
    
    spectrum_error = db.ListProperty(float)
    """The error value associated with each returned spectrum
    @type: C{list}"""
    
    user = db.UserProperty(auto_current_user_add=True)
    """The user that did the search
    @type: L{google.appengine.ext.blobstore.UserProperty}"""
    
    datetime = db.DateTimeProperty(auto_now=True)
    """The date and time the search occurred
    @type: L{google.appengine.ext.blobstore.DateTimeProperty}"""


application = webapp.WSGIApplication([
	('/', MainHandler)
], debug=True)

def main():
	run_wsgi_app(application)

if __name__ == '__main__':
	main()
