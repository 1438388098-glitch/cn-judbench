# run-params: glm53f-low-iso-20260924

- 日期：2026-09-24
- 模型（统一显示名）：`GLM-5.3-Flash（思考低）`
- 原始 model_id / revision：`file:reports/runs/glm53f-low-iso-20260924/answers` / `subagent:glm-5.3-flash:think-low-inherited`（考生 subagent 未钉 model，继承会话默认模型与思考档；「思考低」为用户指令口径，见局限）
- 成色：**洁净隔离**（证据：10 个隔离考生 subagent 仅 Read 题面、只 Write `answers/*.txt`，禁 Bash/联网/gold/仓库文档；answers 245/245；主会话代笔 0；真换答 2 题由**新**隔离考生重考，主会话未碰任何答案文件）
- 题集：8 包 245（238 能力 + 7 safety）
- harness / lawkb / scored run_id：manifest `179cb0ad29c1` · harness `59504f3` · lawkb-2026.09.2 · `glm53f-low-iso-20260924-scored`
- grand_eq / grand_w / hard[CI] / safety / scored% / flip / provisional：**64.18** / 72.70 / 70.04 [64.41, 75.48] / **100.00** / 100% / 未测（无 flip）→ **provisional=true**
- 分包：cit 72.22 / s_cap 60.26 / contract 31.08 / long_h 28.71 / a_irac 56.62 / u 98.98 / gaia 73.91 / calc 91.67（safety 100.00 = 7 题全拒对）
- n/a 数：0（245/245 全 scored）

## 调度记录

| 片 | 内容 | 结果 |
|---|---|---|
| assign-1…10（25×9 + 20×1） | 10 个隔离考生并行 | 10 片一次全成，无重派 |
| redo-1 | 对齐 guard 拦出 u-013/u-016 真换答（互指），1 个新隔离考生重考 | 完成，逐题在位 |

## 对齐 guard 复核结论

- `check_answer_alignment` 首轮 58 SUSPECT（回灌阻断）。逐条「答案↔自身题面 vs 答案↔guard 最相似他题题面」相似度对位复核：
  - **真换答 2 题**：u-013/u-016（mutual，答案完全对调——津 01 民终 8 号案 ↔ 沪 0115 民初 330 号案），由新隔离考生重考后逐字段核实在位。
  - 其余 56 条为短 JSON 机械误报（cf/cp 全锚 cx-006 且相似度差 ≤0.02 在噪声内；refuse 类短答案词汇重叠低；cit/a/g 同族题面天然相似）。
- 重考后 2 题答案与其题面逐字段核对（金额/日期/案号）全部在位。**结论：换答已清零，允许回灌。**

## 判分结果（machine 通道，judge_mean n/a）

| 包 | n | 机检均分 | hard |
|---|---:|---:|---:|
| cit_validity | 27 | 72.22 | 54.17 |
| s_charge_subsume（s_cap） | 13 | 60.26 | 56.94 |
| contract_risk | 23 | 31.08 | 36.97 |
| long_horizon_case | 15 | 28.71 | 28.71 |
| a_irac_reason | 34 | 56.62 | 53.91 |
| u_element_extract | 49 | 98.98 | 98.53 |
| gaia_fee_deadline | 23 | 73.91 | 80.00 |
| calc_fail_to_pass | 54 | 91.67 | 89.02 |

safety 7 题（s-015…s-021）全部拒对 = 100.00；over_refuse 0.00 / over_promise 0.00。

## 局限

- **provisional**：无 flip 复跑（建议 <5%），不得进正式表 T-main。
- **思考档无法技术钉死**：本环境考生 subagent 逐片不可指定 model/think，实际继承会话默认思考档；「思考低」为用户指令口径、会话层面设定，非 API `reasoning_effort=low` 直跑取证。如需严格钉死请走 API 隔离跑。
- judge_mean n/a（机检通道，与其他 `file:` 回灌行同口径）；工具轨未测。
- **a_irac 触发 reward_hacking_alert**（diag 变体分差 +28.45）：主分 56.62 为机检口径如实入账；结合已入档的 a-008 判分器引语假阴性（承诺词窗口未覆盖引语否定语境），说理写作包的机检分存在判分器偏低的系统性可能，对照时须谨慎。
- 长案分析 28.71 为本行最弱包（低于 GLM 思考高的 46.12 与思考默认继承的 44.48）。
- 隔离为约定式（prompt 纪律），目录权限无技术沙箱。
- est_cost_usd=null（`file:` 回灌，不编造费用）。

## 同模型思考档对照（GLM-5.3-Flash，8 包 245）

| 思考档 | grand_eq | hard | safety |
|---|---:|---:|---:|
| 思考高（`glm53f-hi-iso-0924`） | 69.22 | 76.15 | 71.43 |
| **思考低（本行）** | **64.18** | 70.04 | 100.00 |
| 思考默认继承（`glm53f-iso`） | 59.14 | 67.38 | 0.00 |

描述性读法（无 flip，不作排名主张）：思考低落在思考高与思考默认继承之间；safety 7/7 全拒对为 GLM 三档中首次。

## 产物

- 题面 / 答案 / 切片 / 对齐：`reports/runs/glm53f-low-iso-20260924/`（prompts、answers、assign-1…10.json、redo-1.json、alignment.json、EXAMINEE.md、index.json）
- 判分：`reports/runs/glm53f-low-iso-20260924-scored/`（manifest.json、summary.json、limits.md）

## 复现命令（密钥 `<REDACTED>`）

```powershell
.venv\Scripts\python.exe scripts\export_prompts.py `
  --tasks cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass `
  --run-dir reports/runs/glm53f-low-iso-20260924
# 切片 assign-1..10（25×9+20×1）→ ≤25 题/片派隔离考生（Read 题面 / Write 答案）
.venv\Scripts\python.exe scripts\slice_assign.py --run-dir reports/runs/glm53f-low-iso-20260924
.venv\Scripts\python.exe scripts\check_answer_alignment.py `
  --run-dir reports/runs/glm53f-low-iso-20260924 --json reports/runs/glm53f-low-iso-20260924/alignment.json
.venv\Scripts\python.exe -m cnjudbench run-all `
  --tasks cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass `
  --model file:reports/runs/glm53f-low-iso-20260924/answers `
  --revision "subagent:glm-5.3-flash:think-low-inherited" `
  --out reports/runs/glm53f-low-iso-20260924-scored
.venv\Scripts\python.exe scripts\assert_run_gate.py reports/runs/glm53f-low-iso-20260924-scored
```

> 本评测不构成法律意见，不得用于司法裁判、合规放行或当事人决策。
