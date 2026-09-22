"""P3：user_script schema 与 L3b 任务包校验。"""

from __future__ import annotations

import pytest
import yaml

from cnjudbench.schemas.user_script import UserScript, assert_no_gold_leak
from cnjudbench.validate.tasks import validate_task_dir


def test_user_script_requires_personas_and_sampling():
    with pytest.raises(Exception):
        UserScript.model_validate({"script_id": "x", "personas": [], "sampling": "fixed_order"})
    ok = UserScript.model_validate({
        "script_id": "us",
        "personas": [{"id": "p1", "tone": "冷静"}],
        "turn_budget": 4,
        "sampling": "fixed_order",
    })
    assert ok.seed_key == "user_seed"


def test_assert_no_gold_leak_flags_literal():
    script = UserScript.model_validate({
        "script_id": "leak",
        "personas": [{"id": "p1", "tone": "普通"}],
        "sampling": "fixed_order",
        "turns": ["请按 matter_type=民间借贷 整理"],
    })
    errs = assert_no_gold_leak(script, ["民间借贷"])
    assert errs


def test_tau_jud_package_has_user_scripts(repo_root):
    errors = validate_task_dir(repo_root / "tasks" / "tau_jud_intake")
    assert errors == []
    us = repo_root / "tasks" / "tau_jud_intake" / "user_scripts" / "us-intake-01.yaml"
    script = UserScript.model_validate(yaml.safe_load(us.read_text(encoding="utf-8")))
    assert script.personas and script.sampling
