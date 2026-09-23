# 夜报 · 2026-09-23 深夜 → 09-24 晨（R24-R30 autopilot 收官轮）

> 接续上一夜（docs/night-report-2026-09-23.md，v0.6 收官时 531 绿）。
> 本夜六轮提交（R24-R29 + 本报告 R30），测试 531 → **569 绿**，
> 每轮 ci_gate ALL GREEN；HEAD=2347fe7。

## 一、主线：判分器对抗性审计闭环（R24 → R26 → R27）

1. **R24 判分效度大补丁（626f949，c322-c331）**——红队视角自查出三条
   考生侧作弊/误判路径并全部封堵：
   - **时效自证**（c322）：考生 citation 自报 as_of 曾覆盖题面基准日
     （引用废止法条+伪日期可洗掉 stale_statute 零分）。修复后判分强制
     题面 as_of，考生叙述值仅进诊断列；
   - **极性对冲**（c323）：`polarity_opposed`——「不支持」不再得分于
     「支持」（否定头+剥头核心相等即对冲），钳制 labels_match 捷径与
     text_coverage/state 键分；
   - **拒绝误判**（c324）：「本案无需转介」等否定头实质作答不再被
     拒绝词表误判（击穿方向留 F1'，见下阻塞）。
   同轮补统计四项（pass^k k 越界报错 / compare eligibility 两档制 /
   flip vacuous pass 拒绝 / macro 缺包告警）与发布面三项
   （pyproject metadata / CITATION authors / README 修复）。
   **事故与自救**：pyproject 的 `[project.urls]` section 一度插错位置
   截断 `[project]` 表（requires-python/dependencies 被吞），tomllib
   两测试当场抓红，同轮修复。

2. **R26 零漂移验证（b329b6b）**——判分器改动与 gold 改动同权：修复后
   重导基线 baseline-v06b，**245 题逐题分与 random 7.96 / rules 27.03 /
   gold 100 与修复前完全一致**——三项修复只打击考生侧路径，不动基线
   判分面。FRAMEWORK §8.4 立纪律：判分语义改动必须重导基线并留档
   （零漂移也要留证）。

3. **R27 叙事进提纲（a3866cd）**——paper-outline 新增 §E20：与 E19 合成
   「判分器即被测对象」两翼——单变量消融证明改动有效（E19 −2.48
   明码标价），零漂移证明改动无副作用（E20）；F4/F5 未修项如实入局限。

## 二、发布与面板（R25 / R29）

- **R25（ddbe0f8）**：版本四源一致机检（pyproject/CITATION/__init__/
  CHANGELOG/dataset-card）、TODO-assign-repo 占位符集中清单机检、
  §8.3 两档阈值常量与 FRAMEWORK 文字互锁、pass^k threshold 越界拒绝、
  flip 门禁工具包适用面声明、dataset-card 补版本字段。
- **R29（2347fe7）**：公开面板 lawkb 版本数 51→61、提纲 60→61 勘误；
  c360 机检把 index.html 的 lawkb 数与库实况、总题数与 MANIFEST 互锁。
- 顺手勘误：compare.py CORE_SIX 注释 162→168（c262 口径漏改处）。

## 三、扩题：时间效力轴草稿出库（R28，1c42794）

附录 B READY 规格 at-201/202/203/210 出 **cit_validity 判定面草稿
ct-201..211（5 题）**：11 窗全部经 resolve_article 探针验证，覆盖
ok / wrong_vintage / not_yet_effective 三判定；ct-210/211 同条跨施行日
成对（考生轮可测翻转率）。三方编号约定 **at=规格 / ah=IRAC 叙事草稿 /
ct=cit 判定面草稿** 防考生轮混淆。BLOCKED 6 规格（合同法 40/114/226、
担保法 19、刑法 237 两版、民法典 496/497/686/721、买卖解释 25）仍待
flk 源可达后补库（夜里不可达）。

## 三b、收口补轮（R31-R33，06:40-07:00）

- **R31（b5980be）**：草稿隔离机检（判分管线与 data/drafts 实集交集须空；
  途中发现 ah-005 系正式集合法题，改实集断言防前缀误报）+ ct 判分面
  漂洗自证预检（9 题路径中 cit 5 题 mock:gold 全 100）。
- **R32（8a78611）**：ct 基线预演金样——gold 5×100、rules 20.00
  （4 陷阱窗全 0 + ct-211 对照满分），泄题门禁 ≤40 锁进金样；random
  首演 48.00 入台账不入机检（无种子非确定性）。
- **R33（本提交）**：`scripts/export_draft_prompts.py` 漂洗导出工具 +
  `docs/examinee-round-pack.md` 考生轮执行包——发起人按 5 步即可把
  9 题草稿推进 examinee_round，无需再准备材料。

## 四、阻塞项（需用户，同前夜 + 新增）

1. DeepSeek 有效密钥 / 智谱 1113 充值（真实考生跑分）。
2. holdout `--apply` 双审签字、人评 κ 招募。
3. **ct 草稿真考生轮**：ct-201..211 与 ah-201..210 一起入轮（隔离考生
   双答 → gold 裁定 → 入库）。
4. **F4/F5 判分语义修复**（candidate-331/346，blocked）：proto transcript
   污染、statute 倾倒无精确率——改动会重排历史分数，须先跑真考生
   消融留痕（gold-adjudication-policy 同等纪律）。
5. lawkb BLOCKED 规格补库（flk 源日间可达后执行）。

## 五、诚实边界（不变项）

- T-main 仍为空表（provisional 门禁按设计生效）。
- a_irac 头部饱和叙事（E12+/E16）未变；区分度靠工具/时长/统计轨。
- baseline-v06/v06b 仅本地保留（reports/runs 不入库），第三方克隆时
  相关金样测试自动 skip（c237 同模式）。
