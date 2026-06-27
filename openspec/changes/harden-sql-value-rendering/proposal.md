## Why

SimpySql 把 SQL 编译成**纯字符串、无参数绑定**（`MysqlConnection.execute` → `cursor.execute(sql)`），而 `Util/Expression.py` 的 `format_string()` 只对 `str`（加引号）和 `Expression`（原样）特判，其余 Python 值一律 `str()` 裸拼进 SQL。结果是一类静默踩坑——`bytes`、`datetime/date`、单元素 `tuple`、`None` 都会拼出非法 SQL（MySQL 1064/1054），逼每个调用端各自打补丁。

2026-06-15 在 gitruck-infra 的 media_matrix 向量检索上，这些坑**连环爆发**：`gm_query_term_vec` 的词向量缓存写入（bytes）、`mark_hit`（datetime）、标签/素材 IN 回查（单元素 tuple）逐一 1064，整个向量检索子系统此前**从未端到端跑通**，只能在调用端逐点 workaround。由于这是团队所有项目共用的 ORM，根治应在本体一次完成，而非每个项目重复填坑。

## What Changes

- **bytes**：`format_string` 渲染为合法 MySQL 二进制字面量（`0x<hex>` 或参数绑定），不再 `b'\x..'`。
- **datetime / date**：渲染为带引号的标准时间串（`%Y-%m-%d %H:%M:%S`），不再裸拼成 `... 14:36:55.778397`。
- **单元素 tuple 的 IN**：`list_to_str` 对 `tuple` 与 `list` 行为一致地去掉单元素尾逗号（`(x,)` → `(x)`），避免 `.where(col,"in",(x,))` 1064。
- **None**：渲染为 SQL `NULL`（写入/条件语义按 spec Requirement 明确），不再拼出 `None` 字面量（1054 unknown column 'None'）。
- **优先评估参数化绑定**：能否将写入/条件值改走 `cursor.execute(sql, args)` 参数绑定，从根上消除「字符串转义」这一整类问题；若不可行，则收敛到一个**统一的值编码层**（所有上述类型在一处映射）。
- **回归测试**：在已有的 `tests/mysql_tester/test_critical_fixes.py` 补齐四类值的用例。
- **BREAKING（潜在）**：这是全局值渲染行为变更，影响所有依赖本 ORM 的项目；`None`/`datetime` 的既有语义必须保持向后兼容（见 design 的兼容性评估）。

## Capabilities

### New Capabilities
- `sql-value-rendering`: ORM 将 Python 值编译进 SQL 的规则与安全边界——类型→SQL 字面量/绑定参数的映射、IN 集合渲染、`NULL` 语义、以及不变量（合法 SQL、防注入、不静默改写既有行为）。

### Modified Capabilities
<!-- 无：fork-simpysql 为全新 OpenSpec 工作区，openspec/specs/ 下暂无既有能力规范。 -->

## Impact

- **源码**：`simpysql/Util/Expression.py`（`format_string`、`list_to_str`）、`simpysql/Eloquent/MysqlBuilder.py`（`_valueize`、`_compile_in`、`_compile_update`）、`simpysql/Connections/MysqlConnection.py`（`execute`，若走参数化）。
- **影响面**：所有使用 `simpysqls` 的项目（gitruck-infra 及其它）。发版后各项目可**逐步**移除现有 workaround（`Expression("0x..")`、`list(...)` IN、`get_current_time_standard()` 时间串、手动删 None），但不强制——必须先保证新行为与旧 workaround 等价。
- **测试**：`tests/mysql_tester/test_critical_fixes.py`。
- **跨库契约**：不涉及 `gc_task` 等跨项目契约；纯 ORM 库内部改动 + 发版（pip `simpysqls`）。
- **非目标**：不重写查询构建器 API；不改 Mongo/Cassandra/Postgres builder（本次仅 MySQL 路径，其余 builder 视情况后续单独 propose）。
