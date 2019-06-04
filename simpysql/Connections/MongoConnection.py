#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from .Connection import Connection
from ..Util.Logger import logger
import pymongo


class MongoConnection(Connection):

    _connection = {}

    _instance = {}  # 一个库一个instance

    def __init__(self, database, config):
        if config.get('LOG_DIR', None) is not None:
            self._logger = logger.set_path(config.get('LOG_DIR', None))
        self._database = database
        self._config = config

    def get(self, builder):
        _select = dict(builder.__select__) if builder.__select__ else None
        model = self.db(builder._tablename()).find(builder.__where__, _select).skip(builder.__offset__).limit(builder.__limit__)
        if builder.__orderby__:
            model = model.sort(builder.__orderby__)
        return list(model)

    def db(self, tablename):
        return self.connect()[tablename]

    def count(self, builder):
        return self.db(builder._tablename()).find(builder.__where__).count()

    def connect(self):
        if self._connection.get(self._database, None) is None:
            config = self.parse_config(self._config)
            if config['user'] and config['password'] and config['authmechanism']:
                client = pymongo.MongoClient(host=config['host'], port=config['port'], username=config['user'], password=config['password'], authMechanism=config['authmechanism'])
            else:
                client = pymongo.MongoClient(host=config['host'], port=config['port'])
            self._connection[self._database] = client[config['db']]
        return self._connection[self._database]

    @classmethod
    def instance(cls, database, config):
        if cls._instance.get(database, None) is None:
            cls._instance[database] = MongoConnection(database, config)
        return cls._instance.get(database, None)

    def parse_config(self, config):
        return {
            'host': config.get('DB_HOST', ''),
            'port': int(config.get('DB_PORT', '')),
            'user': config.get('DB_USER', None),
            'password': config.get('DB_PASSWORD', None),
            'db': config.get('DB_NAME', ''),
            'charset': config.get('DB_CHARSET', None),
            'authmechanism': config.get('DB_AUTHMECHANISM', None),
        }
