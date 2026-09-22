# DeepSeek V4.1 Flash 重跑 · 多维参数记录

> run 目录：`reports/runs/ds-flash-v41-rerun`  
> run_id：`cbcf7998d59b` · harness：`f5be984`  
> **非法律意见**：本评测不构成法律意见，不得用于司法裁判、合规放行或当事人决策。

## 1. 复现命令（密钥仅经环境变量，不进库/不进日志）

```powershell
$env:OPENAI_API_KEY = "<REDACTED>"   # 不落盘
$env:CNJUD_API_KEY  = "<REDACTED>"
$env:OPENAI_BASE_URL = "https://api.deepseek.com/v1"
python -m cnjudbench run-all `
  --tasks cit_validity,u_element_extract,s_charge_subsume,contract_risk,a_irac_reason,long_horizon_case `
  --model openai:deepseek-flash `
  --base-url https://api.deepseek.com/v1 `
  --temperature 0.0 `
  --out reports/runs/ds-flash-v41-rerun
# 未启用 --with-judge（机检分；Judge 列 n/a）
# 跑前已轮换 .cache/adapter，保证 token/费用/延迟为冷启动实测
```

## 2. 模型与采样参数

| 项 | 值 |
|---|---|
| 产品名 | DeepSeek V4.1 Flash |
| API model | `deepseek-flash`（legacy `deepseek-v4-flash` 亦可，账单按 Flash） |
| model_id | `openai:deepseek-flash` |
| base_url | `https://api.deepseek.com/v1`（OpenAI 兼容） |
| revision | null（API 未返回权重版本号） |
| temperature | 0.0 |
| seed | null（DeepSeek 未强制 seed；temperature=0） |
| thinking | 默认（官方文档：同时支持 non-thinking / thinking） |
| user_seed | null（非 τ 多轮） |
| k_pass | 1（单次；无复跑，故 pass^k 留空） |
| Judge | 未启用（`judge_calls=0`，Judge 列 `n/a`，禁止填 0.00） |
| blend | n/a（无 Judge 不混分） |
| 适配器缓存 | 跑前轮换 `.cache/adapter`，本 run 全量 miss（冷启动） |

## 3. 题集参数

| 任务包 | n | capability | 机检分 |
|---|---:|---|---:|
| cit_validity | 21 | K/Cit | 76.19 |
| u_element_extract | 19 | U | 100.00 |
| s_charge_subsume | 20 | S | 47.64 |
| contract_risk | 17 | C | 60.50 |
| a_irac_reason | 19 | A | 52.22 |
| long_horizon_case | 9 | O | 46.94 |
| **合计** | **105** | | |

- split：`data/public`（holdout 守卫通过）  
- 抽样：**全量**（非 `sample_items` 测试抽样；测试仍按 task×domain 分层 k=3）  
- item_content_hash：`sha256:5b52e89aec796e388f2cf394cc88a29d73f2df9595e21bb21435c0950af390db`  
- prompt_hash：`sha256:143795f9f16c71f45918a347bb2cadfbe6fd6c7536ea3dacfce86f9b4875ae81`  
- slice_union_hash：`sha256:fa78746e3f633e56b6fb9a23ca72e3bf84ff0461c9684be1da8a3e92ffb1b385`  
- lawkb：`lawkb-2026.09.1`（as_of 解析）  
- **未含**：`tool_search_statute` / `gaia_fee_deadline` / `tau_jud_intake`（工具轨与多轮轨需另跑）

## 4. 经济与时间（多维）

| 指标 | 值 |
|---|---|
| model_calls | 105 |
| judge_calls | 0 |
| prompt_tokens | 15,552 |
| completion_tokens | 365,751 |
| cache_hit_tokens | 0（冷启动） |
| cache_miss_tokens | 15,552 |
| **$model** | **0.221783** |
| $judge | 0.00 |
| **$total** | **0.221783** |
| $/solve（≥60.00 分，61 题） | **0.0036** |
| mean latency | 16,014 ms |
| p95 latency | 40,100 ms |
| **wall_time（accountant）** | **1,661,211 ms ≈ 27.69 min** |
| wall_time（进程外） | 1,662,099 ms ≈ 27.70 min |
| 开始（UTC） | 2026-09-22T11:16:59Z |
| 结束（UTC） | 2026-09-22T11:44:41Z |
| 计费时段 | **off-peak**（非周一至周五 01:00–04:00 / 06:00–10:00 UTC） |

### 价目（USD / 1M tokens）

来源：DeepSeek Models & Pricing（api-docs.deepseek.com，2026-09）。`deepseek-flash` = **DeepSeek-V4.1-Flash**。

| 项 | peak | off-peak |
|---|---:|---:|
| input cache hit | 0.006 | 0.003 |
| input cache miss | 0.30 | 0.15 |
| output | 1.20 | 0.60 |

- 本 run 按 **off-peak** 估价（见上表时段）。  
- 校验：`15552×0.15/1e6 + 365751×0.60/1e6 = 0.221783`。  
- **未内置中国法定节假日日历**（节假日全天 off-peak，实扣可能更低）。  
- 账本字段写入 `manifest.accounting` 与 `summary.cost`；密钥未进任何产物。

## 5. 得分多维

### 5.1 总览（百分制两位小数）

| 口径 | 分 |
|---|---:|
| 等权（六任务 macro） | **63.91** |
| 加权（按题量） | **65.68** |

### 5.2 维度（TASK_DIM 映射，空维为 null 不编造）

| K | U | R | S | A | G | O | C |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 76.19 | 100.00 | n/a | 47.64 | 52.22 | n/a | 46.94 | 60.50 |

### 5.3 安全与诊断

| 项 | 值 |
|---|---|
| over_refuse_rate | 0.00 |
| over_promise_rate | 2.86 |
| a_irac_reason diag_drop | −27.19（reward_hacking_alert=false） |
| long_horizon_case diag_drop | 7.56（reward_hacking_alert=false） |
| stale / wrong_vintage | 题级红线按 compose_score **写死 0.00** |

### 5.4 题级失败簇（taxonomy，便于回看）

- `cit_*`：6× `wrong_article`（cit-005/007/011/013/016 等）  
- `s_*`：后半段（s-015…s-021）集中 `format_fail` / `state_drift` / `miss_retrieve`  
- `c_*`：普遍 `element_miss` + `wrong_article`  
- `a_*`：`structure_broken` 高发；a-004/008/011 触发 `over_promise` / `format_fail`  
- `lh_*`：多要件题 `element_miss` / `wrong_article` 拖累至 46.94  

## 6. 与历史 run 对照（仅同口径六任务；题量已扩）

| run | 题量 | 等权 | 备注 |
|---|---:|---:|---|
| ds-flash-v4（旧） | 53 | 69.27 | 扩题前；est_cost 未接入价目 |
| **ds-flash-v41-rerun（本次）** | **105** | **63.91** | 扩题后全量；冷启动；$0.22 / 27.7 min |

> 题量与题目分布变化，均分不可直接当「模型退步」解读。

## 7. 产物

- `reports/runs/ds-flash-v41-rerun/manifest.json`（含 per-item hash、accounting）  
- `reports/runs/ds-flash-v41-rerun/summary.json`（per_task / items / cost / abst / diagnostics）  
- `reports/runs/ds-flash-v41-rerun/limits.md`  
- 面板：`dashboard-data.json` / `dashboard-data.js`（`scripts/sync_dashboard.py` 自动同步）
