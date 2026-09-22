"""诉讼费计算（《诉讼费用交纳办法》2007 财产案件累进 + 两类固定简化）。

- 财产案件：§13 累进费率（1 万以下 50 元起，分段累加）；
- 离婚案件：简化为固定 300 元（办法为 50–300 区间，金样取上限并注明）；
- 劳动案件：10 元。
金额非正数 → ValueError（工具业务性失败，沙箱记档不抛）。
"""

from __future__ import annotations

# (段上限, 该段费率)；首段为 1 万以下固定 50 元
_BRACKETS: list[tuple[float, float]] = [
    (10_000, 0.0),
    (100_000, 0.025),
    (200_000, 0.02),
    (500_000, 0.015),
    (1_000_000, 0.01),
    (2_000_000, 0.009),
    (5_000_000, 0.008),
    (10_000_000, 0.007),
    (20_000_000, 0.006),
    (float("inf"), 0.005),
]
BASE_FEE = 50.0
FIXED: dict[str, float] = {"离婚案件": 300.0, "劳动案件": 10.0}


def calc_fee(*, store, amount: float, type: str = "财产案件") -> dict:
    amt = float(amount)
    if amt <= 0:
        raise ValueError("amount 必须为正")
    if type in FIXED:
        fee = FIXED[type]
    elif type == "财产案件":
        fee = BASE_FEE
        prev = _BRACKETS[0][0]
        for cap, rate in _BRACKETS[1:]:
            if amt > prev:
                fee += (min(amt, cap) - prev) * rate
            prev = cap
    else:
        raise ValueError(f"未知案件类型: {type!r}")
    # 分以下四舍五入到元（办法按元计）
    return {"amount": amt, "type": type, "fee": int(fee + 0.5)}
