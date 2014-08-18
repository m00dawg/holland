import logging
import time

LOG = logging.getLogger(__name__)

class FlushAndLockMySQLAction(object):
    def __init__(self,
                 client,
                 lock_tables=True,
                 extra_flush=True,
                 stop_slave=False):
        self.client = client
        self.lock_tables = lock_tables
        self.extra_flush = extra_flush
        self.stop_slave = stop_slave
        self.slave_stopped_when = None
        self.mysql_locked_when = None

    def __call__(self, event, snapshot_fsm, snapshot_vol):
        if event == 'pre-snapshot':
            if self.stop_slave:
                LOG.info("mysql> STOP SLAVE SQL_THREAD;")
                click = time.time()
                self.client.stop_slave(sql_thread_only=True)
                self.slave_stopped_when = time.time()
                LOG.info("- Stopped in %.3f seconds", time.time() - click)
            if self.extra_flush:
                click = time.time()
                LOG.info("mysql> FLUSH /*!40101 LOCAL */ TABLES;");
                self.client.flush_tables()
                LOG.info("- Tables flushed in %.3f seconds", time.time() - click)
            if self.lock_tables:
                click = time.time()
                LOG.info("mysql> FLUSH TABLES WITH READ LOCK")
                self.client.flush_tables_with_read_lock()
                self.mysql_locked_when = time.time()
                LOG.info("- MySQL locked in %.3f seconds", time.time() - click)
        elif event == 'post-snapshot':
            if self.lock_tables:
                LOG.info("mysql> UNLOCK TABLES;")
                self.client.unlock_tables()
                LOG.info("MySQL locked for %.3f seconds", time.time() - self.mysql_locked_when)
            if self.stop_slave:
                self.client.start_slave()
                LOG.info("mysql> START SLAVE;")
                LOG.info("MySQL replication stopped for %.3f seconds",
                         time.time() - self.slave_stopped_when)
