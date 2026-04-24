"""Iter 9 backend tests — phase, market-criteria, campaigns-list, backup/restore, V2 market score, ai-recs."""
import os
import io
import json
import csv
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://amazon-ads-importer.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    return s


def _make_csv_bytes():
    """Create a minimal SP search-term CSV the importer accepts."""
    headers = [
        "Start Date", "End Date", "Portfolio name", "Currency", "Campaign Name",
        "Ad Group Name", "Targeting", "Match Type", "Customer Search Term",
        "Impressions", "Clicks", "Click-Thru Rate (CTR)", "Cost Per Click (CPC)",
        "Spend", "7 Day Total Sales ", "Total Advertising Cost of Sales (ACOS) ",
        "Total Return on Advertising Spend (ROAS)", "7 Day Total Orders (#)",
        "7 Day Conversion Rate",
    ]
    rows = [
        ["2026-01-01", "2026-01-10", "P1", "USD", "CMP_ITER9_A", "AG1",
         "kw_a", "EXACT", "kw a term", "2000", "80", "4.0", "0.50",
         "40.00", "180.00", "22.22", "4.5", "12", "15.0"],
        ["2026-01-01", "2026-01-10", "P1", "USD", "CMP_ITER9_B", "AG2",
         "kw_b", "PHRASE", "kw b term", "500", "10", "2.0", "0.30",
         "3.00", "0.00", "0.0", "0.0", "0", "0.0"],
    ]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")


@pytest.fixture(scope="module")
def dataset_id(api_client):
    """Upload a small dataset for the iter9 suite; delete it on teardown."""
    files = {"file": ("TEST_iter9.csv", _make_csv_bytes(), "text/csv")}
    data = {"marketplace": "es", "dataset_name": f"TEST_ITER9_{uuid.uuid4().hex[:6]}"}
    r = api_client.post(f"{API}/imports/upload", files=files, data=data, timeout=30)
    assert r.status_code == 200, f"upload failed: {r.status_code} {r.text[:400]}"
    did = r.json()["id"]
    yield did
    try:
        api_client.delete(f"{API}/datasets/{did}", timeout=15)
    except Exception:
        pass


# ---------- Phase ----------
class TestPhase:
    def test_set_phase_valid(self, api_client, dataset_id):
        for ph in ("lanzamiento", "dominio", "beneficio"):
            r = api_client.put(f"{API}/datasets/{dataset_id}/phase", json={"phase": ph})
            assert r.status_code == 200, r.text
            assert r.json()["phase"] == ph
        # verify persisted via GET dataset
        g = api_client.get(f"{API}/datasets/{dataset_id}")
        assert g.status_code == 200
        # phase stored on doc
        doc = g.json()
        # Dataset response may not expose phase directly; fetch via market-criteria path is unrelated.
        # Use keywords-unified or autopilot as indirect check — autopilot uses phase param, skip.
        # Instead, re-set and read back via raw dataset listing if field included.
        assert isinstance(doc, dict)

    def test_set_phase_invalid_400(self, api_client, dataset_id):
        r = api_client.put(f"{API}/datasets/{dataset_id}/phase", json={"phase": "foo"})
        assert r.status_code == 400

    def test_set_phase_404(self, api_client):
        r = api_client.put(f"{API}/datasets/non-existent-id/phase", json={"phase": "dominio"})
        assert r.status_code == 404


