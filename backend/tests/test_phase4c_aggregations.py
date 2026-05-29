"""Phase 4C — Aggregation-level rules: REVIEW_CAMPAIGN + PAUSE_TARGET.

PAUSE_TARGET (per-row, severe):
  - Only on bidded targets (row.targeting set AND customer_search_term None).
  - Strict signals: high clicks, high consumo_pe, high spend, not recoverable,
    cpc_source=='real', relevance in {'low', 'unreviewed'}.
  - Stricter thresholds for 'unreviewed' than for 'low'.
  - NEVER fires for relevance in {'high', 'medium'}.

REVIEW_CAMPAIGN (aggregated per-campaign):
  - Requires min 3 rows in campaign, wait-for-data ratio < 70%,
    significant spend, resolved acos_pe_kdp, and B1 OR B2 evidence.
"""
import pytest
from recommendations import (
    decide, build_recommendations, aggregate_by_campaign, decide_campaign,
)


def make_target_row(**kw):
    """Bidded target row (no customer_search_term harvest)."""
    base = dict(
        term="my target keyword", clicks=10, orders=0, spend=10.0, sales=0.0,
        impressions=1000, cpc_real=1.0, cpc_source="real",
        regalia_neta_kdp=5.0, regalia_source="kdp",
        acos_pe_kdp=40.0, acos_siguiente_con_venta=70.0,  # not recoverable
        consumo_pe=2.5, consumo_fase=2.0, beneficio_kdp=-10.0,
        cvr=0.0, acos_actual=0.0,
        relevance="low", match_type="exact",
        campaign="C1",
        customer_search_term=None, targeting="my target keyword",
    )
    base.update(kw)
    return base


def make_search_term_row(**kw):
    """Search-term harvest row (no targeting clause)."""
    base = dict(
        term="some user query", clicks=10, orders=0, spend=10.0, sales=0.0,
        impressions=1000, cpc_real=1.0, cpc_source="real",
        regalia_neta_kdp=5.0, regalia_source="kdp",
        acos_pe_kdp=40.0, acos_siguiente_con_venta=70.0,
        consumo_pe=2.5, consumo_fase=2.0, beneficio_kdp=-10.0,
        cvr=0.0, acos_actual=0.0,
        relevance="low", match_type="broad",
        campaign="C1",
        customer_search_term="some user query", targeting=None,
    )
    base.update(kw)
    return base


CTX = dict(dataset_id="T", phase="dominio", regalia_source="kdp", sym="$")


# ============================================================================
# PAUSE_TARGET — positive cases
# ============================================================================

def test_pause_target_fires_for_low_relevance_when_all_thresholds_met():
    r = decide(make_target_row(
        clicks=10, consumo_pe=2.2, spend=8.0,   # >=8, >=2.0, >=1.5*5=7.5
        regalia_neta_kdp=5.0, relevance="low",
    ), **CTX)
    assert r.action_type == "PAUSE_TARGET"
    assert r.confidence == "high"
    assert r.risk == "medium"


def test_pause_target_fires_for_unreviewed_only_with_stricter_thresholds():
    r = decide(make_target_row(
        clicks=15, consumo_pe=2.8, spend=12.0,  # >=12, >=2.5, >=2.0*5=10
        regalia_neta_kdp=5.0, relevance="unreviewed",
    ), **CTX)
    assert r.action_type == "PAUSE_TARGET"
    assert r.confidence == "medium"
    assert r.risk == "high"


# ============================================================================
# PAUSE_TARGET — negative cases (must NOT fire)
# ============================================================================

def test_pause_target_does_not_fire_with_customer_search_term():
    """Search-term harvest must never trigger PAUSE_TARGET even at extreme signals."""
    r = decide(make_search_term_row(
        clicks=20, consumo_pe=3.5, spend=20.0, relevance="low",
    ), **CTX)
    assert r.action_type != "PAUSE_TARGET"
    # Should fall to NEGATIVE_EXACT_CANDIDATE (G3) instead.
    assert "NEGATIVE" in r.action_type or r.action_type == "LOWER_BID"


def test_pause_target_does_not_fire_for_high_relevance():
    r = decide(make_target_row(
        clicks=20, consumo_pe=3.0, spend=20.0, relevance="high",
    ), **CTX)
    assert r.action_type != "PAUSE_TARGET"


def test_pause_target_does_not_fire_for_medium_relevance():
    r = decide(make_target_row(
        clicks=20, consumo_pe=3.0, spend=20.0, relevance="medium",
    ), **CTX)
    assert r.action_type != "PAUSE_TARGET"


def test_pause_target_does_not_fire_with_reference_cpc():
    r = decide(make_target_row(
        clicks=20, consumo_pe=3.0, spend=20.0, relevance="low",
        cpc_source="reference",
    ), **CTX)
    assert r.action_type != "PAUSE_TARGET"


def test_pause_target_does_not_fire_below_clicks_threshold_low():
    # relevance=low requires clicks>=8
    r = decide(make_target_row(
        clicks=5, consumo_pe=3.0, spend=15.0, relevance="low",
    ), **CTX)
    assert r.action_type != "PAUSE_TARGET"


