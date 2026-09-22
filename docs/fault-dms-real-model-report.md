# v0.4 新任务真实考生首测：dms（state0）与 tool_fault_recovery

- 日期：2026-09-23（R9）· 考生：GLM subagent（6 agent × 3-4 题，严格无工具纪律）
- 题面：`scripts/export_prompts.py --tasks dms_side_effect_intake,tool_fault_recovery`
- 回灌：`--model file:runs/glm-v04-new/answers`（与 API 跑法同管线）
- 官方逐题分：`runs/glm-v04-new/scored/summary.json`（d-008 漏派，R11 补测=100：获得「案号须原样一致」提示的考生全角保真成功）

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

## 追加（R10 修复后重测，同法同题）

修复：answer.status 单叶判分（题面声明枚举 已完成/无法完成，answer_enums 校验）+
abstain 放宽（重试后降级合法，status=无法完成 即成立）。

| 题 | R1（修复前） | R2（修复后） | 判定 |
|---|---|---|---|
| f-001 | 0 | 33.33 | vary 恢复成立；ptp 参数违例扣分 |
| f-002 | 0 | 0 | **真实判罚**：article 传 int 被 schema 拦截，核验调用实际失败却声称已完成 |
| f-003 | 33.33 | 66.67 | switch_tool + 参数全合法 |
| f-004 | 0 | 0 | **真实判罚**：同 f-002（stale_version 剧本脱节） |
| f-005 | 0 | 100 | vary + status 口径一致 |
| f-006 | 0 | 100 | retry_same（timeout 重试） |
| f-007 | 0 | 100 | vary（补 type 参数） |
| f-008 | 0 | 66.67 | 重试后诚实降级 → abstain 成立（修复生效） |
| mean | 4.17 | **58.33** | |

新发现：**参数纪律差在故障剧本下被放大**——考生抢跑的 schema 违例（int article、
缺 as_of）使注入点失配，随后声称「已完成」构成伪完成，被 recovery×final 正确判 0。
这是 exact/单位测之外的第三类机检信号：完成声明与工具轨迹的一致性。

## 追加（R11）

- d-008 补测：**提示覆盖可救格式保真**——同一考生模型拿到「案号须原样一致
  （不得转换全角/半角）」的显式提示后 100.00（此前半角考生 0–17）。
  差异主要来自考生须知完备度而非能力缺位，与 answer_enums 公平性原则一致：
  「原样保留」应成为 tool_call 任务的标配题面条款（task.yaml 已补）。
- 半角镜像变体 d-201..203 落地（16 题）：源案号半角、金样半角，与全角金样
  形成方向对称夹具——「擅自归一化」任一方向都失分，格式保真从偶发区分点
  固化为受控测量维。
