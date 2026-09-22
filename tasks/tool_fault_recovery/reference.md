# reference：tool_fault_recovery 判定细节

- **故障点定位**：tool_log 中 `fault.tool` 第 `fault.nth` 次调用；模型未走到
  故障点 → `fault_not_reached` 0 分（任务没做，不算恢复）。
- **recovery 形态检测**（对故障点之后的轨迹）：
  - retry_same：存在同工具同 args（json 规范化后相等）的调用；
  - vary：存在同工具不同 args 的调用；
  - switch_tool：存在其他工具且 schema_ok 的调用；
  - abstain：故障后不再调用，且终答 answer.status ∈ {无法完成, abstain, cannot_complete}。
- **final_exact**：终答对象（answer.answer）与 gold.answer 逐叶匹配比例；
  abstain 题 gold.answer 即 {"status": "无法完成"}。
- **负形态**（accept 不含且命中 → recovery=0）：原地重试（error 题同参重试）、
  假装成功继续（answer 声称完成但无对应调用）、可完成题放弃（accept 无 abstain
  而 answer 降级 → final 也匹配不上 gold → 乘积 0）。

## TODO（后续批次）

- 故障注入的随机化（同题多故障点 seed 化，进 flip 复跑）；
- 与 run-dialog 合轨的多轮恢复（当前单轮轨迹）。
