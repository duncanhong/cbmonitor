import os
import urllib2
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Image
from reportlab.lib import utils
import os, glob
import plotter
from optparse import OptionParser

def parse_args():
    """Parse CLI arguments"""
    usage = "usage: %prog database\n\n" +\
            "Example: %prog fast "

    parser = OptionParser(usage)
    options, args = parser.parse_args()

    if len(args) != 1:
        parser.print_help()
        sys.exit()

    return args[0]

db_name = parse_args()
#plot_path = "couchbase-2.0/cbmonitor/plotter.py " + db_name 
#path = os.system(plot_path)

path = plotter.main(db_name)
#print path

filenames = []
for infile in glob.glob(os.path.join(path, '*.png')):
	filenames.append(infile)

w = 400
parts = []
doc = SimpleDocTemplate("report_{0}.pdf".format(db_name), pagesize=letter)
for i in filenames:
	img = utils.ImageReader(i)
	iw, ih = img.getSize()
	aspect = ih / float(iw)
	parts.append(Image(i, width=w, height=w * aspect))
doc.build(parts)