def test_pause_target_does_not_fire_below_clicks_threshold_unreviewed():
    # relevance=unreviewed requires clicks>=12
    r = decide(make_target_row(
        clicks=10, consumo_pe=3.0, spend=15.0, relevance="unreviewed",
    ), **CTX)
    assert r.action_type != "PAUSE_TARGET"


def test_pause_target_does_not_fire_when_recoverable():
    r = decide(make_target_row(
        clicks=20, consumo_pe=3.0, spend=20.0, relevance="low",
        acos_pe_kdp=50.0, acos_siguiente_con_venta=40.0,  # recoverable
    ), **CTX)
    assert r.action_type != "PAUSE_TARGET"


def test_pause_target_does_not_fire_when_spend_too_low():
    # relevance=low requires spend >= regalia*1.5 = 7.5
    r = decide(make_target_row(
        clicks=10, consumo_pe=2.5, spend=5.0, regalia_neta_kdp=5.0,
        relevance="low",
    ), **CTX)
    assert r.action_type != "PAUSE_TARGET"


def test_pause_target_does_not_fire_when_consumo_pe_below_threshold():
    # relevance=low requires consumo_pe >= 2.0
    r = decide(make_target_row(
        clicks=10, consumo_pe=1.5, spend=15.0, relevance="low",
    ), **CTX)
    assert r.action_type != "PAUSE_TARGET"


def test_pause_target_preempts_negative_exact_when_eligible():
    """When PAUSE_TARGET conditions met, NEGATIVE_EXACT is NOT also emitted."""
    r = decide(make_target_row(
        clicks=10, consumo_pe=2.2, spend=10.0, relevance="low",
    ), **CTX)
    assert r.action_type == "PAUSE_TARGET"
    # Single recommendation per row — guaranteed by decide() returning early.


# ============================================================================
# REVIEW_CAMPAIGN — positive cases
# ============================================================================

def _build_camp_rows(campaign, n, **overrides):
    """Helper: build N rows in the same campaign."""
    rows = []
    for i in range(n):
        rows.append(make_search_term_row(
            term=f"kw_{i}",
            customer_search_term=f"kw_{i}",
            campaign=campaign,
            **overrides,
        ))
    return rows


def test_review_campaign_fires_when_aggregate_loss_and_high_acos():
    """B1: aggregate beneficio < 0 AND aggregate ACoS > PE × 1.20."""
    # 3 rows, each with significant loss + acos > PE*1.20
    rows = _build_camp_rows("BadCamp", 3,
        clicks=10, orders=1, spend=10.0, sales=5.0,
        beneficio_kdp=-5.0, acos_actual=200.0,
        consumo_pe=2.0, consumo_fase=1.5,
        relevance="unreviewed",
    )
    recs = build_recommendations(rows, **CTX)
    camp_recs = [r for r in recs if r.action_type == "REVIEW_CAMPAIGN"]
    assert len(camp_recs) == 1
    assert camp_recs[0].campaign == "BadCamp"
    assert camp_recs[0].term is None
    assert camp_recs[0].priority_score <= 90


def test_review_campaign_fires_when_many_negatives_no_positives():
    """B2: >=40% rows with negative signals, zero positives."""
    rows = _build_camp_rows("NegHeavy", 5,
        clicks=10, orders=0, spend=8.0, sales=0.0,
        consumo_pe=1.3, consumo_fase=1.1,
        beneficio_kdp=-8.0, relevance="low",
    )
    recs = build_recommendations(rows, **CTX)
    camp_recs = [r for r in recs if r.action_type == "REVIEW_CAMPAIGN"]
    assert len(camp_recs) == 1


# ============================================================================
# REVIEW_CAMPAIGN — negative cases
# ============================================================================

def test_review_campaign_does_not_fire_with_only_two_rows():
    rows = _build_camp_rows("TinyCamp", 2,
        clicks=10, orders=0, spend=10.0, sales=0.0,
        consumo_pe=2.0, beneficio_kdp=-10.0,
    )
    recs = build_recommendations(rows, **CTX)
    assert not any(r.action_type == "REVIEW_CAMPAIGN" for r in recs)


def test_review_campaign_does_not_fire_when_mostly_wait_for_data():
    # All rows have clicks<3 → WAIT_FOR_DATA dominates (>=70%)
    rows = _build_camp_rows("YoungCamp", 5,
        clicks=1, orders=0, spend=1.0, sales=0.0,
        consumo_pe=0.05, consumo_fase=0.05, beneficio_kdp=-1.0,
    )
    recs = build_recommendations(rows, **CTX)
    assert not any(r.action_type == "REVIEW_CAMPAIGN" for r in recs)


