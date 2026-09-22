# run-params：GLM-5.3-Flash subagent 考生模式（并发 5，含 subagent Judge）

> 2026-09-22。被测模型 = ZCode 会话同款 GLM-5.3-Flash，以 **subagent 考生**模式作答
> （每题独立 agent 上下文，等价于 API 单题单调用；不走智谱付费 API——当日 API 429/1113 余额不足，见「口径差异」）。
> Judge 同为 subagent（GLM-5.3-Flash 自评），k_pass=1。最终 run_id：`b81de02b258f`。

## 复现命令（无密钥参与）

```powershell
# 1) 导出题面（105 题，与 run-all 同源渲染）
.\.venv\Scripts\python.exe scripts\export_prompts.py `
  --tasks cit_validity,u_element_extract,s_charge_subsume,contract_risk,a_irac_reason,long_horizon_case `
  --run-dir reports/runs/glm53flash-subagent-c5

# 2) 派 subagent 答题：每题一个 general-purpose agent，始终 5 个并行（21 波）
#    agent 读 prompts/<task>__<item>.txt → 深度思考 → 写 answers/<item>.txt（纯 JSON 本体）

# 3) 回灌机检 + Judge（与 API 跑法同一管线；judge-answers 按 sha256(judge prompt) 寻址）
.\.venv\Scripts\python.exe -m cnjudbench run-all `
  --tasks cit_validity,u_element_extract,s_charge_subsume,contract_risk,a_irac_reason,long_horizon_case `
  --model file:reports/runs/glm53flash-subagent-c5/answers `
  --revision subagent:glm-5.3-flash:think-max `
  --with-judge --judge file:reports/runs/glm53flash-subagent-c5/judge-answers --k-pass 1 `
  --concurrency 5 `
  --out reports/runs/glm53flash-subagent-c5

# 4) 面板
.\.venv\Scripts\python.exe scripts\sync_dashboard.py --run reports/runs/glm53flash-subagent-c5
```

## 参数

| 参数 | 值 |
|---|---|
| model（被测） | GLM-5.3-Flash（subagent 承载，manifest 记 `file:…/answers`，revision=`subagent:glm-5.3-flash:think-max`） |
| base_url | 无（不走 API；答案经文件回灌） |
| temperature | 名义 0.0（subagent 解码参数不可控，见口径差异） |
| reasoning_effort | 名义 max（以 agent 指令「最高推理深度」替代 API reasoning_effort） |
| thinking | agent 系统默认 + 指令深思 |
| concurrency | 5（每波 5 个 agent 并行） |
| k_pass | 1（每题单次作答；Judge 同为 k_pass=1） |
| Judge | subagent-judge（GLM-5.3-Flash 自评，`--judge file:<judge答案目录>` 哈希回灌）；**k_pass=1、无双盲校准，方向性参考** |

## run 指纹

- 题量：105（cit 21 / u 19 / s 20 / c 17 / a 19 / lh 9）
- run_id：`b81de02b258f`（含 Judge）；harness_sha：`2632664`
- prompt_hash：`sha256:143795f9f16c71f45…`；item_content_hash：`sha256:5b52e89aec796e388…`
- 答案完整性：105/105 落盘，全部通过 JSON 解析预检，**零 n/a**；Judge 回灌 28/28（u 19 + lh 9）

## 分包机检分 + Judge 分（百分制 · 两位小数）

| 包 | 维度 | 机检分 | Judge |
|---|---|---|---|
| cit_validity | Cit | **76.19** | n/a（无 rubric） |
| u_element_extract | U | **92.11** | **11.51** |
| s_charge_subsume | S | **49.60** | n/a（无 rubric） |
| contract_risk | C/G | **60.95** | n/a（无 rubric） |
| a_irac_reason | A | **54.73** | n/a（无 rubric） |
| long_horizon_case | U/O | **52.74** | **84.03** |
| **等权总分（机检）** | | **64.39** | |
| **按题量加权（机检）** | | **65.65** | |

