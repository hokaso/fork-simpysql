#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨 WAN 连接加固单元测试（0.0.4 新增）。

只验证 parse_config / parse_pool_config 这两个纯函数的取值逻辑，不连真实数据库：
- 不配置新键 → 输出与旧版完全一致（向后兼容）
- 配置新键 → 正确透传为 pymysql / PooledDB 参数

集成验证（需真实库，手动跑）：把某个 model 的 .env 配上
``DB_READ_TIMEOUT=1``，对它执行 ``SELECT SLEEP(3)``，应在 ~1s 内抛
pymysql.err.OperationalError，而不是一直挂住。
"""

import pytest

from simpysql.Connections.MysqlConnection import MysqlConnection

BASE_CONFIG = {
    'DB_TYPE': 'mysql',
    'DB_HOST': '10.0.0.1',
    'DB_PORT': '3306',
    'DB_USER': 'u',
    'DB_PASSWORD': 'p',
    'DB_NAME': 'db',
    'DB_CHARSET': 'utf8mb4',
}


def _make(extra=None):
    """构造一个 MysqlConnection（不触发真实连接，parse_* 是纯函数）。"""
    cfg = dict(BASE_CONFIG)
    if extra:
        cfg.update(extra)
    return MysqlConnection('default', cfg)


@pytest.mark.transaction
def test_parse_config_base_unchanged():
    conn = _make()
    parsed = conn.parse_config(conn._config)
    assert parsed['host'] == '10.0.0.1'
    assert parsed['port'] == 3306
    assert parsed['user'] == 'u'
    assert parsed['db'] == 'db'
    assert parsed['charset'] == 'utf8mb4'
    # 未配置超时 → 不出现，保持 pymysql 默认（向后兼容）
    assert 'connect_timeout' not in parsed
    assert 'read_timeout' not in parsed
    assert 'write_timeout' not in parsed


@pytest.mark.transaction
def test_parse_config_with_timeouts():
    conn = _make({
        'DB_CONNECT_TIMEOUT': '5',
        'DB_READ_TIMEOUT': '120',
        'DB_WRITE_TIMEOUT': '120',
    })
    parsed = conn.parse_config(conn._config)
    assert parsed['connect_timeout'] == 5
    assert parsed['read_timeout'] == 120
    assert parsed['write_timeout'] == 120


@pytest.mark.transaction
def test_parse_config_blank_timeout_ignored():
    conn = _make({'DB_READ_TIMEOUT': '', 'DB_WRITE_TIMEOUT': '   '.strip()})
    parsed = conn.parse_config(conn._config)
    # 空串视为未配置
    assert 'read_timeout' not in parsed
    assert 'write_timeout' not in parsed


@pytest.mark.transaction
def test_parse_pool_config_empty():
    conn = _make()
    assert conn.parse_pool_config(conn._config) == {}


@pytest.mark.transaction
def test_parse_pool_config_with_values():
    conn = _make({
        'DB_POOL_MAX': '20',
        'DB_POOL_MIN_CACHED': '2',
        'DB_POOL_MAX_CACHED': '8',
        'DB_POOL_MAX_USAGE': '1000',
        'DB_POOL_PING': '1',
    })
    pool = conn.parse_pool_config(conn._config)
    assert pool == {
        'maxconnections': 20,
        'mincached': 2,
        'maxcached': 8,
        'maxusage': 1000,
        'ping': 1,
    }
