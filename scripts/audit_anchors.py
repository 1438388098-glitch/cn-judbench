# -*- coding: utf-8 -*-
"""锚×as_of 审计（E14 脚本化，进 ci_gate 第 8 步）。

逐题扫描 law_anchors 与 gold.citations 里的 {law, article, as_of}，经
lawkb.resolve_article 解析：
- ok                    → 通过；
- unknown_in_lawkb / unresolved_law → 惰性锚，必须出现在白名单（否则判失败）——
  库外锚不扣分但必须显式登记，防「金样锚在库外/时点错」事故类（曾咬人 4 次：
  lh-06 / at-019 / at-022 / cx-007 同族）；
- ambiguous_versions / wrong_vintage / not_yet_effective / not_effective_on_as_of
  → 硬失败（金样时点语义错误，须修 gold）。

用法：
  python scripts/audit_anchors.py                       # 审计（CI 模式）
  python scripts/audit_anchors.py --update              # 重新生成白名单
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cnjudbench.lawkb.resolve import resolve_article  # noqa: E402
from cnjudbench.lawkb.store import LawkbStore  # noqa: E402

WHITELIST_PATH = REPO / "reports" / "anchor-whitelist.json"

HARD_FAIL = {
    "ambiguous_versions", "wrong_vintage",
    "not_yet_effective", "not_effective_on_as_of",
}


def _bump_date_if_same(old_payload: dict, new_anchors: dict, today: str) -> str:
    """c140 幂等：anchors 内容未变时沿用原 updated 日期（文件字节不变）。"""
    if old_payload.get("anchors") == new_anchors and old_payload.get("updated"):
        return old_payload["updated"]
    return today


def _anchors_of(item: dict):
    """收集题内全部锚引用：(来源, law, article, as_of)。"""
    out = []
    for a in item.get("law_anchors") or []:
        as_of = a.get("effective_on") or a.get("as_of") or item.get("as_of")
        if a.get("law") and a.get("article") and as_of:
            out.append(("law_anchors", a["law"], str(a["article"]), str(as_of)))
    gold = item.get("gold") or {}
    cits = gold.get("citations") if isinstance(gold, dict) else None
    for c in cits or []:
        as_of = c.get("as_of") or c.get("effective_on") or item.get("as_of")
        if c.get("law") and c.get("article") and as_of:
            out.append(("gold.citations", c["law"], str(c["article"]), str(as_of)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--items-root", default=str(REPO / "data" / "public"))
    ap.add_argument("--lawkb", default=str(REPO / "lawkb"))
    ap.add_argument("--update", action="store_true", help="重新生成惰性锚白名单")
    args = ap.parse_args()

    store = LawkbStore.load(Path(args.lawkb))
    items_root = Path(args.items_root)
    lazy: dict[str, list[str]] = defaultdict(list)   # key → item ids
    hard_failures: list[str] = []
    n_items = n_anchors = 0

    for path in sorted(items_root.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            n_items += 1
            for src, law, article, as_of in _anchors_of(item):
                n_anchors += 1
                r = resolve_article(law, article, date.fromisoformat(as_of), store)
                if r.status == "ok":
                    continue
                key = f"{law}#{article}"
                if r.status in HARD_FAIL:
                    hard_failures.append(
                        f"{item['id']} [{src}] {law}#{article}@{as_of} → {r.status}")
                else:  # unknown_in_lawkb / unresolved_law → 惰性锚
                    lazy[key].append(item["id"])

    if args.update:
        # c140 幂等：anchors 内容未变时保留原 updated 日期（内容相同则整文件
        # 字节不变），避免每日 --update 产生仅日期行的 diff 噪声
        new_anchors = {k: sorted(set(v)) for k, v in sorted(lazy.items())}
        old = {}
        if WHITELIST_PATH.is_file():
            try:
                old = json.loads(WHITELIST_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                old = {}
        updated = _bump_date_if_same(old, new_anchors, date.today().isoformat())
        payload = json.dumps({
            "note": "惰性锚白名单：库外 lawkb 锚显式登记（audit_anchors.py --update 生成）",
            "updated": updated,
            "anchors": new_anchors,
        }, ensure_ascii=False, indent=1)
        if WHITELIST_PATH.is_file() and WHITELIST_PATH.read_text(encoding="utf-8") == payload:
            print(f"whitelist unchanged: {WHITELIST_PATH} ({len(lazy)} keys)")
            return 0
        WHITELIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        WHITELIST_PATH.write_text(payload, encoding="utf-8")
        print(f"whitelist written: {WHITELIST_PATH} ({len(lazy)} keys)")
        return 0

    wl: dict = {}
    if WHITELIST_PATH.is_file():
        wl = json.loads(WHITELIST_PATH.read_text(encoding="utf-8")).get("anchors", {})

    unregistered = {k: v for k, v in lazy.items() if k not in wl}
    print(f"audit_anchors: {n_items} items / {n_anchors} anchors; "
          f"lazy={len(lazy)} (whitelisted={len(lazy) - len(unregistered)})")

    for f in hard_failures:
        print(f"HARD FAIL: {f}")
    for k, ids in sorted(unregistered.items()):
        print(f"UNREGISTERED lazy anchor: {k} → {sorted(set(ids))[:5]}")

    if hard_failures or unregistered:
        print("audit_anchors: FAIL")
        return 1
    print("audit_anchors: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