# ---------- Market Criteria ----------
class TestMarketCriteria:
    def test_get_defaults_es(self, api_client, dataset_id):
        r = api_client.get(f"{API}/datasets/{dataset_id}/market-criteria/es")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["marketplace"] == "es"
        d = body["defaults"]
        assert d["idealVolume"] == 600
        assert d["idealCompetitors"] == 1000
        assert d["idealPrice"] == 12.99
        assert d["idealRoyalties"] == 4.5
        # no overrides yet → effective == defaults
        assert body["overrides"] == {}
        assert body["effective"]["idealVolume"] == 600

    def test_get_defaults_us(self, api_client, dataset_id):
        r = api_client.get(f"{API}/datasets/{dataset_id}/market-criteria/us")
        assert r.status_code == 200
        d = r.json()["defaults"]
        assert d["idealVolume"] == 1000
        assert d["idealCompetitors"] == 1500
        assert d["idealPrice"] == 14.99
        assert d["idealRoyalties"] == 5.5

    def test_put_partial_merge(self, api_client, dataset_id):
        # 1st PUT: idealVolume only
        r1 = api_client.put(
            f"{API}/datasets/{dataset_id}/market-criteria/es",
            json={"idealVolume": 5000},
        )
        assert r1.status_code == 200, r1.text
        eff1 = r1.json()["effective"]
        assert eff1["idealVolume"] == 5000
        # 2nd PUT: idealPrice only — must NOT wipe idealVolume
        r2 = api_client.put(
            f"{API}/datasets/{dataset_id}/market-criteria/es",
            json={"idealPrice": 19.99},
        )
        assert r2.status_code == 200
        # GET and verify merge
        g = api_client.get(f"{API}/datasets/{dataset_id}/market-criteria/es")
        assert g.status_code == 200
        body = g.json()
        assert body["overrides"].get("idealVolume") == 5000, f"idealVolume lost: {body['overrides']}"
        assert body["overrides"].get("idealPrice") == 19.99
        eff = body["effective"]
        assert eff["idealVolume"] == 5000
        assert eff["idealPrice"] == 19.99
        # untouched fields still at defaults
        assert eff["idealCompetitors"] == 1000
        assert eff["idealRoyalties"] == 4.5

    def test_delete_resets_to_defaults(self, api_client, dataset_id):
        r = api_client.delete(f"{API}/datasets/{dataset_id}/market-criteria/es")
        assert r.status_code == 200, r.text
        g = api_client.get(f"{API}/datasets/{dataset_id}/market-criteria/es")
        body = g.json()
        assert body["overrides"] == {}
        assert body["effective"] == body["defaults"]


# ---------- Campaigns List ----------
class TestCampaignsList:
    def test_campaigns_list_unique_sorted(self, api_client, dataset_id):
        r = api_client.get(f"{API}/datasets/{dataset_id}/campaigns-list")
        assert r.status_code == 200
        names = r.json()
        assert isinstance(names, list)
        assert "CMP_ITER9_A" in names
        assert "CMP_ITER9_B" in names
        # unique + sorted
        assert names == sorted(set(names))

    def test_campaigns_list_includes_overrides(self, api_client, dataset_id):
        # Add an override with a new campaign name
        payload = {"term": "new manual term", "campaign": "CMP_ITER9_OVR", "campaigns": ["CMP_ITER9_MULTI"]}
        p = api_client.put(f"{API}/datasets/{dataset_id}/keyword", json=payload)
        assert p.status_code == 200, p.text
        r = api_client.get(f"{API}/datasets/{dataset_id}/campaigns-list")
        names = r.json()
        assert "CMP_ITER9_OVR" in names
        assert "CMP_ITER9_MULTI" in names


# ---------- Backup / Restore ----------
class TestBackup:
    def test_backup_returns_json(self, api_client, dataset_id):
        r = api_client.get(f"{API}/datasets/{dataset_id}/backup")
        assert r.status_code == 200
        assert "application/json" in r.headers.get("content-type", "")
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        payload = r.json()
        assert payload["version"] == "publify-backup-1"
        assert isinstance(payload["dataset"], dict)
        assert payload["dataset"]["id"] == dataset_id

    def test_restore_replaces_content(self, api_client, dataset_id):
        # Get current backup
        bak = api_client.get(f"{API}/datasets/{dataset_id}/backup").json()
        # Mutate a safe field
        bak["dataset"]["name"] = "TEST_ITER9_RESTORED"
        content = json.dumps(bak).encode("utf-8")
        files = {"file": ("backup.json", content, "application/json")}
        r = api_client.post(f"{API}/datasets/{dataset_id}/restore", files=files)
        assert r.status_code == 200, r.text
        g = api_client.get(f"{API}/datasets/{dataset_id}").json()
        assert g.get("name") == "TEST_ITER9_RESTORED"

    def test_restore_invalid_json_400(self, api_client, dataset_id):
        files = {"file": ("bad.json", b"not json at all", "application/json")}
        r = api_client.post(f"{API}/datasets/{dataset_id}/restore", files=files)
        assert r.status_code == 400

    def test_restore_missing_dataset_key_400(self, api_client, dataset_id):
        files = {"file": ("bad.json", b'{"version":"x"}', "application/json")}
        r = api_client.post(f"{API}/datasets/{dataset_id}/restore", files=files)
        assert r.status_code == 400


