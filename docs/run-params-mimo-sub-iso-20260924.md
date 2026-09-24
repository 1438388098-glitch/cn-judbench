# run-params: mimo-sub-iso-20260924

{
  "run_id": "mimo-sub-iso-20260924",
  "model": "general subagent (isolated, Read/Write only)",
  "revision": "inherit default model",
  "isolation": "100% isolated via 10 parallel general subagents + 2 redo subagents; 245/245 answers by subagent Read/Write only",
  "tasks": [
    "cit_validity",
    "s_charge_subsume",
    "contract_risk",
    "long_horizon_case",
    "a_irac_reason",
    "u_element_extract",
    "gaia_fee_deadline",
    "calc_fail_to_pass"
  ],
  "n_items": 245,
  "n_capability": 238,
  "n_safety": 7,
  "harness": "8d89995",
  "lawkb": "lawkb-2026.09.2",
  "grand_eq": 62.8,
  "grand_w": 71.26,
  "hard": 68.74,
  "hard_ci95": [
    62.76,
    74.32
  ],
  "safety": 0.0,
  "provisional": true,
  "provisional_reasons": [
    "check_answer_alignment exit code 1 (46 SUSPECT, short JSON template false positives confirmed by sampling)",
    "a_irac_reason reward_hacking_alert (diag_diff_raw=18.97)",
    "no flip analysis yet"
  ],
  "contamination": "none detected",
  "est_cost_usd": null,
  "flip": "TBD (needs --with-judge or flip_rate_check)",
  "baseline_comparison": "ds-flash-v06-full (clean API): grand_eq 68.72 / hard 76.31 / flip 0%",
  "per_task": {
    "cit_validity": {
      "n": 27,
      "mean": 74.07,
      "hard": 58.33,
      "n_hard": 12
    },
    "s_charge_subsume": {
      "n_capability": 13,
      "mean": 52.31,
      "n_safety": 7,
      "safety": 0.0,
      "hard": 53.33
    },
    "contract_risk": {
      "n": 23,
      "mean": 26.74,
      "hard": 33.47,
      "n_hard": 14
    },
    "long_horizon_case": {
      "n": 15,
      "mean": 31.02,
      "hard": 31.02,
      "n_hard": 15
    },
    "a_irac_reason": {
      "n": 34,
      "mean": 57.35,
      "hard": 54.69,
      "n_hard": 32
    },
    "u_element_extract": {
      "n": 49,
      "mean": 82.65,
      "hard": 75.0,
      "n_hard": 34
    },
    "gaia_fee_deadline": {
      "n": 23,
      "mean": 78.26
    },
    "calc_fail_to_pass": {
      "n": 54,
      "mean": 100.0
    }
  },
  "artifacts": {
    "prompts": "reports/runs/mimo-sub-iso-20260924/prompts/",
    "answers": "reports/runs/mimo-sub-iso-20260924/answers/",
    "scored": "reports/runs/mimo-sub-iso-20260924-scored/",
    "alignment": "reports/runs/mimo-sub-iso-20260924/alignment-suspects.json",
    "assigns": "reports/runs/mimo-sub-iso-20260924/assign-{1..10}.json",
    "redo": "reports/runs/mimo-sub-iso-20260924/redo-{1,2}.json"
  }
}
