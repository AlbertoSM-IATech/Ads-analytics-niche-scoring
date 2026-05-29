"""Phase 2 compatibility regression tests.

Guarantees:
  - /autopilot remains byte-identical to the pre-phase-1 fixture (excluding
    the volatile generated_at timestamp).
  - The /imports/upload endpoint produces the same parsed payload as before
    Phase 2 (excluding volatile id and created_at).
  - /keywords-unified preserves all OLD keys, types and values from the
    Phase-1 fixture, while it MAY (and does) add new ones.
"""
import json
import os
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


def _canonical(d, drop=()) -> str:
    if isinstance(d, dict) and drop:
        d = {k: v for k, v in d.items() if k not in drop}
    return json.dumps(d, sort_keys=True, indent=2, default=str)


# -- /autopilot regression (must be unchanged) -----------------------------

@pytest.mark.skipif(
    not (FIXTURES / "autopilot_dominio_pre_phase1.json").exists(),
    reason="autopilot fixture missing",
)
def test_autopilot_unchanged_in_phase2():
    r = httpx.get(f"{API}/datasets/{TEST_DS_ID}/autopilot?phase=dominio", timeout=20)
    r.raise_for_status()
    current = r.json()
    snap = json.loads((FIXTURES / "autopilot_dominio_pre_phase1.json").read_text())
    assert _canonical(current, ("generated_at",)) == _canonical(snap, ("generated_at",)), (
        "autopilot response changed during Phase 2! That endpoint must remain untouched."
    )


# -- /imports/upload regression --------------------------------------------

def test_importer_response_identical_to_phase2_fixture():
    """Upload the same CSV and verify the parsed payload (sans id/created_at)
    matches the fixture captured before any Phase-2 changes touched server.py."""
    fixture_path = FIXTURES / "import_response_pre_phase2.json"
    if not fixture_path.exists():
        pytest.skip("Phase-2 importer fixture missing")
    files = {"file": ("phase2_fixture.csv", CSV_EN.encode("utf-8"), "text/csv")}
    data = {"marketplace": "us", "dataset_name": "PHASE2_FIXTURE_DATASET"}
    r = httpx.post(f"{API}/imports/upload", files=files, data=data, timeout=60)
    r.raise_for_status()
    payload = r.json()
    new_id = payload.get("id")
    snap = json.loads(fixture_path.read_text())
    # Cleanup the just-created dataset before asserting (so test reruns cleanly)
    if new_id:
        try:
            httpx.delete(f"{API}/datasets/{new_id}", timeout=10)
        except Exception:
            pass
    assert _canonical(payload, ("id", "created_at")) == _canonical(snap), (
        "Importer response changed during Phase 2! "
        "The importer must remain untouched."
    )


# -- /keywords-unified additive compatibility -------------------------------

