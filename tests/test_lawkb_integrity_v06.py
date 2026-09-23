# -*- coding: utf-8 -*-
"""R9 入库纪律机检（c182/c183/c184）：

- c182 lawkb 每版本 text_hash == sha256(text/*.txt 实际字节)；
- c183 text/*.txt 无 BOM、无 CRLF（与官方源逐字节可比的前提）；
- c184 题面 canary 全库唯一且带 CNJB-CANARY- 前缀（串题会让 L0 扫描误伤）。
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

from cnjudbench.lawkb.store import LawkbStore

REPO = Path(__file__).resolve().parents[1]


def test_c182_text_hash_matches_files():
    store = LawkbStore.load(REPO / "lawkb")
    assert len(store.versions) >= 60
    for vid, v in store.versions.items():
        raw = (REPO / "lawkb" / v.text_ref).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == v.text_hash.removeprefix("sha256:"), (
            f"{vid}: text_hash 与 {v.text_ref} 实际内容不一致——手改文本必须重算 hash")


def test_c183_lawkb_text_encoding_discipline():
    texts = sorted((REPO / "lawkb" / "text").glob("*.txt"))
    assert len(texts) >= 60
    for p in texts:
        raw = p.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{p.name}: 带 UTF-8 BOM"
        assert b"\r\n" not in raw, f"{p.name}: 混入 CRLF 换行"


def test_c184_canary_unique_and_prefixed():
    seen: list[str] = []
    for f in sorted((REPO / "data" / "public").glob("*.jsonl")):
        for ln in f.read_text(encoding="utf-8-sig").splitlines():
            if ln.strip():
                seen.append(json.loads(ln)["canary"])
    dupes = [c for c, n in Counter(seen).items() if n > 1]
    assert not dupes, f"canary 重复: {dupes[:5]}"
    bad = [c for c in seen if not str(c).startswith("CNJB-CANARY-")]
    assert not bad, f"canary 缺前缀: {bad[:5]}"
