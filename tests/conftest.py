"""共享夹具：仓库根路径与真实 lawkb 库。"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def lawkb_root(repo_root: Path) -> Path:
    return repo_root / "lawkb"


@pytest.fixture(scope="session")
def store(lawkb_root: Path):
    from cnjudbench.lawkb.store import LawkbStore

    return LawkbStore.load(lawkb_root)
