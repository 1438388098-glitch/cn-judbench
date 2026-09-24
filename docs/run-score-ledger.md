# 跑分记分册（run score ledger）

> **本文件是 CN-JudBench 全部跑分历史的唯一汇总账。**
> 新 run 判分完成后必须在此登记；对外报分、论文表、夜报引用总分时以本账为准。
> 单次 run 的完整参数与复现命令见对应 `docs/run-params-*.md`；论文用数字溯源见 `docs/paper-numbers.md`。
>
> **非法律意见**：本评测不构成法律意见，不得用于司法裁判、合规放行或当事人决策。
>
> 数据截至：2026-09-24。来源字段一律以各 `*-scored/summary.json` 为准。

## 0. 记账纪律

1. **主指标 = `capability.grand_eq`（8 包等权）**。`grand_w` 仅参考（受 calc/u 饱和拉动）。
2. **隔离成色必须标注**：`iso` = 考生 subagent/独立 API，未接触 gold；`self` = 会话内自答或主会话代笔；`mixed` = 部分污染后补隔离。`self`/`mixed` **禁止进正式排名表**。
3. **`provisional=true` 不得写入 T-main**。正式表还需 flip&lt;5% + deps 锁定。
4. **禁止把不同 slice / 不同题量 / 能力包 vs 工具包混进同一排名表**。工具沙箱 4 包单独记。
5. 分数字段映射：`grand_eq/grand_w/hard` ← `summary.capability`；`safety` ← `summary.safety_score`（0–100，7 道应拒题）；分包 ← `summary.per_task.*.machine_mean_str`（capability 机检均分；s 包的 safety 7 题不进该均分，单列 safety 列）。
6. 新行入账顺序：跑完 → `*-scored/summary.json` → 本账登记 →（若进论文）`paper-numbers.md` / `paper-tables.md`。

---

## 1. 主记分板 · 8 包能力集（n_capability=238，n_safety=7）

同口径可横比的全量 8 包行。排序按 grand_eq 降序；**仅供对照，正式排名待 flip**。

| # | run 目录 | 模型 / 成色 | grand_eq | grand_w | hard | hard CI95 | safety | scored | provisional | 备注 |
|---|---|---|---:|---:|---:|---|---:|---:|---|---|
| 1 | `mimo-sub-full-scored` | mimo subagent · **mixed（污染）** | 73.62 | 79.93 | 79.12 | — | 100.00 | 100% | true | 主会话看过 gold 后补写 38 题；**禁入正式表** |
| 2 | `mimo-sub-iso-scored` | mimo subagent · iso | 70.89 | 78.01 | 76.76 | [71.91, 81.62] | 71.43 | 100% | true | 208 题复用 MIX 洁净子代理答 + 37 题隔离重答；污染溢价 ≈ +2.73 |
| 3 | `glm53f-self-v06-scored` | GLM-5.3-Flash · **self（污染）** | 69.36 | 77.89 | 78.23 | — | 0.00 | 100% | true | 会话内自答参考跑；**禁入正式表** |
| 4 | `ds-flash-v06-full` | DeepSeek V4.1 Flash · API iso | **68.72** | 77.96 | 76.31 | — | 0.00 | 100% | true | **官方清洁 API 基线行**；flip 0/81=0%；$0.56 |
| 5 | `mimo-v25f-iso-0924-scored` | mimo-v25f · iso | 64.90 | 72.85 | 70.52 | [64.48, 75.89] | 0.00 | 100% | true | 09-24 隔离考生；缺 run-params |
| 6 | `space-bunny-free-sub-iso-20260924-scored` | opencode/space-bunny-free · iso | 62.99 | 72.22 | 71.56 | [66.52, 76.82] | 0.00 | 100% | true | 隔离 subagent |
| 7 | `mimo-sub-iso-20260924-scored` | general subagent · iso | 62.80 | 71.26 | 68.74 | [62.76, 74.32] | 0.00 | 100% | true | 与 #2 不是同一批答案 |
| 8 | `glm53f-iso-scored` | GLM-5.3-Flash · iso | 59.14 | 70.29 | 67.38 | — | 0.00 | 100% | true | 首个双模型隔离对照的 GLM 行 |

基线锚点（同判分口径）：random **7.96** / rules **27.03** / mock:gold **100.00**（`baseline-v06` / `baseline-v06b` 零漂移验证）。

**可引用结论（描述性，非正式排名）**

- 清洁隔离行 grand_eq 区间约 **59–71**；唯一带 flip 的 API 行是 DS-flash 68.72。
- 自答/污染溢价：GLM 69.36 − 59.14 ≈ **+10.2**；mimo MIX 73.62 − ISO 70.89 ≈ **+2.73**（仅污染子集重答后）。
- 共同弱项：contract risk_labels 词表、cit 边界、s 包 safety 应拒（多数 iso 行 safety=0）。

---

## 2. 分包矩阵 · 8 包全量行

