# dms_side_effect_intake · 参考解与金样构造规则

## 金样结构

`gold = {"calls": [...正确调用序列...], "answer": {...}, "expected_state": {...}}`

- `calls` 供 `mock:tools` 重放冒烟与 pass^k 抽样；
- `expected_state` 是 env_diff 唯一判分真相源（判分不读 calls）；
- 叶级键值必须与 `tools/dms.py` 终态完全一致（`documents` 键形如 `<案号>/<文书类型>`）。

## 依赖纪律

- 未建卡即 update/write/hearing → `tool_error: no such case`，终态缺口可量测；
- 案号重复建卡 → `duplicate case_no`；
- 参数 schema 违例（缺/错型/多余键）→ `arg_schema`，终态不变。

## 已落地（v0.4）

- **state0 预置初始环境**：`gold.initial_state` 进夹具，随题注入沙箱与 env_diff
  重放（`ToolSandbox(dms_state0=…)`）；d-101..103 为在办案件直接 update/write/排期，
  d-104 预置双卡（805 分心卡），误伤无关案卡按叶比例扣分；
- 当前 13 题：d-001..008 全新立案流程 + d-101..104 在办案件 + d-fake-001 负例。

## TODO（后续批次）

- state0 哈希锁进 manifest（当前随 item gold 的 item_sha256 覆盖）；
- 卷宗文件树落盘为真实文件树（当前为 dict 模拟）；
- events 计数断言（重复排期检测）。
