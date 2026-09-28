English · [简体中文](./README.zh-CN.md)

# CN-JudBench (法衡)

A multi-dimensional benchmark for large language models / judicial agents on Chinese judicial workflows: **which capability a model has, where it is dangerous, whether it is stable across runs, and at what cost.** 12 task packages, 323 public items; scoring is machine-checked, statistics are pre-registered, and every published number links to a reproducible run. Current release: **v0.6** ([release notes](https://github.com/1438388098-glitch/cn-judbench/releases/tag/v0.6.0), [technical report](docs/technical-report.md)); full history in [CHANGELOG.md](CHANGELOG.md) — the version source of truth is the [FRAMEWORK.md](FRAMEWORK.md) header.

**Abstract (EN)**: CN-JudBench evaluates large language models on Chinese judicial
workflows across 12 task packages (323 public items) spanning citation validity,
element extraction, calculation with hidden unit tests, charge subsumption,
tool invocation with fault injection, multi-turn intake and multi-day case
management. Scoring is machine-checked at the predicate level with a registered
failure taxonomy, contamination canaries, random/rules baseline leak monitoring,
and a preregistered statistical protocol (pass^k combinational semantics, paired
bootstrap CIs, McNemar exact tests, two-tier ranking granularity). Version 0.6
closes three scoring-validity gaps found via live examinee rounds: free-text
state predicates now award partial credit, reward-hacking via answer dumping is
blocked by one-to-one set matching, and per-package baselines guard against
scoring shortcuts. Code is MIT-licensed; the public split is CC BY 4.0
(see CITATION.cff).

- **目标** (Goal): measure *which* legal capability a model can perform in Chinese judicial workflows, *where* it is dangerous, *whether* it is stable across runs, and *at what cost*.
- **分数** (Score): percentage scale, two decimals (0.00–100.00).
- **非法律意见** (Not legal advice): evaluation results must not be used for judicial rulings, compliance sign-off, or party decisions.

## Task packages at a glance (12 packages / 323 items, machine-checked against MANIFEST)

| Package | Items | Capability dim. | Oracle |
|---|---|---|---|
| calc_fail_to_pass | 54 | U | hidden unit tests |
| u_element_extract | 49 | U | element extraction |
| a_irac_reason | 34 | A | structured IRAC |
| cit_validity | 27 | Cit | citation status_ladder |
| tool_search_statute | 26 | G/R/U | tool_sequence/ast |
| contract_risk | 23 | C | must_not / risk disclosure |
| gaia_fee_deadline | 23 | K/U | fee ladder + progress |
| dms_side_effect_intake | 20 | O | env_diff end-state |
| s_charge_subsume | 20 | S | charge subsumption (exact) |
| tau_jud_intake | 16 | C | end-state F1 + Proto |
| tool_fault_recovery | 16 | O | recovery × final |
| long_horizon_case | 15 | U | score–time, multi-day |

## Results at a glance

All scores quoted externally follow one scoring pipeline and are logged in
[docs/run-score-ledger.md](docs/run-score-ledger.md) — the single ledger of record.

- **Baseline anchors** (same scoring pipeline, `baseline-v06c`, re-exported 2026-09-25): random **7.96** · rules **27.40** · mock:gold **100.00**. `mock:gold` replays gold answers through the full scoring pipeline, so 100.00 is the pipeline ceiling and its health gate — **not** a model score.
- **Live examinee round** (v0.5 Phase 5, dual isolated examinees, 62 items): pass^2 = **46.77** [33.87, 59.68] (docs/paper-outline.md §9, E17).
- **Current model board**: 13 full-coverage rows (n_capability=238 · n_safety=7), headline metric = grand total (pack-equal, `capability.grand_eq`; question-weighted total for reference only). **All rows are provisional=true** pending the flip (<5%) gate — descriptive comparisons only, no formal ranking claims. Per-run table: docs/run-score-ledger.md §1; visual panel: [index.html](index.html).

## Quick start (5 minutes)

```bash
# 1) Create a venv and install the package with dev dependencies (pytest/pydantic/PyYAML)
# Windows:
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
# Linux/macOS:
# python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"

# 2) Run tests (green suite; exact count: see the CI badge)
# Windows uses .venv\Scripts\python; Linux/macOS uses .venv/bin/python
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m cnjudbench run-all   --tasks cit_validity,dms_side_effect_intake,tool_fault_recovery   --model mock:gold --out reports/runs/demo
cat reports/runs/demo/report.csv                  # §6.1 paper-table-ready column (solve% is the conservative reading: n/a counts as unsolved)
```

> Run constraint: the package is designed to run from a cloned repository root —
> `tasks/`, `data/public/`, `lawkb/`, `configs/` are repo-root assets and are not
> distributed with the pip package. Run commands from the clone root.

Switch to a real model: `--model openai:<model> --base-url …` (keys only via environment variables); already-generated answers can be replayed with
`--model file:<answers directory>` (the whole pipeline runs on the same API surface, see docs/paper-outline.md §7).
  Before backfilling, always run the answer-alignment guard: `python scripts/check_answer_alignment.py --run-dir <run dir>` (bigram Dice + reverse best-match confirmation; SUSPECT list requires manual review — it has caught two real subagent answer-misalignment incidents).

Paired comparison of two runs (any ranking claim must carry CI and p-values; rankings use the `--preregistered` six-package equal-weight reading):

```bash
# A/B are two real run directories (e.g. reports/runs/ds-flash-v06-full); reports/runs/ is not committed
.venv/Scripts/python -m cnjudbench compare --run-a <run-A> --run-b <run-B>     --preregistered --items-out reports/compare/items.csv
# Output: micro diff±CI + McNemar p; with --preregistered also macro (six-package equal-weight) diff±CI
```

## Full run reference

```bash
# Environment: Python 3.11+, install the package with dev dependencies
# Windows:  py -3.13 -m venv .venv
# Linux/macOS:  python3 -m venv .venv


# Validate task packages and item text (schema + §4.2.1 applicability matrix + lawkb integrity)
python -m cnjudbench validate --items data/public --tasks tasks

# Resolve statute versions by as_of (Appendix D.4: four states + article text)
python -m cnjudbench resolve-law --law 刑法 --article 264 --as-of 2024-06-01

# cit_validity smoke: gold expectations vs parser (no model calls)
python -m cnjudbench smoke-cit-validity

# Machine-checked scoring (P0b): offline gold Mock or OpenAI-compatible endpoint
python -m cnjudbench run --task cit_validity --model mock:gold --out reports/runs/smoke-cit
python -m cnjudbench run-all --tasks cit_validity,u_element_extract,s_charge_subsume --model mock:gold
#   --model openai:<model> --base-url … goes through the real API (keys only via OPENAI_API_KEY / CNJUD_API_KEY env vars)
# Produces reports/runs/<run_id>/summary.json + manifest.json + limits.md (two-decimal percentage; the directory is gitignored)

# Machine check + judge column (P1): --judge mock|openai; tasks without a rubric get judge = n/a (0.00 is forbidden)
python -m cnjudbench run-all --tasks u_element_extract --model mock:gold \
  --with-judge --judge mock --out reports/runs/j1
#   --blend weighted is the only mode that mixes scores (0.7 machine + 0.3 judge); default parallel keeps columns separate

# L2 tool invocation / L3a multi-step (P2): mock:tools replays gold tool trajectories, mock:gold yields exact final answers
python -m cnjudbench run --task tool_search_statute --model mock:tools --out reports/runs/t1
python -m cnjudbench run --task gaia_fee_deadline --model mock:gold --out reports/runs/g1
#   Produces items/<id>.trajectory.json (tool trajectories), hashed into manifest.tools.trajectory_hashes

# P3: contract track / IRAC / long-horizon (L1/L4 machine-checked)
python -m cnjudbench run --task contract_risk --model mock:gold --out reports/runs/c1
python -m cnjudbench run --task a_irac_reason --model mock:gold --out reports/runs/a1
python -m cnjudbench run --task long_horizon_case --model mock:gold --out reports/runs/l4

# P3: τ-Jud multi-turn (run-dialog) — user_seed / model_seed in separate columns, pass^k fixed-user vs swapped-persona
python -m cnjudbench run-dialog --task tau_jud_intake --model mock:dialog \
  --user-seed 42 --k-pass 3 --out reports/runs/tau1
#   summary.stability: pass_k_fixed_user / pass_k_swapped_persona / variance (model|user_script|judge)
#   When the lawyer baseline is missing the report writes "未测" (not measured); fabricating comparisons is forbidden

# CI gate (validate + pytest + mock run-all + artifact assertions + re-run flip rate = 0)
bash scripts/ci_gate.sh          # Windows: powershell -File scripts/ci_gate.ps1
python scripts/flip_rate_check.py --tasks cit_validity --model mock:gold   # recommended API threshold < 5%
```

Mock (`mock:gold`) is zero-network and deterministic; CI only runs Mock; real-API smoke tests are optional.

## Answer backfill and statistical protocol (v0.4)

```bash
# 1) Backfill scoring (no API calls): export prompts → generate answers/<item_id>.txt externally → file: model official scoring
python scripts/export_prompts.py --tasks u_element_extract --run-dir runs/u1
#   (after placing answers under runs/u1/answers/)
python -m cnjudbench run-all --tasks u_element_extract --model file:runs/u1 --out reports/runs/u1-scored

# 2) Flip-rate gate (two runs of the same model, recommended API max-flip 0.05; above the gate → provisional, kept out of formal tables)
python scripts/flip_rate_check.py --tasks u_element_extract --model openai:<model> --max-flip 0.05

# 3) n-gram contamination double check (scans all item text against a corpus, overlap ratio lands in summary.contamination)
python -m cnjudbench run-all --tasks u_element_extract --model mock:gold   --ngram-corpus docs/corpus.txt --ngram-size 8 --out reports/runs/n1

# 4) Paper table generation: the formal table (T-main) only admits provisional=false; everything else goes to appendix T-provisional
python scripts/make_paper_tables.py --runs reports/runs --out docs/paper-tables.md

# 4b) pass^k multi-run aggregation (combinational semantics + bootstrap CI + flip-gate notice, ≥k runs of the same model)
python scripts/aggregate_passk.py --runs reports/runs/ds-a reports/runs/ds-b reports/runs/ds-c   --threshold 100 --out docs/passk-ds.md

# 5) Case-management side-effect task (env_diff end-state diff; d-101..104 ship with a preset open case in state0, d-104 dual-card distraction)
python -m cnjudbench run-all --tasks dms_side_effect_intake --model mock:tools --out reports/runs/dms1

# 6) Human-rating agreement (weighted κ + bootstrap CI + spearman vs machine scores)
python scripts/kappa.py --ratings ratings.csv --machine machine.csv

# 7) Paired comparison (bootstrap CI + McNemar; --preregistered compares only the core six packages, macro = six-package equal weight)
python -m cnjudbench compare --run-a reports/runs/m1 --run-b reports/runs/m2 --preregistered
#   summary.report's solve% is the conservative reading (n/a counts as unsolved), read alongside scored% (n/a excluded)
```

## How a new item is admitted (draft → public)

Drafts go to `data/drafts/` (hard flag `draft: true`, not counted in the MANIFEST) → two isolated real examinees answer (expected error patterns must be empirically triggered, lesson E17) → gold adjudicated under the five-condition policy (docs/gold-adjudication-policy.md §2) → verbatim comparison against official anchor text + text_hash → promoted into the live set and reconciled against the MANIFEST.

> Cross-platform commands: on Windows use `.venv/Scripts/python`; on Linux/macOS the equivalent is `.venv/bin/python` (or plain `python` inside an activated venv).

## How to add a task package

1. Create the three-file set in `tasks/<task_id>/`: `task.yaml` + `predicates.yaml` + `reference.md` (subjective tasks add `rubric.yaml`).  
2. Item text goes into `data/public|holdout|live/*.jsonl`; fields are described in FRAMEWORK Appendix C.  
3. Predicates must obey the §4.2 **output_type closed enum and applicability matrix**; `composite` requires `components`; `hcut` can only be `Cit/Abst/Hall/Cons/Proto`.  
4. Statute anchors use full names + `as_of`, resolved through lawkb multi-version parsing (Appendix D).  
5. Items enter `active` only after schema validation and the Verified state machine.

## 测试 / Tests

```bash
.venv/Scripts/python -m pytest -q
```

## Repository layout

```text
src/cnjudbench/  # package: lawkb parsing / schemas / validate / scale / smoke / predicates / citeguard / adapters / runner / judge / metrics / gates / contamination / report / tools / cli
lawkb/           # statute timeline with multiple versions (generator: scripts/build_min_lawkb.py)
tasks/           # task packages (cit_validity / u_element_extract / s_charge_subsume / tool_search_statute / gaia_fee_deadline)
data/            # public / holdout (ignored) / live
tests/           # pytest
docs/            # research, implementation documents, calibration sets
reports/runs/    # per-run manifest + summary + limits.md + items/*.trajectory.json (gitignored)
```

## Documentation

| File | Description |
|---|---|
| [docs/technical-report.md](docs/technical-report.md) | **Technical report v1** (design, scoring protocol, validity controls, statistical protocol, current results with honest reading) |
| [docs/gold-adjudication-policy.md](docs/gold-adjudication-policy.md) | Gold acceptance and preregistered re-adjudication rules (read before touching gold) |
| [FRAMEWORK.md](FRAMEWORK.md) | Framework design master document (version source of truth, header currently **v0.6**) |
| [docs/DESIGN-benchmark-optimization-v0.4.md](docs/DESIGN-benchmark-optimization-v0.4.md) | Optimization design (benchmark mapping + Sprint A/B/C) |
| [docs/paper-outline.md](docs/paper-outline.md) | Paper skeleton and gap list |
| [index.html](index.html) | Readable score panel (browser preview) |
| [docs/research-notes.md](docs/research-notes.md) | Research round 1: Chinese legal evaluation |
| [docs/research-notes-round2.md](docs/research-notes-round2.md) | Research round 2: coding / agent / engineering hardening |
| [docs/research-notes-round3.md](docs/research-notes-round3.md) | Round 3: anti-reward-hacking scoring and statistical-reading audit ledger (45 dispositions) |
| [docs/lawkb-ingest-queue.md](docs/lawkb-ingest-queue.md) | Statute library verbatim-proofreading intake queue (official text + text_hash) |
| [docs/self-review-new-items-batch4.md](docs/self-review-new-items-batch4.md) | batch4 six items (cit-022..027) self-review and baseline scan, awaiting approval |
| `reports/baseline-report.md` | Baseline distribution and near-perfect-score alerts (R17 leak monitoring, always on) |
| `reports/headroom-report.md` | Item-expansion/pruning headroom report (saturation × rules × empirical p) |
| `reports/repro-inventory.md` | Existence inventory of assets cited by paper-outline |
| [docs/impl-P0a.md](docs/impl-P0a.md) | **P0a implementation doc** (lawkb + validation + smoke task package) |
| [docs/impl-P0b.md](docs/impl-P0b.md) | **P0b implementation doc** (FTP/PTP + CiteGuard + API/Manifest) |
| [docs/impl-P1.md](docs/impl-P1.md) | **P1 implementation doc** (Judge / red lines / gates) |
| [docs/impl-P1-rest.md](docs/impl-P1-rest.md) | **P1 wrap-up** (Judge into runner / CI gate) |
| [docs/impl-P2.md](docs/impl-P2.md) | **P2 implementation doc** (tool sandbox / Tool-Bench / Legal-GAIA) |
| [docs/impl-P3.md](docs/impl-P3.md) | **P3 implementation doc** (τ-Jud / contract track / IRAC / Long-Horizon) |

## Project status

- [x] Design and research (v0.3.1, including external review revisions)
- [x] **P0a implementation doc** (`docs/impl-P0a.md`)
- [x] **P0a code**: lawkb multi-version parsing + item/predicate validation + `cit_validity` smoke (60 tests)
- [x] **P0b implementation doc** (`docs/impl-P0b.md`)
- [x] **P0b code**: FTP/PTP executors + CiteGuard + API adapter (104 tests)
- [x] **P1 implementation doc** (`docs/impl-P1.md`)
- [x] **P1 code**: Judge/Abst/red lines/diagnostic deductions/bootstrap/$/solve/canary (114 tests)
- [x] **P1 wrap-up code**: `--with-judge` into the runner + machine/Judge column split + limits.md + holdout guard + CI gate (133 tests, `scripts/ci_gate` all green)
- [x] **P2 code**: 6-tool sandbox + Legal-Tool-Bench (L2, 19 items, zero score for fabricated calls) + Legal-GAIA curated 10 items (L3a exact + progress) + trajectory hashes into manifest (156 tests)
- [x] **P3 code**: τ-Jud (user_script + end-state F1 + Proto + pass^k dual columns/variance decomposition) + contract track + IRAC + Long-Horizon + `run-dialog` (175 tests)
- [x] **v0.4 Sprint A**: safety/capability column split + status_ladder/fee ladder/must_not + partial-only cardinality + over_refuse×0.50
- [x] **v0.4 statistical protocol**: bootstrap CI / pass^k combinational semantics / report.csv / formal-score provisional gate / n-gram contamination dual check (ci_gate step 7) / random·rules baselines through the same pipeline
- [x] **v0.4 new tasks**: calc_fail_to_pass 46 items (hidden unit-test oracle, five formulas: filing fee / simple interest / periods / semi-annual compounding / preservation fee, hard variants on holiday rollover and caps) + u_element hard subset 28 items — GLM measured 82.1%, see [docs/u-hard-subset-report.md](docs/u-hard-subset-report.md) + dms_side_effect_intake 16 items (env_diff end-state diff; state0 presets an "open case" and dual-card distraction) + tool_fault_recovery 12 items (§5.4 four fault-injection types, recovery×final + R22 nth=2 "success-then-failure" advanced 4 items)
- [x] **v0.4 flip empirics**: GLM examinee mode k=3 retest: per-item pairwise flips 6/11≈55% ≫ 5% gate (docs/u-hard-subset-report.md, appended section) → single-sample runs are always provisional, main tables mandate pass^k
- [x] **v0.4.1 measurement-validity audit**: gold legal-review ablation (same answer re-scored 31.58→86.84, acceptable_articles any-of multi-answer reading) · baseline leak fixes and scan (law_anchors scoring anchors banned from baselines, a_irac random/rules 96→12) · lh-06 anchor temporal fix (inheritance law 10 with repeal window) · lawkb v0.4.1 expansion (12 laws, 51 versions) · v0.4.1 baseline table (random 9.03 / rules 29.25 / mock:gold all-100 on 8 packages, see docs/calc-real-model-report.md §C5) · E12+ element no-name empirical (ah-101..104 still saturated, as_of version selection is the only substantive error cause) · E15 citation bracket false-negative fix (2/29 items wrongly penalized 50→100, trailing brackets stripped on the citation side)
- [x] **v0.5 difficulty restructuring Phase 1+2a+3a+3b+3c+4**: whole-corpus four-level inventory — 38 hard / 88 prune candidates / 143 to test, see [docs/difficulty-audit-v05.md](docs/difficulty-audit-v05.md) · a_irac reduced 32→12 (20 all-saturation items moved to data/archive, 8-subject per-package grid invariant kept) · lawkb adds the SPC [2020] No.15 temporal-effectiveness provisions, 10 articles — 12 laws, 61 versions, Gazette official text + per-article text_hash for after-the-fact verification, source [docs/sources/spc_civil_temporal_2020_gongbao.html](docs/sources/spc_civil_temporal_2020_gongbao.html) · 18 temporal-effectiveness hard items (at-001..018: old/new law transitions 8 / procedure-limitation crossings 5 / private-lending three versions 5, as_of-driven version resolution, negatives verified) · 8 calculation hard variants (cx-001..008: period rollover / limitation interruption / caps and offsets / compounding rivalry, hidden unit-test oracle + trap-value negatives verified) · 10 extraction and tool advanced items (u-044..049 negative-form elements / multi-date + f-105..108 nth=3 fault chains / partial-success state judgment) · 30 practice items (gaia timeline 6 / lh six-domain whole cases 6 / dms deadline monitoring 4 / tau near-deadline intake 4 / contract risk disclosure 6 / document adaptation 4; 4e Judge writing track deferred by risk clause) · Phase 5 dual-isolated examinees ×62 items measured (pass^2=46.77, at/lh/c families discriminate effectively; 4 gold/item-text defects fixed in-loop: at-019 anchor 25→16, at-022 anchor 27→1+acc19, cx-007 expected value 7470→11863.40, tau prompt made explicit; lawkb 61 versions, docs/paper-outline.md §9 E17)
- [ ] To do: DS v0.4 re-run (keys) · holdout freeze execution (protocol ready) · human-rating κ pilot (plan ready) · f-105..108 tool-track real-examinee measurement (needs an API round) · tau real-examinee expansion (v0.6 partial-credit scoring empirically discriminates, see paper-outline E18)

## License

- Code: MIT (see LICENSE).  
- Data / item text / task packages: CC BY 4.0; lawkb statute texts are official works (not subject to copyright protection under Article 5 of the Copyright Law), shipped with sha256 text_hash and source notes (split-license declaration in LICENSE.DATA).
