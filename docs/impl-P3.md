# P3 实施文档 — τ-Jud / 合同轨 / IRAC / Long-Horizon

> 对齐 `FRAMEWORK.md` §2、§5、§5.1、§5.2、§11 **P3**、§12.3。  
> 前置：P0a/P0b 机检 + P1（含收尾）Judge/红线 + P2 工具沙箱/GAIA 可用。  
> **目标**：带状态对话（τ-Jud）、合同风险、IRAC 说理、长程任务可判分；律师基线可选、不阻塞。  
> **不做**：真实外网用户、第三方工具扩容、把 L1 分冒充可部署。

---

## 0. 一句话

让模型在「会改状态的执业对话」里守住协议、把案卡改对，并在合同/说理/长程三类任务上沿用同一套百分制机检 + Judge 分列。

## 1. 范围

| 做 | 不做 |
|---|---|
| τ-Jud（L3b）：`user_script` + 终态 F1 + pass^k + Proto | 真实用户接入 |
| 模拟用户方差分解（`user_seed` 进 manifest） | 把用户噪声记在模型头上 |
| 合同轨 `contract_risk`（L1，composite） | 全量 CUAD 中文搬运 |
| IRAC 轨（L1，`gen` + 抽取后 cite） | 自由文本 PTP 主分 |
| Long-Horizon（L4）score–time | 律师实测基线（可选附录） |
| 案卡状态机 + 轨迹 hash 续写 | 真实办案系统对接 |

## 2. τ-Jud（L3b · 带状态对话）

### 2.1 任务形态

```text
tasks/tau_jud_intake/
  task.yaml            # interaction: L3b, output_type: structured（终案卡）
  user_scripts/*.yaml  # personas[] + turns 策略 + 采样
  predicates.yaml      # 终态 FTP + Proto gate + risk_disclosure/refuse
  rubric.yaml          # 过程说理可选 Judge
data/public/tau_*/items.jsonl   # 含 state_goal
```

**题面增量字段**（附录 C 已预留）：

- `state_goal: {dict}` — 案卡目标终态（字段子集匹配，与 PTP `state` 同构）  
- `interaction: L3b`；主 `output_type` 建议 `structured`（终案卡）或 `composite(["structured","gen"])`。

### 2.2 `user_script` 协议（新建 `schemas/user_script.py`）

```yaml
script_id: us-intake-01
personas:
  - id: p-anxious
    tone: 焦虑反复
    leak_policy: minimal   # 不主动倒出 gold
  - id: p-vague
    tone: 含糊补充
turn_budget: 12
sampling: fixed_order | persona_cycle | seeded_sample
seed_key: user_seed        # run 时写入 manifest，与 model seed 分列
```

**规则**：

1. 必须声明 `personas[]` 与 `sampling`；缺一 validate 报错。  
2. run 固定 `user_seed`（默认 42），写入 manifest：`user_seed` / `model_seed` 分列。  
3. 模拟用户 **禁止** 直接复述 gold 终态字段；违者脚本单测失败。  
4. 方差分解（报告层，非单题）：  
   `total_var ≈ model_var + user_script_var + judge_var`  
   pass^k 两列：固定 `user_seed`（模型稳定度）vs 换 persona 种子（交互稳定度）。

### 2.3 终态与协议分

```text
终态 F1  = |pred ∩ gold_state| 精度/召回调和（字段级，fmt2）
Proto    = 6 项检查单（§5.1）机检 gate：
           规则遵循 / 风险披露 / 非授权不代理 / 应拒转介 / 保密最小必要 / 情绪升级人工
           任一红线 on_fail:zero → 题分 0.00（沿用 gates）
对话税   = 轮次、工具步数进 cost；pass^k（k 默认 3）进 summary
```

**taxonomy 增量**：已有 `state_drift` / `over_promise` / `over_refuse`；τ-Jud 必须落这些标签，不得只写总分。

### 2.4 目录

```text
src/cnjudbench/dialog/
  user_sim.py      # 人设回合、seeded 采样、禁泄 gold
  session.py       # 多轮循环、截断、轨迹
  state_score.py   # state_goal F1
  proto.py         # Proto 检查单
tasks/tau_jud_intake/
data/public/tau_*/
```

## 3. 合同轨 · `contract_risk`（L1）

- `capability: C` 或 `G`；`output_type: composite(["extract","gen"])`；`interaction: L1`。  
- **机检**：风险点列表 FTP `element`/`field`（命中条款风险标签）；`must_not_statute` 禁引失效规则；**无自由文本 PTP**。  
- **Judge**（可选 rubric）：风险说理完整性 → 单独 `judge_mean`，不混机检。  
- 题量：**8–12** 题精品（借款/买卖/劳动/保密），双 `as_of` 至少 2 题。  
- 许可：自撰改写合同节录；CUAD 仅方法参考，不直接当中文数据（§10）。

## 4. IRAC 轨（维度 A）

