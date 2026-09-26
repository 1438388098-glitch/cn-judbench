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


def _pins() -> dict[str, str]:
    freeze = REPO / "requirements-freeze.txt"
    out: dict[str, str] = {}
    for ln in freeze.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and "==" in ln:
            name, _, ver = ln.partition("==")
            out[name.lower().replace("_", "-")] = ver
    return out


def test_freeze_covers_runtime_deps_and_satisfies_lower_bounds():
    """round-7（c435）：freeze 是正式 run 的依赖口径，必须与 pyproject 声明同源——
    运行时依赖逐个在场，且钉版满足 pyproject 下界（防 CI 装 .[dev] 与正式
    口径静默分叉，复现者按 freeze 装环境得到不同判分行为）。"""
    import tomllib

    pins = _pins()
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    deps = pyproject["project"]["dependencies"]
    assert deps, "pyproject 运行时依赖为空"
    for dep in deps:
        name = dep.split(";")[0]
        req_name, _, spec = name.partition(">=")
        req_name = req_name.strip().lower().replace("_", "-").split("[")[0]
        assert req_name in pins, f"freeze 缺运行时依赖 {req_name}（复现口径不完整）"
        if spec:
            lower = spec.strip().lstrip(">=")
            got = tuple(int(x) for x in pins[req_name].split(".")[:3])
            want = tuple(int(x) for x in lower.split(".")[:3])
            assert got >= want, f"freeze 钉版 {req_name}=={pins[req_name]} 低于 pyproject 下界 {lower}"
