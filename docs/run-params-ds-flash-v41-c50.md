# DeepSeek V4.1 Flash · 50 并发对比（c50）

> 追加记录：在串行 run `ds-flash-v41-rerun` 之后，用 `--concurrency 50` 冷启动重跑同六包。  
> run_id：`dab24ad06d29` · 目录：`reports/runs/ds-flash-v41-c50` · harness：`ec1ee9c`  
> **非法律意见**。

## 1. 与串行对照（同六包 105 题，temperature=0，冷启动）

| 指标 | 串行 c1（rerun） | **50 并发 c50** | 变化 |
|---|---:|---:|---|
| **总耗时 wall** | 1,661,211 ms（27.69 min） | **69,442 ms（1.16 min）** | **约 24×** |
| 进程外墙钟 | 1,662,099 ms | 70,098 ms | — |
| mean latency/题 | 16,014 ms | 15,836 ms | ≈持平（单题生成未变快） |
| p95 latency | 40,100 ms | 37,480 ms | ≈持平 |
| model_calls | 105 | 105 | 同 |
| prompt_tokens | 15,552 | 15,552 | 同 |
| completion_tokens | 365,751 | 361,175 | 输出略短 |
| **$total** | **0.221783** | **0.219038** | ≈持平 |
| $/solve | 0.0036 | 0.0037 | ≈持平 |
| **等权总分** | 63.91 | **64.00** | +0.09 |
| **加权总分** | 65.68 | **66.25** | +0.57 |

**结论**：耗时瓶颈在**串行 API 生成**，不在机检/磁盘；50 并发后 wall ≈ 最慢一截请求 + 少量调度，单题 latency 与费用几乎不变。

## 2. 分包得分（c50）

| 任务包 | n | c1 串行 | **c50** | Δ |
|---|---:|---:|---:|---:|
| cit_validity | 21 | 76.19 | **76.19** | 0 |
| u_element_extract | 19 | 100.00 | **100.00** | 0 |
| s_charge_subsume | 20 | 47.64 | **46.85** | −0.79 |
| contract_risk | 17 | 60.50 | **63.16** | +2.66 |
| a_irac_reason | 19 | 52.22 | **56.57** | +4.35 |
| long_horizon_case | 9 | 46.94 | **41.20** | −5.74 |

维分（K/U/S/A/O/C）：**76.19 / 100.00 / 46.85 / 56.57 / 41.20 / 63.16**。

> **注意**：temperature=0 仍有题级翻转（DeepSeek 非严格确定性 / 服务端非完全稳定）。正式榜分需按 FRAMEWORK 做 flip-rate（建议 API &lt; 5%）或固定 seed + 多次采样。并发**不改变**判分逻辑，只改变完成顺序；题序仍按 jsonl 原序写入 summary。

## 3. c50 经济与时间明细

| 项 | 值 |
|---|---|
| concurrency | **50**（`--concurrency 50`，ThreadPoolExecutor 跨包共享） |
| cache | 跑前轮换，全 miss（hit=0 / miss=15,552） |
| $model / $judge / $total | 0.219038 / 0.00 / **0.219038** |
| 计费时段 | off-peak（UTC 11:54–11:55） |
| over_refuse / over_promise | 0.00 / 1.90 |
| 开始 / 结束（UTC） | 2026-09-22T11:54:43Z / 11:55:53Z |

### 价目（同前，USD/1M，off-peak）

input miss 0.15 · output 0.60 ·（peak 两倍）。校验：`15552×0.15 + 361175×0.60`（/1M）= **0.219038**。

## 4. 工程改动（支撑并发）

- `Accountant` / `FileCache`：进程内锁（并发记账与缓存写）
- `run_tasks()`：跨任务包共享线程池，题序稳定
- CLI：`--concurrency N`（默认 1 = 旧行为）
- OpenAI 适配器：429/408 与 5xx 一样有限重试（高并发限流保护）
- 测试：201 passed

## 5. 复现命令

```powershell
python -m cnjudbench run-all `
  --tasks cit_validity,u_element_extract,s_charge_subsume,contract_risk,a_irac_reason,long_horizon_case `
  --model openai:deepseek-flash --base-url https://api.deepseek.com/v1 `
  --temperature 0.0 --concurrency 50 --out reports/runs/ds-flash-v41-c50
```

## 6. 产物

- `reports/runs/ds-flash-v41-c50/{manifest,summary,limits}.*`
- 串行对照：`docs/run-params-ds-flash-v41.md` + `reports/runs/ds-flash-v41-rerun/`
- 面板：`sync_dashboard.py --run reports/runs/ds-flash-v41-c50`
