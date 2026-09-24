"""R21：换答检测 guard——合成换答 fixture 必须命中，干净 run 必须放行。

真实事故背景：R14（a-010/a-011）与 R20（a-001/a-002）两次 subagent 考生
把答案写错文件位，污染题分与 flip 统计。guard 原理：扣除模板公共 bigram 后
做 prompt↔answer 差分 Dice，own 非最优且余量超阈值即嫌疑；双向确认
（互为最优）为强信号。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "check_answer_alignment.py"

_PROMPT_BOILER = "你是法律分析师。就下列争点输出 IRAC JSON：\n" \
    '{"issue": "<争点>", "rule_law": "<法名>", "rule_article": "<条号>",\n' \
    ' "application": "<适用分析要点>", "conclusion": "<结论>",\n' \
    ' "citations": [{"law": "...", "article": "..."}]}\n' \
    "不得编造案例；结论不得作绝对保证。"


def _make_run(tmp_path: Path, items: list[tuple[str, str]], answer_of: dict[str, str]) -> Path:
    """items: (id, 题面特异正文)；answer_of: id→实际作答的题 id（模拟换答）。"""
    run = tmp_path / "run"
    (run / "prompts").mkdir(parents=True)
    (run / "answers").mkdir(parents=True)
    index = []
    for iid, body in items:
        (run / "prompts" / f"t__{iid}.txt").write_text(_PROMPT_BOILER + body, encoding="utf-8")
        index.append({"task_id": "t", "item_id": iid, "prompt_file": f"prompts/t__{iid}.txt",
                      "answer_file": f"answers/{iid}.txt", "prompt_chars": 1})
    for iid, _ in items:
        src = answer_of[iid]
        body = next(b for j, b in items if j == src)
        (run / "answers" / f"{iid}.txt").write_text(
            json.dumps({"issue": body[:12], "application": body}, ensure_ascii=False),
            encoding="utf-8",
        )
    (run / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    return run


def _guard(run: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), "--run-dir", str(run)],
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def test_guard_catches_direct_swap(tmp_path):
    """两题答案互换（互为最优、双向确认成立）必须阻断。"""
    items = [
        ("x1", "争点：未签书面劳动合同的双倍工资如何主张？劳动合同法第八十二条二倍工资。"),
        ("x2", "争点：软件著作权侵权赔偿如何计算？著作权法第五十四条实际损失与法定赔偿。"),
        ("x3", "争点：案外人执行异议之诉中排除执行的权益认定。民诉法第二百三十四条。"),
    ]
    run = _make_run(tmp_path, items, answer_of={"x1": "x2", "x2": "x1", "x3": "x3"})
    r = _guard(run)
    assert r.returncode == 1, r.stdout
    assert "x1" in r.stdout and "x2" in r.stdout and "成立" in r.stdout


def test_guard_passes_aligned_run(tmp_path):
    """对位正确的 run 必须放行。"""
    items = [
        ("y1", "争点：未签书面劳动合同的双倍工资如何主张？劳动合同法第八十二条二倍工资。"),
        ("y2", "争点：软件著作权侵权赔偿如何计算？著作权法第五十四条实际损失与法定赔偿。"),
    ]
    run = _make_run(tmp_path, items, answer_of={"y1": "y1", "y2": "y2"})
    r = _guard(run)
    assert r.returncode == 0, r.stdout


def test_guard_reports_missing_answer(tmp_path):
    items = [("z1", "争点：逾期还款违约责任。民法典第五百七十七条违约责任。")]
    run = _make_run(tmp_path, items, answer_of={"z1": "z1"})
    (run / "answers" / "z1.txt").unlink()
    r = _guard(run)
    assert r.returncode == 1 and "missing" in r.stdout


def test_guard_one_way_suspect_reports_but_does_not_block(tmp_path):
    """c394：单向嫌疑（mutual 不成立）默认报告不阻断——短答案噪声曾致 35%
    误报阻断正常回灌；--strict 恢复全部阻断。真实换答（双向）仍被阻断。

    构造：i1 的答案是模板化短文（own 极低），i2 的答案里混入 i1 题面特异词
    （best_other 超阈），但 i2 自己的 prompt 仍最亲自己的答案 → mutual=False。"""
    run = tmp_path / "run"
    (run / "prompts").mkdir(parents=True)
    (run / "answers").mkdir(parents=True)
    bodies = {
        "i1": "争点：甲与乙就合同解除权行使期限发生争议，合同法第九十五条约定解除权消灭。",
        "i2": "争点：软件著作权侵权赔偿如何计算？著作权法第五十四条实际损失与法定赔偿。",
        "i3": "争点：案外人执行异议之诉中排除执行的权益认定。民诉法第二百三十四条。",
    }
    answers = {
        "i1": "本案尚需补充事实与证据材料，暂无法出具结论性意见，建议进一步咨询。",
        "i2": "软件著作权侵权赔偿按实际损失与法定赔偿计算；另，合同解除权行使期限问题不在本题范围。",
        "i3": "案外人执行异议之诉须审查其对执行标的是否享有足以排除强制执行的民事权益。",
    }
    index = []
    for iid, body in bodies.items():
        (run / "prompts" / f"t__{iid}.txt").write_text(_PROMPT_BOILER + body, encoding="utf-8")
        (run / "answers" / f"{iid}.txt").write_text(
            json.dumps({"issue": "案件咨询", "application": answers[iid]}, ensure_ascii=False),
            encoding="utf-8")
        index.append({"task_id": "t", "item_id": iid, "prompt_file": f"prompts/t__{iid}.txt",
                      "answer_file": f"answers/{iid}.txt", "prompt_chars": 1})
    (run / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")

    r = _guard(run)
    assert r.returncode == 0, r.stdout
    assert "i1" in r.stdout, "单向嫌疑仍须报告供人工复核"
    r2 = subprocess.run([sys.executable, str(SCRIPT), "--run-dir", str(run), "--strict"],
                        capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    assert r2.returncode == 1, r2.stdout
