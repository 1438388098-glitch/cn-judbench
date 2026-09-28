# CN-JudBench (法衡) Technical Report v1

> Release: **v0.6.0** · Framework version source of truth: [FRAMEWORK.md](../FRAMEWORK.md) header (**v0.6**) · Dataset version: **0.6.1** ([CITATION.cff](../CITATION.cff), 2026-09-27) · Report date: 2026-09-28
>
> **Disclaimer (fixed statement, FRAMEWORK §12.1)**: this benchmark measures model behavior on controlled item texts and tool environments only. It **is not legal advice** and must **not** be used for judicial rulings, compliance sign-off, or party decisions. Scores are relative measures on a 0.00–100.00 scale, not usability certifications.
>
> Every number in this report is traceable to a repository file; the source is cited inline. No new model runs were performed for this report.

---

## 摘要（中文）

CN-JudBench（法衡）是面向中国司法工作流的大模型多维评测基准：12 个任务包、323 道公开题（`data/public/MANIFEST.json` 机检对账），覆盖引用效力、要件抽取、隐藏单测计算、罪名涵摄、工具调用与故障注入恢复、多轮接待与多日案件管理。判分为谓词级机检（FTP/PTP 双谓词），配失败 taxonomy、逐题污染金丝雀、random/rules 基线泄题监控、锚×as_of 审计入 CI，以及预注册统计协议（pass^k 组合语义、paired bootstrap CI、McNemar 精确检验、两级排名粒度、预注册核心六包等权口径）。当前结果状态：基线锚点 random 7.96 / rules 27.40 / mock:gold 100.00（baseline-v06c，2026-09-25 重导；mock:gold 为判分管线天花板与健康门禁，**非模型分**）；v0.5 Phase 5 双隔离考生 62 题轮 pass^2 = 46.77 [33.87, 59.68]；主记分板 13 条模型行**全部 provisional=true**，逐 run 明细见 `docs/run-score-ledger.md`。本版不附任何当前公开模型的正式跑分（正式榜运行待后续版本）。评测结果不构成法律意见，不得用于司法裁判、合规放行或当事人决策。

## Abstract

CN-JudBench is a multi-dimensional benchmark for large language models and judicial agents on Chinese judicial workflows: 12 task packages with 323 public items (machine-reconciled against `data/public/MANIFEST.json`), spanning citation validity, element extraction, calculation verified by hidden unit tests, charge subsumption, tool invocation with fault-injection recovery, multi-turn intake, and multi-day case management. Scoring is machine-checked at the predicate level (FTP/PTP) with a registered failure taxonomy, per-item contamination canaries, random/rules baseline leak monitoring, an anchor×as_of statute audit wired into CI, and a preregistered statistical protocol (pass^k combinational semantics, paired bootstrap CIs, McNemar exact tests, two-tier ranking granularity, a preregistered six-package equal-weight comparison unit). Current results status: baseline anchors random 7.96 / rules 27.40 / mock:gold 100.00 (baseline-v06c, re-exported 2026-09-25; mock:gold is the scoring-pipeline ceiling and health gate — **not** a model score); the v0.5 Phase-5 dual-isolated-examinee round (62 items) measured pass^2 = 46.77 [33.87, 59.68]; all 13 rows on the current model board are **provisional=true** (per-run details in `docs/run-score-ledger.md`). This release carries **no formal scores for currently public models** — formal board runs are deferred to later versions. Evaluation results are not legal advice and must not be used for judicial rulings, compliance sign-off, or party decisions.

---

## 1. Motivation

Existing Chinese legal LLM evaluations are dominated by bar-exam-style multiple choice and keyword matching. Our measurements (recorded in `docs/paper-outline.md` §1) indicate two structural problems with that paradigm:

1. **Head-model saturation**: two top-tier same-generation models measured within 1 point of each other on total score (Pearson r = 0.91) under the v0.3 item pool, and 49% of v0.3 items carried zero information (35 dual-full-score + 16 dual-zero items) — driving the v0.4 redesign (`docs/paper-outline.md` §3.3).
2. **Missing measurement infrastructure**: published Chinese legal benchmarks generally lack machine-checkable scoring oracles, contamination controls, baseline leak monitoring, and preregistered statistics (`docs/paper-outline.md` §2, related-work table: LawBench/LexEval-class systems scored "无" on all three). Worse, defects in the benchmark itself — wrong gold answers, scoring anchors leaking into baselines — get misread as model weakness.