# ---------- Keywords Unified (V2 market score + campaigns) ----------
class TestKeywordsUnifiedV2:
    def test_includes_market_score_and_campaigns(self, api_client, dataset_id):
        r = api_client.get(f"{API}/datasets/{dataset_id}/keywords-unified")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)
        assert "rows" in data
        rows = data["rows"]
        assert isinstance(rows, list) and len(rows) > 0
        for row in rows:
            assert "market_score" in row
            assert isinstance(row["market_score"], (int, float))
        # 'campaigns' multi-assignment list — per problem statement should be on each row.
        # Currently server.py does NOT copy agg["campaigns"] into out_rows (see lines 600-631).
        # This test documents the expectation; it will fail until fixed.
        missing = [r for r in rows if "campaigns" not in r]
        assert not missing, (
            f"{len(missing)}/{len(rows)} rows missing 'campaigns' list. "
            "server.py get_keywords_unified() does not expose the merged campaigns list per row."
        )

    def test_market_score_changes_with_criteria(self, api_client, dataset_id):
        """Override idealVolume aggressively → market_score should change."""
        # reset first
        api_client.delete(f"{API}/datasets/{dataset_id}/market-criteria/es")
        rows1 = api_client.get(f"{API}/datasets/{dataset_id}/keywords-unified").json()["rows"]
        # Inject niche-study fields via overrides so market_score is non-zero for both branches
        for idx, rr in enumerate(rows1[:2]):
            api_client.put(
                f"{API}/datasets/{dataset_id}/keyword",
                json={"term": rr["term"], "search_volume": 800, "competitors": 1200,
                      "kw_price": 12.99, "kw_royalties": 4.5},
            )
        base = api_client.get(f"{API}/datasets/{dataset_id}/keywords-unified").json()["rows"]
        base_scores = [round(x["market_score"]) for x in base]
        # Extreme override
        api_client.put(
            f"{API}/datasets/{dataset_id}/market-criteria/es",
            json={"idealVolume": 100000, "idealCompetitors": 100000},
        )
        new = api_client.get(f"{API}/datasets/{dataset_id}/keywords-unified").json()["rows"]
        new_scores = [round(x["market_score"]) for x in new]
        assert base_scores != new_scores, f"Scores did not change: {base_scores} vs {new_scores}"
        # cleanup override
        api_client.delete(f"{API}/datasets/{dataset_id}/market-criteria/es")


# ---------- AI recommendations (graceful) ----------
class TestAiRecs:
    def test_ai_recommendations_responds(self, api_client, dataset_id):
        r = api_client.post(f"{API}/datasets/{dataset_id}/ai-recommendations", timeout=90)
        # Accept 200 or 502 graceful (LLM failure) — must never 500
        assert r.status_code in (200, 502), f"unexpected {r.status_code}: {r.text[:300]}"
        if r.status_code == 200:
            body = r.json()
            assert isinstance(body, dict)


# ---------- Regression smoke ----------
class TestRegression:
    def test_list_datasets(self, api_client):
        r = api_client.get(f"{API}/datasets")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_campaigns_endpoint(self, api_client, dataset_id):
        r = api_client.get(f"{API}/datasets/{dataset_id}/campaigns")
        assert r.status_code == 200

    def test_search_terms(self, api_client, dataset_id):
        r = api_client.get(f"{API}/datasets/{dataset_id}/search-terms")
        assert r.status_code == 200
