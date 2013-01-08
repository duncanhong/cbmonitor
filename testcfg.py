#TODO: allow workers to pull this from cache

RABBITMQ_IP = '10.3.2.86'
OBJECT_CACHE_IP = "10.6.2.58"
OBJECT_CACHE_PORT = "11911"
SERIESLY_IP = '10.6.2.58'
COUCHBASE_IP = '10.5.2.22'
COUCHBASE_PORT = '8091'
COUCHBASE_USER = "Administrator"
COUCHBASE_PWD = "password"
SSH_USER = "root"
SSH_PASSWORD = "couchbase"
WORKERS = ['127.0.0.1']
# valid configs ["kv","query","admin","stats"] or ["all"]
WORKER_CONFIGS = ["all"]
CB_CLUSTER_TAG = "test"
ATOP_LOG_FILE = "/tmp/atop-node.log"
LOGDIR="logs"  # relative to current dir

#Backup Config
ENABLE_BACKUPS = False
BACKUP_DIR = "/tmp/backup"
BACKUP_NODE_IP = "10.3.3.183"
BACKUP_NODE_SSH_USER = "Administrator"
BACKUP_NODE_SSH_PWD = "Membase123"
