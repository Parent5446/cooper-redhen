import httplib, urllib, mimetypes, threading

class Thread(threading.Thread):
    def __init__(self, num, *args, **kwargs):
        self.num = num
        super(Thread, self).__init__(*args, **kwargs)
        
    def run(self):
        num = self.num
        sugg_data = [("action", "browse"), ("type", "infrared"),
                     ("guess", "iodo"), ("output", "json")]
        sugg_headers = {"Content-type": "application/x-www-form-urlencoded",
                        "Content-Length": 50,
                        "Accept": "text/plain"}
        search_data = [("action", "compare"), ("targt", "public"), ("output", "json")]
        search_files = [("spectrum", "jcamp-test.jdx", open("jcamp-test.jdx").read())]
        conn = httplib.HTTPConnection("cooper-redhen.appspot.com")
        body1, headers1 = self.post_multipart(sugg_data)
        body2, headers2 = self.post_multipart(search_data, search_files)

        for key in xrange(100):
            conn.request("POST", "/api", body1, headers1)
            res = conn.getresponse()
            res.read()
            print "SEARCH  ", num, " ", key, ":", res.status, res.reason
            if res.status != 200:
                raise Exception()
            conn.request("POST", "/api", body2, headers2)
            res = conn.getresponse()
            res.read()
            print "COMPARE ", num, " ", key, ":", res.status, res.reason
            if res.status != 200:
                raise Exception()
    
    def post_multipart(self, fields, files=[]):
        """
        Post fields and files to an http host as multipart/form-data.
        fields is a sequence of (name, value) elements for regular form fields.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files
        Return the server's response page.
        """
        BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
        CRLF = '\r\n'
        L = []
        for (key, value) in fields:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        for (key, filename, value) in files:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            L.append('Content-Type: %s' % 'application/octet-stream')
            L.append('')
            L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)

        headers = {"Content-type": 'multipart/form-data; boundary=%s' % BOUNDARY,
                          "Content-length": str(len(body))}
        return body, headers

for num in xrange(50):
    Thread(num).start()
