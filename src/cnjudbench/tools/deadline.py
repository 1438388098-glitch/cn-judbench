"""期间计算（民诉法期间规则的最小确定性子集）。

- 起算：期间开始之日不计入，自下一日起算（民诉法 §201 类推）→
  ``deadline = start + days``；
- 届满末日为周六/周日的，顺延至其后第一个工作日（法定节假日夹具不支持，
  金样只锁周末规则——limits 已声明受控环境）；
- ``days`` 与 ``type`` 二选一：日数期间走 DAY_TABLE，月/年期间走
  PERIOD_TABLE（历法月加法、月末钳制，不做固定天数折算——民诉法 §212
  申请再审六个月、§250 申请执行二年；闰年跨度 730 天近似法曾差一日，
  见金样 2022-08-01+二年=2024-08-01）。
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta

DAY_TABLE: dict[str, int] = {
    "民事上诉": 15,
    "刑事上诉": 10,
    "答辩": 15,
    "举证": 30,
}

# (单位, 数量)：历法加法，月末钳制（如 8-31 + 6 个月 = 2-29/2-28）
PERIOD_TABLE: dict[str, tuple[str, int]] = {
    "申请再审": ("months", 6),
    "申请执行": ("months", 24),  # 二年
}


def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def calc_deadline(*, store, start: str, days: int | None = None, type: str | None = None) -> dict:
    d0 = date.fromisoformat(start)
    if (days is None) == (type is None):
        raise ValueError("days 与 type 必须二选一")
    if days is not None:
        n = int(days)
        if n <= 0:
            raise ValueError("days 必须为正")
        d = d0 + timedelta(days=n)
        period = {"days": n}
    else:
        if type not in DAY_TABLE and type not in PERIOD_TABLE:
            raise ValueError(f"未知期间类型: {type!r}")
        if type in DAY_TABLE:
            n = DAY_TABLE[type]
            d = d0 + timedelta(days=n)
            period = {"days": n}
        else:
            unit, n = PERIOD_TABLE[type]
            d = _add_months(d0, n) if unit == "months" else d0
            period = {"months": n}
    rolled = False
    while d.weekday() >= 5:  # 5=Sat 6=Sun
        d += timedelta(days=1)
        rolled = True
    return {
        "start": start,
        "type": type,
        **period,
        "deadline": d.isoformat(),
        "weekend_rolled": rolled,
    }
