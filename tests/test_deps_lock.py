"""deps 锁契约：仓库必须带 requirements-freeze.txt，provisional 门禁才可能放行。"""

from __future__ import annotations

from pathlib import Path

from cnjudbench.runner.manifest import deps_lock_sha256

REPO = Path(__file__).resolve().parent.parent


def test_requirements_freeze_exists_and_is_pinned():
    freeze = REPO / "requirements-freeze.txt"
    assert freeze.is_file(), "依赖冻结件缺失：正式 run 无法过 provisional 门禁"
    pins = [ln.strip() for ln in freeze.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")]
    assert pins, "冻结件为空"
    assert all("==" in ln for ln in pins), f"存在未钉版本的行：{[l for l in pins if '==' not in l]}"


def test_deps_lock_sha256_resolves_in_repo():
    lock = deps_lock_sha256(REPO)
    assert lock is not None and lock.startswith("sha256:")
