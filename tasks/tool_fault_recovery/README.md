# tool_fault_recovery（工具故障恢复，DESIGN v0.4 §5.4）

- **注入**：`gold.fault = {tool, nth, kind, accept}`——沙箱在第 `nth` 次调用
  `tool` 时按 `kind` 表现故障：`error`（tool_error）/ `empty`（ok 但空结果）/
  `timeout` / `stale_version`（版本过期）。注入在沙箱层完成，模型真实看到错误再反应。
- **恢复形态**（`accept` 按题指定）：`retry_same` 同参重试（仅超时合理）/
  `vary` 换查询参数 / `switch_tool` 换工具 / `abstain` 诚实降级（answer.status=无法完成）。
- **判定**：`fault_recovery` 谓词，主分 = recovery（命中 accept 之一）×
  final_exact（终答对象与 gold.answer 逐叶匹配）；乱编/僵住/可降级而不降级 → 0。
- **产物**：recovery% 列进主表必报列（§6.1）；与 L2 合轨跑。

## 数据

`data/public/tool_fault_recovery.jsonl` 8 题 = 8 科目 × 故障四型 × 恢复形态
（生成器 `scripts/add_fault_items.py`，幂等）。
