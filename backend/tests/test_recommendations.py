"""Phase 3A — Tests for the parallel recommendations engine.

Coverage:
  - All decision rules G1..G12 (16 required + bonuses).
  - Endpoint read-only verification (no DB mutation).
  - Autopilot byte-equivalent before & after multiple /recommendations calls.
  - Importer byte-equivalent.
  - Phase 2A economic metrics are NOT modified by the new endpoint.
"""
import hashlib
import json
import os
from pathlib import Path

import httpx
import pytest

from recommendations import (
    decide, build_recommendations, normalize_match_type, summarize_by_action,
    IRRELEVANT_PATTERNS, ALL_ACTIONS,
)

BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")
API = f"{BACKEND_URL}/api"
TEST_DS_ID = "d17b595d-7e2d-4b8a-8299-ece05cdc70d5"
FIXTURES = Path(__file__).parent / "fixtures"


# ----------------------------------------------------------------------------
# Synthetic test rows (don't depend on the live dataset for unit tests).
# ----------------------------------------------------------------------------

def make_row(**kw):
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
# G1 — WAIT_FOR_DATA
# ----------------------------------------------------------------------------

def test_g1_wait_for_data_when_no_clicks():
    r = decide(make_row(clicks=0), **CTX)
    assert r.action_type == "WAIT_FOR_DATA"


def test_g1_wait_for_data_when_no_economy():
    r = decide(make_row(clicks=10, regalia_neta_kdp=None),
               **{**CTX, "regalia_source": "none"})
    assert r.action_type == "WAIT_FOR_DATA"


# ----------------------------------------------------------------------------
# G9 — consumo fase < 50% → WAIT_FOR_DATA
# ----------------------------------------------------------------------------

def test_g9_wait_when_consumo_fase_below_50():
    r = decide(make_row(orders=0, consumo_pe=0.3, consumo_fase=0.4), **CTX)
    assert r.action_type == "WAIT_FOR_DATA"


# ----------------------------------------------------------------------------
# G8 — consumo fase 50-80 → OBSERVE
# ----------------------------------------------------------------------------

def test_g8_observe_consumo_fase_50_80():
    r = decide(make_row(orders=0, consumo_pe=0.6, consumo_fase=0.6), **CTX)
    assert r.action_type == "OBSERVE"


# ----------------------------------------------------------------------------
# G7 — consumo fase 80-100 → OBSERVE or LOWER_BID
# ----------------------------------------------------------------------------

@pytest.mark.parametrize("relevance,expected", [
    ("high", "OBSERVE"),
    ("low", "LOWER_BID"),
    ("medium", "LOWER_BID"),
    ("unreviewed", "OBSERVE"),
])
def test_g7_relevance_drives_observe_or_lower_bid(relevance, expected):
    r = decide(make_row(orders=0, consumo_pe=0.85, consumo_fase=0.85, relevance=relevance), **CTX)
    assert r.action_type == expected


def test_g7_lower_bid_when_cpc_real_above_cpc_max_rentable():
    # cpc_max_rentable = 5.0 / 10 = 0.5. cpc_real = 0.80 → exceeds.
    r = decide(make_row(orders=0, consumo_pe=0.85, consumo_fase=0.85,
                        cpc_real=0.80, relevance="high"), **CTX)
    assert r.action_type == "LOWER_BID"


# ----------------------------------------------------------------------------
# G6 — supera fase pero no PE → LOWER_BID, never NEGATIVE
# ----------------------------------------------------------------------------

def test_g6_lower_bid_supera_fase_no_pe():
    r = decide(make_row(orders=0, consumo_pe=0.9, consumo_fase=1.1), **CTX)
    assert r.action_type == "LOWER_BID"
    assert "NEGATIVE" not in r.action_type


def test_g6_no_negative_when_supera_fase_but_not_pe():
    # Critical guard: even with low relevance, must NOT recommend NEGATIVE here.
    r = decide(make_row(orders=0, consumo_pe=0.95, consumo_fase=1.3, relevance="low"), **CTX)
    assert r.action_type == "LOWER_BID"


# ----------------------------------------------------------------------------
# G5 — supera PE pero recuperable con siguiente venta → OBSERVE
# ----------------------------------------------------------------------------

def test_g5_no_negative_when_supera_pe_but_recoverable():
    # acos_pe_kdp = 40, buffer 1.10 → 44. acos_next = 42 → recoverable.
    r = decide(make_row(orders=0, consumo_pe=1.1, consumo_fase=1.2,
                        acos_pe_kdp=40.0, acos_siguiente_con_venta=42.0), **CTX)
    assert r.action_type == "OBSERVE"
    assert r.is_recoverable_with_next_sale is True


# ----------------------------------------------------------------------------
# G4 — NEGATIVE_EXACT_CANDIDATE normal
# ----------------------------------------------------------------------------

