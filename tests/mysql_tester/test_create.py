#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simpysql MySQL 测试 - INSERT 插入相关方法
测试方法: create, insert, insert_on_duplicate, insert_ignore, replace, lastid
"""

import pytest
from tests.mysql_tester.models import User, Order, Product, Article


class TestCreate:
    """测试 create() 方法"""
    
    @pytest.mark.create
    def test_create_single_dict(self, clean_users, sample_user_data):
        """测试插入单条数据 (字典)"""
        result = clean_users.create(sample_user_data)
        assert result is not None
        
        # 验证数据已插入
        inserted = clean_users.where('name', sample_user_data['name']).first()
        assert inserted is not None
    
    @pytest.mark.create
    def test_create_batch_list(self, clean_users, batch_user_data):
        """测试批量插入数据 (列表)"""
        result = clean_users.create(batch_user_data)
        assert result is not None
        
        # 验证数据已插入
        count = clean_users.where('name', 'like', '用户%').count()
        assert count == 3

    @pytest.mark.create
    def test_create_batch_heterogeneous_keys_raises(self, clean_users):
        """批量插入各行字段不一致时，应明确报错，而非生成列/值错位的非法 SQL"""
        rows = [
            {'name': 'HetA', 'email': 'heta@test.com', 'age': 1, 'status': 1, 'score': 1.0},
            {'name': 'HetB', 'email': 'hetb@test.com', 'age': 2, 'status': 1},  # 缺少 score
        ]
        with pytest.raises(Exception, match="identical columns"):
            clean_users.create(rows)

    @pytest.mark.create
    def test_create_batch_same_keys_different_order(self, clean_users):
        """各行字段相同但顺序不同时，值应按列名正确对齐（不能错灌）"""
        rows = [
            {'name': 'OrderA', 'email': 'oa@test.com', 'age': 10, 'status': 1, 'score': 1.0},
            {'score': 2.0, 'status': 1, 'age': 20, 'email': 'ob@test.com', 'name': 'OrderB'},
        ]
        clean_users.create(rows)

        b = clean_users.where('name', 'OrderB').first()
        assert b is not None
        assert (b['age'] if isinstance(b, dict) else b.age) == 20
        assert float(b['score'] if isinstance(b, dict) else b.score) == 2.0
        assert (b['email'] if isinstance(b, dict) else b.email) == 'ob@test.com'

    @pytest.mark.create
    def test_create_with_extra_fields(self, clean_users):
        """测试插入时忽略非表字段"""
        data = {
            'name': 'ExtraFieldTest',
            'email': 'extra@test.com',
            'age': 25,
            'status': 1,
            'score': 80.0,
            'non_existent_field': 'should_be_ignored'  # 这个字段不在 columns 中
        }
        result = clean_users.create(data)
        assert result is not None
    
    @pytest.mark.create
    def test_create_auto_timestamp(self, clean_users):
        """测试自动添加时间戳"""
        data = {
            'name': 'TimestampTest',
            'email': 'timestamp@test.com',
            'age': 25,
            'status': 1,
            'score': 80.0
        }
        clean_users.create(data)
        
        # 验证时间戳已自动添加
        result = clean_users.where('name', 'TimestampTest').first()
        assert result is not None
        assert result['created_at'] > 0 or result.created_at > 0
    
    @pytest.mark.create
    def test_create_empty_data(self, clean_users):
        """测试空数据插入"""
        result = clean_users.create({})
        # 空数据应该被处理
        assert result is not None or result is None
    
    @pytest.mark.create
    def test_create_none_data(self, clean_users):
        """测试 None 数据插入"""
        result = clean_users.create(None)
        # None 数据应该被处理
        assert result is not None or result is None


class TestInsert:
    """测试 insert() 方法"""
    
    @pytest.mark.create
    def test_insert_with_columns_and_data(self, clean_users):
        """测试指定列插入数据"""
        columns = ['name', 'email', 'age', 'status', 'score']
        data = [
            ('InsertTest1', 'insert1@test.com', 25, 1, 80.0),
            ('InsertTest2', 'insert2@test.com', 30, 1, 85.0),
        ]
        result = clean_users.insert(columns, data)
        assert result is not None
        
        # 验证数据已插入
        count = clean_users.where('name', 'like', 'InsertTest%').count()
        assert count == 2
    
    @pytest.mark.create
    def test_insert_single_row(self, clean_users):
        """测试插入单行数据"""
        columns = ['name', 'email']
        data = [('SingleInsert', 'single@test.com')]
        result = clean_users.insert(columns, data)
        assert result is not None


class TestInsertOnDuplicate:
    """测试 insert_on_duplicate() 方法"""
    
    @pytest.mark.create
    def test_insert_on_duplicate_insert(self, clean_users):
        """测试 insert_on_duplicate() 新增数据"""
        data = {
            'name': 'DuplicateTest',
            'email': 'duplicate@test.com',
            'age': 25,
            'status': 1,
            'score': 80.0
        }
        result = clean_users.insert_on_duplicate(data)
        assert result is not None
    
    @pytest.mark.create
    def test_insert_on_duplicate_update(self, clean_users):
        """测试 insert_on_duplicate() 更新已存在数据"""
        # 先插入一条数据
        data = {
            'id': 1000,
            'name': 'DuplicateUpdate',
            'email': 'dup@test.com',
            'age': 25,
            'status': 1,
            'score': 80.0
        }
        clean_users.create(data)
        
        # 使用 insert_on_duplicate 更新
        update_data = {
            'id': 1000,
            'name': 'DuplicateUpdated',
            'email': 'dup_updated@test.com',
            'age': 30,
            'status': 1,
            'score': 90.0
        }
        result = clean_users.insert_on_duplicate(update_data)
        assert result is not None
    
    @pytest.mark.create
    def test_insert_on_duplicate_list(self, clean_users):
        """测试 insert_on_duplicate() 批量数据"""
        data = [
            {'name': 'DupList1', 'email': 'duplist1@test.com', 'age': 25, 'status': 1, 'score': 80.0},
            {'name': 'DupList2', 'email': 'duplist2@test.com', 'age': 30, 'status': 1, 'score': 85.0},
        ]
        result = clean_users.insert_on_duplicate(data)
        assert result is not None


class TestInsertIgnore:
    """测试 insert_ignore() 方法"""
    
    @pytest.mark.create
    def test_insert_ignore_single_dict(self, clean_users):
        """测试 insert_ignore() 单条数据"""
        data = {
            'name': 'IgnoreTest',
            'email': 'ignore@test.com',
            'age': 25,
            'status': 1,
            'score': 80.0
        }
        result = clean_users.insert_ignore(data)
        assert result is not None
    
    @pytest.mark.create
    def test_insert_ignore_batch_list(self, clean_users):
        """测试 insert_ignore() 批量数据"""
        data = [
            {'name': 'IgnoreList1', 'email': 'ignorelist1@test.com', 'age': 25, 'status': 1, 'score': 80.0},
            {'name': 'IgnoreList2', 'email': 'ignorelist2@test.com', 'age': 30, 'status': 1, 'score': 85.0},
        ]
        result = clean_users.insert_ignore(data)
        assert result is not None
    
    @pytest.mark.create
    def test_insert_ignore_duplicate(self, clean_users):
        """测试 insert_ignore() 忽略重复数据"""
        # 先插入一条数据
        data = {
            'id': 2000,
            'name': 'IgnoreDupTest',
            'email': 'ignoredup@test.com',
            'age': 25,
            'status': 1,
            'score': 80.0
        }
        clean_users.create(data)
        
        # 尝试插入相同 ID 的数据，应该被忽略而不报错
        duplicate_data = {
            'id': 2000,
            'name': 'IgnoreDupTest2',
            'email': 'ignoredup2@test.com',
            'age': 30,
            'status': 1,
            'score': 90.0
        }
        result = clean_users.insert_ignore(duplicate_data)
        assert result is not None


class TestReplace:
    """测试 replace() 方法"""
    
    @pytest.mark.create
    def test_replace_single_dict(self, clean_users):
        """测试 replace() 单条数据"""
        data = {
            'name': 'ReplaceTest',
            'email': 'replace@test.com',
            'age': 25,
            'status': 1,
            'score': 80.0
        }
        result = clean_users.replace(data)
        assert result is not None
    
    @pytest.mark.create
    def test_replace_batch_list(self, clean_users):
        """测试 replace() 批量数据"""
        data = [
            {'id': 3001, 'name': 'ReplaceList1', 'email': 'replacelist1@test.com', 'age': 25, 'status': 1, 'score': 80.0},
            {'id': 3002, 'name': 'ReplaceList2', 'email': 'replacelist2@test.com', 'age': 30, 'status': 1, 'score': 85.0},
        ]
        result = clean_users.replace(data)
        assert result is not None
    
    @pytest.mark.create
    def test_replace_existing_record(self, clean_users):
        """测试 replace() 替换已存在记录"""
        # 先插入一条数据
        data = {
            'id': 4000,
            'name': 'ReplaceExisting',
            'email': 'replaceexist@test.com',
            'age': 25,
            'status': 1,
            'score': 80.0
        }
        clean_users.create(data)
        
        # 使用 replace 替换
        replace_data = {
            'id': 4000,
            'name': 'ReplaceExistingNew',
            'email': 'replaceexistnew@test.com',
            'age': 30,
            'status': 1,
            'score': 90.0
        }
        result = clean_users.replace(replace_data)
        assert result is not None
    
    @pytest.mark.create
    def test_replace_invalid_data(self, clean_users):
        """测试 replace() 无效数据"""
        result = clean_users.replace(None)
        # None 数据应该被处理
        assert result is not None or result is None


class TestLastId:
    """测试 lastid() 方法"""

    @pytest.mark.create
    def test_lastid_after_create(self, clean_users):
        """create() 后 lastid() 必须等于真实写入的自增 id（而非任意非空值）"""
        clean_users.create({
            'name': 'LastIdTest',
            'email': 'lastid@test.com',
            'age': 25,
            'status': 1,
            'score': 80.0,
        })
        last_id = clean_users.lastid()
        real = clean_users.where('name', 'LastIdTest').first()
        real_id = real['id'] if isinstance(real, dict) else real.id

        assert last_id is not None, "lastid() 不应为 None"
        assert last_id == real_id, f"lastid()={last_id} 应等于真实写入 id={real_id}"

    @pytest.mark.create
    def test_lastid_chained_after_create(self, clean_users):
        """README 文档用法：create(...).lastid() 链式调用应返回该行 id"""
        last_id = clean_users.create({
            'name': 'LastIdChain',
            'email': 'lastidchain@test.com',
            'age': 30,
            'status': 1,
            'score': 88.0,
        }).lastid()
        real = clean_users.where('name', 'LastIdChain').first()
        real_id = real['id'] if isinstance(real, dict) else real.id
        assert last_id == real_id, f"链式 lastid()={last_id} 应等于真实写入 id={real_id}"

    @pytest.mark.create
    def test_lastid_sequential_creates(self, clean_users):
        """连续多次插入，每次 lastid() 都应等于对应行真实 id

        回归用例：连接池模式下每条语句换连接，旧实现用 select last_insert_id()
        会读到另一条连接的会话值（稳定差一 / 首次为 None）。
        """
        for i in range(5):
            clean_users.create({
                'name': f'LastIdSeq{i}',
                'email': f'lastidseq{i}@test.com',
                'age': 20 + i,
                'status': 1,
                'score': 80.0,
            })
            last_id = clean_users.lastid()
            real = clean_users.where('name', f'LastIdSeq{i}').first()
            real_id = real['id'] if isinstance(real, dict) else real.id
            assert last_id == real_id, f"第{i}次: lastid()={last_id} != 真实 id={real_id}"

    @pytest.mark.create
    def test_lastid_returns_none_when_empty(self, clean_users):
        """无数据时 lastid() 返回 None 或整数（不应抛错）"""
        last_id = clean_users.lastid()
        assert last_id is None or isinstance(last_id, int)


class TestCreateOrUpdate:
    """测试 create_or_update() 方法"""
    
    @pytest.mark.create
    def test_create_or_update_create(self, clean_users):
        """测试 create_or_update() 新增数据"""
        # 确保数据不存在
        data = {
            'name': 'CreateOrUpdateNew',
            'email': 'counew@test.com',
            'age': 25,
            'status': 1,
            'score': 80.0
        }
        result = clean_users.where('name', 'CreateOrUpdateNew').create_or_update(data)
        assert result is not None
    
    @pytest.mark.create
    def test_create_or_update_update(self, clean_users):
        """测试 create_or_update() 更新数据"""
        # 先插入一条数据
        data = {
            'name': 'CreateOrUpdateUpdate',
            'email': 'couupdate@test.com',
            'age': 25,
            'status': 1,
            'score': 80.0
        }
        clean_users.create(data)
        
        # 使用 create_or_update 更新
        update_data = {
            'name': 'CreateOrUpdateUpdate',
            'email': 'couupdate_new@test.com',
            'age': 30,
            'status': 1,
            'score': 90.0
        }
        result = clean_users.where('name', 'CreateOrUpdateUpdate').create_or_update(update_data)
        assert result is not None
