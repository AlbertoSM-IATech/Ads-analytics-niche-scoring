"""Phase 3A.1 — Tests for unprofitable-sales rule (G9.5 LOWER_BID + G9.6 OBSERVE).

Critical guards:
  - orders > 0 + beneficio_kdp < 0 + consumo_pe > 1 → LOWER_BID (NOT HOLD).
  - orders > 0 + beneficio_kdp < 0 + consumo_pe <= 1 → OBSERVE.
  - relevance='high' still allows LOWER_BID but never NEGATIVE.
  - cpc_source='reference' lowers confidence to 'low'.
  - Profitable terms still HOLD/SCALE/MOVE_TO_EXACT — no regression.
"""
import pytest
from recommendations import decide


def make_row(**kw):
    """Same helper as test_recommendations.py — replicated locally for isolation."""
    base = dict(
        term="example kw", clicks=10, orders=0, spend=5.0, sales=0.0,
        impressions=1000, cpc_real=0.50, cpc_source="real",
        regalia_neta_kdp=5.0, regalia_source="kdp",
        acos_pe_kdp=40.0, acos_siguiente_con_venta=45.0,
        consumo_pe=0.6, consumo_fase=0.5, beneficio_kdp=-5.0,
        cvr=0.0, acos_actual=0.0,
        relevance="unreviewed", match_type="broad",
        campaign="C1", customer_search_term="example kw", targeting=None,
    )
    base.update(kw)
    return base


CTX = dict(dataset_id="T", phase="dominio", regalia_source="kdp", sym="$")


# ----------------------------------------------------------------------------
# Core rule 1: LOWER_BID when orders>0, profit<0, consumo_pe>1
# ----------------------------------------------------------------------------

def test_lower_bid_when_orders_positive_but_profit_negative_and_consumo_pe_high():
    """The motivating bug: 'mindfulness para principiantes' style row."""
    r = decide(make_row(
        orders=3, clicks=54, spend=21.06, sales=38.97,
        cpc_real=0.39, acos_actual=54.0,
        consumo_pe=4.14, consumo_fase=2.43,
        acos_pe_kdp=39.18, acos_siguiente_con_venta=41.28,
        beneficio_kdp=-5.79, match_type="broad",
    ), **CTX)
    assert r.action_type == "LOWER_BID", (
        f"Expected LOWER_BID for unprofitable selling term, got {r.action_type}"
    )
    # Must NOT be classified as HOLD even though it has orders
    assert r.action_type != "HOLD"
    # Must NOT recommend a negative — it converts
    assert "NEGATIVE" not in r.action_type
    # Risk medium per spec
    assert r.risk == "medium"


def test_hold_not_returned_when_profit_negative_and_consumo_pe_high():
    """Regression guard: HOLD must never appear in this scenario again."""
    r = decide(make_row(
        orders=2, beneficio_kdp=-3.0, consumo_pe=1.5,
        spend=10.0, sales=5.0, acos_actual=200.0,
    ), **CTX)
    assert r.action_type == "LOWER_BID"


# ----------------------------------------------------------------------------
# Core rule 2: OBSERVE when orders>0, profit<0, consumo_pe<=1
# ----------------------------------------------------------------------------

def test_observe_when_orders_positive_profit_negative_but_consumo_pe_not_over_pe():
    r = decide(make_row(
        orders=2, beneficio_kdp=-1.0, consumo_pe=0.8,
        spend=5.0, sales=3.0, acos_actual=160.0, consumo_fase=0.7,
    ), **CTX)
    assert r.action_type == "OBSERVE"


def test_observe_when_orders_positive_profit_negative_consumo_pe_exactly_1():
    """Boundary: consumo_pe == 1.0 still falls into OBSERVE (not over PE)."""
    r = decide(make_row(
        orders=1, beneficio_kdp=-0.5, consumo_pe=1.0,
        spend=5.0, sales=4.0, acos_actual=125.0,
    ), **CTX)
    assert r.action_type == "OBSERVE"


