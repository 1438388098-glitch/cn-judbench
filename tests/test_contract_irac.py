"""P3：合同轨 / IRAC 机检与 score–time AUC 金样。"""

from __future__ import annotations

from pathlib import Path

from cnjudbench.metrics.variance import score_time_auc
from cnjudbench.runner.evaluate import evaluate_item, load_task_package
from cnjudbench.adapters.mock import mock_gold_adapter
from cnjudbench.validate.items import load_items_file


def test_score_time_auc_golden():
    # 梯形：[(0,0),(1,1)] → 0.5 → 50.00；[(0,0),(0.5,0.5),(1,1)] → 0.5 → 50
    assert abs(score_time_auc([(0.0, 0.0), (1.0, 1.0)]) - 50.0) < 1e-6
    assert abs(score_time_auc([(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)]) - 50.0) < 1e-6
    # 满分折线 [(0,1),(1,1)] → 100
    assert abs(score_time_auc([(0.0, 1.0), (1.0, 1.0)]) - 100.0) < 1e-6
    assert score_time_auc([]) is None


def test_contract_irac_mock_scores(repo_root: Path, store):
    from cnjudbench.runner.evaluate import _resolve_predicates

    for tid, items_name in (
        ("contract_risk", "contract_risk.jsonl"),
        ("a_irac_reason", "a_irac_reason.jsonl"),
    ):
        task_dir = repo_root / "tasks" / tid
        task, preds = load_task_package(task_dir)
        rows = load_items_file(repo_root / "data" / "public" / items_name)
        for _ln, item in rows:
            ipreds = _resolve_predicates(item, task_dir, preds)
            r = evaluate_item(task, ipreds, item, mock_gold_adapter(item, store), store)
            assert r.score is not None, (tid, item.id, r.error)
            # a-008 为应拒题（predicates_refuse），其余应接近满分（partial 允许非 100）
            if item.id == "a-008":
                assert r.score == 100.0, (r.display, r.predicate_lines)
            else:
                assert r.score >= 50.0, (item.id, r.display, r.predicate_lines)