def test_g4_negative_exact_candidate_supera_pe_not_recoverable():
    r = decide(make_row(orders=0, consumo_pe=1.1, consumo_fase=1.2,
                        acos_pe_kdp=40.0, acos_siguiente_con_venta=80.0,
                        relevance="unreviewed"), **CTX)
    assert r.action_type == "NEGATIVE_EXACT_CANDIDATE"
    assert r.is_recoverable_with_next_sale is False


# ----------------------------------------------------------------------------
# G3 — NEGATIVE_EXACT_CANDIDATE high priority
# ----------------------------------------------------------------------------

def test_g3_negative_exact_candidate_high_priority():
    r = decide(make_row(orders=0, consumo_pe=1.30, consumo_fase=1.40,
                        acos_pe_kdp=40.0, acos_siguiente_con_venta=80.0,
                        relevance="low", spend=20.0), **CTX)
    assert r.action_type == "NEGATIVE_EXACT_CANDIDATE"
    assert r.priority == "high"
    assert r.confidence == "high"


# ----------------------------------------------------------------------------
# G2 — NEGATIVE_PHRASE_CANDIDATE
# ----------------------------------------------------------------------------

def test_g2_negative_phrase_candidate_pattern_match():
    r = decide(make_row(term="yoga free pdf",
                        orders=0, clicks=5, consumo_fase=0.6), **CTX)
    assert r.action_type == "NEGATIVE_PHRASE_CANDIDATE"
    assert r.risk == "high"   # phrase negatives are aggressive


def test_g2_no_phrase_when_orders_gt_zero():
    # Even with irrelevant pattern, sales = mandatory protection.
    r = decide(make_row(term="yoga free pdf",
                        orders=2, clicks=10, consumo_fase=0.7, beneficio_kdp=2.0,
                        sales=12.0, acos_actual=15.0), **CTX)
    assert r.action_type != "NEGATIVE_PHRASE_CANDIDATE"


def test_g2_no_phrase_when_clicks_below_3():
    r = decide(make_row(term="libro gratis pdf",
                        orders=0, clicks=2, consumo_fase=0.6), **CTX)
    # Fails G2's min-clicks guard → falls through to G1 (wait for data).
    assert r.action_type == "WAIT_FOR_DATA"


def test_g2_no_phrase_when_consumo_fase_below_50():
    r = decide(make_row(term="libro gratis pdf",
                        orders=0, clicks=4, consumo_fase=0.3), **CTX)
    # G2 requires consumo_fase >= 0.5
    assert r.action_type != "NEGATIVE_PHRASE_CANDIDATE"


def test_g2_single_word_free_does_not_trigger():
    """Ambiguous single words like 'free' alone must NOT trigger phrase negative."""
    r = decide(make_row(term="yoga free",  # only 'free', not 'free pdf'/etc
                        orders=0, clicks=10, consumo_fase=0.7), **CTX)
    assert r.action_type != "NEGATIVE_PHRASE_CANDIDATE"


# ----------------------------------------------------------------------------
# G10 — MOVE_TO_EXACT
# ----------------------------------------------------------------------------

def test_g10_move_to_exact_for_profitable_search_term_in_broad():
    r = decide(make_row(orders=2, clicks=15, sales=30.0, spend=6.0,
                        acos_actual=20.0, acos_pe_kdp=40.0,
                        beneficio_kdp=4.0, match_type="broad",
                        customer_search_term="mindfulness book",
                        consumo_pe=0.5), **CTX)
    assert r.action_type == "MOVE_TO_EXACT"


def test_g10_normalize_match_type_automatic_maps_to_auto():
    assert normalize_match_type("Automatic") == "auto"
    r = decide(make_row(orders=2, clicks=15, sales=30.0, spend=6.0,
                        acos_actual=20.0, acos_pe_kdp=40.0,
                        beneficio_kdp=4.0, match_type="automatic",
                        customer_search_term="mindfulness book",
                        consumo_pe=0.5), **CTX)
    assert r.action_type == "MOVE_TO_EXACT"


# ----------------------------------------------------------------------------
# G11 — SCALE
# ----------------------------------------------------------------------------

def test_g11_scale_for_high_margin_low_consumption():
    r = decide(make_row(orders=2, clicks=10, sales=30.0, spend=4.0,
                        acos_actual=13.0, acos_pe_kdp=40.0,
                        beneficio_kdp=6.0, match_type="exact",
                        consumo_pe=0.4), **CTX)
    assert r.action_type == "SCALE"


# ----------------------------------------------------------------------------
# G12 — HOLD (default for profitable with neither MOVE nor SCALE conditions)
# ----------------------------------------------------------------------------

