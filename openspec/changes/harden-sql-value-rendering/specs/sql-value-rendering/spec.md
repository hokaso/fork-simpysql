## ADDED Requirements

### Requirement: bytes 值渲染为合法二进制字面量

当一个 `bytes` / `bytearray` 值出现在 INSERT / UPDATE 的写入值或 WHERE 条件值中时，ORM SHALL 将其编译为 MySQL 合法的二进制表示（十六进制字面量 `0x<hex>`，或经参数绑定传入），而不得对其调用 `str()` 直接拼接。空字节串 SHALL 渲染为合法的空二进制（如 `0x` 不合法，则用 `''`）。

#### Scenario: 写入 bytes 列
- **WHEN** 对含 `bytes` 值的字段执行 `create` / `insert_ignore` / `update`
- **THEN** 生成的 SQL 包含 `0x<hex>`（或绑定占位符），MySQL 执行成功且读回的字节与写入一致
- **AND** SQL 中不出现 `b'\x..'` 形式的非法字面量

### Requirement: datetime/date 值渲染为带引号的时间串

当一个 `datetime.datetime` / `datetime.date` 值出现在写入值或条件值中时，ORM SHALL 将其格式化为带引号的标准时间字符串（datetime → `'%Y-%m-%d %H:%M:%S'`，date → `'%Y-%m-%d'`），而不得裸拼对象的 `str()` 形式。

#### Scenario: UPDATE 设置 datetime 字段
- **WHEN** `where(...).update({"last_hit_at": datetime.datetime.now()})`
- **THEN** 生成 `... set last_hit_at='2026-06-15 14:36:55' where ...`，执行成功
- **AND** SQL 中不出现未加引号的 `2026-06-15 14:36:55.778397`

### Requirement: IN 集合对 tuple 与 list 渲染一致

`IN` / `NOT IN` 子句的集合值渲染 SHALL 与容器是 `list` 还是 `tuple` 无关：单元素集合 SHALL 渲染为 `(x)`（无尾随逗号），多元素渲染为 `(a, b, ...)`，空集合沿用既有「`IN`→`1=0` / `NOT IN`→`1=1`」语义。

#### Scenario: 单元素 tuple 传入 IN
- **WHEN** `where("id", "in", (123,)).get()`
- **THEN** 生成 `... where \`id\` in (123)`，执行成功
- **AND** SQL 中不出现尾随逗号形式 `(123,)`

#### Scenario: 单元素 list 传入 IN（保持既有正确行为）
- **WHEN** `where("id", "in", [123]).get()`
- **THEN** 生成 `... where \`id\` in (123)`，行为与传 tuple 一致

### Requirement: None 值渲染为 SQL NULL

当一个 `None` 出现在写入值或条件值中时，ORM SHALL 将其渲染为 SQL 关键字 `NULL`，而不得拼出 `None` 字面量（会触发 1054 unknown column 'None'）。写入时 `field=NULL`；等值条件渲染遵循各 builder 既有的 `is` 语义约定（如适用）。

#### Scenario: 写入 None 字段
- **WHEN** `create({"note": None, "name": "x"})`
- **THEN** 生成的 SQL 中该列值为 `NULL`，执行成功
- **AND** SQL 中不出现裸 `None`

### Requirement: 不改变既有类型的渲染语义

本能力 SHALL NOT 改变 `str`（仍 escape + 加引号）、数值、`Expression`（原样片段）、子查询/`BaseBuilder` 的既有渲染行为，且 SHALL NOT 引入 SQL 注入面（字符串值仍须经转义或参数绑定）。

#### Scenario: 字符串值仍被转义并加引号
- **WHEN** 写入或条件值为含单引号的字符串（如 `haha'124`）
- **THEN** 该值被正确转义并以 `'...'` 形式出现，执行成功，且不破坏语句结构

#### Scenario: 既有用例回归全绿
- **WHEN** 运行 `tests/mysql_tester/` 全量用例（含 `test_critical_fixes.py`）
- **THEN** 既有用例全部通过，新增四类值的用例亦通过
