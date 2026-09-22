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

## TODO（后续批次）

- 预置初始环境（「在办案件」变体：跳过建卡直接 update/write）需沙箱支持
  初始状态注入（state0 进题面夹具并锁 hash 进 manifest）——当前每题沙箱均从
  空白态起步，故首批题全部为全新立案流程；
- 卷宗文件树落盘为真实文件树（当前为 dict 模拟）；
- events 计数断言（重复排期检测）。
