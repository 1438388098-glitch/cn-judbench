# -*- coding: utf-8 -*-
"""R17 口径一致与发布标配机检（c262/c263/c266-c271）：

- c262 预注册六包合计题数：FRAMEWORK/paper-outline 文档 == MANIFEST 实数
  （batch4 增题后文档曾停在 162，实际 168——论文口径级勘误的回归守卫）；
- c263 providers profiles 价目键 ⊆ PRICE_TABLE（缺价目应显式 null 而非
  指向不存在的键导致 est_cost 静默退化）；
- c266 baseline_report --warn 阈值参数行为（warn=0 → 全量警告）；
- c267 openai_compat err_text 截断透传（1113 余额类排障依赖）；
- c268 reasoning_effort/thinking 注入 payload 与缓存键隔离；
- c269 .autopilot/ 与 reports/runs/ 不入库策略留档；
- c270 runner 退出码语义（单题 n/a 是有效结果，不影响整批完成）；
- c271 dataset-card 题数行 == MANIFEST n_items_total。
"""

import io
import json
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]


def test_c262_core_six_count_docs_match_manifest():
    man = json.loads((REPO / "data" / "public" / "MANIFEST.json")
                     .read_text(encoding="utf-8"))
    core = ["cit_validity", "u_element_extract", "s_charge_subsume",
            "contract_risk", "a_irac_reason", "long_horizon_case"]
    total = sum(int(man["packages"][p]["n_items"]) for p in core)
    assert total == 168, f"六包题数变化({total})时须同步勘误两处文档口径"
    for doc in ("FRAMEWORK.md", "docs/paper-outline.md"):
        text = (REPO / doc).read_text(encoding="utf-8")
        assert f"合计 {total} 题" in text, f"{doc} 未对齐六包合计 {total}"
        assert "合计 162 题" not in text, f"{doc} 残留旧数 162"


def test_c263_profile_price_keys_known():
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.runner.account import PRICE_TABLE

    cfg = yaml.safe_load((REPO / "configs" / "providers.yaml")
                         .read_text(encoding="utf-8-sig")) or {}
    unknown = []
    for pname, pcfg in cfg.items():
        for mname, ment in (pcfg.get("models") or {}).items():
            pk = (ment or {}).get("price_key")
            if pk is not None and pk not in PRICE_TABLE:
                unknown.append(f"{pname}:{mname} -> {pk}")
    assert not unknown, (
        "providers.yaml 引用了 PRICE_TABLE 缺失的价目键（est_cost 将静默为 null）："
        + ", ".join(unknown)
    )


def test_c266_baseline_report_warn_threshold(tmp_path):
    sys.path.insert(0, str(REPO / "scripts"))
    import baseline_report as agg

    out = agg.OUT
    original = out.read_bytes() if out.is_file() else None
    old = sys.argv
    sys.argv = ["baseline_report.py", "--warn", "0"]
    try:
        assert agg.main() == 0
        text = out.read_text(encoding="utf-8")
        assert "- ⚠ " in text  # warn=0 → 每个基线分都进警告（全量列出）
        assert "无：全部基线分 < 0" not in text
    finally:
        sys.argv = old
        if original is not None:
            out.write_bytes(original)
        elif out.is_file():
            out.unlink()


def test_c267_err_text_truncated_into_adapter_error(monkeypatch):
    from cnjudbench.adapters import openai_compat as oc

    body = b'{"error": {"code": "1113"}}' + b"x" * 500

    def _urlopen(req, timeout=None):
        raise oc.urllib.error.HTTPError(req.full_url, 429, "too many requests",
                                        {}, io.BytesIO(body))

    monkeypatch.setattr(oc.time, "sleep", lambda _s: None)
    monkeypatch.setattr(oc.urllib.request, "urlopen", _urlopen)
    ad = oc.OpenAICompatAdapter(model="m", api_key="k", cache_dir=None)
    try:
        ad.complete("hi")
        raise AssertionError("持续 429 应抛 AdapterError")
    except oc.AdapterError as e:
        msg = str(e)
        assert "1113" in msg and "too many requests" in msg  # 错误体透传
        assert msg.count("x") <= 300  # 截断在 300 字符内（防日志爆炸）


def test_c268_thinking_params_injected(monkeypatch):
    from cnjudbench.adapters import openai_compat as oc

    seen = {}

    class _Resp:
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "ok"},
                                            "finish_reason": "stop"}],
                               "usage": {}}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def _urlopen(req, timeout=None):
        seen["body"] = json.loads(req.data)
        return _Resp()

    monkeypatch.setattr(oc.urllib.request, "urlopen", _urlopen)
    ad_effort = oc.OpenAICompatAdapter(model="m", api_key="k", cache_dir=None,
                                       reasoning_effort="high")
    ad_effort.complete("hi")
    assert seen["body"]["reasoning_effort"] == "high"

    ad_think = oc.OpenAICompatAdapter(model="m", api_key="k", cache_dir=None,
                                      thinking={"type": "enabled"})
    ad_think.complete("hi")
    assert seen["body"]["thinking"] == {"type": "enabled"}


def test_c269_gitignore_excludes_workspace_state():
    gi = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert ".autopilot/" in gi and "reports/runs/" in gi
    for rel in (".autopilot/state.json", ".autopilot/backlog.json",
                "reports/runs/baseline-v06/summary.json"):
        r = subprocess.run(["git", "check-ignore", rel], cwd=REPO,
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        assert r.returncode == 0, f"{rel} 未被忽略"


def test_c270_na_item_does_not_break_batch(store):
    """截断题 → n/a 是有效结果：run_tasks 正常完成，其余题不受牵连
    （CLI rc=0 语义的 runner 层等价物：n/a 只进报告、不当作崩溃）。"""
    from cnjudbench.adapters.mock import MockAdapter, mock_gold_adapter
    from cnjudbench.runner.evaluate import run_tasks

    class _Trunc(MockAdapter):
        def complete(self, prompt, *, temperature=0.0, seed=None):
            r = super().complete(prompt, temperature=temperature, seed=seed)
            return replace(r, finish_reason="length")

    def factory(item):
        if item.id == "u-001":
            return _Trunc(lambda _p: "{}")
        return mock_gold_adapter(item, store)

    runs = run_tasks([("u_element_extract", REPO / "tasks" / "u_element_extract",
                       REPO / "data" / "public" / "u_element_extract.jsonl")],
                     factory, store)
    (run,) = runs
    na = [r for r in run.results if r.score is None]
    assert len(na) == 1 and na[0].item_id == "u-001"
    assert run.mean is not None  # 其余题照常计分


def test_c271_dataset_card_count_matches_manifest():
    man = json.loads((REPO / "data" / "public" / "MANIFEST.json")
                     .read_text(encoding="utf-8"))
    card = (REPO / "docs" / "dataset-card.md").read_text(encoding="utf-8")
    m = re.search(r"共 \*\*(\d+) 题\*\*", card)
    assert m, "dataset-card 缺「共 N 题」总数行"
    assert int(m.group(1)) == man["n_items_total"]
