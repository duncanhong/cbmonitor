import os
import sys
import urllib2
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Image
from reportlab.lib import utils
import os, glob
import plotter
from optparse import OptionParser
import json

def parse_args():
    """Parse CLI arguments"""
    usage = "usage: %prog database ip1,ip2 bucket_name plot_query\n\n" +\
            "Example: %prog fast 10.1.1.1,10.1.1.2 default {\"group\": 15000}"

    parser = OptionParser(usage)
    options, args = parser.parse_args()

    if len(args) < 3 :
        parser.print_help()
        sys.exit()

    return args

length = len(parse_args())
db_name = parse_args()[0]
host_ips = parse_args()[1].split(",")
buckets_names = parse_args()[2].split(",")
query_params = ''
if length > 3:
    query_params = json.loads(parse_args()[3])

for host_ip in host_ips:
    for bucket_name in bucket_name:
        path = plotter.plot_all_phases(db_name, host_ip, bucket_name, query_params)

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
