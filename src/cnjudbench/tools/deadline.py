"""期间计算（民诉法期间规则的最小确定性子集）。

- 起算：期间开始之日不计入，自下一日起算（民诉法 §201 类推）→
  ``deadline = start + days``；
- 届满末日为周六/周日的，顺延至其后第一个工作日（法定节假日夹具不支持，
  金样只锁周末规则——limits 已声明受控环境）；
- ``days`` 与 ``type`` 二选一：type 走常见期间表，days 显式覆盖。
"""

from __future__ import annotations

from datetime import date, timedelta

TYPE_TABLE: dict[str, int] = {
    "民事上诉": 15,
    "刑事上诉": 10,
    "答辩": 15,
    "举证": 30,
    "申请再审": 180,
    "申请执行": 730,
}


def calc_deadline(*, store, start: str, days: int | None = None, type: str | None = None) -> dict:
    d0 = date.fromisoformat(start)
    if (days is None) == (type is None):
        raise ValueError("days 与 type 必须二选一")
    n = int(days) if days is not None else TYPE_TABLE[type]
    if n <= 0:
        raise ValueError("days 必须为正")
    d = d0 + timedelta(days=n)
    rolled = False
    while d.weekday() >= 5:  # 5=Sat 6=Sun
        d += timedelta(days=1)
        rolled = True
    return {
        "start": start,
        "days": n,
        "type": type,
        "deadline": d.isoformat(),
        "weekend_rolled": rolled,
    }
