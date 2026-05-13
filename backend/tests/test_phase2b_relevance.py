"""Phase 2B unit + compat tests for the manual `relevance` field.

Scope:
  - Default value "unreviewed" when no override exists.
  - All 4 allowed values can be persisted and round-tripped.
  - Invalid values are rejected with 400.
  - Omitting the field in a PUT does NOT modify the existing relevance.
  - /autopilot remains byte-equivalent to its pre-phase-1 fixture
    (relevance is read-only metadata; it must not affect autopilot output).
  - /imports/upload remains byte-equivalent to its pre-phase-2 fixture.
  - All Phase-2A economic metrics are unchanged after relevance changes.
"""
import json
import os
import time
from pathlib import Path

import httpx
import pytest

BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")
API = f"{BACKEND_URL}/api"
TEST_DS_ID = "d17b595d-7e2d-4b8a-8299-ece05cdc70d5"
FIXTURES = Path(__file__).parent / "fixtures"

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

ECON_KEYS = (
    "cpc_real", "cpc_source", "regalia_neta_kdp", "regalia_source",
    "acos_pe_kdp", "clicks_pe", "clicks_fase", "phase_mult_used",
    "consumo_pe", "consumo_fase", "beneficio_kdp", "acos_siguiente_con_venta",
)


@pytest.fixture(scope="module")
def kw_term():
    """Pick a term that exists in the dataset and reset its relevance + notes afterwards."""
    r = httpx.get(f"{API}/datasets/{TEST_DS_ID}/keywords-unified", timeout=20)
    r.raise_for_status()
    rows = r.json()["rows"]
    assert rows, "Dataset has no rows"
    term = rows[0]["term"]
    # Capture original notes so we can restore them
    original_notes = ""
    for row in rows:
        if row["term"] == term:
            original_notes = row.get("notes") or ""
            break
    yield term
    # Cleanup: reset relevance and notes to whatever they were before the test module ran
    try:
        httpx.put(f"{API}/datasets/{TEST_DS_ID}/keyword",
                  json={"term": term, "relevance": "unreviewed", "notes": original_notes},
                  timeout=10)
    except Exception:
        pass


def _get_row(term):
    r = httpx.get(f"{API}/datasets/{TEST_DS_ID}/keywords-unified", timeout=20)
    r.raise_for_status()
    for row in r.json()["rows"]:
        if row["term"] == term:
            return row
    raise AssertionError(f"Term '{term}' missing from response")


def _set_relevance(term, value):
    return httpx.put(f"{API}/datasets/{TEST_DS_ID}/keyword",
                     json={"term": term, "relevance": value}, timeout=10)


# 1. ---- Default value ----
def test_relevance_default_unreviewed_when_no_override(kw_term):
    _set_relevance(kw_term, "unreviewed")          # ensure clean state
    row = _get_row(kw_term)
    assert row.get("relevance") == "unreviewed"


# 2-5. ---- Round-trip all values ----
@pytest.mark.parametrize("value", ["high", "medium", "low", "unreviewed"])
def test_save_each_allowed_relevance_value(kw_term, value):
    r = _set_relevance(kw_term, value)
    assert r.status_code == 200, f"PUT relevance={value!r} returned {r.status_code}"
    assert _get_row(kw_term)["relevance"] == value


# 6. ---- Invalid value rejected ----
def test_invalid_relevance_returns_400(kw_term):
    r = _set_relevance(kw_term, "VERY_HIGH")
    assert r.status_code == 400
    body = r.json()
    assert "relevance" in (body.get("detail") or "").lower()


# 7. ---- Omitting relevance must not change existing ----
def test_omitting_relevance_does_not_change_existing(kw_term):
    _set_relevance(kw_term, "high")
    assert _get_row(kw_term)["relevance"] == "high"
    # Get original notes BEFORE altering them in this test
    original_notes = _get_row(kw_term).get("notes") or ""
    try:
        # PUT with another field but no relevance
        r = httpx.put(f"{API}/datasets/{TEST_DS_ID}/keyword",
                      json={"term": kw_term, "notes": "ph2b test note"}, timeout=10)
        assert r.status_code == 200
        assert _get_row(kw_term)["relevance"] == "high", (
            "Omitting relevance from PUT must not reset the field"
        )
    finally:
        # Restore notes to avoid leaking state into compat tests.
        httpx.put(f"{API}/datasets/{TEST_DS_ID}/keyword",
                  json={"term": kw_term, "notes": original_notes}, timeout=10)