列 = `per_task.*.machine_mean_str`（capability 机检均分）。`safety` 列单独见上表。

| run | cit | s_cap | contract | long_h | a_irac | u | gaia | calc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mimo-sub-full（污染） | 74.07 | 69.84 | 44.06 | 54.25 | 62.87 | 96.94 | 86.96 | 100.00 |
| mimo-sub-iso | 74.07 | 67.27 | 36.86 | 48.70 | 60.66 | 96.94 | 82.61 | 100.00 |
| glm53f-self（污染） | 84.44 | 39.01 | 32.80 | 49.75 | 63.24 | 98.98 | 91.30 | 95.37 |
| ds-flash-v06 | 71.85 | 44.74 | 31.04 | 44.05 | 75.22 | 95.92 | 86.96 | 100.00 |
| mimo-v25f-iso-0924 | 74.07 | 59.65 | 16.23 | 39.31 | 64.71 | 98.98 | 78.26 | 87.96 |
| space-bunny-free-iso | 60.00 | 45.22 | 36.69 | 34.17 | 65.44 | 95.92 | 73.91 | 92.59 |
| mimo-sub-iso-20260924 | 74.07 | 52.31 | 26.74 | 31.02 | 57.35 | 82.65 | 78.26 | 100.00 |
| glm53f-iso | 68.15 | 18.41 | 37.29 | 44.48 | 47.79 | 97.96 | 60.87 | 98.15 |

结构速读（仅 iso 行）：

- **DS-flash** 长文 IRAC（a_irac 75.22）与精确计算（calc 100）最强。
- **GLM-iso** contract 相对最好（37.29），但 a_irac/gaia 明显偏弱。
- **mimo 系** cit/u 稳定高位；mimo-v25f 在 contract/calc 掉队（16.23 / 87.96）。
- **s 包** 对所有考生都苛（词表 set_f1）；safety 应拒几乎全军覆没（除 mimo-sub-iso 71.43、污染 MIX 100）。

---

## 3. 工具沙箱 4 包（与能力集不可混排）

| run | 模型 | grand_eq | tau | tool_search | fault | dms | 口径 |
|---|---|---:|---:|---:|---:|---:|---|
| `ds-flash-v06-tools` | DeepSeek V4.1 Flash | 60.23 | 51.18 | 56.00 | 37.50 | 96.23 | v0.6 · n=77 |
| `glm53f-subagent-v04` / audit 切片 | GLM-5.3-Flash | — | 0.00* | — | 58.33* | 64.36* | **v0.4 口径**，不可与上行直接比 |
| `ci-l2` / `ci-v04` | mock:tools | 100 / 97.50 | — | 100 | 100 | 95 | 冒烟金样 |

\* 来自 `v05new-*` / `audit-*` 切片均分，题量与 v0.6 全量不同，仅作定性对照。

---

## 4. 历史 run 全目录（含冒烟 / 切片 / 金样）

完整 70 个含 `summary.json` 的目录速查。`—` 表示该 summary 无此字段（旧 schema 或空跑）。

### 4.1 金样与基线

| 目录 | 模型 | grand_eq | n | 用途 |
|---|---|---:|---:|---|
| `baseline-v041` / `baseline-v041-check` | mock:gold | 100.00 | 191 / 34 | v0.4.1 金样 |
| `baseline-v06` | mock:gold | 100.00 | 238 | v0.6 基线（random 7.96 / rules 27.03） |
| `baseline-v06b` | mock:gold | 100.00 | 238 | 判分修复后零漂移复核 |
| `aa11b923171e` | mock:gold | 100.00 | 89 | 3 包金样 |
| `ci` / `ci-gold-all` / `ci-l2` / `ci-v04` | mock:gold / mock:tools | 100 / 100 / 100 / 97.50 | 123 / 131 / 25 / 36 | CI 门禁金样 |
| `iso-mock-smoke` / `smoke-p1` / `p2-*` / `p3-*` / `dod-final` | mock:* | — / 100 等 | 小 | 开发冒烟 |

### 4.2 DeepSeek 系

| 目录 | grand_eq | n | 备注 |
|---|---:|---:|---|
| `ds-flash-v06-full` | **68.72** | 238 | **主表候选**（见 §1） |
| `ds-flash-v06-tools` | 60.23 | 77 | 工具 4 包（见 §3） |
| `ds-flash-v06-smoke` | 71.85 | 27 | cit 冒烟 |
| `ds-flash-v41-c50` / `ds-flash-v41-rerun` | — | 切片 | v0.4.1 期分包分 |
| `ds-flash-v41-v04` | n/a | 0 | 空跑 |
| `ds-flash-c` / `-final` / `-fixed` / `-full` / `-gaia` / `-smoke` / `-tau1` / `-tool` / `-v2` / `-v3` / `-v4` | — | 切片 | v0.4 早期调试，分数不可与 v0.6 比 |

### 4.3 GLM 系

