# 真考生轮执行包（草稿 ct-201..211 + ah-201..210）

> 目的：把 `data/drafts/` 现存 9 题草稿推进 examinee_round 状态。
> 本包让发起人（用户或白天 agent）按步骤执行即可，无需再准备材料。
> 纪律依据：`data/drafts/README.md` 状态机、`docs/gold-adjudication-policy.md` §2。

## 0. 范围与前置

| 系 | 题 | 任务包 | 考点 |
|---|---|---|---|
| ct-201/202/203/210/211 | 5 | cit_validity | 时间效力判定（wrong_vintage/not_yet/ok 三态，ct-210/211 成对） |
| ah-201/202/203/210 | 4 | a_irac_reason | 时间效力的 IRAC 叙事（预期错误模式见各 draft_notes） |

判分面预检已通过：漂洗后 mock:gold 9 题全部可判分（cit 系 100 自证，
tests/test_draft_isolation_v06.py c362；基线预演 rules 20.00 泄题门禁
tests/test_draft_baseline_v06.py c364）。

## 1. 导出（每考生一份，漂洗不触碰 data/drafts 与 data/public）

```bash
.venv/Scripts/python scripts/export_draft_prompts.py \
  --drafts data/drafts/cit_validity,data/drafts/a_irac_reason \
  --run-dir reports/runs/draft-examinee-<考生号>
```

产物：`prompts/`（9 题）、`answers/`（空）、`index.json`、`EXAMINEE.md`、
`items.jsonl`（漂洗临时集，仅 run-dir 内）。

## 2. 双考生作答（隔离 subagent）

1. 每名考生一个独立 subagent 会话，系统提示词只给 `EXAMINEE.md` 落盘协议
   （历次轮教训：考生**不得**看到 gold/draft_notes/预期错误模式——
   export 产物不含这些字段，勿在会话中补料）；
2. 考生读 prompts/ 写 answers/<item_id>.txt，最终消息仅回 `done: <ids>`；
3. 两名考生不得共享答案或讨论。

## 3. 换答 guard 与回灌判分

1. guard：核对 answers/*.txt 数量==9、文件名==index.json 清单、JSON 可解析
   （历次轮教训：错位/缺答先拦截，见 README 回灌段换答 guard）；
2. 回灌：`python -m cnjudbench run-all --tasks cit_validity,a_irac_reason
   --model file:reports/runs/draft-examinee-1 --out reports/runs/draft-examinee-1-scored`
   （file: 模式按 answer_file 回灌，考生答案不调 API）；
3. 两名考生分别产出 -1-scored / -2-scored。

## 4. 裁定与入库（五条件）

1. 逐题读判分产物 + 两考生答案，对照 `docs/gold-adjudication-policy.md` §2
   五条件；ct 系另核对 `resolve_article` 判定窗（11 窗探针已预验证，
   tests/test_temporal_drafts_v06.py c356）；
2. 双考生独立答对且 gold 判分无误 → 进 public（补入 data/public/<task>.jsonl、
   MANIFEST 对账、canary 改正式 hex）；预期错误模式 ≥1 人触发 → 留档入
   `docs/gold-item-review-log.md`；五条件不过 → archive；
3. **入库即改版本语义**：323→332 题等数字须同步（对账表
   `docs/paper-numbers.md`、MANIFEST、dataset-card、index.html——c360 机检
   会强制公开面板对齐）；基线重导 + 判分零漂移验证
   （FRAMEWORK §8.4 纪律）。

## 5. 已知预期（来自基线预演，供裁定参考）

- rules 基线 ct-201/202/203/210 全 0、ct-211 满分：考生若在陷阱窗
  （wrong_vintage/not_yet）失手即与基线同型错误，属实质错因非评分噪声；
- random 撞对 ct-201（wrong_vintage）概率存在：单题满分不构成区分度证据，
  须结合双考生一致性判读。
