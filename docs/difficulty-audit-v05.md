# 全库难度盘点 v0.5（Phase 0 产出）

> 日期：2026-09-23。依据：DESIGN-difficulty-practice-v05.md §1。
> **处置状态**：Phase 1 已执行——a_irac T4a/T4b 砍候选 20 题移入
> `data/archive/a_irac_reason.jsonl`，public 余 12 题（本文档的 tier 分布
> 仍按盘点时点的 271 题口径记录，是历史证据面，不随剖减改写）。
> 证据面全部为**现行判分器**（R38 后）下的 GLM 真考生 run；存量答案已用 file: 回灌重判
> （audit-u-hard1 / audit-calc1 / audit-dmsfault1 / audit-fault2，零 API）。
> 机器可读版：reports/difficulty-audit-v05.json（逐题含 tier/mean/n）。

## 一、方法与证据白名单

| 证据 | run | 覆盖 | 说明 |
|---|---|---|---|
| a_irac k=3 trio | airac-refuse-r38-fixed + airac-k2-run2 + airac-k3-fixed-run3 | 32 题×3 样本 | R38 后判分，过 pass³ 门禁的那组 |
| u_element hard | audit-u-hard1（= u-hard-glm1 答案重判） | 28 hard 题×1 | |
| calc | audit-calc1（= calc-glm-r2 答案重判） | 46 题×1 | |
| dms | audit-dmsfault1（= glm-v04-new 答案重判） | 13 题×1 | |
| fault | audit-dmsfault1 + audit-fault2（= glm-fault-r2 重判） | 8 题×2 样本 | f-101..104 无考生答案 → 待测，不虚判 |

**排除的证据（重要）**：glm53f-subagent-v04 是金样修复**前**的基线（a_irac 41.71、contract
24.84、s_charge 38.81、long_horizon 40.69）——低分很可能是金样污染而非难度，不得用于分级；
ds-flash-v41-v04 无可解析逐题分；全部 mock/smoke/ci run（重放 gold 全 100）排除。

## 二、四级分布（271 题）

| 包 | T1夹具 | T3实难 | T4a砍候选(3+样本确认) | T4b砍候选(待第3样本) | 待测 |
|---|---|---|---|---|---|
| a_irac_reason | 0 | **4** | **28** | 0 | 0 |
| calc_fail_to_pass | 0 | **16** | 0 | 30 | 0 |
| u_element_extract | 0 | **5** | 0 | 23 | 15(base) |
| tool_fault_recovery | 0 | **8** | 0 | 0 | 4 |
| dms_side_effect_intake | 1 | **5** | 0 | 7 | 3 |
| cit_validity | 0 | 0 | 0 | 0 | 21 |
| contract_risk | 0 | 0 | 0 | 0 | 17 |
| s_charge_subsume | 0 | 0 | 0 | 0 | 20 |
| tool_search_statute | 1 | 0 | 0 | 0 | 25 |
| gaia_fee_deadline | 0 | 0 | 0 | 0 | 17 |
| tau_jud_intake | 0 | 0 | 0 | 0 | 12 |
| long_horizon_case | 0 | 0 | 0 | 0 | 9 |
| **合计** | **2** | **38** | **28** | **60** | **143** |

## 三、T3 实难题清单（38 题，头部模型真失分）

- **a_irac（4）**：a-008 33.3（应拒措辞风格波动）、a-019 50、ah-005 50、a-003 83.3（条号精度翻转）
- **calc（16）**：**复利 ci-001..012 整族全 50**（半年复利系统性和失分！）+ cf-011/012/015/018/019 + cp-005/006
- **fault（8）**：f-001..008 全族 0-33——**工具故障恢复是全库最强区分轴**
- **dms（5）**：d-001 0、d-002/d-003 16.7、d-007 0、d-101 83.3——状态终态题头部模型会整题崩
- **u_element（5）**：u-027/030/031/036/041 各 50

## 四、削减池与政策

- **T4a（28，确认可砍）**：全在 a_irac。Phase 1 执行时每包保 5 题地板（跨域分布+
  答题协议变体 a-009/010/013 至少留 1）+ 4 道应拒题 + 全部 hard 不动 → 预计砍 23 题。
- **T4b（60，待第3样本）**：calc 30 / u_element 23 / dms 7。补第 3 样本（复用存量答案
  或再派一轮 subagent 考生）后再定砍留；本轮不动。
- **待测（143）**：cit/tool_search/gaia/tau 的旧证据是修复前的但金样大体可信；**contract /
  s_charge / long_horizon 三包旧分 24-40 属"金样未审计"区**，禁止当难度证据——
  排期金样逐题复核（R16 方法）+ 新鲜 GLM 实测后再分级。u_element base 15 待补测。

## 五、对扩容计划的直接修正

1. **计算轴升级为第二优先**：复利整族 12 题全 50 是系统性失分（不是个例抖动），
   3b 的 +8 题应围绕复利/违约金竞合加深。
2. **工具轴区分度最强**：fault 全族 + dms 崩题证明 L2/L3a 不是"送分轨"——
   4b 期限监控（env_diff 基座）预期区分度良好。
3. **a_irac 加题必须落在四道实难题的同族**：条号精度、法定构成情形（ah-005 族）、
   应拒措辞（a-008 族）——泛泛的"多争点"已被证明无效。

## 附录：Phase 1 执行后的剩余层级分布（2026-09-23）

public 剩 251 题 / 12 包（原 271）。a_irac 32→12：保 T3 实难 4
（a-003/a-008/a-019/ah-005）+ T4a 中的应拒 3 题（a-020/021/022，R37 安全轨
永不砍）+ 地板 2 题（a-009 协议变体、a-015 跨域劳动，锚定测试/采样基建）
+ 科目网格保底 3 题（a-014 合规、a-016 家事、a-017 知产——「8 科目×每包
全交叉」为数据集公开不变量，剖减不得破坏）；砍 20 题入
`data/archive/a_irac_reason.jsonl`。其余包本轮不动（T4b 按 DESIGN
§3/§4 走「增」路线处置）。下表 tier 沿用盘点时点标签：

| 包 | T1夹具 | T3实难 | T4a(应拒/地板/网格保留) | T4b待3样 | 待测 | 剩余 |
|---|---|---|---|---|---|---|
| a_irac_reason | – | 4 | 8 | – | – | 12 |
| calc_fail_to_pass | – | 16 | – | 30 | – | 46 |
| cit_validity | – | – | – | – | 21 | 21 |
| contract_risk | – | – | – | – | 17 | 17 |
| dms_side_effect_intake | 1 | 5 | – | 7 | 3 | 16 |
| gaia_fee_deadline | – | – | – | – | 17 | 17 |
| long_horizon_case | – | – | – | – | 9 | 9 |
| s_charge_subsume | – | – | – | – | 20 | 20 |
| tau_jud_intake | – | – | – | – | 12 | 12 |
| tool_fault_recovery | – | 8 | – | – | 4 | 12 |
| tool_search_statute | 1 | – | – | – | 25 | 26 |
| u_element_extract | – | 5 | – | 23 | 15 | 43 |
| **合计** | **2** | **38** | **8** | **60** | **143** | **251** |

被砍 20 题在审计时点的证据：GLM 三样本全满分（见 §四 T4a 名单），
对头部模型零区分度；archive 保留可追溯，validate 不扫 archive。
