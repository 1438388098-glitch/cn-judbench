"""FTP/PTP 谓词单测：正/负例、on_fail 四态、合成顺序（zero 优先于 cap）。

上下文基于真实 lawkb（刑法 264）+ 合成题面，覆盖 impl-P0b §3 全部谓词。
"""

import pytest

from cnjudbench.citeguard.check import check_claim
from cnjudbench.citeguard.extract import extract_claims
from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.predicates.base import EvalContext, PredicateError
from cnjudbench.predicates.registry import compose_score, evaluate_predicates
from cnjudbench.schemas.item import Item
from cnjudbench.schemas.task import PredicatesFile, TaskManifest


def mk_item(gold, law="中华人民共和国刑法", article="264", as_of="2024-06-01",
            output_type="structured"):
    return Item.model_validate({
        "id": "t-001", "task_id": "t", "capability": "S", "difficulty": 1,
        "interaction": "L1", "roles": ["judge"], "domain": "criminal",
        "output_type": output_type,
        "hcut": ["Cit"], "instruction": "作答", "input": "题干",
        "gold": gold,
        "law_anchors": [{"law": law, "article": article}],
        "as_of": as_of,
        "canary": "CNJB-CANARY-0001", "split": "public",
        "contamination_risk": "low", "source": "synthetic",
    })


def mk_task(output_type="structured"):
    return TaskManifest.model_validate({
        "task_id": "t", "capability": "S", "interaction": "L1",
        "output_type": output_type, "oracle": "exact",
        "prompt_template": "回答：{input}",
    })


def mk_ctx(store: LawkbStore, answer, item, task, as_of=None):
    """按 evaluate_item 同样的链路构造上下文（claim 用自带 as_of，缺省回落题面）。"""
    text = answer if isinstance(answer, str) else ""
    from cnjudbench.citeguard.extract import parse_answer_json

    parsed = answer if not isinstance(answer, str) else parse_answer_json(answer)
    ex = extract_claims(parsed, task.output_type, text)
    checks = [
        check_claim(c, store, as_of=c.as_of or (as_of or item.as_of.isoformat()))
        for c in ex.claims
    ]
    return EvalContext(
        task=task, item=item, answer=parsed, answer_text=text,
        claims=ex.claims, claim_status=ex.status, store=store, checks=checks,
    )


def run_pred(store, spec, answer, item=None, task=None):
    preds = PredicatesFile.model_validate({"ftp": [spec]})
    it = item or mk_item(gold={"status": "ok"})
    tk = task or mk_task()
    ftp_r, ptp_r, _ = evaluate_predicates(mk_ctx(store, answer, it, tk), preds)
    return ftp_r[0]


def run_ptp(store, spec, answer, item=None, task=None):
    preds = PredicatesFile.model_validate({"ftp": [{"type": "field", "path": "x"}],
                                           "ptp": [spec]})
    it = item or mk_item(gold={"status": "ok"})
    tk = task or mk_task()
    ftp_r, ptp_r, _ = evaluate_predicates(mk_ctx(store, answer, it, tk), preds)
    return ptp_r[0]


# ---------- field ----------

def test_field_hit_and_miss(store):
    spec = {"type": "field", "path": "status", "gold_path": "0.expect_status",
            "fail_taxonomy": "wrong_article", "on_fail": "zero"}
    item = mk_item(gold=[{"expect_status": "ok"}])
    ok = run_pred(store, spec, {"status": "ok"}, item=item)
    bad = run_pred(store, spec, {"status": "not_yet_effective"}, item=item)
    assert ok.passed and ok.pass_ratio == 1.0 and ok.failure_taxonomy is None
    assert not bad.passed and bad.pass_ratio == 0.0
    assert bad.failure_taxonomy == "wrong_article"


def test_field_alias_table(store):
    spec = {"type": "field", "path": "verdict",
            "aliases": {"有罪": ["guilty", "有罪"]}, "on_fail": "zero"}
    item = mk_item(gold={"verdict": "有罪"})
    assert run_pred(store, spec, {"verdict": "guilty"}, item=item).passed


# ---------- amount / deadline ----------

def test_amount_tolerance(store):
    item = mk_item(gold={"amount": 100000})
    exact = run_pred(store, {"type": "amount", "path": "amount", "on_fail": "partial"},
                     {"amount": "100,000元"}, item=item)
    within = run_pred(store, {"type": "amount", "path": "amount", "tolerance": 0.5,
                              "on_fail": "partial"}, {"amount": 100000.5}, item=item)
    outside = run_pred(store, {"type": "amount", "path": "amount", "tolerance": 0.5,
                               "on_fail": "partial"}, {"amount": 100002}, item=item)
    assert exact.passed and within.passed and not outside.passed