CN-JudBench therefore asks a narrower, operational question rather than "does the model know law":

> **Which capability dimension works, which one is dangerous to rely on, is the behavior stable across runs, and at what cost?** (FRAMEWORK §0)

Four properties follow from this framing and are enforced throughout the framework: capability-first taxonomy before item count (FRAMEWORK §1, hard constraint 1); machine-checkable oracles with an oracle-hardness ladder (hidden unit tests / state diffs > exact > constrained F1 > judge-assisted columns); safety/capability score separation (safety fixtures never enter the capability main score); and stability and cost reported at the same rank as accuracy (pass^k, $/solve, p95 latency; FRAMEWORK §1, constraint 8).

## 2. Benchmark Design

### 2.1 Capability taxonomy and interaction layers

Items are tagged over an 8-dimension capability dictionary — **K**nowledge, **U**nderstanding/extraction, **R**etrieval, **S**ubsumption, **A**rgumentation, **O**utcome, **G**eneration, **C**ommunication (FRAMEWORK §3; authoritative dictionary `src/cnjudbench/capabilities`, enforced by `validate`) — crossed with interaction layers L1 (static QA) through L4 (long-horizon casework) (FRAMEWORK §2) and validated for 8-domain coverage (each package has ≥1 item per domain; `docs/dataset-card.md` §3).

Item sources (323 items, machine-checked): synthetic 305, synthetic_adversarial 14, real_amended 4 (`docs/dataset-card.md` §3). Author difficulty distribution d1–d4 = 6 / 81 / 117 / 119 (`docs/paper-numbers.md`, from MANIFEST); 68 items carry `saturation_flag: true` from dual/three-sample empirical audits (`docs/dataset-card.md` §1.1). The statute backbone **lawkb** stores multiple versions per article with `as_of` time-slice resolution and sha256 text hashes: 13 laws, 67 versions (`docs/dataset-card.md` §6).

### 2.2 The 12 task packages

| Package | Items | Capability dim. | Oracle |
|---|---:|---|---|
| calc_fail_to_pass | 54 | U | hidden unit tests (fail-to-pass) |
| u_element_extract | 49 | U | element extraction (field F1, `field_keep` PTP) |
| a_irac_reason | 34 | A | structured IRAC |
| cit_validity | 27 | Cit | citation validity (status_ladder) |
| tool_search_statute | 26 | G/R/U | tool_sequence / tool_ast |
| contract_risk | 23 | C | must_not / risk disclosure |
| gaia_fee_deadline | 23 | K/U | fee relative-error ladder + progress |
| dms_side_effect_intake | 20 | O | env_diff end-state diff |
| s_charge_subsume | 20 | S | charge subsumption (exact) |
| tau_jud_intake | 16 | C | end-state F1 + Proto (multi-turn) |
| tool_fault_recovery | 16 | O | recovery × final (fault injection) |
| long_horizon_case | 15 | U | score–time, multi-day |
| **Total** | **323** | | |

Source: README task table, reconciled against `data/public/MANIFEST.json` per-package `n_items` (sum = 323, machine-checked).

### 2.3 Task design principles

The packages are chosen so that each capability axis is scored by the **hardest oracle that can still be checked mechanically** (oracle-hardness ladder, `docs/paper-outline.md` §3.2):

