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

STATS_OT = ["mc-ep_queue_size", "mc-ep_commit_time", "mc-curr_items", "mc-curr_items_tot",  "mc-ep_overhead", 
            "mc-ep_oom_errors", "mc-ep_bg_fetched",
            "mc-ep_tap_bg_fetched", "mc-ep_access_scanner_num_items", "mc-ep_tap_backfill_resident",
            "mc-vb_active_perc_mem_resident", "mc-vb_replica_perc_mem_resident", "mc-vb_active_ops_delete",
            "mc-vb_active_ops_create", "mc-vb_active_ops_update", "mc-vb_replica_queue_size"]

STATS_AVG = ["mc-ep_queue_size", "mc-ep_commit_time", "mc-ep_bg_max_wait", "mc-ep_bg_wait_avg", "mc-vb_active_ops_delete",
             "mc-vb_active_ops_create", "mc-vb_active_ops_update", "mc-vb_replica_queue_size"]

STATS_90 = ["mc-ep_bg_max_wait", "mc-ep_bg_wait_avg"]

STATS_TIME = ["mc-ep_warmup_time"]

def get_query(metric, host_ip, bucket_name, start_time, end_time):
    """Query data using metric as key"""
    # get query response
    queries = {}
    if metric in STATS_OT:
        query_params = { "group": 15000,  # 15 seconds
                        "ptr": '/{0}'.format(metric),
                        "reducer": "avg",
                        "from": start_time,
                        "to": end_time,
                        "f": ["/mc-host", "/mc-bucket"],
                        "fv": [host_ip, bucket_name]
                       }
        query["over_time"] = query_params
    if metric in STATS_OT_AVG:
        query_params = { "group": (end_time - start_time)
                        "ptr": '/{0}'.format(metric),
                        "reducer": "avg",
                        "from": start_time,
                        "to": end_time,
                        "f": ["/mc-host", "/mc-bucket"],
                        "fv": [host_ip, bucket_name]
                       }
        query["average"] = query_params
    if metric in STATS_AVG_90:
        query_params = { "group": (end_time - start_time)
                        "ptr": '/{0}'.format(metric),
                        "reducer": "max",
                        "from": start_time,
                        "to": end_time,
                        "f": ["/mc-host", "/mc-bucket"],
                        "fv": [host_ip, bucket_name]
                       }
        query["90th"] = query_params
    if metric in STATS_TIME:
        query_params = { "group": (end_time - start_time)
                        "ptr": '/{0}'.format(metric),
                        "reducer": "max",
                        "from": start_time,
                        "to": end_time,
                        "f": ["/mc-host", "/mc-bucket"],
                        "fv": [host_ip, bucket_name]
                       }
        query["absolute_time"] = query_params

    return query

def plot_metric(db, metric, query, outdir, phase_num, phase_desc):

    if "overtime" in query.keys():
        response = db.query(query["over_time"])

        # convert data and generate sorted lists of timestamps and values
        data = dict((k, v[0]) for k, v in response.iteritems())

        timestamps = list()
        values = list()

        for timestamp, value in sorted(data.iteritems()):
            timestamps.append(int(timestamp))
            values.append(value)

        # Substract first timestamp; conver to seconds
        timestamps = [(key - timestamps[0]) / 1000 for key in timestamps]
        
        plot_metric_overtime(metric, timestamps, values, outdir, phase_num, phase_desc)
        
    for x in ["average", "90th", "absolute_time"]:

        if x in query.keys():
            response = db.query(query[x])
            data = dict((k, v[0]) for k, v in response.iteritems())
            value = data.values()[0]
            plot_metric_single_value(metric, x, value, outdir, phase_num, phase_desc)
        
def plot_metric_single_value(metric, stats_desc, value, outdir, phase_num, phase_desc):
    """Plot chart and save it as PNG file"""
    fig = figure()
    ax = fig.add_subplot(1, 1, 1)

    ax.set_title('{0}_phase_{1}_{2}'.format(metric, str(phase_num), phase_desc))
    ax.set_xlabel('{0} {1} value = {2}'.format(metric, stats_desc, value))

    fig.savefig('{0}/{1}_phase_{2}_{3}_{4}.png'.format(outdir, metric, str(phase_num), phase_desc, stats_desc))

def plot_metric_overtime(metric, keys, values, outdir, phase_num, phase_desc):
    """Plot chart and save it as PNG file"""
    fig = figure()
    ax = fig.add_subplot(1, 1, 1)

    ax.set_title('{0}_phase_{1}_{2}'.format(metric, str(phase_num), phase_desc))
    ax.set_xlabel('Time elapsed (sec)')

    grid()

    ax.plot(keys, values, '.')
    fig.savefig('{0}/{1}_phase_{2}_{3}_overtime.png'.format(outdir, metric, str(phase_num), phase_desc))

def plot_all_phases(db_name, host_ip, bucket_name, query_params):
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
            if '/' not in metric:  # views and xdcr stuff
                query = get_query(metric, host_ip, bucket_name, start_time, end_time)
                if len(query) > 0:
                    plot_metric(db, metric, query, outdir, i,  phases[str(i)].keys()[0])

#                try:
#                    subprocess.call(['convert', '{0}/*'.format(outdir), 'report.pdf'])
#                    print "PDF report was successfully generated!"
#                except OSError:
    print "All images saved to: {0}".format(outdir)
    return outdir
