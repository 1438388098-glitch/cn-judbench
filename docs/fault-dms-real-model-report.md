# v0.4 新任务真实考生首测：dms（state0）与 tool_fault_recovery

- 日期：2026-09-23（R9）· 考生：GLM subagent（6 agent × 3-4 题，严格无工具纪律）
- 题面：`scripts/export_prompts.py --tasks dms_side_effect_intake,tool_fault_recovery`
- 回灌：`--model file:runs/glm-v04-new/answers`（与 API 跑法同管线）
- 官方逐题分：`runs/glm-v04-new/scored/summary.json`（d-008 漏派 n/a）

## 结果

| 任务 | mean | 逐题 |
|---|---|---|
| dms_side_effect_intake | 61.39（12 有效题） | 全角案号考生全 100（d-004..006/d-102..104）；半角考生 0–17（d-001..003/d-007） |
| tool_fault_recovery | 4.17（8 题） | f-003 33.33，其余 0 |

## 发现

1. **全半角案号保真是跨任务强区分点**：同一任务包，全角考生 6/6 满分、
   半角考生大面积崩盘——与 u-hard flip 实证（R6）互为印证，d-104 双卡分心
   题上全角考生亦未误伤 805 分心卡（state0 设计有效）。
2. **fault 的 final_exact 过严，构成公平性缺陷**：prompt 未规定 answer 对象
   schema，考生自由作答（status=「完成」vs gold「已完成」、type=「财产案件」
   vs gold「civil」）recovery 全对而 final=0 → 4.17。与 calc formula_id 教训
   同构：**考生须知必须覆盖判分口径**。待修：task.yaml 声明 answer schema
   （answer_enums 机制扩展）+ 谓词只比声明过的叶。
3. **abstain 判定过窄**：f-008 考生「重试一次再诚实降级」是教科书式恢复，
   但 abstain 要求故障后零调用 → recovery=0。待修：accept 含 abstain 时
   以终答 status=无法完成 判定，不要求 after 为空。
4. **d-fake-001 负例只对 mock 有效**：真实考生正常调用工具（fake_tool 不触发），
   得 20（文书内容自由发挥失配）。负例夹具的功能定位应标注为 harness 自检。

## 结论

- dms 任务包（含 state0/双卡分心）对真实模型**即刻有效**，无需修改；
- fault 任务包判分管线工作正常，但需一轮公平性修正（answer schema 声明 +
  abstain 放宽）后方可用于正式测量；修复后以同法重测。
- 真实考生测量流程（export → subagent → file: 回灌）已跑通，DS 复跑同法可执行。
