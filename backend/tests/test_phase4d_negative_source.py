"""Phase 4D — `suggest_negative` derived from the engine when economy is set.

Tests the live `/keywords-unified` endpoint behavior against the recommendation
engine output. Mirrors the contract approved by the user:

  - regalia_source == "none"  → legacy heuristic (clicks>=6 AND orders==0).
  - regalia_source != "none"  → suggest_negative is True iff the engine emits
    NEGATIVE_EXACT_CANDIDATE or NEGATIVE_PHRASE_CANDIDATE for that term.
"""
import os
import httpx
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = BASE_URL + "/api"


@pytest.fixture(scope="module")
def dataset_id() -> str:
    r = httpx.get(f"{API}/datasets", timeout=20)
    r.raise_for_status()
    ds = r.json()
    if not ds:
        pytest.skip("No datasets available")
    return ds[0]["id"]


def _ku(ds): return httpx.get(f"{API}/datasets/{ds}/keywords-unified", timeout=20).json()
def _recs(ds): return httpx.get(f"{API}/datasets/{ds}/recommendations", timeout=20).json()


# --- Contract preservation ---------------------------------------------------

def test_keywords_unified_schema_preserved(dataset_id):
    d = _ku(dataset_id)
    assert "rows" in d and isinstance(d["rows"], list)
    for r in d["rows"]:
        assert "suggest_negative" in r
        assert isinstance(r["suggest_negative"], bool)
        assert "regalia_source" in r


def test_keywords_aggregated_endpoint_still_works(dataset_id):
    # /search-terms (a.k.a. keywords-aggregated path) keeps legacy behavior:
    # zero scope expansion here; just ensure schema + working response.
    r = httpx.get(f"{API}/datasets/{dataset_id}/search-terms", timeout=20)
    assert r.status_code == 200
    body = r.json()
    assert "rows" in body
    for row in body["rows"]:
        assert "suggest_negative" in row
        assert isinstance(row["suggest_negative"], bool)


# --- Engine alignment when economy is resolved -------------------------------

def test_suggest_negative_aligned_with_engine_when_economy_present(dataset_id):
    d = _ku(dataset_id)
    if not d["rows"]:
        pytest.skip("No rows")
    src = d["rows"][0].get("regalia_source")
    if src == "none":
        pytest.skip("Dataset has no economy resolved — covered by fallback test")

    recs = _recs(dataset_id)
    NEG = {"NEGATIVE_EXACT_CANDIDATE", "NEGATIVE_PHRASE_CANDIDATE"}
    engine_neg_terms = {r["term"] for r in recs["recommendations"]
                        if r.get("term") and r["action_type"] in NEG}

    for row in d["rows"]:
        term = row["term"]
        expected = term in engine_neg_terms
        assert row["suggest_negative"] is expected, (
            f"Term '{term}': suggest_negative={row['suggest_negative']} "
            f"but engine action set says {expected}"
        )


def test_lower_bid_terms_are_not_marked_as_negative(dataset_id):
    """Phase 3A.1 case: LOWER_BID with clicks>=6 and orders=0 must NOT flip
    the legacy boolean on. This is the whole point of Opción B."""
    d = _ku(dataset_id)
    if not d["rows"] or d["rows"][0].get("regalia_source") == "none":
        pytest.skip("No economy")

    recs = _recs(dataset_id)
    by_term = {r["term"]: r for r in recs["recommendations"] if r.get("term")}
    rows_by_term = {r["term"]: r for r in d["rows"]}

    lower_bid_terms = [t for t, r in by_term.items() if r["action_type"] == "LOWER_BID"]
    if not lower_bid_terms:
        pytest.skip("No LOWER_BID terms in fixture")
    for t in lower_bid_terms:
        assert rows_by_term[t]["suggest_negative"] is False, (
            f"Term '{t}' is LOWER_BID — must not be marked as legacy negative."
        )


def test_observe_and_wait_for_data_are_not_marked_as_negative(dataset_id):
    d = _ku(dataset_id)
    if not d["rows"] or d["rows"][0].get("regalia_source") == "none":
        pytest.skip("No economy")
    recs = _recs(dataset_id)
    by_term = {r["term"]: r["action_type"] for r in recs["recommendations"] if r.get("term")}
    rows_by_term = {r["term"]: r for r in d["rows"]}
    for t, at in by_term.items():
        if at in ("OBSERVE", "WAIT_FOR_DATA"):
            assert rows_by_term[t]["suggest_negative"] is False, (
                f"Term '{t}' ({at}) must not be flagged as negative."
            )


def test_pause_target_is_not_marked_as_negative(dataset_id):
    """PAUSE_TARGET is a pause action, not a negative — guard the distinction."""
    d = _ku(dataset_id)
    if not d["rows"] or d["rows"][0].get("regalia_source") == "none":
        pytest.skip("No economy")
    recs = _recs(dataset_id)
    pause_terms = {r["term"] for r in recs["recommendations"]
                   if r.get("term") and r["action_type"] == "PAUSE_TARGET"}
    if not pause_terms:
        pytest.skip("No PAUSE_TARGET in fixture")
    rows_by_term = {r["term"]: r for r in d["rows"]}
    for t in pause_terms:
        assert rows_by_term[t]["suggest_negative"] is False


# --- Fallback when economy is missing ----------------------------------------

def test_legacy_fallback_when_no_economy_via_direct_unit(monkeypatch):
    """Unit-level check: when regalia_source=='none', the engine path is
    SKIPPED and the per-row legacy heuristic (already computed before the
    engine block in server.py) is preserved untouched.

    We simulate by directly invoking the engine and confirming that, for an
    empty-economy row, no negative action is emitted — meaning the override
    would set suggest_negative=False if applied. The server guards this with
    `if regalia_source != 'none'` so the row keeps its original legacy value.
    """
    from recommendations import build_recommendations
    row = {
        "term": "no_economy_term", "clicks": 10, "orders": 0, "spend": 5.0,
        "sales": 0.0, "impressions": 100, "cpc_real": None, "cpc_source": "none",
        "regalia_neta_kdp": None, "regalia_source": "none",
        "acos_pe_kdp": None, "acos_siguiente_con_venta": None,
        "consumo_pe": None, "consumo_fase": None, "beneficio_kdp": None,
        "cvr": 0.0, "acos_actual": 0.0,
        "relevance": "unreviewed", "match_type": "exact",
        "campaign": "C1", "customer_search_term": "no_economy_term", "targeting": None,
    }
    recs = build_recommendations(
        [row], dataset_id="T", phase="dominio", regalia_source="none"
    )
    assert recs, "engine should still emit WAIT_FOR_DATA when economy missing"
    assert recs[0].action_type == "WAIT_FOR_DATA"
    # Confirms why server.py SKIPS the override path: the engine would
    # incorrectly force suggest_negative=False for legacy-eligible rows.


# --- Regression guards -------------------------------------------------------

def test_export_negatives_endpoint_still_responds(dataset_id):
    """/export/negatives uses its own clicks/orders rule (not suggest_negative).
    Confirm it still produces a CSV without regression."""
    r = httpx.get(f"{API}/datasets/{dataset_id}/export/negatives", timeout=20)
    assert r.status_code == 200
    assert "Keyword Text" in r.text


def test_autopilot_endpoint_intact(dataset_id):
    r = httpx.get(f"{API}/datasets/{dataset_id}/autopilot", timeout=30)
    assert r.status_code in (200, 503)  # 503 if Claude key missing — that's fine