- **Citation validity** (`cit_validity`): every citation is resolved through lawkb at the item's `as_of` date; fabricated statutes force the item to 0.00, and stale/wrong-vintage citations trigger `stale_statute`. The v0.6 scoring-validity fixes force the item's `as_of` — a candidate cannot launder a dead statute by self-reporting a favorable date (paper-outline §9 E20).
- **Element extraction** (`u_element_extract`): FTP fields must be hit while PTP `field_keep` predicates protect already-correct fields; negative-form elements and multi-date ambiguity variants probe the extraction boundary (`docs/dataset-card.md` §2).
- **Calculation with hidden unit tests** (`calc_fail_to_pass`): candidate answers are executed against fail-to-pass unit tests (five formula families with hard variants on holiday rollover, limitation interruption, caps, compounding) — the answer must *run*, not *look right* (FRAMEWORK §14 #12).
- **Charge subsumption** (`s_charge_subsume`): exact structured JSON with element-level predicates; 7 safety fixtures ("should refuse" cases) are scored in a separate safety column and excluded from capability aggregates (FRAMEWORK §14 #2, ledger §0).
- **Tool invocation with fault injection** (`tool_search_statute`, `tool_fault_recovery`): a 6-tool sandbox scores tool sequences and argument ASTs; narrating a call without executing it is `fake_tool` → 0.00. Fault-recovery items inject four fault types and score recovery × final-answer quality, including nth-order "success-then-failure" chains (FRAMEWORK §14 #12; paper-outline §8 E10).
- **Multi-turn intake** (`tau_jud_intake`): scripted users with fixed `user_seed`, end-state F1 on the case card, practice-protocol (Proto) checks, and pass^k reported separately for fixed-user vs swapped-persona stability (FRAMEWORK §5.1).
- **Multi-day case management** (`long_horizon_case`, `dms_side_effect_intake`): whole-case workflows scored over days (score–time), and side-effect items diff the tool-environment end state (`env_diff`), with preset open cases and dual-card distraction states (`docs/dataset-card.md` §2).

A fixed statement of fairness is enforced at validation time: any `answer_enums` declared in scoring must appear verbatim in the item text — "the examinee notice must cover the scoring criteria" (paper-outline §8 E8; `docs/dataset-card.md` §4).

## 3. Scoring Protocol

All scores live on a **percentage scale with two decimals** (0.00–100.00); unscorable items are `null`/`n/a` and filling 0.00 is forbidden (FRAMEWORK §0). The protocol:

1. **Predicate-level machine checking.** Each item declares FTP (must-hit) and PTP (must-not-break) predicates from a closed 22-type registry (FRAMEWORK Appendix B, aligned with the validator's 22-class enum per CHANGELOG 0.6.1), gated by an applicability matrix over `output_type` — free text never receives mechanical PTP predicates (FRAMEWORK §4.2). Item composition follows a fixed order: item_raw → item-level redline handling (Hall −20.00 per fabricated element; fabricated statute → 0.00) → gate caps (cap_50/force_zero) → capability aggregate (FRAMEWORK §8.1).
2. **pass^k combinational semantics.** The headline stability metric requires **all k independent samples of the same item to pass** (combination, not average); multi-run aggregation via `scripts/aggregate_passk.py` with bootstrap CI; runs with fewer than k usable attempts return None rather than a fake 0.00 (CHANGELOG 0.6.0, c388).
3. **One-to-one set matching against answer dumping.** Element-set scoring uses a 1–1 greedy set_f1: dumping the entire element inventory can no longer harvest duplicate credit. The honest price of this anti-hacking tightening, measured by single-variable ablation on the same 105 real answers, is **−2.48 points on grand** (s_charge 0.4482→0.3911, −5.71), while a full-dump attack drops from full score to 0.5 (`docs/paper-outline.md` §9 E19; `tests/test_setf1_onetoone_v06.py`).
4. **any-of multi-answer reading.** Gold may declare `acceptable_articles`; hitting any one covers the predicate, and same-law articles resolved through lawkb aliasing join the anchor set — one legitimate reading among several is not penalized (FRAMEWORK §14 #14).
5. **scored% / n/a accounting.** Parse failures are candidate-fault 0.00 (`format_fail`); only server truncation (`finish_reason=length`) is `n/a`. Summaries report scored_rate alongside a conservative solve% (n/a counts as unsolved) and warn below 90% scored coverage — "answered 60% and got the rest right" can no longer masquerade as a higher score (FRAMEWORK §8.4; paper-outline §9 E18 item 3).

## 4. Validity Controls

- **Contamination canaries.** Every item carries a sha256-derived `CNJB-CANARY-*` string scanned in outputs; an 8-gram normalized-overlap double check against an external corpus is wired into the CI gate (`--ngram-corpus docs/corpus.txt`); the anti-contamination ladder L0–L4 marks logit-based membership inference as applicable to open weights only (FRAMEWORK §9; `docs/dataset-card.md` §5).
- **Baseline leak monitoring.** random/rules baselines run through the *same* scoring pipeline and are banned from reading scoring anchors (`law_anchors`). This control caught a real leak: a_irac baselines scored 96 — above the real examinee's 90 — until fixed to 12; a regression test locks the invariant (`docs/paper-outline.md` §9 E13, `test_baselines_never_cite_scoring_anchors`). `reports/baseline-report.md` keeps near-perfect-score alerts permanently on.
- **Anchor×as_of audit in CI.** A full-corpus resolution audit of every law anchor against its `as_of` (E14) found exactly one real gold bug (lh-06, an anchor citing the not-yet-effective Civil Code Art. 509) and is scripted as the admission gate for lawkb expansion (`docs/paper-outline.md` §9 E14).
- **Preregistered gold re-adjudication policy.** Since 2026-09-23 (policy v1.0), any gold change must satisfy five preregistered conditions — legal basis independent of the candidate's answer, typed as `gold_bug` vs `multi_answer_gap`, a two-sided check that baselines do not rise, an entry in `docs/gold-item-review-log.md`, and before/after re-scoring ablation of the *same* candidate answers (`docs/gold-adjudication-policy.md`). Pre-policy history, including non-compliant cases, is retained as attack-surface evidence (policy §5).
- **Pipeline self-certification.** `mock:gold` replays gold answers through the full scoring pipeline and must score 100.00 — if gold cannot self-certify, the gold is buggy, not the model (paper-outline §3.5). Gold-error contamination is quantified by ablation: re-scoring the *same* 19 a_irac candidate answers before and after the gold legal review moved the score **31.58 → 86.84** (paper-outline §9 E11; `docs/paper-numbers.md`) — when gold is wrong, the "model score" measures the gold-model disagreement, not capability. The v0.6 scoring-validity fixes (as_of anti-self-certification, polarity-opposed clamping, refusal negation exemption) were verified **zero-drift** on all 245 per-item baseline scores (`tests/test_baseline_zero_drift_v06.py`; paper-outline §9 E20) — the fixes only close candidate-side cheating paths.
- **Answer-alignment guard.** Before backfilling externally generated answers, `scripts/check_answer_alignment.py` (bigram Dice + reverse best-match confirmation) flags suspect substitutions for manual review; it has caught two real subagent answer-misalignment incidents (README).

## 5. Statistical Protocol (Preregistered)

- **Paired inference.** `cnjudbench compare --run-a <A> --run-b <B>` computes paired bootstrap 95% CIs (1,000 resamples) on per-item score diffs and McNemar exact tests; ranking claims must carry CI and p-values (FRAMEWORK §8.4).
- **Preregistered comparison unit.** To prevent post-hoc metric shopping, model-ranking claims are restricted to the **core six packages, equal-weight macro** — `cit_validity · u_element_extract · s_charge_subsume · contract_risk · a_irac_reason · long_horizon_case` — 168 items total, of which 161 are capability-comparable (7 safety fixtures in s_charge are excluded from paired samples); 12-package and per-package scores are descriptive navigation only (FRAMEWORK §8.3). The preregistration exists because reading the same data under a non-preregistered reading flips conclusions: on the E17 examinee pair, the full 62-item diff (4.08 [−2.80, 10.26], McNemar p = 0.34) is not significant, while the preregistered six-package reading of the same pair (40 paired items, diff 10.62) yields macro 14.67 [8.41, 21.05] with the CI excluding zero — both are disclosed, the preregistered reading is formal (paper-outline §9 E18; golden-locked in `tests/test_e18_repro_golden_v06.py`).
- **Two-tier ranking granularity.** n ≥ 100: rankable with CIs; 50 ≤ n < 100: point ± CI marked *descriptive*, no ranking; n < 50: description only (FRAMEWORK §8.3; thresholds locked in `metrics/compare.py` `RANKABLE_MIN_N` / `CI_DESCRIPTIVE_MIN_N`).
- **Provisional contract and flip gate.** A run without a locked flip rate (<5% per-item pairwise flips on identical re-runs) and dependency lock is `provisional: true` and barred from formal tables (T-main). The empirical motivation: a k=3 retest of a real examinee showed 6/11 pairwise item flips (≈55%) — single-sample boards carry false resolution (paper-outline §8 E7). As of 0.6.1 (c429), `compare` itself downgrades to `descriptive_only` when either run is provisional (CHANGELOG 0.6.1).

## 6. Current Results (Honest Reading)

**This section reports exactly what the repository contains and no more.** All external quotes follow one scoring pipeline and are logged in `docs/run-score-ledger.md` — the single ledger of record.

### 6.1 Baseline anchors

Same-pipeline anchors on `baseline-v06c` (re-exported 2026-09-25): **random 7.96 · rules 27.40 · mock:gold 100.00** (ledger §1 note; `docs/dataset-card.md` header). Interpretation discipline: `mock:gold` replays gold answers through the full pipeline, so 100.00 is the **pipeline ceiling and health gate — not a model score**. The rules-vs-random gap of ~19 points shows the item set is not solvable by shallow heuristics alone; the anchor chain (v06 rules 27.03 → v06b zero-drift re-export → v06c 27.40, the +0.37 attributed to scoring fixes R29/R32 predating the v06b re-export) is documented per-run in the ledger.

### 6.2 Live examinee round (dual isolated examinees)

The v0.5 Phase-5 round answered 62 new items with two mutually isolated examinee subagents (export → leak guard → answer → swap guard → `file:` backfill, all machine-checked). **Grand pass^2 = 46.77 [33.87, 59.68]** (bootstrap 95%; golden-locked in `tests/test_passk_golden_v06.py`; `docs/paper-outline.md` §9 E17, n=62). The families that genuinely separate examinees are the as_of temporal-effectiveness axis (pass^2 8/22), six-domain whole-case (0/6), and risk-disclosure (0/6) items — i.e., statute-version identification, cross-period liability, and disclosure completeness are where stability collapses. The same round surfaced 4 gold/item-text defects in 62 items (defect rate 4/62), all fixed in-loop — fresh items must pass a real-examinee round before admission (E17; README "How a new item is admitted"). The round's harness lesson became a v0.6 scoring fix: tau state predicates previously required verbatim matching that real examinees could never satisfy structurally; converted to partial credit, the *same* examinee answers re-score 0.00 → 13.09 (S1) and 0.00 → 5.56 (S2), separating the two examinees for the first time (paper-outline §9 E18; FRAMEWORK header).

### 6.3 Model board: all rows provisional

The current board holds **13 full-coverage model rows** (n_capability=238 · n_safety=7), with grand_eq spanning **59.14–71.62** (leaderboard in `docs/run-score-ledger.md` §1). **Every row is provisional=true**: none has passed the <5% flip gate and dependency lock, so the board supports descriptive reading only — no formal ranking claims are made anywhere in this report. The one row with a recorded flip rate is the API-isolated DeepSeek-V4.1-Flash run (grand 68.72, hard 76.31, flip 0/81 = 0%, cost $0.56 — ledger §1 #5); its flip evidence is per-run and does not transfer to other rows. Safety is the sharpest descriptive signal: 6 of 13 rows score 0.00 on the 7-item should-refuse fixture set (ledger §1 "可引用结论"), and the GLM-5.3-Flash thinking-tier contrast (high 69.59 / low 64.18 / default-inherited 59.14, with safety moving in the *opposite* direction) shows capability and safety dissociate under reasoning-effort changes.

### 6.4 Absent results

**This release contains no formal scores for any currently public model.** The 13 ledger rows are provisional descriptive measurements retained for calibration and harness debugging; formal board runs — preregistered, flip-gated, dependency-locked, and ultimately paired with holdout/live splits — are deferred to later versions. Readers should cite baseline anchors and the examinee-round pass^2 (with their caveats) and nothing else as "results."

## 7. Limitations and Threats to Validity

1. **Scale and language.** 323 items, 12 packages, Chinese only; per-domain cells are below statistical power and never ranked (FRAMEWORK §8.3 granularity rules; `docs/dataset-card.md` §6).
2. **Synthetic-dominant composition.** 305/323 items are synthetic; language is more regular than real filings; real case files require the holdout freeze protocol (protocol ready at `docs/holdout-live-protocol.md`, execution pending — paper-outline §7.3).
3. **Saturation at the top.** 68 items are empirically saturated (`saturation_flag: true`); element extraction and IRAC saturate for head models — discrimination must come from the oracle ladder, not harder prose (paper-outline §9 E12/E12+).
4. **lawkb coverage.** The statute store is a curated excerpt (13 laws / 67 versions); out-of-store articles are reported as `unknown_in_lawkb` (not hallucination), but statute-predicate discriminative power is bounded by coverage (paper-outline §5, E11).
5. **Difficulty calibration depends on the model pool** used for empirical re-labeling (`docs/paper-outline.md` §5); author-labeled difficulty agrees with empirical pass bands only 33.9% (Spearman ρ = +0.152, `reports/difficulty-emp-crosstab.md`).
6. **Scoring-validity residuals.** Two known scoring attack surfaces are confirmed but unfixed pending preregistered ablation: transcript-contamination in Proto redline scanning (F4) and missing precision in statute-set dumping (F5) — backlog candidate-571 (`docs/paper-outline.md` §9 E20).
7. **Flip gate for closed APIs.** Identical-configuration re-runs of closed APIs cost money; rows lacking flip evidence stay provisional by design.
8. **Contamination controls are risk signals, not proof.** Canaries and n-gram checks cannot prove absence from pretraining corpora; Chinese legal boilerplate raises false-similarity rates (FRAMEWORK §9.1).

## 8. Roadmap

From README "To do" and `docs/paper-outline.md` §7:

- Formal board runs for currently public models under the preregistered protocol (flip-gated, dependency-locked), plus the f-105..108 tool-track and tau real-examinee rounds.
- Holdout freeze execution (`freeze_holdout.py --apply` after dual review) to enable the private-split leaderboard tier; live rolling subset for post-cutoff knowledge.
- Human-rating κ pilot (protocol and tooling ready; human ceiling for judge-assisted columns).
- Scoring-validity backlog: F4/F5 fixes under the same ablation-then-rebaseline discipline (candidate-571); lawkb expansion gated by the anchor×as_of audit (7 packages awaiting review).
- Temporal-effectiveness probes at-201..211 awaiting a real examinee round (paper-outline §7.10).

## 9. Reproduction

Environment: Python 3.11+ (developed and CI-tested on 3.11/3.13); run from a clone root (README "Run constraint"). All commands below are quoted from README / FRAMEWORK.

```bash
# Install (Windows; Linux/macOS equivalent in README)
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"

# Validate items, predicates, applicability matrix, lawkb integrity
python -m cnjudbench validate --items data/public --tasks tasks

# Deterministic zero-network scoring-pipeline check (mock:gold ceiling)
python -m cnjudbench run-all --tasks cit_validity,u_element_extract,s_charge_subsume --model mock:gold

# Multi-turn with pass^k fixed-user vs swapped-persona
python -m cnjudbench run-dialog --task tau_jud_intake --model mock:dialog --user-seed 42 --k-pass 3 --out reports/runs/tau1

# Paired comparison (bootstrap CI + McNemar; preregistered six-package macro)
python -m cnjudbench compare --run-a <run-A> --run-b <run-B> --preregistered --items-out reports/compare/items.csv

# Flip-rate gate (formal tables require < 5%)
python scripts/flip_rate_check.py --tasks u_element_extract --model openai:<model> --max-flip 0.05

# pass^k aggregation over >= k runs of one model
python scripts/aggregate_passk.py --runs reports/runs/ds-a reports/runs/ds-b reports/runs/ds-c --threshold 100 --out docs/passk-ds.md

# CI gate (validate + pytest + mock run-all + artifact assertions + flip = 0)
bash scripts/ci_gate.sh          # Windows: powershell -File scripts/ci_gate.ps1
```

## 10. Citation

BibTeX (from `CITATION.cff` / `docs/dataset-card.md` §7):

```bibtex
@misc{cnjudbench2026,
  title  = {CN-JudBench: A Multi-dimensional Benchmark for Large Language Models
            in Chinese Judicial Workflows},
  author = {{CN-JudBench (法衡) Authors}},
  year   = {2026},
  note   = {v0.6.1, 323 items, 12 task packages; MIT (code) / CC BY 4.0 (data)},
  url    = {https://github.com/1438388098-glitch/cn-judbench}
}
```

License: code MIT (`LICENSE`); data / item text / task packages CC BY 4.0 (`LICENSE.DATA`); lawkb statute texts are official works shipped with sha256 text hashes.
