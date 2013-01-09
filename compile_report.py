import os
import sys
import urllib2
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Image
from reportlab.lib import utils
import os, glob
import plotter
from optparse import OptionParser

def parse_args():
    """Parse CLI arguments"""
    usage = "usage: %prog database ip1,ip2\n\n" +\
            "Example: %prog fast 10.1.1.1,10.1.1.2"

    parser = OptionParser(usage)
    options, args = parser.parse_args()

    if len(args) != 2:
        parser.print_help()
        sys.exit()

    return args

db_name = parse_args()[0]
host_ips = parse_args()[1].split(",")
#plot_path = "couchbase-2.0/cbmonitor/plotter.py " + db_name 
#path = os.system(plot_path)

for host_ip in host_ips:
    path = plotter.main(db_name, host_ip)
    #print path

    filenames = []
    for infile in glob.glob(os.path.join(path, '*.png')):
	filenames.append(infile)

    w = 400
    parts = []
    doc = SimpleDocTemplate("report_{0}_{1}.pdf".format(db_name, host_ip), pagesize=letter)
    for i in filenames:
	img = utils.ImageReader(i)
	iw, ih = img.getSize()
	aspect = ih / float(iw)
	parts.append(Image(i, width=w, height=w * aspect))
    doc.build(parts)
