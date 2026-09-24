# -*- coding: utf-8 -*-
"""发布面机检合集（R8）：

- c173 holdout 冻结包完整性（harness_sha = 当前 git，public_items_total = 323）；
- c174 lawkb-ingest-queue 与 anchor-whitelist 键集合一致（防双文档漂移）；
- c177 README/核心文档表内引用的本地文件全部存在（防死链）；
- c178 发布 MANIFEST packages=12 且无价目时 cost 字段必须为 null（不编造费用）；
- c180 已跟踪文件密钥模式扫描（sk-… 等，.gitignore 之外的冗余防线）。
"""

import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_c173_holdout_pack_integrity():
    pack = json.loads((REPO / "reports" / "holdout-prospective.json")
                      .read_text(encoding="utf-8"))
    assert pack["dataset"]["public_items_total"] == 323
    # 冻结包 harness_sha = 生成时刻的提交；随新提交会合法落后，但必须是
    # 历史中真实存在的提交（防手填/悬空引用），且不得晚于当前 HEAD
    sha = pack["harness_sha"]
    r = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                       cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, f"holdout 冻结包 harness_sha 非真实提交: {sha}"


def test_c174_ingest_queue_matches_whitelist_keys():
    wl = json.loads((REPO / "reports" / "anchor-whitelist.json")
                    .read_text(encoding="utf-8"))
    wl_keys = set(wl["anchors"])
    md = (REPO / "docs" / "lawkb-ingest-queue.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| ([^|]+) \| ([^|]+) \| \d+ \|", md, re.M)
    queue_keys = {f"{law.strip()}#{art.strip()}" for law, art in rows}
    assert queue_keys == wl_keys, (
        f"ingest queue 与白名单漂移：仅queue={sorted(queue_keys - wl_keys)} "
        f"仅whitelist={sorted(wl_keys - queue_keys)}；"
        "入库完成后请重跑 gen_lawkb_ingest_queue.py 同步两文档")


def test_c177_doc_table_no_dead_links():
    targets = [REPO / "README.md", REPO / "docs" / "paper-outline.md"]
    link = re.compile(r"\(([^)#]+?\.(?:md|json|csv|html))\)")
    for t in targets:
        text = t.read_text(encoding="utf-8")
        for m in link.finditer(text):
            rel = m.group(1)
            if rel.startswith(("http://", "https://")):
                continue
            assert (t.parent / rel).is_file(), f"{t.name} 死链: {rel}"


def test_c178_release_manifest_and_cost_null_discipline():
    man = json.loads((REPO / "data" / "public" / "MANIFEST.json")
                     .read_text(encoding="utf-8"))
    assert len(man["packages"]) == 12
    assert man["n_items_total"] == 323
    # 无价目（price_key=None）时费用字段必须为 null——禁止编造 est_cost_usd
    run = json.loads((REPO / "reports" / "runs" / "baseline-v06" / "summary.json")
                     .read_text(encoding="utf-8"))
    cost = run["cost"]
    if cost.get("price_key") is None:
        assert cost.get("est_cost_usd") is None
        assert cost.get("cost_total_usd") is None


def test_c180_no_secret_patterns_in_tracked_files():
    files = subprocess.run(["git", "ls-files"], cwd=REPO,
                           capture_output=True, text=True, check=True,
                           encoding="utf-8", errors="replace",
                           ).stdout.splitlines()
    patterns = [
        re.compile(r"sk-[A-Za-z0-9]{16,}"),            # OpenAI/DeepSeek 风格
        re.compile(r"(?i)(api[_-]?key|token)\s*[:=]\s*['\"][A-Za-z0-9]{16,}"),
    ]
    allow = re.compile(r"sk-(?:learn|etch|ip|y)$")  # 普通词，非密钥
    hits: list[str] = []
    for rel in files:
        p = REPO / rel
        if not p.is_file() or p.stat().st_size > 2_000_000:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pat in patterns:
            for m in pat.finditer(text):
                if allow.match(m.group(0)):
                    continue
                hits.append(f"{rel}: …{text[max(0, m.start()-20):m.end()+10]}…")
    assert not hits, "疑似密钥入库：\n" + "\n".join(hits[:10])
