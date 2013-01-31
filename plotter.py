#!/usr/bin/env python
from optparse import OptionParser
import subprocess
import sys
import time
from tempfile import mkdtemp

import matplotlib
matplotlib.use('Agg')
from matplotlib.pyplot import figure, grid, table
from seriesly import Seriesly


STATS_OT = ["mc-ep_queue_size", "mc-ep_commit_time", "mc-curr_items", "mc-curr_items_tot",  "mc-ep_overhead", 
            "mc-ep_oom_errors", "mc-ep_bg_fetched", "mc-vb_active_expired",
            "mc-ep_tap_bg_fetched", "mc-ep_access_scanner_num_items", "mc-ep_tap_backfill_resident",
            "mc-vb_active_perc_mem_resident", "mc-vb_replica_perc_mem_resident", "mc-vb_replica_queue_size", "mc-ep_diskqueue_drain"]

STATS_AVG = ["mc-ep_queue_size", "mc-ep_commit_time", "mc-ep_bg_max_wait", "mc-ep_bg_wait_avg", "mc-vb_replica_queue_size"]

STATS_90 = ["mc-ep_bg_max_wait", "mc-ep_bg_wait_avg"]

STATS_TIME = ["mc-ep_warmup_time"]

NS_STATS_OT = ["cpu_utilization_rate", "opsPerSec", "diskUsed", "dataUsed", "memUsed"]

ATOP_STATS_OT = ["cpu_beam", "cpu_mc", "swap", "rsize_beam", "rsize_mc", "rddsk", "wrdsk"]

ATOP_STATS_90 = ["cpu_beam", "cpu_mc", "rsize_beam", "rsize_mc"]

AVG_TABLE = {}

Nth_TABLE = {}

TIME_TABLE = {}

def get_query(metric, host_ip, bucket_name, start_time, end_time):
    """Query data using metric as key"""
    # get query response
    query = {}
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
    if metric in STATS_AVG:
        query_params = { "group": 300000,
                        "ptr": '/{0}'.format(metric),
                        "reducer": "avg",
                        "from": start_time,
                        "to": end_time,
                        "f": ["/mc-host", "/mc-bucket"],
                        "fv": [host_ip, bucket_name]
                       }
        query["average"] = query_params
    if metric in STATS_90:
        query_params = { "group": 300000,
                        "ptr": '/{0}'.format(metric),
                        "reducer": "max",
                        "from": start_time,
                        "to": end_time,
                        "f": ["/mc-host", "/mc-bucket"],
                        "fv": [host_ip, bucket_name]
                       }
        query["90th"] = query_params
    if metric in STATS_TIME:
        query_params = { "group": (end_time - start_time)*1000,
                        "ptr": '/{0}'.format(metric),
                        "reducer": "any",
                        "from": start_time,
                        "to": end_time,
                        "f": ["/mc-host", "/mc-bucket"],
                        "fv": [host_ip, bucket_name]
                       }
        query["absolute_time"] = query_params
        
    if metric in NS_STATS_OT:
        query_params = { "group": 15000,
                        "ptr": '/{0}'.format(metric),
                        "reducer": "avg",
                        "from": start_time,
                        "to": end_time
                       }
        query["over_time"] = query_params

    if metric in ATOP_STATS_OT:
        query_params = { "group": 15000,  # 15 seconds
                        "ptr": '/{0}'.format(metric),
                        "reducer": "avg",
                        "from": start_time,
                        "to": end_time,
                        "f": ["/ip"],
                        "fv": [host_ip]
                       }
        query["over_time"] = query_params

    if metric in ATOP_STATS_90:
        query_params = { "group": 300000,
                        "ptr": '/{0}'.format(metric),
                        "reducer": "max",
                        "from": start_time,
                        "to": end_time,
                        "f": ["/ip"],
                        "fv": [host_ip]
                       }
        query["90th"] = query_params

    return query

def plot_metric(db, metric, query, outdir, phase_num, phase_desc):

    if "over_time" in query.keys():
        response = db.query(query["over_time"])

        # convert data and generate sorted lists of timestamps and values
        data = dict((k, v[0]) for k, v in response.iteritems())

        timestamps = list()
        values = list()
        sample_count = 0

        for timestamp, value in sorted(data.iteritems()):
            timestamps.append(int(timestamp))
            values.append(value)
            if value is not None:
                sample_count = sample_count + 1

        if sample_count >= 12:
            # Substract first timestamp; conver to seconds
            timestamps = [(key - timestamps[0]) / 1000 for key in timestamps]

            plot_metric_overtime(metric, timestamps, values, outdir, phase_num, phase_desc)

    if "average" in query.keys():
        response = db.query(query["average"])
        data = dict((k, v[0]) for k, v in response.iteritems())
        values = list()

        for timestamp, value in data.iteritems():
            values.append(value)

        values = [x for x in values if x is not None]
        sum = 0
        average_value = None
        if len(values) >= 1:
            for x in values:
                sum = sum + x
            average_value = sum / len(values)

            store_metric_single_value(metric, "average", average_value, phase_num)

    if "90th" in query.keys():
        response = db.query(query["90th"])
        data = dict((k, v[0]) for k, v in response.iteritems())
        values = list()

        for timestamp, value in data.iteritems():
            values.append(value)

        values = [x for x in values if x is not None]
        value = None
        if len(values) >= 1:
            values.sort()
            pos = int(len(values) * 0.9)
            value = values[pos]

            store_metric_single_value(metric, "90th", value, phase_num)

    if "absolute_time" in query.keys():
        response = db.query(query["absolute_time"])
        data = dict((k, v[0]) for k, v in response.iteritems())
        value = None
        if len(data) > 0:
            value = data.values()[0]

            store_metric_single_value(metric, "absolute_time", value, phase_num)

