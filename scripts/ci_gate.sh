#!/usr/bin/env bash
# CI 门禁（impl-P1-rest §5）：validate → pytest → mock run-all → 产物断言 → 翻转率=0。
# 任一步失败即 exit 1。CI 只跑 Mock，不烧真 API、不需要任何密钥。
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python}"

echo "== [1/5] validate =="
"$PY" -m cnjudbench validate --items data/public --tasks tasks

echo "== [2/5] pytest =="
"$PY" -m pytest -q

echo "== [3/5] run-all (mock:gold, with-judge) =="
"$PY" -m cnjudbench run-all \
  --tasks cit_validity,u_element_extract,s_charge_subsume \
  --model mock:gold --with-judge --judge mock \
  --out reports/runs/ci

echo "== [4/5] assert run gate =="
"$PY" scripts/assert_run_gate.py reports/runs/ci

echo "== [5/5] flip rate (mock 必须 0) =="
"$PY" scripts/flip_rate_check.py

echo "CI GATE: ALL GREEN"