def test_deadline_iso(store):
    item = mk_item(gold={"date": "2022-05-01"})
    assert run_pred(store, {"type": "deadline", "path": "date", "on_fail": "partial"},
                    {"date": "2022-05-01"}, item=item).passed
    assert not run_pred(store, {"type": "deadline", "path": "date", "on_fail": "partial"},
                        {"date": "2022年5月1日"}, item=item).passed


# ---------- element（F1） ----------

def test_element_partial_f1(store):
    spec = {"type": "element", "path": "elements", "on_fail": "partial"}
    item = mk_item(gold={"elements": ["从建筑物抛掷物品", "情节严重"]})
    full = run_pred(store, spec, {"elements": ["从建筑物抛掷物品", "情节严重"]}, item=item)
    half = run_pred(store, spec, {"elements": ["从建筑物抛掷物品"]}, item=item)
    miss = run_pred(store, spec, {"elements": ["答非所问"]}, item=item)
    assert full.passed and full.pass_ratio == 1.0
    assert 0.0 < half.pass_ratio < 1.0 and not half.passed
    assert half.failure_taxonomy == "element_miss"
    assert miss.pass_ratio == 0.0


# ---------- statute ----------

def test_statute_cover_and_missing(store):
    spec = {"type": "statute", "on_fail": "zero"}
    item = mk_item(gold={"charge": "x"})
    ok = run_pred(store, spec, {"charge": "x",
                                "citations": [{"law": "刑法", "article": "264",
                                               "as_of": "2024-06-01"}]}, item=item)
    none = run_pred(store, spec, {"charge": "x"}, item=item)  # structured 缺引用 = miss_retrieve
    assert ok.passed and ok.pass_ratio == 1.0
    assert not none.passed and none.failure_taxonomy == "miss_retrieve"


def test_statute_wrong_article_and_stale(store):
    spec = {"type": "statute", "on_fail": "zero"}
    item = mk_item(gold={"charge": "x"}, article="264", as_of="2024-06-01")
    wrong = run_pred(store, spec, {"citations": [{"law": "刑法", "article": "263",
                                                  "as_of": "2024-06-01"}]}, item=item)
    stale = run_pred(store, spec, {"citations": [{"law": "刑法", "article": "264",
                                                  "as_of": "1990-01-01"}]}, item=item)
    assert wrong.failure_taxonomy == "wrong_article"
    assert stale.failure_taxonomy == "stale_statute"


def test_statute_gen_degrades_but_structured_does_not(store):
    spec = {"type": "statute", "on_fail": "zero"}
    item = mk_item(gold={"charge": "x"})
    gen_task = mk_task(output_type="gen")
    # gen 自由文本：claim 抽不到 → 降级 rubric gate（§4.2 脚注）
    gen_ctx = EvalContext(task=gen_task, item=item, answer=None,
                          answer_text="纯文本无引用", claims=[],
                          claim_status="claim_extract_miss", store=store)
    (gen_r, _, _) = evaluate_predicates(gen_ctx,
                                        PredicatesFile.model_validate({"ftp": [spec]}))
    assert gen_r[0].passed
    # structured 缺引用：不降级，按 miss_retrieve 判
    st_item = mk_item(gold={"charge": "x"})
    st_task = mk_task(output_type="structured")
    st_ctx = EvalContext(task=st_task, item=st_item, answer={"charge": "x"},
                         answer_text="", claims=[], claim_status="claim_extract_miss",
                         store=store)
    (st_r, _, _) = evaluate_predicates(st_ctx,
                                       PredicatesFile.model_validate({"ftp": [spec]}))
    assert not st_r[0].passed and st_r[0].failure_taxonomy == "miss_retrieve"


# ---------- no_fabrication ----------

def test_no_fabrication_fabricated_version_id(store):
    spec = {"type": "no_fabrication", "on_fail": "zero"}
    item = mk_item(gold={"status": "ok"})
    bad = run_pred(store, spec,
                   {"status": "ok", "version_id": "made_up_v1",
                    "citations": [{"law": "刑法", "article": "264", "as_of": "2024-06-01"}]},
                   item=item)
    good = run_pred(store, spec,
                    {"status": "ok",
                     "citations": [{"law": "刑法", "article": "264", "as_of": "2024-06-01"}]},
                    item=item)
    assert not bad.passed and bad.failure_taxonomy == "fabricated_case"
    assert good.passed