def test_g12_hold_for_profitable_term():
    r = decide(make_row(orders=1, clicks=10, sales=10.0, spend=5.0,
                        acos_actual=50.0, acos_pe_kdp=40.0,
                        beneficio_kdp=0.0, match_type="exact",
                        consumo_pe=0.9), **CTX)
    assert r.action_type == "HOLD"


# ----------------------------------------------------------------------------
# Cross-cutting: relevance=high never auto-recommends NEGATIVE_EXACT
# ----------------------------------------------------------------------------

def test_relevance_high_blocks_automatic_negative_exact():
    # Same inputs that would trigger G4 with unreviewed, but relevance=high.
    base = dict(orders=0, consumo_pe=1.15, consumo_fase=1.2,
                acos_pe_kdp=40.0, acos_siguiente_con_venta=80.0)
    r_unrev = decide(make_row(**base, relevance="unreviewed"), **CTX)
    r_high = decide(make_row(**base, relevance="high"), **CTX)
    assert r_unrev.action_type == "NEGATIVE_EXACT_CANDIDATE"
    assert r_high.action_type != "NEGATIVE_EXACT_CANDIDATE"


# ----------------------------------------------------------------------------
# Phase 3A: these were reserved. Phase 4C activates both — see
# test_phase4c_aggregations.py for the new positive coverage. Here we only
# verify the schema still names them and that the simple "no campaign"
# baseline does NOT trigger them.
# ----------------------------------------------------------------------------

def test_review_campaign_and_pause_target_action_types_remain_in_schema():
    assert "REVIEW_CAMPAIGN" in ALL_ACTIONS
    assert "PAUSE_TARGET" in ALL_ACTIONS


def test_pause_target_not_emitted_when_customer_search_term_set():
    # All rows here are search-term harvests (customer_search_term==term),
    # so PAUSE_TARGET must never fire even with extreme signals.
    rows = [
        make_row(orders=0, clicks=20, spend=20.0, consumo_pe=3.0, relevance="low",
                 cpc_source="real")
    ]
    recs = build_recommendations(rows, dataset_id="X", phase="dominio", regalia_source="kdp")
    emitted = {r.action_type for r in recs}
    assert "PAUSE_TARGET" not in emitted


# ----------------------------------------------------------------------------
# Priority score bounds and bucket consistency
# ----------------------------------------------------------------------------

def test_priority_score_bounds_and_bucket_consistency():
    rows = [make_row(orders=o, consumo_pe=c, spend=s, relevance=r)
            for o in (0, 1) for c in (0.2, 0.8, 1.2, 1.5) for s in (1, 15) for r in ("high", "low")]
    recs = build_recommendations(rows, dataset_id="X", phase="dominio", regalia_source="kdp")
    for rec in recs:
        assert 0.0 <= rec.priority_score <= 100.0
        if rec.priority_score >= 70:
            assert rec.priority == "high"
        elif rec.priority_score >= 40:
            assert rec.priority == "medium"
        else:
            assert rec.priority == "low"


# ----------------------------------------------------------------------------
# Cross-cutting: relevance does NOT change Phase-2A econ values in metrics
# ----------------------------------------------------------------------------

def test_relevance_does_not_affect_econ_metrics_in_metrics_block():
    base = dict(orders=0, consumo_pe=0.7, consumo_fase=0.7, clicks=10,
                spend=5.0, sales=0.0, cpc_real=0.5, regalia_neta_kdp=5.0,
                acos_pe_kdp=40.0, beneficio_kdp=-5.0)
    rec_a = decide(make_row(**base, relevance="unreviewed"), **CTX)
    rec_b = decide(make_row(**base, relevance="high"), **CTX)
    ECON = ("cpc_real", "acos_pe_kdp", "consumo_pe", "consumo_fase", "beneficio_kdp", "clicks", "clicks_pe", "clicks_fase")
    for k in ECON:
        assert getattr(rec_a.metrics, k) == getattr(rec_b.metrics, k)


# ----------------------------------------------------------------------------
# Endpoint read-only verification + autopilot + importer regression
# ----------------------------------------------------------------------------

def _doc_hash() -> str:
    """Hash of the full dataset doc to detect any mutation."""
    doc = httpx.get(f"{API}/datasets/{TEST_DS_ID}", timeout=20).json()
    return hashlib.sha256(json.dumps(doc, sort_keys=True, default=str).encode()).hexdigest()


def test_endpoint_returns_well_formed_payload():
    r = httpx.get(f"{API}/datasets/{TEST_DS_ID}/recommendations", timeout=30)
    r.raise_for_status()
    payload = r.json()
    assert "count" in payload
    assert "by_action" in payload
    assert "phase" in payload
    assert "regalia_source" in payload
    assert isinstance(payload["recommendations"], list)
    # Reserved actions are present in the by_action keys
    for k in ("REVIEW_CAMPAIGN", "PAUSE_TARGET"):
        assert k in payload["by_action"]


