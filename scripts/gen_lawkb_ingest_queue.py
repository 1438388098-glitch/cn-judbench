# -*- coding: utf-8 -*-
"""c156：惰性锚入库队列生成器。

读 audit_anchors 的白名单（lazy=库外锚），产出 docs/lawkb-ingest-queue.md：
每行 = 法名×条号×影响题数×拟取版本×核验状态。入库纪律（gold-adjudication
-policy §4 / FRAMEWORK lawkb 节）：官方文本（国家法律法规数据库/最高法官网）
逐字比对后才可入库，每条附 text_hash 供事后核验；未逐字校对的文本不入库。

用法： python scripts/gen_lawkb_ingest_queue.py
"""
from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WHITELIST = ROOT / "reports" / "anchor-whitelist.json"
OUT = ROOT / "docs" / "lawkb-ingest-queue.md"

# 拟取版本：按法名给默认官方来源与版本线索（须人工到官方源逐字校对后入库）
SOURCE_HINTS = {
    "诉讼费用交纳办法": ("国务院令第481号（2007-04-01 施行）", "国家法律法规数据库"),
    "治安管理处罚条例": ("已被治安管理处罚法取代（2006-03-01）——入库仅为其废止窗口", "国家法律法规数据库"),
    "中华人民共和国民法典": ("2020-05-28 通过，2021-01-01 施行", "国家法律法规数据库"),
    "中华人民共和国民事诉讼法": ("2021 修正（2022-01-01 施行）/ 2023 修正（2024-01-01）", "国家法律法规数据库"),
    "中华人民共和国刑事诉讼法": ("2018 修正（2018-10-26）", "国家法律法规数据库"),
    "中华人民共和国刑法": ("1997 刑法 + 历次修正案（按条文版本）", "国家法律法规数据库"),
    "中华人民共和国担保法": ("1995-10-01 施行，2021-01-01 随民法典废止——入库为其废止窗口", "国家法律法规数据库"),
}


def main() -> int:
    wl = json.loads(WHITELIST.read_text(encoding="utf-8"))
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                             check=True, cwd=ROOT).stdout.decode().strip()
    except Exception:  # noqa: BLE001
        sha = "unknown"

    rows = []
    for key in sorted(wl.get("anchors", {})):
        law, _, article = key.partition("#")
        ids = wl["anchors"][key]
        hint = SOURCE_HINTS.get(law, ("（待补版本线索）", "国家法律法规数据库 / 最高法官网"))
        rows.append((law, article, len(ids), ", ".join(ids[:6]) + ("…" if len(ids) > 6 else ""), hint))

    lines = [
        "# lawkb 惰性锚入库队列（自动生成，勿手改；`scripts/gen_lawkb_ingest_queue.py`）",
        "",
        f"> 生成：{date.today().isoformat()} · harness={sha} · 锚白名单共 "
        f"{len(rows)} 键（lazy：库内暂无法条版本、不扣分但显式登记）。",
        "> 入库纪律：仅收官方文本（国家法律法规数据库 flk.npc.gov.cn / 最高法官网），",
        "> 逐字比对后写入 lawkb/laws + lawkb/text，附 text_hash；无法逐字校对的文本不入库。",
        "",
        "| 法名 | 条号 | 影响题数 | 影响题（样例） | 拟取版本 | 官方来源 | 核验状态 |",
        "|---|---|---|---|---|---|---|",
    ]
    for law, article, n, ids, (ver, src) in rows:
        lines.append(f"| {law} | {article} | {n} | {ids} | {ver} | {src} | ⬜ 待逐字校对 |")
    lines += [
        "",
        "## 优先级建议",
        "",
        "1. **诉讼费用交纳办法 13/14 条**（影响 45 题，最大簇）：诉讼费用计算是 calc/gaia",
        "   两包金样的判定依据，入库后可把 statute 三检从「惰性跳过」升级为真实核验；",
        "2. **民事诉讼法 122/126/128/171/246 条**：多包共用管辖/期间/上诉条文；",
        "3. **担保法 19 条 / 治安管理处罚条例 19 条**：仅废止窗口价值，随对偶题入库；",
        "4. **民法典 1/201/680/1260 条**：民法典已入库 27 条文版本，补条文即可。",
        "",
        "状态标记：⬜ 待逐字校对 → 🔄 校对中 → ✅ 已入库（附 text_hash + commit）。",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"written: {OUT} ({len(rows)} keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
