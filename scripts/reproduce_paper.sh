#!/usr/bin/env bash
# 论文金样数字一键复现（c278）：
#   1) E18 预注册比较双口径 + E17 pass^2 金样（pytest 锁定值核对）；
#   2) 难度校准审计（作者标注 vs 实证通过率，输出 reports/difficulty_emp.json）；
#   3) 组合 pass^k 报表（剔除饱和对照）。
# 依赖：本地存在 .venv 与 reports/runs/v05new-*（第三方克隆会跳过 2/3 并提示）。
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  if [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe";
  elif [ -x ".venv/bin/python" ]; then PY=".venv/bin/python";
  else PY="python"; fi
fi

echo "== [1/3] 金样数字核对（E18 双口径 / E17 pass^2）=="
"$PY" -m pytest tests/test_e18_repro_golden_v06.py tests/test_passk_golden_v06.py -q

if [ -d reports/runs/v05new-s1m-score ] && [ -d reports/runs/v05new-s2m-score ]; then
  echo "== [2/3] 难度校准审计 =="
  "$PY" scripts/calibrate_difficulty.py \
    --runs reports/runs/v05new-s1m-score reports/runs/v05new-s2m-score
  echo "== [3/3] pass^k 报表（剔除饱和）=="
  "$PY" scripts/aggregate_passk.py \
    --runs reports/runs/v05new-s1m-score reports/runs/v05new-s2m-score \
    --exclude-saturation --out reports/passk-repro.md
else
  echo "== [2/3][3/3] 跳过：缺少 reports/runs/v05new-s{1,2}m-score 考生运行目录 =="
  echo "   （金样数字已由 [1/3] 的 pytest 锁定核对；报表生成本地考生数据）"
fi

echo "REPRODUCE: OK（数字与 docs/paper-outline.md §实验 口径一致）"