def test_endpoint_is_read_only():
    """Multiple calls to /recommendations must NOT mutate the dataset document."""
    before = _doc_hash()
    for _ in range(5):
        httpx.get(f"{API}/datasets/{TEST_DS_ID}/recommendations", timeout=30).raise_for_status()
    after = _doc_hash()
    assert before == after, "/recommendations mutated the dataset — must be read-only!"


@pytest.mark.skipif(
    not (FIXTURES / "autopilot_dominio_pre_phase3.json").exists(),
    reason="autopilot pre-phase3 fixture missing",
)
def test_autopilot_unchanged_after_recommendations_calls():
    """Autopilot must remain byte-equivalent regardless of /recommendations activity."""
    snap = json.loads((FIXTURES / "autopilot_dominio_pre_phase3.json").read_text())
    # Hammer /recommendations 5 times
    for _ in range(5):
        httpx.get(f"{API}/datasets/{TEST_DS_ID}/recommendations", timeout=30).raise_for_status()
    cur = httpx.get(f"{API}/datasets/{TEST_DS_ID}/autopilot?phase=dominio", timeout=30).json()
    # `generated_at` is volatile in both responses.
    cur.pop("generated_at", None)
    snap.pop("generated_at", None)
    assert json.dumps(cur, sort_keys=True) == json.dumps(snap, sort_keys=True), (
        "autopilot output changed after /recommendations calls"
    )


def test_importer_still_byte_equivalent_in_phase3a():
    """Importer regression — same payload as the Phase-2 baseline."""
    fixture_path = FIXTURES / "import_response_pre_phase2.json"
    if not fixture_path.exists():
        pytest.skip("Phase-2 importer fixture missing")
    CSV_EN = (
        "Campaign Name,Ad Group Name,Customer Search Term,Keyword Text,Match Type,"
        "Impressions,Clicks,Click-Thru Rate (CTR),Cost Per Click (CPC),Spend,"
        "7 Day Total Sales,7 Day Total Orders (#),"
        "Total Advertising Cost of Sales (ACOS),Total Return on Advertising Spend (ROAS),Start Date\n"
        "Campaign Alpha,AdGroup A,mindfulness book,mindfulness,broad,1200,45,3.75%,$0.62,$27.90,$89.97,3,31.01%,3.23,2025-01-01\n"
        "Campaign Alpha,AdGroup A,buddha quotes,mindfulness,broad,800,20,2.50%,$0.50,$10.00,$0.00,0,0.00%,0,2025-01-02\n"
        "Campaign Beta,AdGroup B,yoga mat,yoga,exact,500,30,6.00%,$0.40,$12.00,$60.00,2,20.00%,5.0,2025-01-02\n"
        "Campaign Beta,AdGroup B,no sales term,yoga,broad,900,10,1.10%,$0.30,$3.00,$0.00,0,0.00%,0,2025-01-03\n"
    )
    files = {"file": ("phase3a_fixture.csv", CSV_EN.encode("utf-8"), "text/csv")}
    data = {"marketplace": "us", "dataset_name": "PHASE2_FIXTURE_DATASET"}
    r = httpx.post(f"{API}/imports/upload", files=files, data=data, timeout=60)
    r.raise_for_status()
    payload = r.json()
    new_id = payload.get("id")
    snap = json.loads(fixture_path.read_text())
    if new_id:
        try:
            httpx.delete(f"{API}/datasets/{new_id}", timeout=10)
        except Exception:
            pass
    for k in ("id", "created_at"):
        payload.pop(k, None)
    assert json.dumps(payload, sort_keys=True, default=str) == \
           json.dumps(snap, sort_keys=True, default=str)


# ----------------------------------------------------------------------------
# Recommendation IDs are deterministic across calls
# ----------------------------------------------------------------------------

def test_recommendation_ids_are_deterministic():
    a = httpx.get(f"{API}/datasets/{TEST_DS_ID}/recommendations", timeout=30).json()
    b = httpx.get(f"{API}/datasets/{TEST_DS_ID}/recommendations", timeout=30).json()
    ids_a = sorted(r["id"] for r in a["recommendations"])
    ids_b = sorted(r["id"] for r in b["recommendations"])
    assert ids_a == ids_b


# ----------------------------------------------------------------------------
# IRRELEVANT_PATTERNS list integrity check
# ----------------------------------------------------------------------------

def test_irrelevant_patterns_are_specific_not_single_words():
    """Every pattern must be a multi-word phrase to avoid blocking valid traffic."""
    for p in IRRELEVANT_PATTERNS:
        assert " " in p, f"Pattern {p!r} is a single word — too aggressive."