**Judge 列警示（必读）**：
- 裁判 = 被测同族模型（GLM-5.3-Flash）自评，k_pass=1，未双盲校准 → 仅方向性参考，**不得用于正式对比**（limits.md 已自动携带同款警示）。
- rubric 覆盖仅 2/6 包：cit/s/c/a 四包无 rubric.yaml → 按规范记 n/a（非 0.00）。
- u_element judge 11.51 与机检 92.11 严重背离：裁判对「要件完整性/引用对应」打分极端严格（多数项 0–1/4）；long_horizon judge 84.03 反向宽松。两包 rubric 粒度不同 + 自评偏置，两个 Judge 数值之间不可互比。
- long_horizon 的 rubric 为 draft（未合议）：本次为通过 Rubric schema 校验，仅给两个 gate 补了 `on_fail: flag`（**零罚分占位**，Judge 路径 gate 本就不触发，评分语义未变；status 仍为 draft）。

abst：over_refuse 0.00%，over_promise 1.90%。诊断掉分：a_irac_reason diag_drop −17.34（诊断集高于主集，非 reward hacking）；long_horizon_case +3.53；reward_hacking_alert 均为 false。

## 花费 / 耗时 / tokens

- **总花费：$0（无 API 计费）**；`est_cost_usd=null`（无真实调用，禁止编造费用）。subagent 消耗的是 coding plan 额度，不计入本表。
- harness `wall_time_ms` 仅机检+judge 回灌（亚秒级）；**答题/裁判墙钟未精确计量**：答题 21 波 + 裁判 6 波 × 每波 5 agent，单 agent 12s–380s 不等，总量级约 1 小时。
- tokens：prompt/completion/cache 全部不可计量 → 0（如实记录，非真实值）；model_calls=105（每题 1 次）、judge_calls=28（每 rubric 题 1 次）。

## 口径差异（与 API 跑法对比必读）

1. **无 API 直调**：温度/seed/reasoning_effort 无法像 API 一样精确施加，subagent 以指令层等效（思考强度要求最高、单题独立上下文）。
2. **作答入口多一层机制指令**（读题文件、写答案文件），题面文本与 API 完全同源（同一 `prompt_template.replace("{input}", item.input)`）。
3. **每题独立 agent = 独立上下文**，无跨题污染，与 API 单题单调用等价。
4. machine 判分管线与历史 run 完全一致（同 harness 2632664），**跨 run 机检分可直接对比**；Judge 列均为 n/a，不可比。

## 与历史 run 对照（机检分）

| 包 | GLM-5.3-Flash subagent c5 | DS-V4.1-Flash c50 | DS-V4.1-Flash rerun |
|---|---|---|---|
| cit_validity | 76.19 | 76.19 | 76.19 |
| u_element_extract | 92.11 | 100.00 | 100.00 |
| s_charge_subsume | **49.60** | 46.85 | 47.64 |
| contract_risk | 60.95 | 63.16 | 60.50 |
| a_irac_reason | 54.73 | 56.57 | 52.22 |
| long_horizon_case | **52.74** | 41.20 | 46.94 |
| 等权 | 64.39 | — | — |

（DS 两列取自 reports/runs/ds-flash-v41-c50、ds-flash-v41-rerun。glm-53-flash-c50 仅 5 题、c10 全灭 `model_calls=0`——均系智谱 1113 余额 + 适配器重试 bug，无有效分可对照。）

## 相关产物

- run：`reports/runs/glm53flash-subagent-c5/`（manifest.json / summary.json / limits.md / prompts/ / answers/ / judge-prompts/ / judge-answers/ / index.json / judge-index.json）
- 面板：`C:\Users\20579\XiaomiMiMoProjects\2026-09-22\ai-benchmark-subagent-github`（已同步）
- 新增代码：`src/cnjudbench/adapters/file_answers.py`（含 HashedFileAnswersAdapter）、cli `file:` 模型规格与 `--judge file:` 规格、`scripts/export_prompts.py`、`scripts/export_judge_prompts.py`、测试 `tests/test_file_answers_adapter.py`（全套 208 passed）
- 数据改动：`tasks/long_horizon_case/rubric.yaml` 两个 gate 补 `on_fail: flag`（零罚分占位，过 schema 校验；评分语义未变）
