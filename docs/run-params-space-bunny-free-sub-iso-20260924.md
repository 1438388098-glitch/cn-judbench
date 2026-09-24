# Space Bunny Free 隔离 subagent 考生跑（8 包 245 题）· 参数与结果

> 非法律意见：不得用于司法裁判、合规放行或当事人决策。

## 1. 产物与口径

- 原始作答目录：`reports/runs/space-bunny-free-sub-iso-20260924/`
- 官方判分目录：`reports/runs/space-bunny-free-sub-iso-20260924-scored/`
- 题集：8 包公开集，`cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass`
- 题数：245；harness：`8d89995`；scored manifest run_id：`e9a910e0ac02`
- 判分：官方 `file:reports/runs/space-bunny-free-sub-iso-20260924/answers` 回灌；schema v0.6；Judge 未启用
- `grand_eq` 为 8 包等权主指标；`grand_w` 仅作参考

## 2. 模型与思考强度

- subagent 不指定模型，继承当前会话默认模型：`opencode/space-bunny-free`
- 思考强度：`think-default-inherited`；即继承当前会话默认，未显式指定 `low/medium/high/max`
- manifest revision：`subagent:opencode/space-bunny-free:think-default-inherited`
- `file:` 回灌不产生真实 API 调用、token、延迟或费用；`est_cost_usd=null`

## 3. 隔离与切片

- 10 片：`assign-1..assign-10.json`
- 分包题数：`25,25,25,25,25,24,24,24,24,24`，合计 245；每片 ≤25
- 齐套：`answers/*.txt` 245/245，文件名集合与 `index.json` 完全一致，全部 UTF-8 JSON 可解析
- 隔离成色（按落盘轨迹/协议判定）：纯隔离考生 subagent 245/245；本会话接管时已有部分答案，后续由隔离考生进程补齐；主会话代笔 0；外部 API 0
- 限制：隔离依赖 Read/Write 提示词约束，目录权限没有技术沙箱，不能证明考生从未越界；重派/补漏调度日志未单独持久化
- 对齐 guard：原始 52 条 `SUSPECT`（19 条结构化、33 条计算）；逐条以本题题面关键字段复核，均与本题对齐，未发现换答

## 4. 结果

### 总表

| 指标 | 值 |
|---|---:|
| capability grand_eq | **62.99** |
| capability grand_w | 72.22 |
| hard 均分 | 71.56 |
| hard 95% CI | [66.52, 76.82] |
| capability n | 238 |
| hard n | 180 |
| safety n | 7 |
| safety score | **0.00** |
| scored rate | 100.00%（n/a=0） |
| flip rate | n/a |
| provisional | **true** |

### 分包表

| 包 | capability n | 机检均分 | hard 均分 | safety | safety n | scored% |
|---|---:|---:|---:|---:|---:|---:|
| cit_validity | 27 | 60.00 | 48.33 | n/a | 0 | 100.00 |
| s_charge_subsume | 13 | 45.22 | 45.65 | 0.00 | 7 | 100.00 |
| contract_risk | 23 | 36.69 | 36.76 | n/a | 0 | 100.00 |
| long_horizon_case | 15 | 34.17 | 34.17 | n/a | 0 | 100.00 |
| a_irac_reason | 34 | 65.44 | 64.84 | n/a | 0 | 100.00 |
| u_element_extract | 49 | 95.92 | 94.12 | n/a | 0 | 100.00 |
| gaia_fee_deadline | 23 | 73.91 | 80.00 | n/a | 0 | 100.00 |
| calc_fail_to_pass | 54 | 92.59 | 93.90 | n/a | 0 | 100.00 |

- random/rules grand_eq：7.96 / 27.03
- 同口径 DS-flash 8 包历史基线 grand_eq 68.72、hard 76.31、flip 0%；此处只作数字对照，不作强弱排名主张

## 5. provisional 与局限

- `provisional=true`：单次 subagent 跑没有 flip 复跑，manifest `stats.flip_rate=null`；不得进入正式 T-main 表
- 未启用 Judge：`judge_mean=n/a`
- `file:` 回灌没有真实费用、延迟、API 稳定性数据；这些字段不补造
- 8 包只覆盖 capability 集；工具沙箱 4 包未纳入本 run
- 对齐 guard 原始退出码为 1，但 52 条均完成人工关键字段复核后才回灌

## 6. 复现命令

```powershell
.venv\Scripts\python.exe scripts\export_prompts.py `
  --tasks cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass `
  --run-dir reports/runs/space-bunny-free-sub-iso-20260924

.venv\Scripts\python.exe scripts\check_answer_alignment.py `
  --run-dir reports/runs/space-bunny-free-sub-iso-20260924 `
  --json reports/runs/space-bunny-free-sub-iso-20260924/alignment.json

.venv\Scripts\python.exe -m cnjudbench run-all `
  --tasks cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass `
  --model file:reports/runs/space-bunny-free-sub-iso-20260924/answers `
  --revision "subagent:opencode/space-bunny-free:think-default-inherited" `
  --out reports/runs/space-bunny-free-sub-iso-20260924-scored
```

## 7. 验证

- `scripts/assert_run_gate.py reports/runs/space-bunny-free-sub-iso-20260924-scored`：通过
- 全量 pytest（`PYTHONIOENCODING=utf-8`）：585 passed、15 warnings；不把默认 Windows GBK 输出误报当作评测失败
