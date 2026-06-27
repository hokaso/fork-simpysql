## Context

SimpySql 走「编译成纯字符串 → `cursor.execute(sql)`」，无参数绑定。值渲染集中在 `simpysql/Util/Expression.py`：

- `format_string(value)`：`str` → `'{}'.format(pymysql.converters.escape_string(...))`；`Expression` → 原样；`BaseBuilder` → 子查询；**其余一律返回原值**，最终被 `_valueize` / `_compile_*` 用 `str()` 拼接。
- `list_to_str(data)`：仅当 `data` 是 **list 且 len==1** 时做 `.replace(",)", ")")`；`tuple` 不处理 → 单元素 tuple 留尾逗号。

调用方：`MysqlBuilder._valueize`（INSERT/REPLACE 值）、`_compile_update`（SET 值）、`_compile_in`（IN 集合）。

现状导致 `bytes` / `datetime` / 单元素 tuple / `None` 拼出非法 SQL（MySQL 1064/1054）。2026-06-15 gitruck-infra media_matrix 向量检索连环踩坑，逐点在调用端 workaround（详见 proposal）。本设计要在 ORM 本体一次根治。

## Goals / Non-Goals

**Goals:**
- 让 `bytes`、`datetime/date`、单元素 `tuple` 的 IN、`None` 四类值在 MySQL 路径上渲染为合法 SQL。
- 行为**向后兼容**：`str`/数值/`Expression`/子查询渲染不变；现有调用端的 workaround（`0x` Expression、`list()` IN、字符串时间）在新行为下仍等价、可平滑移除。
- 补回归测试到 `tests/mysql_tester/test_critical_fixes.py`。

**Non-Goals:**
- 不重写查询构建器对外 API。
- 本次只动 MySQL 路径（`MysqlBuilder` / `MysqlConnection` / `Expression` 的 MySQL 分支）；Mongo/Cassandra/Postgres builder 不在范围（如需，另行 propose）。
- 不强制各项目立即删除 workaround（解耦发布）。

## Decisions

### 决策 1：优先「参数化绑定」，字符串转义为兜底
- **方案 A（首选）**：把写入值 / 条件值改走 pymysql 的参数绑定 —— `cursor.execute(sql_with_%s, args)`。`MysqlConnection.execute` 增加可选 `params`，`MysqlBuilder` 编译时把值收集成占位符 + 参数列表。从根上消除「Python 值 → SQL 文本」整类问题（bytes/datetime/None/注入一并解决）。
- **方案 B（兜底）**：维持字符串编译，但在 `format_string` 增加类型分支：`bytes`→`0x<hex>`（空→`''`）、`datetime`→`'%Y-%m-%d %H:%M:%S'`、`date`→`'%Y-%m-%d'`、`None`→`NULL`；并修 `list_to_str` 让 tuple 与 list 同样去单元素尾逗号。
- **取舍**：A 最干净但改动面大（涉及连接层 + 所有 compile_* 的值流、批量 INSERT 的占位符展开、`Expression`/子查询仍需走文本）、且要保证 LOG 仍能打出可读 SQL；B 改动小、风险可控、与现有 workaround 天然等价。**建议**：先以 B 落地止血（与现网 workaround 行为一致、可逐步回收），同时评估 A 作为后续大版本方向。最终选型在 apply 前由人确认。

### 决策 2：集中到单一值编码函数
无论 A/B，所有类型映射收敛到 `Expression` 的**一个**入口（如 `format_value`），`_valueize` / `_compile_update` / `_compile_in` 统一调用，杜绝「同一类型在不同 compile 路径行为不一致」。

### 决策 3：IN 渲染规范化
`list_to_str` 对 `list` 与 `tuple` 统一处理：`len==0` 维持既有 `1=0`/`1=1`；`len==1` 去尾逗号；`len>1` 原样。集合元素逐个过决策 2 的值编码函数（这样 IN 里的 bytes/None 也安全）。

## Risks / Trade-offs

- **全局行为变更影响所有项目** → 以 `tests/mysql_tester/` 全量回归为闸；新增四类值用例；发版用新小版本号，各项目按需升级。
- **None 语义歧义**（写入 `NULL` vs 条件 `IS NULL`）→ 写入值统一 `NULL`；条件等值是否自动转 `IS NULL` 须对齐既有 `where(..,'is','null')` 约定，避免悄悄改变查询结果。spec 已要求「不改变既有语义」。
- **方案 A 的日志可读性**（参数化后 LOG 里 SQL 带占位符）→ 若选 A，日志层需把 args 回填渲染成可读 SQL（仅日志用，不回流执行）。
- **datetime 精度**：现状裸拼带微秒；标准串截到秒。若有列依赖微秒，需显式保留 —— 默认截秒（与既有 `__create_time__` 行为一致）。
- **不可改 .venv 副本**：消费方（如 gitruck-infra）的 `.venv` 里 simpysql 由 `uv sync` 覆盖，修复只在本源仓改 + 发版生效。

## Migration Plan

1. 选定方案（A/B）并实现，集中到单一值编码入口。
2. `tests/mysql_tester/test_critical_fixes.py` 增四类值回归用例，全量回归绿。
3. 发版 pip `simpysqls`（新小版本）。
4. 各消费项目升级依赖后，**可选**逐步移除调用端 workaround（`Expression("0x..")`、`list()` IN、`get_current_time_standard()`、手动删 None），每移除一处需有对应测试覆盖。
5. **回滚**：纯库内改动，回滚 = 各项目固定回旧版本号；workaround 仍在则功能不受影响。

## Open Questions

- 选 A（参数化）还是 B（字符串编码兜底）作为本次落地范围？（建议 B 先止血，A 列为后续）
- `None` 在等值条件下是否自动转 `IS NULL`，还是仅在写入值转 `NULL`、条件维持现状？
- 是否一并规范 Postgres builder 的同类问题，还是严格只限 MySQL？