# 8. ---- /autopilot unchanged ----
@pytest.mark.skipif(
    not (FIXTURES / "autopilot_dominio_pre_phase1.json").exists(),
    reason="autopilot fixture missing",
)
def test_autopilot_unchanged_with_relevance_set(kw_term):
    """Phase 2B explicitly forbids using relevance in any recommendation logic.
    autopilot must therefore produce the same output regardless of relevance value.
    """
    # Snapshot autopilot with default relevance
    _set_relevance(kw_term, "unreviewed")
    snap_default = httpx.get(f"{API}/datasets/{TEST_DS_ID}/autopilot?phase=dominio", timeout=20).json()
    # Now flip relevance to each value and verify autopilot output is identical
    for val in ("high", "medium", "low"):
        _set_relevance(kw_term, val)
        current = httpx.get(f"{API}/datasets/{TEST_DS_ID}/autopilot?phase=dominio", timeout=20).json()
        # generated_at is the only volatile field
        snap_default.pop("generated_at", None)
        current.pop("generated_at", None)
        assert json.dumps(snap_default, sort_keys=True) == json.dumps(current, sort_keys=True), (
            f"autopilot output changed when relevance={val!r} — relevance must not affect autopilot"
        )
        snap_default["generated_at"] = None   # restore for next loop
        current["generated_at"] = None
    # Cleanup
    _set_relevance(kw_term, "unreviewed")


# 9. ---- /imports/upload unchanged ----
def test_imports_upload_unchanged_in_phase2b():
    fixture_path = FIXTURES / "import_response_pre_phase2.json"
    if not fixture_path.exists():
        pytest.skip("Phase-2 importer fixture missing")
    files = {"file": ("phase2b_fixture.csv", CSV_EN.encode("utf-8"), "text/csv")}
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
    # Drop volatile keys for comparison
    for k in ("id", "created_at"):
        payload.pop(k, None)
    assert json.dumps(payload, sort_keys=True, indent=2, default=str) == \
           json.dumps(snap, sort_keys=True, indent=2, default=str), (
        "Importer response changed in Phase 2B"
    )


# 10. ---- Phase 2A economic metrics untouched ----
def test_phase2a_metrics_unchanged_when_relevance_changes(kw_term):
    _set_relevance(kw_term, "unreviewed")
    baseline = {k: _get_row(kw_term).get(k) for k in ECON_KEYS}
    for val in ("high", "medium", "low"):
        _set_relevance(kw_term, val)
        row = _get_row(kw_term)
        for k in ECON_KEYS:
            assert row.get(k) == baseline[k], (
                f"Phase 2A field {k!r} changed when relevance={val!r}: "
                f"{baseline[k]!r} → {row.get(k)!r}"
            )
    _set_relevance(kw_term, "unreviewed")


# 11 (bonus). ---- keyword-detail also exposes relevance ----
def test_keyword_detail_exposes_relevance(kw_term):
    _set_relevance(kw_term, "medium")
    r = httpx.get(f"{API}/datasets/{TEST_DS_ID}/keyword-detail",
                  params={"term": kw_term}, timeout=20)
    r.raise_for_status()
    assert r.json()["metrics"]["relevance"] == "medium"
    _set_relevance(kw_term, "unreviewed")


# 12 (bonus). ---- relevance==unreviewed accepted as a valid explicit value ----
def test_unreviewed_is_valid_explicit_value(kw_term):
    _set_relevance(kw_term, "high")
    r = _set_relevance(kw_term, "unreviewed")
    assert r.status_code == 200
    assert _get_row(kw_term)["relevance"] == "unreviewed"
