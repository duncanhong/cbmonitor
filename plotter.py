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

STATS = ["mc-curr_items", "mc-curr_items_tot", "mc-ep_queue_size", "mc-ep_overhead", "mc-ep_oom_errors",
         "mc-ep_bg_fetched", "mc-ep_tap_bg_fetched", "mc-ep_warmup_time", "mc-vb_active_perc_mem_resident",
         "mc-vb_replica_perc_mem_resident", "mc-vb_active_ops_delete", "mc-vb_active_ops_create",
         "mc-vb_active_ops_update", "mc-vb_replica_queue_size"]

def stats_filter(metric):
    if len(STATS) == 0:
        return True
    for x in STATS:
        if x == metric:
            return True
    return False

def get_metric(db, metric, host_ip, bucket_name, query_params, start_time, end_time):
    """Query data using metric as key"""
    # get query response
    if query_params == '':
       query_params = { "group": 15000,  # 15 seconds
                        "ptr": '/{0}'.format(metric),
                        "reducer": "avg",
                        "from": start_time,
                        "to": end_time,
                        "f": ["mc-host", "mc-bucket"],
                        "fv": [host_ip, bucket_name]
                      }
    else:
        query_params["ptr"] = "/{0}".format(metric)
        query_params["from"] = start_time
        query_params["to"] = end_time
        query_params["f"] = "mc-host"
        query_params["fv"] = host_ip

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

    return timestamps, values, query_params['reducer']

def plot_metric(metric, keys, values, outdir, phase_num, phase_desc, reducer):
    """Plot chart and save it as PNG file"""
    fig = figure()
    ax = fig.add_subplot(1, 1, 1)

    ax.set_title('{0}_phase_{1}_{2}({3})'.format(metric, str(phase_num), phase_desc, reducer))
    ax.set_xlabel('Time elapsed (sec)')

    grid()

    ax.plot(keys, values, '.')
    fig.savefig('{0}/{1}_phase_{2}_{3}.png'.format(outdir, metric, str(phase_num), phase_desc))

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


def plot_all_phases(db_name, host_ip, bucket_name, query_params):
    # parse database name from cli arguments
    #db_name = parse_args()

    # initialize seriesly client
    db = Seriesly()[db_name]
    db_event = Seriesly()['event']

    # plot all metrics to PNG images
    outdir = mkdtemp()
    
    # get a set of all unique keys based on time range
    all_docs = db.get_all()
    all_keys = set(key for doc in all_docs.itervalues()
                    for key in doc.iterkeys())

    # get system test phase info and plot phase by phase
    all_event_docs = db_event.get_all()
    phases = {}
    for doc in all_event_docs.itervalues():
        phases[doc.keys()[0]] = doc.values()[0]

    num_phases = len(phases)
    for i in range(num_phases):
        start_time = phases[str(i)].values()[0]
        start_time = int(start_time[:10])
        end_time = 0
        if i == num_phases-1:
            end_time = str(time.time())
            end_time = int(end_time[:10])
        else:
            end_time = phases[str(i+1)].values()[0]
            end_time = int(end_time[:10])

        for metric in all_keys:
            #print metric
            if '/' not in metric and stats_filter(metric) == True:  # views and xdcr stuff
                keys, values, reducer = get_metric(db, metric, host_ip, bucket_name, query_params, start_time, end_time)
                plot_metric(metric, keys, values, outdir, i,  phases[str(i)].keys()[0], reducer)

#                try:
#                    subprocess.call(['convert', '{0}/*'.format(outdir), 'report.pdf'])
#                    print "PDF report was successfully generated!"
#                except OSError:
    print "All images saved to: {0}".format(outdir)
    return outdir

#if __name__ == '__main__':
#    main()
