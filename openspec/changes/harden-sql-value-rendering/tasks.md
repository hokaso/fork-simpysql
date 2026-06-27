## 1. 决策与基线（apply 前人审）

- [ ] 1.1 确认落地方案：B（`format_string` 字符串编码兜底，先止血）还是 A（参数化绑定，大版本方向）——见 design「决策 1」「Open Questions」
- [ ] 1.2 确认 `None` 在条件场景的语义（仅写入转 `NULL` / 是否自动 `IS NULL`），对齐既有 `where(..,'is','null')` 约定
- [ ] 1.3 确认范围是否仅限 MySQL builder（Postgres 同类问题本次是否纳入）
- [ ] 1.4 建立基线：先跑一遍 `tests/mysql_tester/` 全量，记录当前绿/红，作为回归对照

## 2. 失败用例先行（红）

- [ ] 2.1 在 `tests/mysql_tester/test_critical_fixes.py` 增 bytes 写入用例（断言生成 `0x<hex>` / 无 `b'\x..'`，写读一致）
- [ ] 2.2 增 datetime/date 写入与 UPDATE 用例（断言带引号时间串、无裸拼）
- [ ] 2.3 增单元素 tuple 的 `IN` 用例（断言 `(x)` 无尾逗号），并加单元素 list 对照用例
- [ ] 2.4 增 `None` 写入用例（断言 `NULL`、无裸 `None`）
- [ ] 2.5 增防回归用例：含单引号字符串仍被转义加引号；`Expression`/子查询渲染不变

## 3. 核心实现（集中到单一值编码入口）

- [ ] 3.1 在 `simpysql/Util/Expression.py` 收敛一个值编码入口（如 `format_value`），覆盖 bytes/datetime/date/None + 既有 str/数值/Expression/BaseBuilder 分支
- [ ] 3.2 `_valueize`（INSERT/REPLACE）、`_compile_update`（SET）统一改调用该入口
- [ ] 3.3 修 `list_to_str`：`tuple` 与 `list` 一致去单元素尾逗号；空集合维持 `1=0`/`1=1`；元素逐个过值编码入口（IN 内 bytes/None 亦安全）
- [ ] 3.4 （若选方案 A）`MysqlConnection.execute` 增可选参数绑定通道 + 日志回填可读 SQL；编译层产出占位符 + args

## 4. 验证与回归

- [ ] 4.1 第 2 节用例全部转绿
- [ ] 4.2 `tests/mysql_tester/` 全量回归，与 1.4 基线对比无回退
- [ ] 4.3 用 gitruck-infra media_matrix 向量检索真实路径冒烟：`gm_query_term_vec` insert/mark_hit + 标签/素材 IN 回查在**未打 workaround** 下端到端跑通

## 5. 发布与下游回收（解耦，非阻塞）

- [ ] 5.1 bump 版本号，发版 pip `simpysqls`，README/CHANGELOG 记录行为变更与兼容性说明
- [ ] 5.2 通知下游项目升级；逐项目**可选**移除调用端 workaround（`Expression("0x..")` / `list()` IN / `get_current_time_standard()` / 手动删 None），每处移除须有测试覆盖
- [ ] 5.3 更新永久记忆 `simpysql-write-pitfalls`：标注哪些坑已在 ORM 本体根治、最低版本号