# ----------------------------------------------------------------------------
# relevance=high still allows LOWER_BID but never NEGATIVE
# ----------------------------------------------------------------------------

def test_high_relevance_still_allows_lower_bid_but_never_negative():
    r = decide(make_row(
        orders=2, beneficio_kdp=-5.0, consumo_pe=2.5,
        spend=15.0, relevance="high",
    ), **CTX)
    assert r.action_type == "LOWER_BID"
    assert "NEGATIVE" not in r.action_type


# ----------------------------------------------------------------------------
# cpc_source='reference' lowers confidence
# ----------------------------------------------------------------------------

def test_reference_cpc_lowers_confidence_for_profit_negative_rule():
    r_real = decide(make_row(
        orders=2, beneficio_kdp=-5.0, consumo_pe=2.0,
        cpc_source="real",
    ), **CTX)
    r_ref = decide(make_row(
        orders=2, beneficio_kdp=-5.0, consumo_pe=2.0,
        cpc_source="reference",
    ), **CTX)
    assert r_real.action_type == "LOWER_BID"
    assert r_ref.action_type == "LOWER_BID"
    assert r_real.confidence == "medium"
    assert r_ref.confidence == "low"


def test_reference_cpc_also_lowers_confidence_for_observe_variant():
    """Same lower-confidence rule applies to the OBSERVE branch."""
    r = decide(make_row(
        orders=1, beneficio_kdp=-0.5, consumo_pe=0.7,
        cpc_source="reference",
    ), **CTX)
    assert r.action_type == "OBSERVE"
    assert r.confidence == "low"


# ----------------------------------------------------------------------------
# No regression: profitable terms still HOLD/SCALE/MOVE_TO_EXACT
# ----------------------------------------------------------------------------

def test_profitable_term_still_scale_when_high_margin():
    r = decide(make_row(
        orders=3, clicks=10, sales=40.0, spend=4.0,
        beneficio_kdp=11.0, acos_actual=10.0, acos_pe_kdp=40.0,
        consumo_pe=0.4, match_type="exact",
    ), **CTX)
    assert r.action_type == "SCALE"


def test_profitable_term_still_hold_when_break_even():
    r = decide(make_row(
        orders=1, clicks=10, sales=10.0, spend=5.0,
        beneficio_kdp=0.0,   # exactly break-even, not negative
        acos_actual=50.0, acos_pe_kdp=40.0,
        consumo_pe=0.9, match_type="exact",
    ), **CTX)
    assert r.action_type == "HOLD"


def test_profitable_term_still_move_to_exact_from_broad():
    r = decide(make_row(
        orders=2, clicks=15, sales=30.0, spend=6.0,
        acos_actual=20.0, acos_pe_kdp=40.0,
        beneficio_kdp=4.0, match_type="broad",
        customer_search_term="mindfulness book", consumo_pe=0.5,
    ), **CTX)
    assert r.action_type == "MOVE_TO_EXACT"


# ----------------------------------------------------------------------------
# Priority bucket coherence with the spec
# ----------------------------------------------------------------------------

def test_lower_bid_high_priority_when_consumo_pe_very_high():
    r = decide(make_row(
        orders=3, clicks=54, spend=21.06, sales=38.97,
        beneficio_kdp=-5.79, consumo_pe=4.14,   # >= 2.0
    ), **CTX)
    assert r.action_type == "LOWER_BID"
    assert r.priority == "high"


def test_lower_bid_medium_priority_when_consumo_pe_moderate():
    """consumo_pe between 1.0 and 2.0 yields medium priority."""
    r = decide(make_row(
        orders=2, clicks=20, spend=8.0, sales=4.0,
        beneficio_kdp=-1.0, consumo_pe=1.3,
    ), **CTX)
    assert r.action_type == "LOWER_BID"
    assert r.priority in ("medium", "low")   # natural score, no hard override