- 任务：`a_irac_reason`，`capability: A`，`output_type: gen` 或 `composite(["extract","gen"])`，`interaction: L1`。  
- **IRAC-Recall（机检）**：抽取 Issue / Rule / Application / Conclusion 锚点后 FTP `element` + `statute`（cite 合法）+ PTP `must_not_statute`；**禁止**对自由文本直接 PTP。  
- **Judge**：论证连贯、反方回应（rubric 分项，百分制映射写死）。  
- 红线：`fabricated_case` / `wrong_article` / `over_promise` 照旧。  
- 题量：**8–10** 题；含 1 题应拒/应升人工（并 `abst`）。

## 5. Long-Horizon（L4 · score–time）

- 任务形态：多日/多轮卷宗推进（可复用 τ-Jud 会话 + 工具）；`interaction: L4`。  
- **主指标**：score–time 曲线上报 **AUC 归一分** + 终态分；步数/时延进 `cost`（p95、$/solve）。  
- **律师基线（可选、不阻塞，§12.3）**：若无实测律师数据 → 报告写「律师基线：未测」，**禁止**编造对照。  
- 题量：**4–6** 个长程案卡即可（少而全，不注水）。

## 6. 评分（接 P0–P2，不改 compose 红线）

```text
τ-Jud 题分 = 终态 F1 × Proto gate − 红线 zero
            pass^k 单独成列（固定 user_seed / 换 persona 两列）
合同/IRAC  = 既有 FTP/PTP partial 乘法链 + Judge 并列
Long-Horizon = 终态分为主，score–time AUC 为稳健列
一律 scale.fmt2（ROUND_HALF_EVEN）；机检与 Judge 分列；缺 rubric → judge n/a
```

**适用面矩阵**：若新增谓词（如 `proto_item`），必须同步 FRAMEWORK §4.2.1；优先复用 `state` / `risk_disclosure` / `refuse` / `element`。

## 7. CLI

```bash
python -m cnjudbench run --task contract_risk --model mock:gold --out reports/runs/c1
python -m cnjudbench run --task a_irac_reason --model mock:gold --out reports/runs/a1
python -m cnjudbench run-dialog --task tau_jud_intake --model mock:gold \
  --user-seed 42 --k-pass 3 --out reports/runs/tau1
python -m cnjudbench run --task long_horizon_case --model mock:gold --out reports/runs/l4
python -m cnjudbench validate --items data/public --tasks tasks
```

**新增**：`run-dialog`（τ-Jud）；`run` 已可跑 L1/L4 机检。manifest 继续写 trajectory hash + `user_seed` + `model_seed`。

## 8. 测试与 DoD

| 测试 | 断言 |
|---|---|
| `test_user_script_schema` | 缺 personas/sampling → validate 失败 |
| `test_user_sim_no_gold_leak` | 模拟用户回复不含 gold 终态字面 |
| `test_state_f1` | 终态字段 F1 金样；漂移扣 `state_drift` |
| `test_proto_gates` | 6 项检查单：应拒未拒 → over_promise zero |
| `test_variance_split` | summary 有 model/user/judge 方差列；pass^k 两列 |
| `test_contract_irac` | 风险 FTP / IRAC-Recall 抽取后机检；无自由文本 PTP |
| `test_score_time` | Long-Horizon AUC 与终态分 fmt2；律师基线可为 null |
| `test_e2e_mock_p3` | Mock 全流程 exit 0；limits.md 含 user_seed |

**P3 DoD**：

1. 全量 pytest 绿（含 P0–P2 回归）。  
2. τ-Jud + 合同 + IRAC + Long-Horizon 任务包过 validate + 适用面。  
3. `user_seed` 进 manifest；pass^k 双列可出。  
4. Proto 红线一票否决可测（0.00）。  
5. 律师基线缺失时报告如实写「未测」。  
6. 真模型/真律师可选冒烟，不阻塞。

## 9. 顺序

| 步 | 内容 | 验证 |
|---|---|---|
| 1 | `user_script` schema + validate | 单测 |
| 2 | `user_sim` + `session` 多轮 | 单测 |
| 3 | `state_score` + `proto` | 单测 |
| 4 | `run-dialog` + 方差/pass^k | 单测 |
| 5 | `contract_risk` 题包 | validate |
| 6 | `a_irac_reason` 题包 | validate |
| 7 | Long-Horizon 4–6 题 + score–time | 单测 |
| 8 | e2e mock + README | DoD |

## 10. 风险与边界

- **禁止** 把模拟用户方差全部记在模型账上（审查 #5）。  
- **禁止** 无律师实测却写律师对比分。  
- 合同/IRAC 仍走「抽取后机检」；自由文本只进 Judge 列。  
- τ-Jud 案卡状态以题面 `state_goal` 为唯一金样，与 lawkb `as_of` 一致。  
- 题量精品导向；Long-Horizon 少题可以，**不**为凑数放水。  
- 免责声明与许可段（FRAMEWORK §10/§12）每份对外报告必须保留。
