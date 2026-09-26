# -*- coding: utf-8 -*-
"""测试卫生机检：测试套件自身不得引入跨平台/跑脏仓库类缺陷。

- 禁止硬编码项目 venv 解释器路径（Linux CI 无 .venv，必 FileNotFoundError）；
  子进程一律用 tests/conftest.py::project_python()。
"""

from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent

# Path 拼接式（".venv" / "Scripts" ...）与完整字面路径两种形态；forward-slash 的
# 文档正则（如 test_judge_na_discipline 解析 README 命令行）与路径过滤元组不受限。
FORBIDDEN = '".venv" /', '.venv/Scripts/python.exe'


def test_no_hardcoded_venv_interpreter():
    offenders: list[str] = []
    for p in sorted(TESTS_DIR.glob("test_*.py")):
        if p.name == Path(__file__).name:  # 本文件持有禁用模式清单，排除自身
            continue
        text = p.read_text(encoding="utf-8")
        hit = [pat for pat in FORBIDDEN if pat in text]
        if hit:
            offenders.append(f"{p.name}: {hit}")
    assert not offenders, (
        "测试硬编码 venv 解释器，Linux CI 必炸；请改用 conftest.project_python()：\n"
        + "\n".join(offenders)
    )
