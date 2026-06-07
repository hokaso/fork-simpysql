#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from .Eloquent.BuilderFactory import builderfactory
from .Util.MagicMetaClass import MagicMetaClass
from functools import wraps
import time


class DBModel(MagicMetaClass):
    __create_time__ = None  # 插入时间字段

    __update_time__ = None  # 更新时间字段

    # 获取创建时间字段
    def create_time_column(self):
        return self.__create_time__

    # 获取更新时间字段
    def update_time_column(self):
        return self.__update_time__

    # 获取当前时间戳
    def fresh_timestamp(self):
        return int(time.time())

    @classmethod
    def transaction(cls, callback):
        """
        事务装饰器/方法

        注意：本方法返回一个「需要再调用一次才会执行」的包装器，
        既可作装饰器，也可直接调用。若写成 ModelDemo.transaction(demo)
        而忘了结尾的 ()，事务将不会执行（静默空操作），务必加上 ()。

        用法1 - 装饰器方式:
            @ModelDemo.transaction
            def demo(id):
                ModelDemo.where('id', id).update({'name': "44"})
                return True
            demo(42)

        用法2 - 直接调用方式（注意结尾的 ()）:
            def demo():
                ModelDemo.where('id', 42).update({'name': "44"})
                return True
            result = ModelDemo.transaction(demo)()
        """
        builder = cls.__new__(cls)
        @wraps(callback)
        def wrapper(*args, **kwargs):
            return builder._get_connection().transaction(lambda: callback(*args, **kwargs))
        return wrapper

    def __new__(cls, *args, **kwargs):
        if len(args) > 0 and isinstance(args[0], str):
            return builderfactory.make(super(DBModel, cls).__new__(cls), alias=args[0])
        return builderfactory.make(super(DBModel, cls).__new__(cls))