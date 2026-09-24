# 论文数字溯源清单（c293）

> 论文与提纲中出现的实验数字的**唯一对账表**：每个数字标注来源（金样测试 /
> 报告文件 / MANIFEST），可机检的由 `tests/test_paper_numbers_v06.py` 守卫。
> 写作引用任何数字前先在此登记；数字变更必须同步来源与提纲。

## 总量口径

| 数字 | 含义 | 来源 | 机检 |
|---|---|---|---|
| 323 / 12 包 | 公开集题量 / 包数 | `data/public/MANIFEST.json` `n_items_total` | c271/c274 |
| 168 / 161 | 预注册核心六包合计 / capability 可比较（s_charge 7 道 safety 夹具不进配对样本；n_aligned 实测值） | MANIFEST 六包 `n_items` 和；`data/public` role 字段实数 | c262/c367 |
| 6/81/117/119 | 难度 1–4 档分布 | MANIFEST items.difficulty 统计 | c291 |
| 8 域 | 科目全覆盖 | `data/public/*.jsonl` domain 字段 | c299 |

## 统计与区分度（金样锁定）

| 数字 | 含义 | 来源 | 机检 |
|---|---|---|---|
| diff 4.08 [−2.80, 10.26]、McNemar p=0.3438、n=62 | E18 全集口径 S1 vs S2 | 金样 `tests/test_e18_repro_golden_v06.py`（compare v05new-s1m/s2m-score） | ✓ |
| macro 14.67 [8.41, 21.05]、n=40、剔 22 | E18 预注册口径（六包等权） | 同上 + `n_dropped_by_filter` | c282 |
| pass^2 = 46.77 [33.87, 59.68] | E17 双考生组合通过率 | 金样 `tests/test_passk_golden_v06.py` | ✓ |
| 剔除饱和 30 题 / 余 46 | pass^k 剔饱和口径 | `reports/passk-repro.md`（`scripts/aggregate_passk.py --exclude-saturation`） | c301 |
| set_f1 消融 −2.48 分 | 1-1 贪心配对 vs 旧非独占规则（反整段倾倒的代价/收益） | FRAMEWORK 头部 v0.6 摘要（E19 真数据消融）、`tests/test_setf1_onetoone_v06.py` | 历史运行记录 |

## 判分效度审计（历史运行记录，报告留档）

| 数字 | 含义 | 来源 |
|---|---|---|
| 31.58 → 86.84（Δ55.26） | a_irac 金样消融：同批答案修正金样后重判 | `docs/calc-real-model-report.md` §C3–C7 |
| 96 → 12 | random/rules 基线泄题修复前后（a_irac） | R16-R25 技术账（记忆/夜报），回归测试 `test_baselines_never_cite_scoring_anchors` |
| 33.9% / ρ=+0.152 | 作者难度×实证通过率对角一致率 / Spearman | `reports/difficulty-emp-crosstab.md`（`scripts/calibrate_difficulty.py`） |
| S1 0.00→13.09、S2 0.00→5.56 | tau state partial 化后真考生重判 | `docs/paper-outline.md` §E18（同份答案重判运行记录） |
| 6/62（缺陷率 9.7%） | fresh 题真考生轮抓出金样/题面缺陷 | `docs/paper-outline.md` §E17、`docs/self-review-new-items-*.md` |
| random 7.96 / rules 27.03 | v0.6 判分收紧后基线（baseline-v06） | `reports/runs/baseline-v06`、dataset-card 口径行 | ✓ |
| 判分修复后基线零漂移 | R24 c322-c324 修复重导 baseline-v06b：245 题逐题分与三基线汇总与修复前完全一致 | `reports/runs/baseline-v06b`、`tests/test_baseline_zero_drift_v06.py`、calc-real-model-report §C5 | ✓ |
| DS-flash v0.6 全 12 包 grand 68.72（hard 76.31，flip 0%，$0.56） | T1 首个非 GLM 真考生 v0.6 全量行；工具轨分化首证（dms 96.23 vs GLM 64.36、fault 37.50 vs GLM 58.33，GLM 为 v0.4 口径） | `reports/runs/ds-flash-v06-full` + `-tools`、`docs/run-params-ds-flash-v06.md` | 历史运行记录 |
| c322-c324 修复组 | as_of 强制题面 / 极性对冲 / 拒绝否定豁免（判分效度 v0.6 收尾） | `tests/test_validity_fixes_v06.py`（8 测试，s-006 伪 as_of 反自证样例） | ✓ |
| eligibility 两档制 100/50 | 排名资格阈值（n≥100 rankable；n≥50 CI 仅 descriptive） | `src/cnjudbench/metrics/compare.py` `RANKABLE_MIN_N`/`CI_DESCRIPTIVE_MIN_N` + FRAMEWORK §8.3 | c342 |

> 「历史运行记录」类数字无法 pytest 机检（依赖本地考生 run 目录），
> 以报告文件 + 提纲双重留档为准；引用时注明口径与运行日期。

## 对账纪律

1. 论文表（paper-tables.md）列值只能来自本表登记的来源，禁止临场报数。
2. 新实验数字：先跑实验 → 生成报告 → 本表登记 → 提纲引用。
3. 每轮 autopilot 收官时 `--brief` 检查本表机检全绿。
