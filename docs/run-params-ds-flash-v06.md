# DeepSeek V4.1 Flash · v0.6 判分全量 12 包跑 · 参数记录

> run 目录：`reports/runs/ds-flash-v06-full`（capability 8 包）+ `reports/runs/ds-flash-v06-tools`（工具沙箱 4 包）+ `reports/runs/ds-flash-v06-smoke`（cit 冒烟，前缀缓存命中）
> harness：`611f18d` · full run_id：`9cb2a3acb6ca` / tools run_id：`673a81043d87`
> **非法律意见**：本评测不构成法律意见，不得用于司法裁判、合规放行或当事人决策。

## 1. 复现命令（密钥仅经环境变量，不进库/不进日志）

```bash
# 注意：宿主进程环境残留旧键（尾号 aafe92）会遮蔽 .env.local 新键（进程环境优先
# 是设计行为）——必须在命令前缀显式覆盖
DEEPSEEK_API_KEY="<REDACTED>" .venv/Scripts/python -m cnjudbench run-all \
  --tasks cit_validity,u_element_extract,s_charge_subsume,contract_risk,a_irac_reason,long_horizon_case,gaia_fee_deadline,calc_fail_to_pass \
  --model deepseek:deepseek-flash --concurrency 100 \
  --out reports/runs/ds-flash-v06-full

DEEPSEEK_API_KEY="<REDACTED>" .venv/Scripts/python -m cnjudbench run-all \
  --tasks tau_jud_intake,tool_search_statute,tool_fault_recovery,dms_side_effect_intake \
  --model deepseek:deepseek-flash --concurrency 50 \
  --out reports/runs/ds-flash-v06-tools

# 翻转率复跑（正式表门禁 <5%）
DEEPSEEK_API_KEY="<REDACTED>" .venv/Scripts/python scripts/flip_rate_check.py \
  --tasks cit_validity,s_charge_subsume,a_irac_reason \
  --model deepseek:deepseek-flash --max-flip 0.05
```

## 2. 模型与采样参数

| 项 | 值 |
|---|---|
| 产品名 | DeepSeek V4.1 Flash |
| API model | `deepseek-flash` |
| model_ref | `deepseek:deepseek-flash`（configs/providers.yaml profile；v0.4 期为裸 `openai:` 接线） |
| base_url | `https://api.deepseek.com/v1`（profile 内置） |
| temperature | 0.0（profile 默认） |
| timeout | 60s（profile 默认）；重试 max_retries=2 |
| 并发 | 100（capability 批）/ 50（工具沙箱批）——用户授权 100 并发 |
| Judge | 未启用（机检分；judge_mean 列 n/a） |
| 密钥 | 进程级覆盖 `DEEPSEEK_API_KEY`（新键；.env.local 同步登记；configs 取键顺序 DEEPSEEK_API_KEY 置首位） |

## 3. 结果（v0.6 判分，323 题全 12 包，0 拒判）

| 包 | n | 均分 |
|---|---|---|
| cit_validity | 27 | 71.85 |
| u_element_extract | 49 | 95.92 |
| s_charge_subsume | 20 | 29.08 |
| contract_risk | 23 | 31.04 |
| a_irac_reason | 34 | 75.22 |
| long_horizon_case | 15 | 44.05 |
| gaia_fee_deadline | 23 | 86.96 |
| calc_fail_to_pass | 54 | 100.00 |
| **capability grand** | **238** | **68.72**（hard 76.31；scored_rate 100%） |
| tau_jud_intake | 16 | 51.17 |
| tool_search_statute | 26 | 56.41 |
| tool_fault_recovery | 16 | 37.50 |
| dms_side_effect_intake | 20 | 96.23 |

- **稳定性**：flip 0/81 = 0.00%（三冒烟包两次独立跑逐题指纹一致；temp=0）→ 过 5% 门禁，本 run 具备进正式表资格（还差 Judge 列与 deps 断言按需补）。
- **分层**：random 7.96 / rules 27.03 / DS-flash 68.72——与基线清晰分层。
- **费用**：两批实价合计 **$0.56**（deepseek-flash 价目；cache 重放 27 题为冒烟前缀合法命中）。
- **跨模型分化（首个双模型 v0.6 证据）**：dms DS-flash 96.23 vs GLM-5.3-Flash 64.36（v0.4 实测）；fault DS 37.50 vs GLM 58.33——工具轨两模型互有胜负，「工具轨分化」论断有了第二个模型的数据支撑（口径注意：GLM 为 v0.4 判分时代数字）。

## 4. 与 v0.4.1 期 DS-flash 跑的口径差异

- 判分：v0.6（set_f1 1-1、极性对冲、as_of 强制题面、tau partial 化等）——**与 v0.4.1 期 run 不可直接比分**；
- 接线：本次走 `deepseek:` profile（providers.yaml），v0.4 期为 `openai:` + 环境变量 base_url；
- 题集：323 题 v0.6 全集（含 batch4 cit stale 族 6 题）vs v0.4 期六包子集。
