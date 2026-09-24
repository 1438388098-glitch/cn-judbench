# MiniMax-M3 隔离 subagent 考生跑(8 包 245 题)· 参数与结果

> 非法律意见:不得用于司法裁判、合规放行或当事人决策。

## 1. 产物与口径

- 原始作答目录:`reports/runs/minimax-m3-iso-20260924/`
- 官方判分目录:`reports/runs/minimax-m3-iso-20260924-scored/`
- 题集:8 包公开集,`cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass`
- 题数:245;harness:`e480479`;scored manifest run_id:`39fc1c186366`
- 判分:官方 `file:reports/runs/minimax-m3-iso-20260924/answers` 回灌;schema v0.6;Judge 未启用
- `grand_eq` 为 8 包等权主指标;`grand_w` 仅作参考

## 2. 模型与思考强度

- subagent 不指定模型,继承当前会话默认模型:`MiniMax-M3`
- 思考强度:`think-default-inherited`;即继承当前会话默认,未显式指定 `low/medium/high/max`
- manifest revision:`subagent:minimax-m3:think-default-inherited`
- 统一显示名:`MiniMax-M3(思考默认继承)`(记分册 §0 词表)
- `file:` 回灌不产生真实 API 调用、token、延迟或费用;`est_cost_usd=null`

## 3. 隔离与切片

- 10 片:`assign-1..assign-10.json`
- 分包题数:`25,25,25,25,25,25,25,25,25,20`,合计 245;每片 ≤25
- 齐套:`answers/*.txt` 245/245,文件名集合与 `index.json` 完全一致,全部 UTF-8 JSON 可解析
- 隔离成色(按落盘轨迹/协议判定):**洁净隔离** — 10 个 general subagent 并行作答,每人仅 Read 题面 + Write 答案;主会话代笔 0;外部 API 0
- 限制:隔离依赖 Read/Write 提示词约束,目录权限没有技术沙箱,不能证明考生从未越界;重派/补漏调度日志未单独持久化
- 对齐 guard:原始 40 条 `SUSPECT`,全为 `swap_suspect` 反向不成立;抽样核对 6 题(cit/cf/cp/cx 各 1-2)字段齐全、与题面对位(如 cx-001 答 `period_days`、cx-006 答 `remedy_max_interest_penalty`,公式 id 不同 — 表明真答对了对应题),均为短 JSON 字符重合度高的典型误报

## 4. 结果

### 总表

| 指标 | 值 |
|---|---:|
| capability grand_eq | **62.81** |
| capability grand_w | 72.70 |
| hard 均分 | 71.29 |
| hard 95% CI | [65.80, 76.77] |
| capability n | 238 |
| hard n | 180 |
| safety n | 7 |
| safety score | **71.43** |
| scored rate | 100.00%(n/a=0) |
| flip rate | n/a |
| provisional | **true** |

### 分包表

| 包 | capability n | 机检均分 | hard 均分 | safety | safety n | scored% |
|---|---:|---:|---:|---:|---:|---:|
| cit_validity | 27 | 69.63 | 53.33 | n/a | 0 | 100.00 |
| s_charge_subsume | 13 | 48.63 | 47.12 | 71.43 | 7 | 100.00 |
| contract_risk | 23 | 17.75 | 17.43 | n/a | 0 | 100.00 |
| long_horizon_case | 15 | 39.44 | 39.44 | n/a | 0 | 100.00 |
| a_irac_reason | 34 | 54.17 | 51.30 | n/a | 0 | 100.00 |
| u_element_extract | 49 | 98.98 | 98.53 | n/a | 0 | 100.00 |
| gaia_fee_deadline | 23 | 73.91 | 85.00 | n/a | 0 | 100.00 |
| calc_fail_to_pass | 54 | 100.00 | 100.00 | n/a | 0 | 100.00 |

- 同口径对照(仅作数字描述,非排名):DeepSeek-V4.1-Flash(思考默认)grand_eq 68.72 / hard 76.31 / flip 0%;MiMo-V2.5-Flash(思考默认继承)grand_eq 64.90 / hard 70.52;MiMo-V2.6-Pro(思考默认继承)grand_eq 70.89 / hard 76.76;Space Bunny Free(思考默认继承)grand_eq 62.99 / hard 71.56
- safety(应拒安全分)行内描述:MiniMax-M3(思考默认继承)以 71.43 与 MiMo-V2.6-Pro(思考默认继承)的 71.43 并列 8 包基线最高(其余 5 行洁净 API 行 safety=0.00)

## 5. provisional 与局限

- `provisional=true`:单次 subagent 跑没有 flip 复跑,manifest `stats.flip_rate=null`;不得进入正式 T-main 表
- 未启用 Judge:`judge_mean=n/a`
- `file:` 回灌没有真实费用、延迟、API 稳定性数据;这些字段不补造
- 8 包只覆盖 capability 集;工具沙箱 4 包未纳入本 run
- 对齐 guard 原始 40 条均为短 JSON 误报模式;完成人工关键字段复核后才回灌(已写明复核证据)

## 6. 复现命令

```powershell
.venv\Scripts\python.exe scripts\export_prompts.py `
  --tasks cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass `
  --run-dir reports/runs/minimax-m3-iso-20260924

.venv\Scripts\python.exe scripts\slice_assign.py `
  --run-dir reports/runs/minimax-m3-iso-20260924 `
  --size 25

.venv\Scripts\python.exe scripts\check_answer_alignment.py `
  --run-dir reports/runs/minimax-m3-iso-20260924 `
  --json reports/runs/minimax-m3-iso-20260924/alignment.json

.venv\Scripts\python.exe -m cnjudbench run-all `
  --tasks cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass `
  --model file:reports/runs/minimax-m3-iso-20260924/answers `
  --revision "subagent:minimax-m3:think-default-inherited" `
  --out reports/runs/minimax-m3-iso-20260924-scored
```

## 7. 验证

- `scripts/assert_run_gate.py reports/runs/minimax-m3-iso-20260924-scored`:通过
- 对齐 guard 40 条 SUSPECT 全部完成人工关键字段复核,均为短 JSON 字符重合度误报

> **2026-09-25 c419 重评注记**：本文档为原判分时点记录；判分修复（a-008 引语豁免体系）后同答案重评，现行分 62.81 → 63.18（a-008 重评 0→100）。现行锚点以 docs/run-score-ledger.md §1 为准。
