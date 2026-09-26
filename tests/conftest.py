"""共享夹具：仓库根路径与真实 lawkb 库。"""

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def project_python() -> str:
    """子进程测试用的解释器路径（跨平台）。

    优先项目 venv 两种布局（与 scripts/demo_pipeline.sh 的回退序一致），
    venv 不存在（如 Linux CI 装的是 pip install -e .）时回退当前解释器；
    可用环境变量 CNJUD_TEST_PYTHON 强制指定。
    """
    override = os.environ.get("CNJUD_TEST_PYTHON")
    if override:
        return override
    for cand in (
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",
        REPO_ROOT / ".venv" / "bin" / "python",
    ):
        if cand.is_file():
            return str(cand)
    return sys.executable


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
