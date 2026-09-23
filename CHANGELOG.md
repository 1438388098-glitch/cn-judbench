# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 惯例，
版本号遵循语义化版本。数据面（data/public、lawkb）与代码面同版本发布，
每版配套 `data/public/MANIFEST.json` 的 `dataset_content_hash` 供第三方核对。

## [0.6.0] — 2026-09-24

### 新增
- `configs/providers.yaml` 提供商配置面：base_url/密钥环境变量/默认采样与
  思考参数/价目键统一声明；密钥只从进程环境或 `.env.local`（gitignore）读取。
- 判分失败分类学 `cnjudbench/taxonomy.py`：19 个失败标签权威字典，
  测试拦截未登记字面量，报告 taxonomy 口径全仓一致。
- 账本 cache 重放分列（c243）：FileCache 重放调用的 latency 不进 p95 样本，
  `n_cache_replays` 单独计数进 cost_ledger。
- 组合通过率 pass^k（同题 k 次独立采样全过率）与 `aggregate_passk.py`
  报表；E17 金样 pass^2 = 46.77 [33.87, 59.68]。
- E18 预注册比较双口径（全集 62 题 / 预注册 40 题）并行披露，
  口径选择改变结论的警示写入 `docs/paper-outline.md`。
- 发布面机检体系：`baseline_report.py`（rules/random 泄题前兆监控）、
  `headroom_report.py`（扩题余量判定）、`repro_inventory.py`
  （论文引用资产盘点）、泄露面扫描（prompt 不含 gold 与 canary）。
- 数据集卡 BibTeX 引用条目（§7）；`docs/README.md` 文档索引。

### 修正
- 预注册核心六包合计题数勘误：162 → **168**（cit 27 + u 49 + s_charge 20 +
  contract 23 + a_irac 34 + long_horizon 15），FRAMEWORK 与论文提纲同步。
- 判分效度三修复（c322-c324）：时效判定**强制题面 as_of**（考生 citation
  自报 as_of 仅进诊断列，引用废止法条+伪日期无法洗掉 stale_statute）；
  极性对冲 `polarity_opposed`（一侧否定头+核心相等不得分，「未支持」≠「支持」）；
  拒绝判定否定豁免（「本案无需转介」不再误判为拒绝）。修复后按纪律重导
  基线：baseline-v06b 与修复前 **245 题逐题分零漂移**
  （`tests/test_baseline_zero_drift_v06.py`）。
- tau state 谓词部分得分化：自由文本字段（risk_note/next_steps）由逐字
  包含匹配（真考生结构性 0 分）改为标量命中/文本覆盖连续分/列表 set_f1，
  `on_fail` 由 zero 改 partial（c290 收尾，语义锁定于
  `tests/test_state_partial_v06.py`）。
- 解析失败语义收紧：解析失败 = 0 分（format_fail，考生责任）；
  `finish_reason=length` 才记 n/a（截断非考生能力）。
- 密钥取用顺序：进程环境变量优先于 `.env.local`（防旧键遮蔽会话新键）。

### 变更
- 发布一致性机检（c336-c346）：版本四源一致（pyproject/CITATION/__init__/
  CHANGELOG/dataset-card）、占位仓库地址集中清单、CITATION 日期对齐、
  §8.3 两档阈值常量互锁（`RANKABLE_MIN_N`/`CI_DESCRIPTIVE_MIN_N`）、
  `aggregate_passk --threshold` 越界拒绝、flip 门禁工具包适用面声明。
- 全仓 Python 版本下限 3.11（CI matrix 3.11 + 3.13）。
- `.gitattributes` 强制 data/public、lawkb/text、docs/corpus.txt 检出 LF，
  防 autocrlf 机器复现 CRLF 挂测试。
- 仓库状态目录 `.autopilot/`、运行产物 `reports/runs/` 明确不入库。

## [0.5.0] — 2026-09-23

### 新增
- 题库扩充：271 → **323 题**（12 包）。Phase 1 剖减 a_irac 全分饱和题 20 题
  入 archive；Phase 3a/3b/3c 新增难题 36 题；Phase 4 新增实务题 30 题；
  v0.6 batch4 新增 cit stale 族 6 题。
- 双考生（at/lh/c 人设轮换）实证：有效区分 confirmed；考生轮修 4 处
  金样缺陷。
- holdout/live 前瞻集冻结协议（`docs/holdout-live-protocol.md`）与
  gold 裁定政策（`docs/gold-adjudication-policy.md`）。

### 修正
- 实证难度审计：作者标注难度与实证通过率脱钩（一致率 33.9%，
  Spearman ρ=+0.152）——难度分层改为以实证通过率准绳，
  `calibrate_difficulty.py` 常驻化审计。

## [0.4.0] — 2026-09-22

### 新增
- v0.4 计分架构：role 分层（capability 进主分 / safety 夹具单列）、
  hard 分层（difficulty≥3 进 hard_mean）、provisional 产物隔离、
  diagnostic_ftp 单独合成。
- 判分纪律：缺 Judge 记 n/a 禁填 0.00；无价目 `est_cost_usd=null`
  禁编造费用。

[0.6.0]: https://github.com/TODO-assign-repo/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/TODO-assign-repo/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/TODO-assign-repo/releases/tag/v0.4.0
