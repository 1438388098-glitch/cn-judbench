from pathlib import Path
import json

root = Path(r"C:/Users/20579/XiaomiMiMoProjects/2026-09-22/ai-benchmark-subagent-github")
d = json.loads((root / "dashboard-data.json").read_text(encoding="utf-8"))
(root / "dashboard-data.js").write_text(
    "window.CNJB_DATA=" + json.dumps(d, ensure_ascii=False) + ";\n",
    encoding="utf-8",
)

app = root / "app.js"
t = app.read_text(encoding="utf-8")
old = (
    "  /** 演示排名：模型 × 思考强度。机检/Judge 分列，百分制两位小数。 */\n"
    "  const MODELS = ["
)
new = """  /** 真实评测：window.CNJB_DATA（sync_dashboard.py 自动替换）；无则演示。 */
  const REAL = typeof window !== "undefined" ? window.CNJB_DATA : null;
  const MODELS = REAL
    ? [{
        id: "ds-flash",
        name: REAL.model_id || "deepseek-flash",
        vendor: "DeepSeek",
        note: (REAL.condition && REAL.condition.note) || "真实 run · 机检分",
        scores: {
          low: { machine: (REAL.overview && REAL.overview.equal_weight) || 0, judge: null, cost: 0, p95: 0, dims: REAL.dims || [] },
          mid: { machine: (REAL.overview && REAL.overview.equal_weight) || 0, judge: null, cost: 0, p95: 0, dims: REAL.dims || [] },
          high: { machine: (REAL.overview && REAL.overview.equal_weight) || 0, judge: null, cost: 0, p95: 0, dims: REAL.dims || [] },
        },
      }]
    : ["""
if old not in t:
    raise SystemExit("anchor missing in app.js")
app.write_text(t.replace(old, new, 1), encoding="utf-8")
print("patched app.js + wrote dashboard-data.js")