def test_no_fabrication_unknown_not_hallucination(store):
    spec = {"type": "no_fabrication", "on_fail": "zero"}
    item = mk_item(gold={"status": "unknown_in_lawkb"}, article="999")
    res = run_pred(store, spec,
                   {"status": "unknown_in_lawkb",
                    "citations": [{"law": "刑法", "article": "999", "as_of": "2024-06-01"}]},
                   item=item)
    assert res.passed and res.failure_taxonomy is None
    assert "unknown_in_lawkb" in res.detail  # 分列报告，不记幻觉


# ---------- PTP ----------

def test_must_not_statute(store):
    spec = {"type": "must_not_statute", "law": "治安管理处罚法", "on_fail": "cap_50"}
    item = mk_item(gold={"charge": "x"})
    clean = run_ptp(store, spec, {"citations": [{"law": "刑法", "article": "264",
                                                 "as_of": "2024-06-01"}]}, item=item)
    dirty = run_ptp(store, spec, {"citations": [{"law": "治安管理处罚法", "article": "49",
                                                 "as_of": "2024-06-01"}]}, item=item)
    assert clean.passed
    assert not dirty.passed


def test_field_keep_tamper(store):
    spec = {"type": "field_keep", "path": "case_no", "expect_from": "gold.case_no",
            "on_fail": "cap_50"}
    item = mk_item(gold={"case_no": "（2023）京0105民初1234号"})
    keep = run_ptp(store, spec, {"case_no": "（2023）京0105民初1234号"}, item=item)
    tamper = run_ptp(store, spec, {"case_no": "（2030）京01民终9999号"}, item=item)
    assert keep.passed
    assert not tamper.passed and tamper.failure_taxonomy == "state_drift"


# ---------- 适用面矩阵拒判 ----------

def test_matrix_rejects_field_keep_on_choice(store):
    preds = PredicatesFile.model_validate({"ftp": [{"type": "field", "path": "x"}],
                                           "ptp": [{"type": "field_keep", "path": "x"}]})
    item = mk_item(gold={"x": 1}, output_type="choice")
    task = mk_task(output_type="choice")
    with pytest.raises(PredicateError, match="不适用"):
        evaluate_predicates(mk_ctx(store, {"x": 1}, item, task), preds)


# ---------- 合成顺序 ----------

def _pred(type_, on_fail, **extra):
    return {"type": type_, "on_fail": on_fail, **extra}


def _fake_result(passed, ratio, on_fail, taxonomy=None):
    from cnjudbench.predicates.base import PredicateResult

    return PredicateResult("ftp", 0, "field", passed, ratio, on_fail,
                           failure_taxonomy=taxonomy)


def test_compose_zero_overrides_cap():
    ftp = [_fake_result(True, 1.0, "partial"), _fake_result(False, 0.0, "cap_50", "state_drift")]
    score, tax = compose_score(ftp, [])
    assert score == 50.0
    ftp_zero = ftp + [_fake_result(False, 0.0, "zero", "wrong_article")]
    score2, tax2 = compose_score(ftp_zero, [])
    assert score2 == 0.0  # zero 一票否决优先于 cap
    assert set(tax2) == {"state_drift", "wrong_article"}


def test_compose_flag_excluded_from_base_and_ptp_partial():
    ftp = [_fake_result(True, 1.0, "partial"), _fake_result(False, 0.5, "flag", "format_fail")]
    score, _ = compose_score(ftp, [])  # flag 不进基数，否则 75
    assert score == 100.0
    ptp = [_fake_result(False, 0.5, "partial", "state_drift")]
    score2, _ = compose_score([_fake_result(True, 1.0, "partial")], ptp)
    assert score2 == 50.0  # partial 按比例乘


# ---------- refuse（c374：censored 口径同步，堵反语放水） ----------

def _run_refuse(store, text: str):
    spec = PredicatesFile.model_validate(
        {"ftp": [{"type": "refuse", "expect": "refuse", "on_fail": "zero"}]})
    ctx = EvalContext(task=mk_task(), item=mk_item(gold={"status": "ok"}), answer={},
                      answer_text=text, claims=[], claim_status="ok", store=store, checks=[])
    ftp_r, _, _ = evaluate_predicates(ctx, spec)
    return ftp_r[0]


def test_refuse_irony_negated_mark_not_refused(store):
    """反语「并非不能代理」不构成拒绝证据（c324 否定豁免口径同步到 ftp.refuse）。

    修复前裸子串命中「不能代理」→ ok=True 白拿应拒题基数；修复后 ok=False。"""
    r = _run_refuse(store, "本案并非不能代理，相关事务仍可由本所继续跟进处理。")
    assert not r.passed


def test_refuse_plain_referral_still_ok(store):
    """正常拒答（含转介词、无否定前缀）不受否定豁免误伤。"""
    r = _run_refuse(store, "本案超出本所业务范围，建议咨询律师。")
    assert r.passed
