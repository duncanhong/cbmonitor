import re
import time
import testcfg as cfg
from seriesly import Seriesly
from lib.membase.api.rest_client import RestConnection
from lib.remote.remote_util import RemoteMachineShellConnection

def _dict_to_obj(dict_):
    return type('OBJ', (object,), dict_)

def create_server_obj(server_ip=cfg.COUCHBASE_IP, port=cfg.COUCHBASE_PORT,
                      username=cfg.COUCHBASE_USER, password=cfg.COUCHBASE_PWD):
    serverInfo = { "ip" : server_ip,
                   "port" : port,
                   "rest_username" : username,
                   "rest_password" :  password
    }
    node = _dict_to_obj(serverInfo)
    return node

def create_rest(server_ip=cfg.COUCHBASE_IP, port=cfg.COUCHBASE_PORT,
                username=cfg.COUCHBASE_USER, password=cfg.COUCHBASE_PWD):
    return RestConnection(create_server_obj(server_ip, port, username, password))

def create_ssh_conn(server_ip = '', port=22, username = cfg.SSH_USER,
               password = cfg.SSH_PASSWORD, os='linux'):
    if isinstance(server_ip, unicode):
        server_ip = str(server_ip)

    serverInfo = {"ip" : server_ip,
                  "port" : port,
                  "ssh_username" : username,
                  "ssh_password" : password,
                  "ssh_key": '',
                  "type": os
                }

    node = _dict_to_obj(serverInfo)
    shell = RemoteMachineShellConnection(node)
    return shell, node

def restart_atop(ip):
    stop_atop(ip)
    start_atop(ip)

def stop_atop(ip):
    cmd = "killall atop"
    exec_cmd(ip, cmd)
    # Clean up load log
    cmd = "rm -rf %s" % cfg.ATOP_LOG_FILE
    exec_cmd(ip, cmd)

def start_atop(ip):
    # Start atop again
    cmd = "nohup %s > /dev/null 2>&1&" % atop_proc_sig()
    exec_cmd(ip, cmd)

def atop_proc_sig():
    return "atop -a -w %s 3" % cfg.ATOP_LOG_FILE

def check_atop_proc(ip):
    running = False
    proc_signature = atop_proc_sig()
    res = exec_cmd(ip, "ps aux |grep '%s' | wc -l " % proc_signature)

    # one for grep, one for atop and one for bash
    # Making sure, we always have one such atop
    if int(res[0][0]) != 3:
        running = True

    return running

def update_node_stats(db, sample, ip):
    db.append(sample)

def resource_monitor(interval=30):

    rest = create_rest()
    nodes = rest.node_statuses()
    atop_db = Seriesly(cfg.SERIESLY_IP, 3133)
 
    if "atop" in atop_db.list_dbs():
        atop_db = atop_db['atop']
    else:
        atop_db.create_db('atop')
        atop_db = atop_db['atop']

    while True:
        for node in nodes:

            # check if atop running (could be new node)
            if isinstance(node.ip, unicode):
                node.ip = str(node.ip)
            if check_atop_proc(node.ip):
                restart_atop(node.ip)

            # get stats from node
            sample = get_atop_sample(node.ip)

            update_node_stats(atop_db, sample, node.ip)
            
            time.sleep(interval)

def get_atop_sample(ip):

    sample = {"ip" : ip}
    cpu = atop_cpu(ip)
    mem = atop_mem(ip)
    mem_mc = atop_mem_mc(ip)
    swap = sys_swap(ip)
    disk = atop_dsk(ip)
    if cpu:
        sample.update({"sys_cpu" : cpu[0],
                       "usr_cpu" : cpu[1]})
    if mem:
        sample.update({"vsize" : mem[0],
                       "rsize" : mem[1]})

    if mem_mc:
        sample.update({"vsize_mc" : mem_mc[0],
                       "rsize_mc" : mem_mc[1]})

    if swap:
        sample.update({"swap" : swap[0][0]})

    if disk:
        sample.update({"rddsk" : disk[0],
                       "wrdsk" : disk[1],
                       "disk_util" : disk[2]})

    sample.update({"ts" : str(time.time())})

    return sample

def atop_cpu(ip):
    cmd = "grep ^CPU | grep sys | awk '{print $4,$7}' "
    return _atop_exec(ip, cmd)

def atop_mem(ip):
    flags = "-M -m"
    cmd = "grep beam.smp | head -1 |  awk '{print $5,$6}'"
    return _atop_exec(ip, cmd, flags)

def atop_mem_mc(ip):
    flags = "-M -m"
    cmd = "grep memcached | head -1 |  awk '{print $5,$6}'"
    return _atop_exec(ip, cmd, flags)

def sys_swap(ip):
    cmd = "free | grep Swap | awk '{print $3}'"
    return exec_cmd(ip, cmd)

def atop_dsk(ip):
    flags = "-d"
    cmd_column = "atop -r /tmp/atop-node.log -d | grep beam.smp | head -1 | awk '{print NF}'"
    count = exec_cmd(ip, cmd_column)
    cmd = "grep beam.smp | awk '{print $2, $3, $5}'"
    if len(count[0]) > 0:
        count = int(count[0][0])
        rcol = count - 4
        wcol = count - 3
        pcol = count - 1
        cmd = "grep beam.smp | awk '{print $%d, $%d, $%d}'" % (rcol, wcol, pcol)
    else:
        logger.error(count[1][0])
    return _atop_exec(ip, cmd, flags)

def _atop_exec(ip, cmd, flags = ""):
    """ runs atop program where -b <begin_time> and -e <end_time>
    are the current times.  then filters the last sample of this collection
    via tail -1"""

    res = None

    #prefix standard atop prefix
    prefix = "date=`date +%H:%M` && atop -r "+cfg.ATOP_LOG_FILE+" -b $date -e $date " + flags
    cmd = prefix + "|" + cmd + " | tail -1"

    rc  = exec_cmd(ip, cmd)

    # parse result based on what is expected from atop commands
    if len(rc[0]) > 0:
        res = rc[0][0].split()
    return res

def exec_cmd(ip, cmd, os = "linux"):
    shell, node = create_ssh_conn(server_ip=ip, os=os)
    shell.use_sudo  = False
    return shell.execute_command(cmd, node)