def store_metric_single_value(metric, stats_desc, value, phase_num):
    "store all the single value to one table"
    if stats_desc == "average":
        if metric in AVG_TABLE.keys():
            AVG_TABLE[metric].update({phase_num: value})
        else:
            AVG_TABLE[metric] = {}
            AVG_TABLE[metric].update({phase_num: value})
    elif stats_desc == "90th":
        if metric in Nth_TABLE.keys():
            Nth_TABLE[metric].update({phase_num: value})
        else:
            Nth_TABLE[metric] = {}
            Nth_TABLE[metric].update({phase_num: value})
    elif stats_desc == "absolute_time":
        if metric in TIME_TABLE.keys():
            TIME_TABLE[metric].update({phase_num: value})
        else:
            TIME_TABLE[metric] = {}
            TIME_TABLE[metric].update({phase_num: value})

def plot_metric_single_value(stats_desc, outdir, num_phases):
    """Plot chart and save it as PNG file"""
    matrix = None
    if stats_desc == "average":
        matrix = AVG_TABLE
    elif stats_desc == "90th":
        matrix = Nth_TABLE
    elif stats_desc == "absolute_time":
        matrix = TIME_TABLE

    if len(matrix) > 0:
        fig = figure()
        ax = fig.add_subplot(1, 1, 1)
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)
        ax.set_title('{0}_Value'.format(stats_desc))

        table_vals = []
        col_labels = []
        row_labels = []
        for k in matrix.iterkeys():
            temp_list = []
            for i in range(num_phases):
                if  i in matrix[k].keys():
                    temp_list.append(matrix[k][i])
                else:
                    temp_list.append(None)

            table_vals.append(temp_list)
            col_labels.append(k)

        invert_table = []
        for i in len(table_vals[0]):
            temp_list = []
            for j in len(table_vals):
                temp_list.append(table_vals[j][i])
            invert_table.append(temp_list)

        for i in range(num_phases):
            row_labels.append("P %d" % (i))

        table(cellText=invert_table, colWidths = [0.2]*len(col_labels), rowLabels=row_labels,
              colLabels=col_labels, loc='center')

        fig.savefig('{0}/zz-{1}_value.png'.format(outdir, stats_desc))

def plot_metric_overtime(metric, keys, values, outdir, phase_num, phase_desc):
    """Plot chart and save it as PNG file"""
    fig = figure()
    ax = fig.add_subplot(1, 1, 1)

    ax.set_title('{0}_phase_{1}_{2}'.format(metric, str(phase_num), phase_desc))
    ax.set_xlabel('Time elapsed (sec)')

    grid()

    ax.plot(keys, values, '.')
    fig.savefig('{0}/{1}_phase_{2}_{3}_overtime.png'.format(outdir, metric, str(phase_num), phase_desc))

def plot_all_phases(db_name, host_ip, bucket_name):
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
    phases_info = {}
    for doc in all_event_docs.itervalues():
        phases_info[int(doc.keys()[0])] = doc.values()[0]
    phases_info.keys().sort()

    phases = []
    for v in phases_info.itervalues():
        phases.append(v)
    num_phases = len(phases)
    run_id = ''

    for i in range(num_phases):
        if i == 0:
            run_id = phases[i]['run_id']

        start_time = phases[i].values()[0]
        start_time = int(start_time[:10])
        end_time = 0
        if i == num_phases-1:
            end_time = str(time.time())
            end_time = int(end_time[:10])
        else:
            end_time = phases[i+1].values()[0]
            end_time = int(end_time[:10])

        for metric in all_keys:
            #print metric
            if '/' not in metric:  # views and xdcr stuff
                query = get_query(metric, host_ip, bucket_name, start_time, end_time)
                if len(query) > 0:
                    plot_metric(db, metric, query, outdir, i,  phases[i].keys()[0])

#                try:
#                    subprocess.call(['convert', '{0}/*'.format(outdir), 'report.pdf'])
#                    print "PDF report was successfully generated!"
#                except OSError:
    plot_metric_single_value("average", outdir, num_phases)
    plot_metric_single_value("90th", outdir, num_phases)
    plot_metric_single_value("absolute_time", outdir, num_phases)

    print "All images saved to: {0}".format(outdir)
    return outdir, run_id
