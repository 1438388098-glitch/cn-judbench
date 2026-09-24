# -*- coding: utf-8 -*-
"""R10 发布物一致性机检（c193/c194）：

- c193 lawkb/VERSION == LawkbStore.store_version == MANIFEST.lawkb_store_version
  （三处来源，复现者据此取库版本，不同步即拿错库）；
- c194 taxonomy 权威字典值域守卫：判分模块中的失败分类标签必须 ⊆
  cnjudbench.taxonomy.TAXONOMY（对齐 capabilities.py 先例，防论文错误
  分类表口径漂移）。
"""

import json
import re
from pathlib import Path

from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.taxonomy import TAXONOMY

REPO = Path(__file__).resolve().parents[1]


def test_c193_lawkb_version_three_way_consistency():
    file_version = (REPO / "lawkb" / "VERSION").read_text(encoding="utf-8").strip()
    store = LawkbStore.load(REPO / "lawkb")
    man = json.loads((REPO / "data" / "public" / "MANIFEST.json")
                     .read_text(encoding="utf-8"))
    assert file_version == store.store_version == man["lawkb_store_version"]


def test_c194_taxonomy_literals_within_authority():
    # 扫描判分链路模块里 taxonomy 赋值/取默认值的字符串字面量（紧贴引号，
    # 避免吃进变量名）；extra.get("fail_taxonomy", "tag") 形态单独匹配
    targets = sorted((REPO / "src" / "cnjudbench" / "predicates").glob("*.py"))
    targets += [REPO / "src" / "cnjudbench" / "runner" / "evaluate.py",
                REPO / "src" / "cnjudbench" / "citeguard" / "check.py",
                REPO / "src" / "cnjudbench" / "dialog" / "session.py",
                REPO / "src" / "cnjudbench" / "dialog" / "proto.py"]
    pat = re.compile(
        r'(?:failure_)?taxonomy\s*=\s*(?:None if [^,\n]*?else )?"([a-z_]+)"'
        r'|"fail_taxonomy",\s*\n?\s*"([a-z_]+)"')
    used: dict[str, list[str]] = {}
    for p in targets:
        for m in pat.finditer(p.read_text(encoding="utf-8")):
            tag = m.group(1) or m.group(2)
            if tag:
                used.setdefault(tag, []).append(p.name)
    assert used, "未扫描到任何 taxonomy 字面量——正则或模块路径变了，请修测试"
    unknown = {t: files for t, files in used.items() if t not in TAXONOMY}
    assert not unknown, f"taxonomy 未登记（taxonomy.py 为权威）: {unknown}"


def test_c405_dialog_taxonomy_channel_aligned():
    """c405：dialog 侧 taxonomy 通道纳入 c194 扫描面；未登记 over_refuse 禁用。"""
    session_src = (REPO / "src" / "cnjudbench" / "dialog" / "session.py").read_text(encoding="utf-8")
    assert '"over_refuse"' not in session_src,         "dialog taxonomy 不得使用未登记字面量 over_refuse（应拒未拒归 over_promise 通道）"
    tax = (REPO / "src" / "cnjudbench" / "taxonomy.py").read_text(encoding="utf-8")
    assert '"over_refuse"' not in tax, "先登记 taxonomy 再使用"
