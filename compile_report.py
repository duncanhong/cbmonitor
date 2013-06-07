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
    usage = "usage: %prog database ip1,ip2 bucket_name \n\n" +\
            "Example: %prog fast 10.1.1.1,10.1.1.2 default"

    parser = OptionParser(usage)
    parser.add_option("-g", "--graph_only", help="only generate zip file for all graphes", action="store_true", dest="graph")
    options, args = parser.parse_args()

    if len(args) < 3 :
        parser.print_help()
        sys.exit()

    return options, args

options, args = parse_args()

db_name = args[0]
host_ips = args[1].split(",")
bucket_names = args[2].split(",")

for host_ip in host_ips:
    for bucket_name in bucket_names:
        path, run_id = plotter.plot_all_phases(db_name, host_ip, bucket_name)

        if not options.graph:
            filenames = []
            for infile in glob.glob(os.path.join(path, '*.png')):
	        filenames.append(infile)
            w = 400
            parts = []
            doc = SimpleDocTemplate("report_{0}_{1}_{2}_{3}.pdf".format(db_name, host_ip, bucket_name, run_id), pagesize=letter)
            filenames.sort()
            for i in filenames:
	        img = utils.ImageReader(i)
	        iw, ih = img.getSize()
	        aspect = ih / float(iw)
	        if i.find("zz") >= 0:
	    	    w = 700
	        else:
	    	    w = 400
	        parts.append(Image(i, width=w, height=w * aspect))
            doc.build(parts)
        else:
            os.system("rm -rf {0}_{1}_{2}*".format(db_name, host_ip, bucket_name))
            os.system("cp -rf {0} {1}_{2}_{3}".format(path, db_name, host_ip, bucket_name))
            os.system("tar cvf {0}_{1}_{2}.zip {0}_{1}_{2}".format(db_name, host_ip, bucket_name))
