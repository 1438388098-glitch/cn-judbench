"""cit_validity 冒烟端到端：真实题面 + 真实 lawkb（P0a DoD 3/4）。"""

from pathlib import Path

from cnjudbench.lawkb.resolve import slice_union_hash
from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.smoke import run_smoke
from cnjudbench.validate.items import validate_items_dir
from cnjudbench.validate.tasks import validate_task_dir

REPO = Path(__file__).resolve().parents[1]
ITEMS = REPO / "data" / "public" / "cit_validity.jsonl"
TASKS = REPO / "tasks"


def test_task_package_passes_validation():
    assert validate_task_dir(TASKS / "cit_validity") == []


def test_items_pass_validation(store):
    errors = validate_items_dir(ITEMS, TASKS)
    assert errors == [], errors


def test_smoke_all_match_and_covers_five_statuses(lawkb_root: Path):
    store = LawkbStore.load(lawkb_root)
    report = run_smoke(ITEMS, store)
    assert report.rows, "冒烟未读到任何题"
    assert report.all_match, [
        (r.item_id, r.expect_status, r.actual_status) for r in report.rows if not r.ok
    ]
    assert len(report.distinct_statuses) >= 5  # DoD：覆盖至少 5 种 resolve status
    assert report.slice_union_hash and report.slice_union_hash.startswith("sha256:")


def test_slice_union_hash_deterministic(lawkb_root: Path):
    store = LawkbStore.load(lawkb_root)
    h1 = run_smoke(ITEMS, store).slice_union_hash
    h2 = run_smoke(ITEMS, store).slice_union_hash
    assert h1 == h2
    assert h1 != slice_union_hash([])  # 空 run 的 hash 与非空不同
