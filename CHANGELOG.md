# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 惯例，
版本号遵循语义化版本。数据面（data/public、lawkb）与代码面同版本发布，
每版配套 `data/public/MANIFEST.json` 的 `dataset_content_hash` 供第三方核对。

## [未发布]

### 新增
- 判分复核与报告真实性（c398/c416/c430）：面板 MODELS 数据块由 summary.json
  一键再生（字节级对账机检锁定）；思考对照/安全卡数据纳入账面互锁；
  limits 报告的「lawkb 待校对」改为从 store 实时收集（超 8 处截断计数），
  不再硬编码空表谎报「全部已核」。
- compare 统计出口 provisional 门禁（c429）：任一侧 run 缺 manifest 或
  provisional=true（含 baseline-v06c 等全部现行主记分板 run）时，排名资格
  一律降档 descriptive_only 并显式给出原因——落实 DESIGN §8「provisional
  产物不得进对外对比表」，防止未过 flip 门禁的 run 产出「显著」级结论。
- 评测管线信任面（round-1 批次）：ci_gate 两版新增第 7/9 步「导出→占位
  作答→换答对齐 guard→file: 回灌→产物核对」全管线（R14/R20 两次真实
  错位事故的防线入 Gate）；测试侧跨平台解释器 helper
  （`tests/conftest.py::project_python`）与测试卫生元测试。

### 修正
- 判分与数据链（c399/c401/c402/c404/c405）：dialog proto 转介判定同步
  censored 否定豁免口径；lawkb 别名剥尾逐级尝试中间态（合同法解释（二）
  （2009年）类引用不再解析失败）；连字符条号 253-1 映射 253之一；dialog
  taxonomy 通道对齐（删未登记字面量）。
- 确定性与健壮性（c400/c410-c413/c459）：user_sim 随机种子换 crc32
  （`hash()` 进程盐化曾致 run-dialog 同 seed 跨进程话轮漂移）；smoke 目录
  模式过滤非 cit 题；fmt2 超大值精度放宽+负零规范化；常驻工具裸跑缺输入
  友好 SystemExit；export_prompts 重导出清场；baselines 抽取源头过滤非
  有限值（超大标的额 inf 崩溃/非法 Infinity）；aggregate_passk 两份逐字
  复制的 bootstrap 收敛到 `metrics.bootstrap_ci_mean`（同口径金样锁定）。
- 面板与校验（c406-c409）：validate 跨对象交叉一致性三件；面板藏匿规则
  特异性回归修复（`.rank-row` 反超 `.is-in` 致真实浏览器整榜永久隐藏）。
- 基线与账面对账（c417-c419）：判分语义修订后按纪律重导
  baseline-v06c（rules 27.03 → **27.40**，归因 R29/R32 修复晚于 v06b；
  双树逐题对比证当晚零漂移）；存量 12 run 重评（a_irac 应拒族 7 题
  0→100，6 行总分上修/排名 #10/#11 换位），ledger/面板/论文轨全链更新。
- 评测管线信任面（round-1 批次续）：修复 pytest 运行把受跟踪文件
  `docs/holdout-dual-review-pack.md` 生成日期刷成当天（工作区变脏）——
  c226 快照恢复网补齐；修复 10+ 测试硬编码 `.venv/Scripts/python.exe`
  （Linux CI 必 FileNotFoundError）；修复 ci_gate.ps1 在 powershell.exe
  下本就无法解析的三处潜伏断裂（无 BOM 文件按 GBK 误读吃引号致 4 处
  parser error、`python -c` 传参引号剥落改 stdin 管道、步骤编号 /7 与
  实际步数不符），PSParser 0 errors 且新步骤定向执行通过。
- 文档真源对账（round-1/2 批次）：论文轨五处 v0.6 基线 rules 27.03 →
  现行 27.40（baseline-v06c，历史链保留）；FRAMEWORK v0.6 横幅补现行
  规模 12 任务包 323 题（机检对账 MANIFEST）与附录 B/§4.2.1 矩阵补
  status_ladder/unit_tests/env_diff/fault_recovery 四类（与校验器 22 类
  枚举对齐）；README 测试数下限与 lawkb 版本数勘误。

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
- 判分效度扩展修复（c373-c388，2026-09-25 夜）：a-008 引语豁免四类假阴性
  （成对引号区间/转述引导词/紧邻后置否定，反豁免守卫防伪引语开口）；
  远距否定免责声明 20 字框架豁免（c383）；否定豁免同步 answer 分支并收紧为
  紧邻 2 字（c384/c385，「帮不了你，建议咨询律师」不再误罚空拒）；judge 列
  与 machine 列同口径剔除 safety 夹具与机检 n/a（c373/c387）；over_refuse
  实词表补行政·知产 9 词（c376）；truncated 题带 abst 双标签（c375）；
  pass^k「有题但全部试次不足 k」返回 None 禁 0.00 充数（c388）；
  `summary.abst.over_refuse_items` 触发题单列闭环复核承诺（c380）。
- 卫生与机检（c372/c377-c382/c389-c393）：add_items_batch2/3 补 main guard +
  涉 data/public 顶层写盘 guard 机检（R19 教训门禁化）；竹马候选池质量扫描
  （真池只读字节级断言）；污染 run 目录 CONTAMINATED.md 自证标注机检；
  死链检查扩展到 FRAMEWORK/dataset-card/research-notes-round3；引语豁免
  reward_hacking 暴露面审计工具；公开面板无 JS 降级（html.js 门控 + noscript）；
  ledger↔面板主记分板逐行对账机检（c391）；删除 14 个零引用一次性生成器
  （c390）；providers 配置层五函数裸单测（c393）。

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
- 题库扩充：271 → **317 题**（12 包）。Phase 1 剖减 a_irac 全分饱和题 20 题
  入 archive；Phase 3a/3b/3c 新增难题 36 题；Phase 4 新增实务题 30 题
  （v0.6 batch4 再增 cit stale 族 6 题至 323，见 0.6.0 与 FRAMEWORK v0.6
  横幅现行规模）。
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
