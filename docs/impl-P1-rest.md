# P1 收尾实施文档 — Judge 进 runner / 真 Judge / CI 门禁

> 前置：`docs/impl-P1.md` 核心库已落地（Judge/Abst/红线/诊断/bootstrap/成本/canary，114 测）。  
> 本文只覆盖 **P1 未完成项**，不重复已交付模块。

---

## 0. 一句话

把 P1 库真正接进 `run`/`run-all` 产出链路，补真 Judge 与 CI 门禁，使「机检分 + Judge 分 + limits」一次跑齐。

## 1. 范围

| 做 | 不做 |
|---|---|
| CLI `--with-judge` / `--judge mock\|openai` | 多 Judge 辩论 |
| summary 分列 machine / judge | 工具沙箱（P2） |
| `limits.md` 写入 `reports/runs/<id>/` | τ-Jud（P3） |
| OpenAIJudge（复用 adapter，k_pass=2） | Min-K% logit 实装（仅接口） |
| CI 门禁脚本（pytest + validate + smoke） | 对外发布流水线 |
| holdout 路径拒读校验进 runner | |
| 翻转率复跑脚本（Mock=0 / API 阈值写 limits） | |

## 2. 交付物

```text
src/cnjudbench/
  judge/openai_judge.py    # 真 Judge（接 adapters）
  runner/with_judge.py     # 可选后处理：item 级 judge 分
  cli.py                   # --with-judge --judge-id --k-pass
  report/writeup.py        # 已有；接进 run 落盘
scripts/
  ci_gate.sh | ci_gate.ps1 # validate + pytest + mock run-all
  flip_rate_check.py       # 复跑对比谓词翻转
tests/
  test_cli_with_judge.py
  test_limits_written.py
  test_holdout_guard.py
.github/workflows/ci.yml   # 可选：跑 ci_gate
```

## 3. CLI 与产物

```bash
python -m cnjudbench run-all \
  --tasks cit_validity,u_element_extract,s_charge_subsume \
  --model mock:gold --out reports/runs/r1 \
  --with-judge --judge mock

# summary.json 增加：
#   per_task: { machine_mean_str, judge_mean_str, n_machine, n_judge }
#   diagnostics: { diag_drop, reward_hacking_alert? }
#   abst: { over_refuse_rate, over_promise_rate }
#   cost: { pass_k, dollar_per_solve, p95_latency_ms }
#   contamination: { hits: [...] }
# 同目录：limits.md
```

**规则**：

1. **机检分与 Judge 分分列**，禁止默认加权成一个未标注数（`combine` 仅显式 `--blend weighted`）。  
2. `judge_calls` 进 manifest；Mock 也计次。  
3. 缺 rubric 的任务：judge 列为 `n/a`，**禁止填 0.00**。  
4. holdout 目录若出现在参数/引用 → 校验失败退出码 ≠ 0。

## 4. OpenAIJudge

- 构造：`OpenAIJudge(adapter, k_pass=2)`；prompt_hash = hash(judge_id + rubric JSON)。  
- 输出要求模型给 rubric 各项原始分 JSON；解析失败 → 该项 0 并记 `format_fail`，不重试刷分。  
- 成本：prompt/completion tokens 累加进 `accounting`。

## 5. CI 门禁（scripts/ci_gate）

```text
1) validate --items data/public --tasks tasks
2) pytest -q
3) run-all --model mock:gold --with-judge --judge mock --out reports/runs/ci
4) 断言 summary 含 machine/judge 分列 + limits.md + DISCLAIMER
5) flip_rate_check：Mock 两跑谓词翻转率必须 = 0
任一失败 → exit 1
```

## 6. 测试与 DoD

| 测试 | 断言 |
|---|---|
| `test_cli_with_judge` | summary 有 judge_mean_str；无 rubric → n/a |
| `test_limits_written` | limits.md 含 DISCLAIMER、翻转率、unknown 分列 |
| `test_holdout_guard` | 引用 data/holdout → 非 0 退出 |
| `test_openai_judge_mock_adapter` | k_pass=2 计 2 次调用；分可 fmt2 |

**DoD**：`ci_gate` 本地全绿；`run-all --with-judge` 产物齐全；Mock 翻转率 0；README「如何跑」补 judge 示例。

## 7. 顺序

1. `with_judge` 后处理 + summary 字段  
2. limits.md 落盘  
3. OpenAIJudge  
4. CLI 参数  
5. holdout guard + flip_rate_check  
6. ci_gate 脚本  
7. 文档与 README

## 8. 风险

- Judge 空解析不得静默满分。  
- `--blend` 默认 `parallel`，避免混分。  
- CI 只跑 Mock，不烧真 API。
