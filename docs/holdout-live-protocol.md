# holdout 冻结与 live 滚动协议（DESIGN v0.4 §7 L3 / FRAMEWORK 附录 C）

状态：**v1（流程文 + 工具已备，冻结未执行）**。执行冻结是**发布动作**：
一旦 `data/holdout/` 建立，公开包从此不可再回补对应题，须团队双人复核后执行。

## 1. 为什么必须冻结

- 论文对比表的可信度来自「模型没在测试集上被调过参」。公开包（split=public）会被
  爬取、会被训练；90 天后其上的分数就是训练集分数。
- L0 canary / L2 n-gram 只能**检测**泄漏；冻结 holdout 才能保证「永远干净的题目池」。

## 2. 冻结规则（scripts/freeze_holdout.py）

1. **抽样比例**：每任务包按 30% 抽取（向上取整，最少 3 题），hard 题
   （difficulty≥3）按其包内占比**分层保比例**——holdout 不能只有简单题。
2. **确定性**：种子 = `sha256("cnjb-holdout-v1:" + task_id)` 的前 8 hex，
   任何人可复算同一份名单（预注册，防止挑题）。
3. **物理隔离**：选中题写入 `data/holdout/<task>.jsonl`（带 `split: holdout`），
   并从 `data/public/<task>.jsonl` 移除；`data/holdout/` 整目录进 `.gitignore`
   + 发布打包排除项（**本地保留、仓库不含**，密级同 .env.local）。
4. **守卫链**：既有 `assert_no_holdout`（路径层）与 `assert_items_not_holdout`
   （题面 split 层）自动覆盖新目录；canary 逐题唯一性在冻结后复验。
5. **回补禁令**：公开包被移除的题位**不得**用新题回补凑数——公开包规模就此定格，
   新题只能进 `data/live` 或下一版数据集。

## 3. live 滚动池（季度）

- `data/live/`：每季度新增一批题（≥每包 5 题），发布后 **90 天**转入
  `data/holdout/` 候选，90 天内公开可测（供社区热身）但**不计正式分**。
- 正式榜声明必须写明每题的 `in_live_since` / `in_holdout_since` 日期。
- 榜单刷新节奏：季度；两次刷新之间公开包分数只降不升（回归性 bug 除外，须公告）。

## 4. 执行清单（冻结日）

- [ ] 双人复核 `freeze_holdout.py --dry-run` 输出的题号名单并签字；
- [ ] `--apply` 执行后跑 `python -m cnjudbench validate --items data/public --tasks tasks`
      与全量 pytest（数量断言需同步改：冻结后公开包题数 = 冻结前 × 0.7 向下取整）；
- [ ] 在 `reports/holdout-manifest.json` 记录：日期、名单、种子、复核人（匿名代号）；
- [ ] 论文 T 表脚注加「holdout 冻结于 <日期>，n=<题数>」。

## 5. 与污染四层的关系

L0 canary（每题唯一金丝雀）→ L1 holdout 路径/题面守卫 → **L2 n-gram 双检**
（`--ngram-corpus`）→ L3 本协议 → L4 logit 审计（接口保留，闭源 n/a）。
冻结完成后，正式分声明模板的 `holdout_guard: pass` 才从「守卫通过」升级为
「冻结池存在」。
