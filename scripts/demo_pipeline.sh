#!/usr/bin/env bash
# 评测全管线排练（c304）：单命令走完「导出题面 → 生成答卷 → 换答对齐 guard →
# file: 回灌判分 → 产物核对」。全部本地进行（无 API、无密钥），供评审者与新
# 考生接入方理解数据流；真实考生只把第 2 步换成外部模型按 index.json 回填。
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  if [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe";
  elif [ -x ".venv/bin/python" ]; then PY=".venv/bin/python";
  else PY="python"; fi
fi

WORK="${DEMO_WORK:-$(mktemp -d)}"
# Git Bash 的 /tmp 对原生 python 是无效路径，转 Windows 形式（cygpath 缺失则回退本地目录）
if command -v cygpath >/dev/null 2>&1; then WORK=$(cygpath -m "$WORK");
elif [ ! -d "$WORK" ] || [ "${WORK#/}" != "$WORK" ]; then WORK=.tmp_demo; mkdir -p "$WORK"; fi
PKG="${DEMO_PKG:-u_element_extract}"
echo "== demo pipeline：包 $PKG，工作目录 $WORK =="

echo "== [1/5] 导出题面（prompts/ + index.json + 空 answers/） =="
"$PY" scripts/export_prompts.py --tasks "$PKG" --run-dir "$WORK/run"

echo "== [2/5] 外部考生作答（演示：占位 JSON；真实流程为模型按 index.json 回填） =="
"$PY" - <<PYEOF
import json
from pathlib import Path
run = Path("$WORK/run")
index = json.loads((run / "index.json").read_text(encoding="utf-8"))
assert index, "index.json 为空"
for entry in index:
    (run / entry["answer_file"]).write_text(
        json.dumps({"note": "demo answer; replace with model output"},
                   ensure_ascii=False),
        encoding="utf-8")
print(f"answers 回填 {len(index)} 份（演示占位）")
PYEOF

echo "== [3/5] 换答对齐 guard（bigram Dice + 反向确认；已两次抓到答案错位） =="
"$PY" scripts/check_answer_alignment.py --run-dir "$WORK/run"

echo "== [4/5] file: 回灌判分（与真实 API 跑法完全同管线） =="
"$PY" -m cnjudbench run --task "$PKG" --model "file:$WORK/run/answers" --out "$WORK/scored"

echo "== [5/5] 产物核对（manifest/summary/limits + report.csv + schema_version） =="
for f in manifest.json summary.json limits.md report.csv; do
  test -f "$WORK/scored/$f"
done
"$PY" - <<PYEOF
import json
from pathlib import Path
s = json.loads(Path("$WORK/scored/summary.json").read_text(encoding="utf-8"))
assert s["schema_version"] == "0.6"
print(f"scored tasks={len(s.get('tasks', {}))} schema={s['schema_version']} "
      f"（演示占位答案 0 分属预期，流程即目的）")
PYEOF

echo "DEMO PIPELINE: OK（产物在 $WORK/scored；真实考生复用 1/3/4/5 步）"
