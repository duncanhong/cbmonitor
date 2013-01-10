#!/usr/bin/env python
from optparse import OptionParser
import subprocess
import sys
import time
from tempfile import mkdtemp

import matplotlib
matplotlib.use('Agg')
from matplotlib.pyplot import figure, grid
from seriesly import Seriesly
from cache import ObjCacher, CacheHelper

STATS = ["mc-curr_items"]

def stats_filter(metric):
    if len(STATS) == 0:
        return True
    for x in STATS:
        if x.find(metric) != -1:
            return True
    return False

def get_metric(db, metric, host_ip, bucket_name, query_params):
    """Query data using metric as key"""
    # get query response
    if query_params == ''
       query_params = { 'group': 15000,  # 15 seconds
                        'ptr': '/{0}'.format(metric),
                        'reducer': 'avg'}
                        'f': 'mc-host'
                        'fv': host_ip
                      }
    response = db.query(query_params)

    # convert data and generate sorted lists of timestamps and values
    data = dict((k, v[0]) for k, v in response.iteritems())

    timestamps = list()
    values = list()

    for timestamp, value in sorted(data.iteritems()):
        timestamps.append(int(timestamp))
        values.append(value)

    # Substract first timestamp; conver to seconds
    timestamps = [(key - timestamps[0]) / 1000 for key in timestamps]

    return timestamps, values

def plot_metric(metric, keys, values, outdir):
    """Plot chart and save it as PNG file"""
    fig = figure()
    ax = fig.add_subplot(1, 1, 1)

    ax.set_title(metric)
    ax.set_xlabel('Time elapsed (sec)')

    grid()

    ax.plot(keys, values, '.')
    fig.savefig('{0}/{1}.png'.format(outdir, metric))


def parse_args():
    """Parse CLI arguments"""
    usage = "usage: %prog database\n\n" +\
            "Example: %prog ns_db "

    parser = OptionParser(usage)
    options, args = parser.parse_args()

    if len(args) != 1:
        parser.print_help()
        sys.exit()

    return args[0]


def main(db_name, host_ip, bucket_name, query_params):
    # parse database name from cli arguments
    #db_name = parse_args()

    # initialize seriesly client
    db = Seriesly()[db_name]

    # plot all metrics to PNG images
    outdir = mkdtemp()
    
    # get a set of all unique keys based on time range
    all_docs = db.get_all()
    all_keys = set(key for doc in all_docs.itervalues()
                    for key in doc.iterkeys())

    # get system test phase info and plot phase by phase
    graph_phases = CacheHelper.graph_phases()
    if len(graph_phases) > 0:
        for phases in graph_phases:
            #print phases.graph_phase_info
            num_phases = len(phases)
            for i in range(num_phases):
                start_time = phases[str(i)].values()[0]
                end_time =0
                if i == num_phases-1:
                    end_time = time.time()
                else:
                    end_time = phases[str(i+1)].values()[0]

                for metric in all_keys:
                    #print metric
                    if '/' not in metric and stats_filter(metric) == True:  # views and xdcr stuff
                        keys, values = get_metric(db, metric, host_ip, bucket_name, query_params)
                        plot_metric(metric, keys, values, outdir)

                try:
                    subprocess.call(['convert', '{0}/*'.format(outdir), 'report.pdf'])
                    print "PDF report was successfully generated!"
                except OSError:
                    print "All images saved to: {0}".format(outdir)
    return outdir

if __name__ == '__main__':
    main()
