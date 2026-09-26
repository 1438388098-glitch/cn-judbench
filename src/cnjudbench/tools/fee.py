"""诉讼费计算（《诉讼费用交纳办法》2007，官方文本见 lawkb fee_13_2007）。

- 财产案件：§13(一) 累进费率（1 万以下 50 元起，分段累加）；
- 离婚案件：§13(二)1 每件 50–300 元，受控口径取上限 300（金样既有口径）；
  涉及财产分割的，``amount`` 即财产总额：不超过 20 万元不另行交纳，
  超过 20 万元的部分按 0.5% 交纳；
- 劳动案件：§13(二)3 外的 §13(四) 10 元。
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
DIVORCE_FEE_CAP = 300.0          # §13(二)1 区间 50–300 受控取上限
DIVORCE_PROPERTY_THRESHOLD = 200_000.0  # 财产分割：超过 20 万部分 0.5%
DIVORCE_PROPERTY_RATE = 0.005
FIXED: dict[str, float] = {"劳动案件": 10.0}


def calc_fee(*, store, amount: float, type: str = "财产案件",
             property_amount: float | None = None) -> dict:
    amt = float(amount)
    if amt <= 0:
        raise ValueError("amount 必须为正")
    extra: dict = {}
    if type == "离婚案件":
        # 涉及财产分割：amount 即财产总额；显式 property_amount 优先
        prop = float(property_amount) if property_amount is not None else amt
        if prop < 0:
            raise ValueError("property_amount 不能为负")
        fee = DIVORCE_FEE_CAP
        if prop > DIVORCE_PROPERTY_THRESHOLD:
            fee += (prop - DIVORCE_PROPERTY_THRESHOLD) * DIVORCE_PROPERTY_RATE
        extra["property_amount"] = prop
    elif type in FIXED:
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
    return {"amount": amt, "type": type, **extra, "fee": int(fee + 0.5)}