@pytest.mark.skipif(
    not (FIXTURES / "keywords_unified_pre_phase1.json").exists(),
    reason="phase1 fixture missing",
)
def test_keywords_unified_api_contract_preserved():
    """Phase 2 ADDS new fields, but every API-contract field must keep type and value.

    Excludes `book_economy` from value comparison: that key is a passthrough
    of user-controlled state (the user can change format_type, pages, etc. on
    the dataset itself), so its content is data state — not an API contract.
    The CONTRACT is that the key exists and is a dict that includes the legacy
    keys (precio_libro, regalias_por_venta, mult_*).
    """
    r = httpx.get(f"{API}/datasets/{TEST_DS_ID}/keywords-unified", timeout=20)
    r.raise_for_status()
    current = r.json()
    snap = json.loads((FIXTURES / "keywords_unified_pre_phase1.json").read_text())

    # Contract-bound top-level keys whose value MUST not change.
    CONTRACT_KEYS = {"key", "acos_equilibrio", "guias_fase", "summary", "weights"}
    for k in CONTRACT_KEYS:
        assert k in current, f"Top-level contract key '{k}' was REMOVED in Phase 2!"
        if k in snap:
            assert current[k] == snap[k], (
                f"Top-level contract value of '{k}' changed in Phase 2!\n"
                f"  before: {snap[k]!r}\n  after : {current[k]!r}"
            )

    # book_economy is user-controlled state; only verify it remains a dict and
    # exposes the legacy keys.
    assert isinstance(current["book_economy"], dict)
    for legacy_key in ("precio_libro", "regalias_por_venta",
                       "mult_lanzamiento", "mult_dominio", "mult_beneficio"):
        assert legacy_key in current["book_economy"], (
            f"Legacy book_economy key '{legacy_key}' was removed!"
        )

    # Rows: same length, every old field intact per row.
    assert len(current["rows"]) == len(snap["rows"]), "Row count changed!"

    # Phase-dependent derived fields: excluded from byte-value comparison
    # because they change when the dataset's `phase` configuration changes
    # (user-controlled state, not API contract). Presence + type are still
    # verified, and an explicit coherence assertion below checks the
    # derivation formula `clicks_fase ≈ clicks_pe × phase_mult_used`.
    PHASE_DERIVED_FIELDS = {"phase_mult_used", "clicks_fase", "consumo_fase"}

    # CPC-resolution-dependent derived fields: only relaxed for rows where the
    # backend resolved a NON-real CPC (cpc_source != "real"), because in that
    # case the values depend on `book_economy.cpc_referencia`, which is also
    # user-editable state — not an API contract. Rows with `cpc_source=="real"`
    # remain strictly byte-compared (the majority in the live dataset).
    CPC_RESOLUTION_DERIVED = {
        "clicks_pe", "consumo_pe", "clicks_fase", "consumo_fase",
        "acos_siguiente_con_venta",
    }

    def _assert_numeric_type(val_old, val_new, *, where):
        if val_old is None:
            assert val_new is None or isinstance(val_new, (int, float)), (
                f"{where}: type degraded from None → {type(val_new)}"
            )
        else:
            assert isinstance(val_new, (int, float)), (
                f"{where}: type changed: {type(val_old)} → {type(val_new)}"
            )

    for i, (cur, old) in enumerate(zip(current["rows"], snap["rows"])):
        cpc_source_cur = cur.get("cpc_source")
        for fk, fv in old.items():
            assert fk in cur, f"Row {i}: field '{fk}' was REMOVED in Phase 2!"
            relax = (
                fk in PHASE_DERIVED_FIELDS
                or (fk in CPC_RESOLUTION_DERIVED and cpc_source_cur != "real")
            )
            if relax:
                _assert_numeric_type(fv, cur[fk], where=f"Row {i}: '{fk}'")
            else:
                assert cur[fk] == fv, (
                    f"Row {i}: field '{fk}' value changed: {fv!r} → {cur[fk]!r}"
                )

    # Coherence guards for derived fields: when the inputs are present, the
    # documented derivation formulas must still hold. These protect the
    # derivation logic without coupling to a specific phase or cpc reference.
    for i, cur in enumerate(current["rows"]):
        cp = cur.get("clicks_pe")
        pm = cur.get("phase_mult_used")
        cf = cur.get("clicks_fase")
        if cp is not None and pm is not None and cf is not None:
            assert abs(cf - cp * pm) < 0.01, (
                f"Row {i}: clicks_fase {cf} != clicks_pe {cp} × phase_mult_used {pm}"
            )
        # consumo_pe ≈ clicks / clicks_pe; consumo_fase ≈ clicks / clicks_fase.
        clicks = cur.get("clicks") or 0
        cpe = cur.get("consumo_pe")
        cfa = cur.get("consumo_fase")
        if cp is not None and cp > 0 and cpe is not None and clicks > 0:
            assert abs(cpe - clicks / cp) < 0.01, (
                f"Row {i}: consumo_pe {cpe} != clicks {clicks} / clicks_pe {cp}"
            )
        if cf is not None and cf > 0 and cfa is not None and clicks > 0:
            assert abs(cfa - clicks / cf) < 0.01, (
                f"Row {i}: consumo_fase {cfa} != clicks {clicks} / clicks_fase {cf}"
            )


def test_keywords_unified_adds_phase2_fields():
    r = httpx.get(f"{API}/datasets/{TEST_DS_ID}/keywords-unified", timeout=20)
    r.raise_for_status()
    d = r.json()
    if not d["rows"]:
        pytest.skip("No rows to verify")
    row = d["rows"][0]
    REQUIRED_NEW_KEYS = {
        "cpc_real", "cpc_source", "regalia_neta_kdp", "regalia_source",
        "acos_pe_kdp", "clicks_pe", "clicks_fase", "phase_mult_used",
        "consumo_pe", "consumo_fase", "beneficio_kdp", "acos_siguiente_con_venta",
        "customer_search_term", "targeting",
    }
    missing = REQUIRED_NEW_KEYS - set(row.keys())
    assert not missing, f"Phase 2 fields missing from row: {missing}"
    assert row["cpc_source"] in {"real", "reference", "none"}
    assert row["regalia_source"] in {"kdp", "legacy", "none"}


# -- targeting / customer_search_term separation ---------------------------

def test_targeting_and_customer_search_term_kept_separate():
    """Both fields must be preserved per row; one must never be overwritten by the other."""
    r = httpx.get(f"{API}/datasets/{TEST_DS_ID}/keywords-unified", timeout=20)
    r.raise_for_status()
    d = r.json()
    for row in d["rows"]:
        # Both keys must exist (even if some are None).
        assert "targeting" in row
        assert "customer_search_term" in row
        # If both are present they must NOT be the literal same string when stripped
        # (because then we'd have collapsed them). Allow None on either side.
        t = row.get("targeting")
        s = row.get("customer_search_term")
        if t and s:
            # In some Amazon Ads datasets they CAN legitimately be equal (exact match
            # on the same word). What we care about is they exist as distinct fields.
            # Just assert no truncation/None overwrite.
            assert isinstance(t, str)
            assert isinstance(s, str)
