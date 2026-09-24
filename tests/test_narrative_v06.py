# -*- coding:utf-8 -*-
"""R27 论文叙述与公开面板一致性机检（c351-c355）。

E20（判分器对抗性审计+零漂移）进提纲后，叙述、表格、框架头部、公开
面板四处须互锁；公开面板的题量数字与 MANIFEST 对齐（46→54 类漂移再红）。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

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


def test_c389_no_js_degradation():
    """c389：无 JS 时页面不得失明——藏匿态须 html.js 门控 + noscript 降级提示。"""
    html = _read("index.html")
    assert "document.documentElement.classList.add" in html, "缺 html.js 标记内联脚本"
    assert "<noscript>" in html and "run-score-ledger" in html, "缺 noscript 降级提示"
    css = _read("styles.css")
    # c409：藏匿必须是 :not(.is-in) 形式——裸 html.js .rank-row（0,2,1）会反超
    # .rank-row.is-in（0,2,0），真实浏览器榜单曾因此永久隐藏（视觉验收实测）
    assert "html.js .reveal:not(.is-in)" in css and "html.js .rank-row:not(.is-in)" in css, \
        "opacity 藏匿未用 html.js + :not(.is-in) 门控"
    assert "\n.reveal {" not in "\n" + css, "裸 .reveal 藏匿仍在"


def test_c391_panel_models_match_ledger_main_board():
    """c391/c416：面板数据块与总账互锁——MODELS 主记分板逐行、THINK_COMPARISONS
    与 SAFETY_CARDS 映射到对应 run 的 grand/safety。面板数据是手工内嵌、
    ledger 是唯一汇总账——任何一侧手改数字都会悄悄说谎。"""
    ledger = _read("docs", "run-score-ledger.md")
    ledger_rows = re.findall(
        r"^\| \d+ \| `([a-z0-9\-]+)` \|[^\n]*?\| (?:洁净隔离|API 隔离) \| \*{0,2}(\d+\.\d{2})\*{0,2} \|",
        ledger, re.M)
    assert len(ledger_rows) == 13, f"主记分板应 13 行，实得 {len(ledger_rows)}"
    js = _read("app.js")
    panel_rows = re.findall(
        r'run:\s*"([a-z0-9\-]+)"[\s\S]*?grand_eq:\s*(\d+\.?\d*)', js)
    panel = dict(panel_rows)
    assert len(panel_rows) == 13, f"面板应 13 个模型，实得 {len(panel_rows)}"
    panel_safety = dict(re.findall(
        r'run:\s*"([a-z0-9\-]+)"[\s\S]*?safety:\s*(\d+\.?\d*)', js))
    assert len(panel_safety) == 13
    assert {r for r, _ in ledger_rows} == set(panel), (
        f"面板与总账 run 集合不一致：仅账={ {r for r, _ in ledger_rows} - set(panel) } "
        f"仅面板={ set(panel) - {r for r, _ in ledger_rows} }")
    for run, grand in ledger_rows:
        assert abs(float(panel[run]) - float(grand)) < 1e-9, \
            f"{run} 总分账实不符：ledger={grand} app.js={panel[run]}"

    # c416：思考对照点值 == 对应 run 的 grand_eq（映射错/值漂移即红）
    think = re.findall(
        r'\{ label: "([^"]+)", value: (\d+\.?\d*) \}', js)
    think_by_label = {}
    for label, value in think:
        think_by_label.setdefault(label, []).append(float(value))
    for label, run in (("思考默认继承", "glm53f-iso-scored"),
                       ("思考低", "glm53f-low-iso-20260924-scored"),
                       ("思考高", "glm53f-hi-iso-0924-scored"),
                       ("思考高", "db21lite-iso-0924-scored")):
        expected = float(panel[run])
        assert expected in think_by_label.get(label, []), \
            f"思考对照 {label} 缺 {run} 的 {expected}（对照点与账不符）"
    assert 65.67 in think_by_label.get("思考低", []), "豆包 Lite 思考低 flip 定分 65.67 应在对照"

    # c416：安全卡 score == 对应 run 的 safety_score
    safety_cards = re.findall(r'name: "([^"]+)",\s*\n\s*score: (\d+\.?\d*)', js)
    card_to_run = {
        "MiMo-V2.6-Pro": "mimo-sub-iso-scored",
        "GLM-5.3-Flash（思考高）": "glm53f-hi-iso-0924-scored",
        "豆包2.1 Pro（思考高）": "db21pro-iso-0924-scored",
        "MiniMax-M3": "minimax-m3-iso-20260924-scored",
        "MiMo（20260924b）": "mimo-sub-iso-20260924b-scored",
        "GLM-5.3-Flash（思考低）": "glm53f-low-iso-20260924-scored",
        "GLM-5.3-Flash（思考默认继承）": "glm53f-iso-scored",
        "豆包 2.1 Lite（思考低）": "doubao21lite-flip-20260924-scored",
    }
    assert len(safety_cards) >= 8, f"安全卡应 ≥8 张，实得 {len(safety_cards)}"
    for name, score in safety_cards:
        run = card_to_run.get(name)
        if run is None:
            continue  # 未映射的新卡提示人工补充映射，不在机检内猜测
        assert abs(float(score) - float(panel_safety.get(run, -1))) < 1e-9, \
            f"安全卡 {name} 分值 {score} 与 {run} safety {panel_safety.get(run)} 不符"
        # 拒对数与分值自洽（7 题制：71.43≈5/7、100=7/7、0=0/7）
        slots_m = re.search(
            re.escape(f'name: "{name}"') + r"[\s\S]*?slots: \[([0-9, ]+)\]", js)
        if slots_m:
            n_ok = sum(int(x) for x in slots_m.group(1).split(",") if x.strip())
            assert abs(n_ok / 7 * 100 - float(score)) < 0.01, \
                f"安全卡 {name} slots 拒对数 {n_ok}/7 与分值 {score} 不自洽"


def test_c398_panel_models_block_regenerable():
    """c398：面板 MODELS 块必须等于 gen_panel_models.py 再生结果。

    数字来自各 *-scored/summary.json、身份来自 ledger §1——手工改动任何一处
    都会被 --check 打回（reports/runs 缺失的新环境自然跳过不了，这是本地机检）。"""
    if not (ROOT / "reports" / "runs").is_dir():
        pytest.skip("reports/runs 缺失（新 clone）")
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "gen_panel_models.py"), "--check"],
        cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
