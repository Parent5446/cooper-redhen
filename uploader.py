"""
Take a directory of JCAMP files, store the data in a CSV file, and transfer
the file to the Google Data Store.

Usage:
./uploader.py <appcfg.py> <directory>
 - appcfg.py : Path to Google App Engine's appcfg.py script
 - directory : Directory to scan for JCAMP files

NOTE: The directory given must contain only JCAMP files. Furthermore, this
script will process recursively, so subdirectories will also be checked.

@todo: Create script to update the matcher.
"""

from __future__ import with_statement
import re
import os
import sys
import bisect
import tempfile

def main_client(appcfg, dirname, recursive=False):
    """
    Extract all files from a directory and transfer them to the server.
    
    @param dirname: Name of the directory
    @type  dirname: C{str}
    @raise Exception: If the given file name is not a directory
    """
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        chem_types = flat_heavyside = ordered_heavyside = high_low = {}
        peak_list = []
        csvfile = fp.name
        fp.write("chemcial_name,chemical_type,spectrum_type,xvalues,yvalues\n")
        if not os.path.exists(dirname) or not os.path.isdir(dirname):
            raise Exception("Not a directory.")
        files = os.listdir(dirname)
        for file_name in files:
            if os.path.isdir(file_name):
                if recursive:
                    main_client(file_name)
                else:
                    continue
            with open(file_name) as file_obj:
                contents = file_obj.read()
                chemical_name = get_field(contents, '##TITLE=')
                chemical_type = 'Unknown'
                spectrum_type = 'Infrared'
                xvalues, yvalues = get_data(contents)
                # AppEngine require integer lists to have 'L' at the end of
                # each value.
                xvalues = '[' + 'L, '.join([str(x) for x in xvalues]) + 'L]'
                fp.write('"%s","%s","%s","%s","%s"' % (chemical_name,
                           chemical_type, spectrum_type, xvalues, str(yvalues)))
    raise Exception(csvfile)
    os.execl(appcfg, "upload_data", "--config_file=bulkloader.yaml",
             "--filename=%s" % csvfile, "--kind=Spectrum",
             "--url=http://cooper-redhen.appspot.com/upload")

def transfer(file_obj):
    """
    Submit a POST request to the server with the spectrum information.
    
    @param file_obj: Filename to upload
    @type  file_obj: C{str}
    @raise Exception: If the server gave a response code other than 200
    """
    

def get_field(contents, name):
    '''
    Get a specific data label from the file.
    
    @param name: Name of data label to retrieve
    @type  name: C{str}
    @return: Value of the data label
    @rtype: C{str}
    
    @warning: Does not support Windows-style line breaks.
    '''
    # FIXME: Does not support Windows format.
    index = contents.index(name) + len(name)
    return contents[index:contents.index('\n', index)].strip()

def get_data(contents):
    '''
    Parse a string of JCAMP file data and extract all needed data.
   
    Search a JCAMP file for the chemical's name, type, and spectrum data.
    Then integrate the X, Y data and store alGet a specific data label from
    the file.l variables in the object.
    
    @warning: Does not handle Windows-format line breaks.
    @param contents: String containing spectrum information
    @type  contents: C{unicode} or C{str}
    '''
    x = float(get_field(contents, '##FIRSTX=')) # The first x-value
    delta_x = float(get_field(contents, '##DELTAX=')) # The Space between adjacent x values
    x_factor = float(get_field(contents, '##XFACTOR=')) # for our purposes it's 1, but if not use this instead
    y_factor = float(get_field(contents, '##YFACTOR=')) # some very small number, but if not use this instead
    xy = []
    # Process the XY data from JCAMP's (X++(Y..Y)) format.
    raw_xy = contents[contents.index('##XYDATA=(X++(Y..Y))') + 20:]
    pattern = re.compile(r'(\D+)([\d.-]+)')
    for match in re.finditer(pattern, raw_xy):
        if '\n' in match.group(1):
            # Number is the first on the line and is an x-value
            x = float(match.group(2)) * x_factor
        else:
            # Number is a relative y-value.
            xy.append((x, float(match.group(2)) * y_factor))
            x += delta_x
    # Keep the data in ascending order. It will be descending in the file
    # if our delta X is negative.
    if delta_x < 0:
        xy.reverse()
    # Integrate xy numerically over a fixed range.
    xvalue_range = (700.0, 3900.0)
    # Initialize the data and find the interval of integration.
    data = [0.0 for i in xrange(1000)]
    interval = (xvalue_range[1] - xvalue_range[0]) / len(data)
    # Find index in xy where integrals start
    start = bisect.bisect_left(xy, (xvalue_range[0], 0))
    # oldX = start of range, oldY = linear interpolation of corresponding y
    oldX, oldY = xvalue_range[0], (xy[start - 1][1] +
         (xy[start][1] - xy[start - 1][1]) * (xvalue_range[0] - xy[start][0]) /
         (xy[start - 1][0] - xy[start][0]))
    for x, y in xy[start:]: #Iterate over xy from start
        newIndex = int((x - xvalue_range[0]) / interval)
        oldIndex = int((oldX - xvalue_range[0]) / interval)
        if newIndex != oldIndex:
            # We're starting a new integral.
            boundary = newIndex * interval,\
                       ((y - oldY) * (newIndex * interval - oldX) /
                       (x - oldX) + oldY) #Linear interpolation
            data[oldIndex] += (boundary[1] + oldY) * (boundary[0] - oldX) / 2
            if newIndex < len(data): # if data isn't filled 
                data[newIndex] += (boundary[1] + y) * (x - boundary[0]) / 2
        else:
            data[newIndex] += (y + oldY) * (x - oldX) / 2
        if x > xvalue_range[1]:
            break #If finished, break
        oldX, oldY = x, y #Otherwise keep going
    return (range(int(xvalue_range[0]), int(xvalue_range[0] + len(data))), data)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print __doc__
    else:
        main_client(sys.argv[1], sys.argv[2], True)
