# run-params: doubao21lite-iso-20260924

> 非法律意见：不得用于司法裁判、合规放行或当事人决策。

## 1. 产物与口径

- 原始作答目录：`reports/runs/doubao21lite-iso-20260924/`
- 官方判分目录：`reports/runs/doubao21lite-iso-20260924-scored/`
- 题集：8 包公开集 `cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass`
- 题数：245（238 能力 + 7 safety）；harness `59504f3`；scored manifest run_id `52a39de2264c`
- 判分：官方 `file:reports/runs/doubao21lite-iso-20260924/answers` 回灌；schema v0.6；Judge 未启用
- `grand_eq` 为 8 包等权主指标；`grand_w` 仅作参考

## 2. 模型与思考强度

- subagent 不指定模型，继承当前会话默认模型：**豆包 2.1 Lite**
- 思考强度：低（用户截图确认当前为低挡）
- manifest revision：`subagent:doubao-2.1-lite:think-low`
- 统一显示名：**豆包 2.1 Lite（思考低）**
- `file:` 回灌不产生真实 API 调用、token、延迟或费用；`est_cost_usd=null`

## 3. 隔离与切片

- 切片：`assign-1..assign-10.json`，每片 ≤25（25×9 + 20 = 245）
- 实际调度：前 3 片（assign-1/2/4）由独立 subagent 并行完成；其余 170 题由一个全量补卷 subagent 一次性完成（它读 index.json 后自动跳过已存在文件、只补缺题）
- 齐套：`answers/*.txt` 245/245，文件名集合与 index.json 完全一致，全部 UTF-8 JSON 可解析
- 隔离成色：**洁净隔离**——所有答案均由 subagent 独立 Read 题面 + Write 答案完成；主会话未写过、未改过任何 `answers/*.txt`；subagent 未接触 gold/判分器/仓库文档
- 调度备注：本会话 subagent 派发侧不稳定（一轮派多个大部分被静默拒绝），最终改为单 agent 全量补卷；不影响答案隔离性
- 对齐 guard：原始 45 条 SUSPECT，全部 `swap_suspect` 反向不成立；抽样核对 cit-002 / cf-001 / cx-006 / s-017 等字段对位正确（cf 用 fee_tiered_2007、cx 用 remedy_max_interest_penalty，公式 id 不同），均为短 JSON 字符重合度高的典型误报

## 4. 结果

### 总表

| 指标 | 值 |
|---|---:|
| capability grand_eq | **65.67**（flip run2 定分；run1=74.53 偏高不计入） |
| capability grand_w | 75.58 |
| hard 均分 | 74.22 |
| hard 95% CI | [68.18, 79.81] |
| capability n | 238 |
| hard n | 180 |
| safety n | 7 |
| safety score | **100.00** |
| scored rate | 100.00%（n/a=0） |
| flip rate | **27.35%**（67/245，阈值 <5%） |
| flip rate | 27.35%（67/245，阈值 <5%，FAIL） |
| provisional | **true**（flip 27.35% >> 5%，方差极大） |

### 分包表

| 包 | capability n | 机检均分 | hard 均分 | safety | safety n | scored% |
|---|---:|---:|---:|---:|---:|---:|
| cit_validity | 27 | 74.07 | 58.33 | n/a | 0 | 100.00 |
| s_charge_subsume | 13 | 55.05 | 55.48 | 100.00 | 7 | 100.00 |
| contract_risk | 23 | 7.80 | 0.00 | n/a | 0 | 100.00 |
| long_horizon_case | 15 | 34.57 | 34.57 | n/a | 0 | 100.00 |
| a_irac_reason | 34 | 66.91 | 64.84 | n/a | 0 | 100.00 |
| u_element_extract | 49 | 100.00 | 100.00 | n/a | 0 | 100.00 |
| gaia_fee_deadline | 23 | 86.96 | 95.00 | n/a | 0 | 100.00 |
| calc_fail_to_pass | 54 | 100.00 | 100.00 | n/a | 0 | 100.00 |

- 同口径对照（仅作数字描述，非排名主张）：DeepSeek-V4.1-Flash（思考默认）grand_eq 68.72 / hard 76.31；MiMo-V2.6-Pro（思考默认继承）grand_eq 70.89 / hard 76.76；MiniMax-M3（思考默认继承）grand_eq 62.81 / hard 71.29
- safety（应拒安全分）：豆包 2.1 Lite（思考低）以 100.00 与 MiMo-V2.6-Pro 的 71.43 并列/超过，7 道应拒题全部正确拒绝

## 5. provisional 与局限

- `provisional=true`：flip 复跑完成，flip rate=27.35%（67/245），远超 5% 阈值；run1 grand_eq=74.53 vs run2=65.67（Δ=-8.86），说明低思考档 subagent 答题方差极大，单次分数不可靠；不得进入正式 T-main 表。flip 集中在 contract_risk（23/23 全翻）、a_irac（14/34）、long_h（11/15）；u/calc 基本稳定；safety 两次均 100.00
- 未启用 Judge：`judge_mean=n/a`
- `file:` 回灌无真实费用/延迟/API 稳定性数据
- 8 包只覆盖 capability 集；工具沙箱 4 包未纳入
- 对齐 guard 45 条均为短 JSON 误报模式，已抽样核对关键字段

## 6. 复现命令

```powershell
.venv\Scripts\python.exe scripts\export_prompts.py `
  --tasks cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass `
  --run-dir reports/runs/doubao21lite-iso-20260924

.venv\Scripts\python.exe scripts\slice_assign.py `
  --run-dir reports/runs/doubao21lite-iso-20260924 --size 25

.venv\Scripts\python.exe scripts\check_answer_alignment.py `
  --run-dir reports/runs/doubao21lite-iso-20260924 `
  --json reports/runs/doubao21lite-iso-20260924/alignment.json

.venv\Scripts\python.exe -m cnjudbench run-all `
  --tasks cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass `
  --model file:reports/runs/doubao21lite-iso-20260924/answers `
  --revision "subagent:doubao-2.1-lite:think-low" `
  --out reports/runs/doubao21lite-iso-20260924-scored
```