def test_review_campaign_does_not_fire_when_profitable():
    # Profitable rows → no B1 and no B2 (positives present).
    rows = _build_camp_rows("GoodCamp", 4,
        clicks=10, orders=3, spend=4.0, sales=40.0,
        beneficio_kdp=11.0, acos_actual=10.0,
        consumo_pe=0.4, consumo_fase=0.3, relevance="high",
        match_type="exact",
    )
    recs = build_recommendations(rows, **CTX)
    assert not any(r.action_type == "REVIEW_CAMPAIGN" for r in recs)


def test_review_campaign_does_not_fire_when_spend_too_low():
    # spend < max(5, regalia*5) = max(5, 25) = 25
    rows = _build_camp_rows("LowSpend", 3,
        clicks=4, orders=0, spend=2.0, sales=0.0,
        consumo_pe=0.4, consumo_fase=0.3, beneficio_kdp=-2.0,
        regalia_neta_kdp=5.0,
    )
    recs = build_recommendations(rows, **CTX)
    assert not any(r.action_type == "REVIEW_CAMPAIGN" for r in recs)


def test_review_campaign_does_not_fire_when_acos_pe_unresolved():
    # Without economy resolved, regalia_source='none' → per-row recs are
    # WAIT_FOR_DATA. Also acos_pe_kdp would be None for the agg.
    rows = _build_camp_rows("NoEconomy", 4,
        clicks=10, orders=0, spend=10.0, sales=0.0,
        regalia_neta_kdp=None, regalia_source="none",
        acos_pe_kdp=None,
    )
    recs = build_recommendations(rows, dataset_id="T", phase="dominio",
                                 regalia_source="none", sym="$")
    assert not any(r.action_type == "REVIEW_CAMPAIGN" for r in recs)


def test_review_campaign_skips_rows_without_campaign():
    rows = []
    for i in range(4):
        rows.append(make_search_term_row(
            term=f"kw_{i}", customer_search_term=f"kw_{i}", campaign=None,
            clicks=10, orders=0, spend=10.0, consumo_pe=2.0,
            beneficio_kdp=-10.0,
        ))
    recs = build_recommendations(rows, **CTX)
    assert not any(r.action_type == "REVIEW_CAMPAIGN" for r in recs)


# ============================================================================
# Aggregator unit tests
# ============================================================================

def test_aggregate_by_campaign_sums_and_counts_correctly():
    rows = _build_camp_rows("A", 3,
        clicks=10, orders=1, spend=5.0, sales=2.0, beneficio_kdp=-1.0,
        consumo_pe=2.0, regalia_neta_kdp=5.0, acos_pe_kdp=40.0,
    )
    rows += _build_camp_rows("B", 2,
        clicks=5, orders=0, spend=2.0, sales=0.0, beneficio_kdp=-2.0,
        consumo_pe=0.5, regalia_neta_kdp=5.0, acos_pe_kdp=40.0,
    )
    # Make per-row recs (used by aggregator to count negatives/positives).
    per_row_recs = build_recommendations(rows, **CTX)
    agg = aggregate_by_campaign(rows, per_row_recs)
    assert "A" in agg and "B" in agg
    assert agg["A"]["n_rows"] == 3
    assert agg["A"]["total_clicks"] == 30
    assert agg["A"]["total_orders"] == 3
    assert agg["A"]["total_spend"] == pytest.approx(15.0)
    assert agg["A"]["total_sales"] == pytest.approx(6.0)
    assert agg["A"]["total_beneficio_kdp"] == pytest.approx(-3.0)
    assert agg["A"]["has_beneficio"] is True
    assert agg["A"]["agg_acos"] == pytest.approx(250.0)
    assert agg["B"]["agg_acos"] is None  # zero sales


# ============================================================================
# Coexistence + ordering
# ============================================================================

def test_per_row_and_campaign_recs_coexist_sorted_by_priority_score():
    rows = _build_camp_rows("BadCamp", 4,
        clicks=10, orders=0, spend=10.0, sales=0.0,
        consumo_pe=1.3, beneficio_kdp=-10.0, relevance="low",
        consumo_fase=1.1,
    )
    recs = build_recommendations(rows, **CTX)
    # 4 per-row recommendations + 1 campaign rec
    assert len(recs) == 5
    types = [r.action_type for r in recs]
    assert types.count("REVIEW_CAMPAIGN") == 1
    # Sorted descending by priority_score
    scores = [r.priority_score for r in recs]
    assert scores == sorted(scores, reverse=True)


# ============================================================================
# Regression guards
# ============================================================================

def test_pause_target_does_not_change_search_term_recs_in_simple_rows():
    """Phase 3A.1 motivating case must still yield LOWER_BID, NOT PAUSE_TARGET."""
    r = decide(make_search_term_row(
        term="mindfulness para principiantes",
        customer_search_term="mindfulness para principiantes",
        orders=3, clicks=54, spend=21.06, sales=38.97,
        cpc_real=0.39, acos_actual=54.0,
        consumo_pe=4.14, consumo_fase=2.43,
        acos_pe_kdp=39.18, acos_siguiente_con_venta=41.28,
        beneficio_kdp=-5.79, match_type="broad",
    ), **CTX)
    assert r.action_type == "LOWER_BID"
