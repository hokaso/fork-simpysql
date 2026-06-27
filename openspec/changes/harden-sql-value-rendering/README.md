# harden-sql-value-rendering

集中加固 SimpySql 的 SQL 值渲染：bytes/datetime/单元素 tuple/None 不再裸拼进 SQL（消除 1064/1054），让各项目调用端不必逐处打补丁。
