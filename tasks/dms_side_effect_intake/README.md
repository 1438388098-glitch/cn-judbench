# dms_side_effect_intake（案管副作用，DESIGN v0.4 §5.3）

- **环境**：案管沙箱（`tools/dms.py`：案卡表 + 卷宗文书树 + 事件表，纯 dict 确定性状态）。
- **流程**：多步立案（建卡 → 更新字段 → 落文书 → 排期），步骤间有依赖
  （未建卡即写文书 → tool_error）。
- **判定**：`env_diff` 谓词在空白状态上重放轨迹，终态与 `gold.expected_state`
  逐叶比对，ratio 进主分基数——**无关键词、无文本相似，只看世界改变了什么**。
- **版本锁**：沙箱实现随 harness_sha 锁进 manifest（轨迹 hash 既有机制）。
