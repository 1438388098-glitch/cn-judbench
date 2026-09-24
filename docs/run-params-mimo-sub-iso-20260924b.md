# run-params: mimo-sub-iso-20260924b

- 日期：2026-09-24
- 模型（统一显示名）：`MiMo（思考默认继承）`
  - ⚠️ 模型身份说明：本 run 由通用 subagent（继承会话默认模型与思考强度）隔离作答，按本仓库 `docs/run-score-ledger.md` §0 惯例「`mimo-sub*` / `general subagent` → MiMo（思考默认继承）」记为该显示名。底层实际模型以平台默认 subagent 模型为准，待平台侧确认；此不确定性已体现在 `provisional=true`。
- 原始 model_id / revision：`file:reports/runs/mimo-sub-iso-20260924b/answers` ；revision `subagent:mimo-sub:think-default-inherited`
- 成色：**洁净隔离**（证据：10 片 assign 各 ≤25 题；answers 245/245 齐套且全部合法 JSON；harness `contamination.hits=[]`；主会话代笔 0 —— 主代理全程未补写/改写任何 answers）
- 题集：8 包 245（238 能力 + 7 safety）
- harness / lawkb / scored run_id：harness `e480479` · manifest `c76e925cf71c` · slice_union_hash `sha256:b3017a3702ec88d68b36f6a45ed0a055abe6a496c20957e01eb4dcd96ab24d85` · scored run_id `c76e925cf71c`
- grand_eq / grand_w / hard[CI] / safety / scored% / flip / provisional：
  - **grand_eq = 65.75**（包等权，排名主指标；8 包能力均分等权）
  - grand_w = 73.44（仅参考）
  - hard = 72.33 ［67.29, 77.38］
  - safety_score = 100.00（7 道应拒夹具全拒对：refuse + 转介执业律师 + 不保证结果）
  - scored_rate = 100.00%（245/245 成功判分，0 n/a）
  - flip = 未测（未跑 `flip_rate_check`，见局限）
  - **provisional = true**
- 分包（机检均分，两位小数）：
  - cit / s_cap / contract / long_h / a_irac / u / gaia / calc
  - **59.26 / 62.27 / 31.24 / 41.65 / 65.44 / 88.78 / 78.26 / 99.07**
  - 说明：s_cap 为 s 包 13 道能力题均分；safety 7 题不进 s_cap、不进 grand_eq（grand_eq 仅含 238 能力题）。
- 对齐 guard：原始 SUSPECT = 45（全部 `swap_suspect`，`mutual=false` 0 例）。抽样 + 字段级核对结论：均为短 JSON 数值/编号相似误报（cit 的 as_of 与题面引用逐题一致；calc 家族 `formula_id` 合法、数值合理），**无真实换答**。退出码 1 为 guard 保守阻断，经人工抽样复核后放行。
- 局限：
  - 无 flip（未跑 flip_rate_check）→ 不满足正式表门禁，标 provisional；
  - 未启用 Judge（机检分，`judge_mean=n/a`）；
  - 模型身份以平台默认 subagent 模型为准（本仓 convention 记为 MiMo（思考默认继承）），实际底层模型待确认；
  - 目录/会话无技术沙箱，隔离为指令级（subagent 仅 Read/Write，禁 Bash/联网/读仓库）。
- 产物：`prompts/` `answers/` `*-scored/` `assign-0..9.json`
- 复现命令（密钥 `<REDACTED>`，本 run 为 `file:` 回灌、无外部 API 密钥）：

```bash
# 1) 导出题面（8 包 245）
.venv/Scripts/python.exe scripts/export_prompts.py \
  --tasks cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass \
  --run-dir reports/runs/mimo-sub-iso-20260924b

# 2) 切片（10 片 ≤25，轮转）-> assign-0..9.json（本 run 已生成）

# 3) 并行派 10 名隔离考生 subagent（只 Read 题面 + Write 答案）-> answers/ 245 文件

# 4) 对齐核对
.venv/Scripts/python.exe scripts/check_answer_alignment.py \
  --run-dir reports/runs/mimo-sub-iso-20260924b \
  --json reports/runs/mimo-sub-iso-20260924b/alignment.json

# 5) 官方判分（file: 回灌）
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m cnjudbench run-all \
  --tasks cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass \
  --model file:reports/runs/mimo-sub-iso-20260924b/answers \
  --revision "subagent:mimo-sub:think-default-inherited" \
  --out reports/runs/mimo-sub-iso-20260924b-scored

# 6) 门禁
.venv/Scripts/python.exe scripts/assert_run_gate.py reports/runs/mimo-sub-iso-20260924b-scored
```

> **非法律意见**：本评测不构成法律意见，不得用于司法裁判、合规放行或当事人决策。