| 目录 | grand_eq | n | 成色 | 备注 |
|---|---:|---:|---|---|
| `glm53f-iso-scored` | **59.14** | 238 | iso | 8 包全量（见 §1） |
| `glm53f-iso-5p-scored` | 61.75 | 137 | iso | 5 包子集，勿与全量比 |
| `glm53f-self-v06-scored` | 69.36 | 238 | **self 污染** | 仅管线验证 |
| `glm53f-self-v06-scored-*`（8 个分包） | 分包分 | 分包 | self | 分包调试 |
| `glm53f-v04-merged-v06rescore` | 66.24 | 87 | mixed | v0.4 答案 × v0.6 判分 |
| `glm53f-subagent-v04` | 57.19 | 98 | mixed | v0.4 口径 |
| `glm53f-regrade-v04` | 48.63 | 79 | mixed | 重判 |
| `glm53flash-subagent-c5` | — | 切片 | iso? | 非公开集切片 |
| `glm-53-flash-c10` / `-c50` | — / — | 切片 | API | 早期 |
| `glm53f-v06-smoke` | n/a | 0 | API | 空跑 |

### 4.4 mimo / 其他隔离 subagent 系

| 目录 | grand_eq | n | 成色 | 备注 |
|---|---:|---:|---|---|
| `mimo-sub-full-scored` | 73.62 | 238 | **mixed** | 污染全量 |
| `mimo-sub-iso-scored` | 70.89 | 238 | iso | 污染子集隔离重答 |
| `mimo-sub-iso-20260924-scored` | 62.80 | 238 | iso | 新一批全隔离 |
| `mimo-v25f-iso-0924-scored` | 64.90 | 238 | iso | **缺 run-params** |
| `space-bunny-free-sub-iso-20260924-scored` | 62.99 | 238 | iso | |
| `mimo-sub-e2e-scored` | 75.57 | 89 | mixed? | 3 包 e2e |

### 4.5 切片 / 审计 / 难度实验（不可进主表）

| 目录 | grand_eq | n | 内容 |
|---|---:|---:|---|
| `airac-hard2-r25` / `-scored2` | 89.66 / 93.10 | 29 | a_irac hard 重跑 |
| `airac-refuse-r38` / `-fixed` | 84.38 / 96.88 | 32 | a_irac refuse 修复前后 |
| `audit-calc1` | 82.61 | 46 | calc 审计 |
| `audit-u-hard1` | 91.07 | 28 | u hard |
| `audit-fault2` | 58.33 | 8 | fault |
| `audit-dmsfault1` | 38.43 | 21 | dms+fault |
| `v05new-s1m-score` / `s2-score` / `s2m-score` | 65.87 / 61.08 / 62.85 | 62 | E18 双考生区分度 |
| `acc-p1p2` | — | 切片 | 验收 |

---

## 5. run-params 对照

| run | run-params |
|---|---|
| ds-flash-v06-full / tools | [run-params-ds-flash-v06.md](run-params-ds-flash-v06.md) |
| glm53f-iso-scored | [run-params-glm53f-iso-v06.md](run-params-glm53f-iso-v06.md) |
| glm53f-self-v06-scored | [run-params-glm53f-self-v06.md](run-params-glm53f-self-v06.md) |
| mimo-sub-iso-20260924 | [run-params-mimo-sub-iso-20260924.md](run-params-mimo-sub-iso-20260924.md) |
| space-bunny-free-sub-iso-20260924 | [run-params-space-bunny-free-sub-iso-20260924.md](run-params-space-bunny-free-sub-iso-20260924.md) |
| ds-flash-v41 / v41-c50 / airac-hard2 / glm53flash-subagent-c5 | 同前缀 `run-params-*.md` |
| **mimo-v25f-iso-0924** | **缺** — 待补 |
| **mimo-sub-iso**（70.89） | **缺** — 待补 |
| **mimo-sub-full**（73.62，污染） | **缺** — 建议补污染说明即可 |

> 注：`run-params-glm53f-iso-v06.md` 表内 s_cap 写 11.96、safety 写「0 错」，与 `glm53f-iso-scored/summary.json`（s_cap **18.41**、safety_score **0.00**）不一致。以 summary 为准；run-params 的 11.96 实为「capability 均分再摊入 7 道 safety 零分」的另一种汇总，且「0 错」应为「0 对」笔误。待修订该文。

---

## 6. 新行入账模板

```markdown
### <run-scored 目录名>
- 日期：
- 模型 / rev / 思考强度：
- 成色：iso | self | mixed（一句话证据）
- 题集：8 包 245 / 工具 4 包 / 切片 n=…
- grand_eq / grand_w / hard[CI] / safety / scored% / flip% / provisional
- 分包：cit/s/contract/lh/a_irac/u/gaia/calc = …
- run-params：
- 是否可进 T-main：否（原因）/ 待 flip
```

登记后同步：§1 主记分板（若 8 包全量）、§2 分包矩阵、§5 对照表。
