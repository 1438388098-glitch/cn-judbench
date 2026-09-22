# s_charge_subsume · 参考解与金样构造规则

## 金样结构

`gold = {"charge": 罪名, "elements": [构成要件...], "defendant_name": 姓名}`。

- `charge`：唯一罪名；`field` 谓词 `on_fail: zero`（错罪名一票否决）。
- `elements`：要件集合；`element` 谓词按集合 F1 折减基数。
- `citations` 由模型给出，经 CiteGuard 与 `law_anchors` 对比（存在/条号/时效）。
- `defendant_name`：输入原样给出；`field_keep` 篡改 → cap_50。

## 判分语义（P0b 执行器）

- 罪名错 → 0.00；引用不覆盖锚点或引用已失效版本 → 0.00（statute zero）；
- 禁引《治安管理处罚法》作为刑事依据 → cap_50；
- 要件缺漏 → F1 折减；被告名改写 → cap_50。

## 构造纪律

1. 只用 lawkb 已入库条文的真实犯罪案例型（264/263/266/234/253之一/205之一/291之二）。
2. `as_of` 与案发时点一致；同一罪名可跨修法时点出题（如 253之一 2009/2015 版）。
3. 要件用规范表述（如「非法占有目的」「数额较大」），避免同义改写歧义。
