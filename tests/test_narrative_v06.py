# -*- coding:utf-8 -*-
"""R27 论文叙述与公开面板一致性机检（c351-c355）。

E20（判分器对抗性审计+零漂移）进提纲后，叙述、表格、框架头部、公开
面板四处须互锁；公开面板的题量数字与 MANIFEST 对齐（46→54 类漂移再红）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def test_c351_e20_反自证审计节齐备():
    outline = _read("docs", "paper-outline.md")
    assert "### E20" in outline
    for kw in ("时效自证", "极性对冲", "拒绝误判", "零漂移", "candidate-331/346"):
        assert kw in outline, f"E20 缺关键词: {kw}"
    assert "§E20" in outline, "T5 表行须挂 E20 指向"


def test_c352_framework_头部_含判效三修复():
    fw = _read("FRAMEWORK.md")
    assert "c322 as_of 强制题面反自证" in fw
    assert "判分改动→基线重导纪律" in fw


def test_c353_readme_不硬编码精确测试计数():
    readme = _read("README.md")
    m = re.search(r"(\S+)\s*项测试全绿", readme)
    assert m, "README 须保留测试行"
    assert m.group(1).endswith("+"), \
        f"README 测试计数须用模糊表述（如 550+），现为 {m.group(1)!r}"


def test_c354_index_html_包题数与_MANIFEST_一致():
    man = json.loads((ROOT / "data" / "public" / "MANIFEST.json")
                     .read_text(encoding="utf-8"))
    html = _read("index.html")
    n_calc = man["packages"]["calc_fail_to_pass"]["n_items"]
    assert f"calc_fail_to_pass {n_calc} 题" in html, \
        f"公开面板 calc 题数与 MANIFEST（{n_calc}）不一致"


def test_c355_paper_numbers_覆盖_E20_两翼():
    pn = _read("docs", "paper-numbers.md")
    assert "c322-c324" in pn and "零漂移" in pn, \
        "E20 两翼（修复组行 + 零漂移行）须在对账表登记"
