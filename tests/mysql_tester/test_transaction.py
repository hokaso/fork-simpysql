#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simpysql MySQL 测试 - 事务方法
测试方法: transaction (装饰器方式和直接调用方式)
"""

import pytest
from tests.mysql_tester.models import User, Order, Product, Article


class TestTransactionDecorator:
    """测试 @Model.transaction 装饰器方式"""
    
    @pytest.mark.transaction
    def test_transaction_decorator_commit(self, clean_users):
        """测试装饰器方式事务提交"""
        @User.transaction
        def create_user():
            clean_users.create({'name': 'DecoratorCommit', 'email': 'decorator@test.com', 'age': 25, 'status': 1, 'score': 80.0})
            return True
        
        result = create_user()
        assert result is True
        
        # 验证数据已提交
        user = clean_users.where('name', 'DecoratorCommit').first()
        assert user is not None
    
    @pytest.mark.transaction
    def test_transaction_decorator_rollback(self, clean_users):
        """测试装饰器方式事务回滚"""
        # 先插入一条数据
        clean_users.create({'name': 'BeforeDecoratorRollback', 'email': 'before@test.com', 'age': 25, 'status': 1, 'score': 80.0})
        
        @User.transaction
        def failed_operation():
            # 更新数据
            clean_users.where('name', 'BeforeDecoratorRollback').update({'age': 100})
            # 然后抛出异常
            raise Exception('Intentional rollback test')
        
        # 事务应该捕获异常并回滚
        with pytest.raises(Exception):
            failed_operation()
        
        # 验证数据已回滚
        user = clean_users.where('name', 'BeforeDecoratorRollback').first()
        age = user['age'] if isinstance(user, dict) else user.age
        assert age == 25  # 应该是原始值，不是100
    
    @pytest.mark.transaction
    def test_transaction_decorator_with_params(self, clean_users):
        """测试装饰器方式带参数的事务"""
        @User.transaction
        def create_user_with_params(name, email, age):
            clean_users.create({'name': name, 'email': email, 'age': age, 'status': 1, 'score': 80.0})
            return True
        
        result = create_user_with_params('ParamsUser', 'params@test.com', 30)
        assert result is True
        
        # 验证数据已提交
        user = clean_users.where('name', 'ParamsUser').first()
        assert user is not None
        age = user['age'] if isinstance(user, dict) else user.age
        assert age == 30
    
    @pytest.mark.transaction
    def test_transaction_decorator_multiple_operations(self, clean_users):
        """测试装饰器方式事务中多个操作"""
        @User.transaction
        def multiple_operations():
            clean_users.create({'name': 'DecoratorMulti1', 'email': 'multi1@test.com', 'age': 25, 'status': 1, 'score': 80.0})
            clean_users.create({'name': 'DecoratorMulti2', 'email': 'multi2@test.com', 'age': 30, 'status': 1, 'score': 85.0})
            clean_users.where('name', 'DecoratorMulti1').update({'age': 26})
            return True
        
        result = multiple_operations()
        assert result is True
        
        # 验证所有操作都已提交
        count = clean_users.where('name', 'like', 'DecoratorMulti%').count()
        assert count == 2
        
        user1 = clean_users.where('name', 'DecoratorMulti1').first()
        age = user1['age'] if isinstance(user1, dict) else user1.age
        assert age == 26
    
    @pytest.mark.transaction
    def test_transaction_decorator_return_value(self, clean_users):
        """测试装饰器方式事务返回值"""
        @User.transaction
        def get_user_count():
            clean_users.create({'name': 'DecoratorReturn', 'email': 'return@test.com', 'age': 25, 'status': 1, 'score': 80.0})
            return clean_users.count()
        
        result = get_user_count()
        assert result >= 1
    
    @pytest.mark.transaction
    def test_transaction_decorator_with_closure(self, clean_users):
        """测试装饰器方式事务闭包捕获变量"""
        name = 'DecoratorClosure'
        
        @User.transaction
        def create_user_with_name():
            clean_users.create({'name': name, 'email': f'{name.lower()}@test.com', 'age': 25, 'status': 1, 'score': 80.0})
            return name
        
        result = create_user_with_name()
        assert result == name


class TestTransactionDirectCall:
    """测试 Model.transaction(func)() 直接调用方式"""
    
    @pytest.mark.transaction
    def test_transaction_direct_call_commit(self, clean_users):
        """测试直接调用方式事务提交"""
        def create_user():
            clean_users.create({'name': 'DirectCallCommit', 'email': 'direct@test.com', 'age': 25, 'status': 1, 'score': 80.0})
            return True
        
        result = clean_users.transaction(create_user)()
        assert result is True
        
        # 验证数据已提交
        user = clean_users.where('name', 'DirectCallCommit').first()
        assert user is not None
    
    @pytest.mark.transaction
    def test_transaction_direct_call_rollback(self, clean_users):
        """测试直接调用方式事务回滚"""
        # 先插入一条数据
        clean_users.create({'name': 'BeforeDirectRollback', 'email': 'before@test.com', 'age': 25, 'status': 1, 'score': 80.0})
        
        def failed_operation():
            # 更新数据
            clean_users.where('name', 'BeforeDirectRollback').update({'age': 100})
            # 然后抛出异常
            raise Exception('Intentional rollback test')
        
        # 事务应该捕获异常并回滚
        with pytest.raises(Exception):
            clean_users.transaction(failed_operation)()
        
        # 验证数据已回滚
        user = clean_users.where('name', 'BeforeDirectRollback').first()
        age = user['age'] if isinstance(user, dict) else user.age
        assert age == 25  # 应该是原始值，不是100


class TestTransactionInstanceMethod:
    """测试实例级别的 transaction 方法"""
    
    @pytest.mark.transaction
    def test_instance_transaction_commit(self, clean_users):
        """测试实例级别 transaction 方法提交"""
        def create_user():
            clean_users.create({'name': 'InstanceCommit', 'email': 'instance@test.com', 'age': 25, 'status': 1, 'score': 80.0})
            return True
        
        result = clean_users.transaction(create_user)()
        assert result is True
        
        # 验证数据已提交
        user = clean_users.where('name', 'InstanceCommit').first()
        assert user is not None

    @pytest.mark.transaction
    def test_builder_level_transaction_commit(self, clean_users):
        """Builder 实例级事务：Model.where(...).transaction(fn)() 应与类级一致，调用后执行并提交"""
        def create_user():
            clean_users.create({'name': 'BuilderTx', 'email': 'buildertx@test.com', 'age': 25, 'status': 1, 'score': 80.0})
            return 'ok'

        # where(...) 返回 builder 实例，.transaction 命中 MysqlBuilder.transaction（已统一为返回包装器）
        result = clean_users.where('status', 1).transaction(create_user)()
        assert result == 'ok'

        user = clean_users.where('name', 'BuilderTx').first()
        assert user is not None

    @pytest.mark.transaction
    def test_builder_level_transaction_rollback(self, clean_users):
        """Builder 实例级事务异常时应回滚"""
        clean_users.create({'name': 'BuilderTxRb', 'email': 'buildertxrb@test.com', 'age': 25, 'status': 1, 'score': 80.0})

        def failed():
            clean_users.where('name', 'BuilderTxRb').update({'age': 999})
            raise Exception('boom')

        with pytest.raises(Exception, match='boom'):
            clean_users.where('status', 1).transaction(failed)()

        user = clean_users.where('name', 'BuilderTxRb').first()
        age = user['age'] if isinstance(user, dict) else user.age
        assert age == 25, "实例级事务回滚失败"


class TestTransactionClassMethod:
    """测试类级别的 transaction 方法"""
    
    @pytest.mark.transaction
    def test_class_transaction_decorator(self, user_model):
        """测试类级别 transaction 方法存在"""
        # 验证类有 transaction 方法
        assert hasattr(user_model, 'transaction')


class TestTransactionExceptions:
    """测试事务异常处理"""
    
    @pytest.mark.transaction
    def test_transaction_decorator_with_division_error(self, clean_users):
        """测试装饰器方式事务中的除零错误"""
        @User.transaction
        def division_error():
            clean_users.create({'name': 'DecoratorDivError', 'email': 'diverror@test.com', 'age': 25, 'status': 1, 'score': 80.0})
            x = 1 / 0  # 除零错误
            return x
        
        with pytest.raises(Exception):
            division_error()
        
        # 验证数据已回滚
        user = clean_users.where('name', 'DecoratorDivError').first()
        assert user is None or user == {}
    
    @pytest.mark.transaction
    def test_transaction_decorator_with_key_error(self, clean_users):
        """测试装饰器方式事务中的键错误"""
        @User.transaction
        def key_error():
            clean_users.create({'name': 'DecoratorKeyError', 'email': 'keyerror@test.com', 'age': 25, 'status': 1, 'score': 80.0})
            d = {}
            return d['non_existent_key']  # 键错误
        
        with pytest.raises(Exception):
            key_error()
        
        # 验证数据已回滚
        user = clean_users.where('name', 'DecoratorKeyError').first()
        assert user is None or user == {}


class TestTransactionComplex:
    """测试复杂事务场景"""
    
    @pytest.mark.transaction
    def test_transaction_decorator_select_and_update(self, clean_users):
        """测试装饰器方式事务中的查询和更新操作"""
        @User.transaction
        def select_and_update():
            # 先插入
            clean_users.create({'name': 'DecoratorSelectUpdate', 'email': 'selectupdate@test.com', 'age': 25, 'status': 1, 'score': 80.0})
            # 查询
            user = clean_users.where('name', 'DecoratorSelectUpdate').first()
            # 更新
            clean_users.where('name', 'DecoratorSelectUpdate').update({'age': 30})
            return True
        
        result = select_and_update()
        assert result is True
        
        # 验证最终状态
        user = clean_users.where('name', 'DecoratorSelectUpdate').first()
        age = user['age'] if isinstance(user, dict) else user.age
        assert age == 30
    
    @pytest.mark.transaction
    def test_transaction_decorator_with_delete(self, clean_users):
        """测试装饰器方式事务中的删除操作"""
        # 先插入数据
        clean_users.create({'name': 'DecoratorToDelete', 'email': 'todelete@test.com', 'age': 25, 'status': 1, 'score': 80.0})
        
        @User.transaction
        def delete_operation():
            clean_users.where('name', 'DecoratorToDelete').delete()
            return True
        
        result = delete_operation()
        assert result is True
        
        # 验证数据已删除
        user = clean_users.where('name', 'DecoratorToDelete').first()
        assert user is None or user == {}
    
    @pytest.mark.transaction
    def test_transaction_decorator_partial_failure(self, clean_users, clean_orders):
        """测试装饰器方式部分失败的事务"""
        # 插入用户
        clean_users.create({'name': 'DecoratorPartialFail', 'email': 'partial@test.com', 'age': 25, 'status': 1, 'score': 80.0})
        user = clean_users.where('name', 'DecoratorPartialFail').first()
        user_id = user['id'] if isinstance(user, dict) else user.id
        
        @User.transaction
        def partial_ops():
            # 创建订单
            clean_orders.create({'user_id': user_id, 'order_no': 'ORD001', 'amount': 100.00, 'status': 1})
            # 更新用户
            clean_users.where('id', user_id).update({'score': 90.0})
            # 失败
            raise Exception('Partial failure')
        
        with pytest.raises(Exception):
            partial_ops()
        
        # 验证用户分数未更新
        user = clean_users.where('name', 'DecoratorPartialFail').first()
        score = user['score'] if isinstance(user, dict) else user.score
        assert float(score) == 80.0
    
    @pytest.mark.transaction
    def test_transaction_decorator_with_kwargs(self, clean_users):
        """测试装饰器方式带关键字参数的事务"""
        @User.transaction
        def create_user_with_kwargs(name, email, **kwargs):
            data = {'name': name, 'email': email, 'status': 1, 'score': 80.0}
            data.update(kwargs)
            clean_users.create(data)
            return True
        
        result = create_user_with_kwargs('KwargsUser', 'kwargs@test.com', age=35)
        assert result is True
        
        # 验证数据已提交
        user = clean_users.where('name', 'KwargsUser').first()
        assert user is not None
        age = user['age'] if isinstance(user, dict) else user.age
        assert age == 35
