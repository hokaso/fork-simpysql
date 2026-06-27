#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .MysqlConnectionpool import connectionpool
from .Connection import Connection
from functools import wraps
from ..Util.Logger import logger
import threading  # 引入 threading 解决事务的线程安全问题


class MysqlConnection(Connection):
    _instance = {}

    def __init__(self, database, config):
        if config.get('LOG_DIR', None) is not None:
            self._logger = logger.set_path(config.get('LOG_DIR', None))
        self._database = database
        self._config = config
        # 使用 threading.local 保证每个线程拥有独立的事务连接标识
        self._local = threading.local()

    # 获取一个新的连接池连接
    def _get_pool_connection(self):
        return connectionpool.connection(
            self.parse_config(self._config),
            self._database,
            self.parse_pool_config(self._config),
        )

    # 返回当前线程最近一次 insert/replace 产生的自增 id（无则 None）
    def last_insert_id(self):
        return getattr(self._local, 'last_insert_id', None)

    def execute(self, sql, cursorclass=None):
        self.log(sql)

        # 判断当前线程是否在事务中，如果在，复用事务连接；如果不在，从池里拿新连接
        in_transaction = getattr(self._local, 'transaction_conn', None) is not None
        conn = self._local.transaction_conn if in_transaction else self._get_pool_connection()

        try:
            cursor = conn.cursor(cursor=cursorclass)
            affected_rows = cursor.execute(sql)

            # 区分查询与修改的返回值
            # UNION 查询可能以 (select 开头，需要去除前导括号来判断
            sql_stripped = sql.strip().lower()
            # 去除前导括号（用于 UNION 查询如 (select...) union (select...)）
            while sql_stripped.startswith('('):
                sql_stripped = sql_stripped[1:].strip()
            if sql_stripped.startswith(('select', 'show', 'desc', 'explain')):
                data = cursor.fetchall()
            else:
                data = affected_rows

            # 在连接归还前，缓存本次插入产生的自增 id（按线程隔离）。
            # 连接池模式下 lastid() 不能再开新连接查询 last_insert_id()，
            # 必须复用插入语句所在的这条连接的值。
            if sql_stripped.startswith(('insert', 'replace')):
                self._local.last_insert_id = cursor.lastrowid

            # 非事务状态下，单条语句执行完立即 commit
            if not in_transaction:
                conn.commit()

            cursor.close()
            return data

        finally:
            # 如果不在事务中，用完立刻归还（关闭）连接
            if not in_transaction:
                conn.close()

    def transaction(self, callback):
        # 检查是否已经是嵌套事务
        is_nested = getattr(self._local, 'transaction_conn', None) is not None
        conn = self._local.transaction_conn if is_nested else self._get_pool_connection()

        if not is_nested:
            self._local.transaction_conn = conn

        try:
            result = callback()
            # 只有最外层事务才执行真正的 commit
            if not is_nested:
                conn.commit()
            return result
        except Exception as e:
            # 任何一层报错，外层连接回滚
            if not is_nested:
                conn.rollback()
            raise e
        finally:
            # 只有最外层才负责归还连接并清空标志
            if not is_nested:
                conn.close()
                self._local.transaction_conn = None

    def transaction_wrapper(self, callback):
        @wraps(callback)
        def wrapper(*args, **kwargs):
            return self.transaction(lambda: callback(*args, **kwargs))
        return wrapper

    @classmethod
    def instance(cls, database, config):
        if cls._instance.get(database, None) is None:
            cls._instance[database] = MysqlConnection(database, config)
        return cls._instance.get(database, None)

    def parse_config(self, config):
        parsed = {
            'host': config.get('DB_HOST', ''),
            'port': int(config.get('DB_PORT', '')),
            'user': config.get('DB_USER', ''),
            'password': config.get('DB_PASSWORD', ''),
            'db': config.get('DB_NAME', ''),
            'charset': config.get('DB_CHARSET', ''),
        }
        # 可选连接超时（秒），透传给 pymysql.connect。
        # 不配置 = 保持 pymysql 默认（connect 默认 10s、read/write 无超时），行为与旧版完全一致。
        # 跨 WAN / 跨机房连库时强烈建议配置 read/write_timeout，避免链路抖动把调用线程无限挂死。
        for env_key, pymysql_key in (
            ('DB_CONNECT_TIMEOUT', 'connect_timeout'),
            ('DB_READ_TIMEOUT', 'read_timeout'),
            ('DB_WRITE_TIMEOUT', 'write_timeout'),
        ):
            value = config.get(env_key)
            if value not in (None, ''):
                parsed[pymysql_key] = int(value)
        return parsed

    def parse_pool_config(self, config):
        # 可选连接池参数（DBUtils PooledDB）。不配置 = 使用 MysqlConnectionpool 内置默认值，
        # 行为与旧版完全一致。跨 WAN 建议设置有限的 DB_POOL_MAX_USAGE 以回收长寿连接。
        pool = {}
        for env_key, pool_key in (
            ('DB_POOL_MAX', 'maxconnections'),
            ('DB_POOL_MIN_CACHED', 'mincached'),
            ('DB_POOL_MAX_CACHED', 'maxcached'),
            ('DB_POOL_MAX_USAGE', 'maxusage'),
            ('DB_POOL_PING', 'ping'),
        ):
            value = config.get(env_key)
            if value not in (None, ''):
                pool[pool_key] = int(value)
        return pool
