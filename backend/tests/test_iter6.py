"""
Iteration 6 backend tests - Autopilot by phase + inline editing for campaign/match_type.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://amazon-ads-importer.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

BOOK_ECONOMY = {"precio_libro": 10.0, "regalias_por_venta": 3.5}  # PE ≈ 35%
BOOK_INFO = {"title": "book_economy", "subtitle": "", "description": "", "categories": []}

# Build a CSV with a diverse set of rows to exercise all phase rules.
# Terms chosen:
#  - "term_pause_lanz": clicks=13, orders=0, spend=6.5 → pause in all three phases (hard-pause)
#  - "term_pause_dom_ben": clicks=9, orders=0, spend=4.5 → pause in dominio & beneficio, investigate/pause in lanzamiento (clicks<12)
#  - "term_pause_ben_only": clicks=6, orders=0, spend=3.0 → pause in beneficio (>=5), investigate/hold in others (<8 clicks)
#  - "term_scale_lanz": clicks=20, orders=5, spend=10, sales=100 (ACoS 10%, ROAS 10) → scale everywhere but bid delta differs
#  - "term_scale_dom": clicks=10, orders=3, spend=8, sales=40 (ACoS 20%, ROAS 5) → scale dominio (+15%)
#  - "term_scale_ben": clicks=20, orders=6, spend=5, sales=60 (ACoS ~8.3%, ROAS 12) → scale beneficio (+10)
CSV = (
    "Campaign Name,Ad Group Name,Customer Search Term,Keyword Text,Match Type,"
    "Impressions,Clicks,Click-Thru Rate (CTR),Cost Per Click (CPC),Spend,"
    "7 Day Total Sales,7 Day Total Orders (#),"
    "Total Advertising Cost of Sales (ACOS),Total Return on Advertising Spend (ROAS),Start Date\n"
    "Camp A,Grp 1,term_pause_lanz,x,broad,500,13,2.6%,0.50,6.50,0.00,0,0.00%,0,2025-01-01\n"
    "Camp A,Grp 1,term_pause_dom_ben,x,broad,400,9,2.3%,0.50,4.50,0.00,0,0.00%,0,2025-01-01\n"
    "Camp A,Grp 1,term_pause_ben_only,x,broad,300,6,2.0%,0.50,3.00,0.00,0,0.00%,0,2025-01-01\n"
    "Camp A,Grp 1,term_scale_lanz,x,exact,1000,20,2.0%,0.50,10.00,100.00,5,10.00%,10.0,2025-01-01\n"
    "Camp A,Grp 1,term_scale_dom,x,exact,500,10,2.0%,0.80,8.00,40.00,3,20.00%,5.0,2025-01-01\n"
    "Camp A,Grp 1,term_scale_ben,x,exact,800,20,2.5%,0.25,5.00,60.00,6,8.33%,12.0,2025-01-01\n"
)


@pytest.fixture(scope="module")
def session():
    return requests.Session()


@pytest.fixture(scope="module")
def ds(session):
    files = {"file": ("iter6.csv", CSV.encode("utf-8"), "text/csv")}
    data = {"marketplace": "us", "dataset_name": "TEST_ITER6"}
    r = session.post(f"{API}/imports/upload", files=files, data=data, timeout=60)
    assert r.status_code == 200, r.text
    j = r.json()
    # Configure book economy for PE calculation
    b = session.put(f"{API}/datasets/{j['id']}/book",
                    json={"info": BOOK_INFO, "economy": BOOK_ECONOMY}, timeout=30)
    assert b.status_code == 200
    yield j
    session.delete(f"{API}/datasets/{j['id']}", timeout=30)


class TestAutopilotPhases:
    def test_phase_lanzamiento_multiplier_and_structure(self, session, ds):
        r = session.get(f"{API}/datasets/{ds['id']}/autopilot",
                        params={"phase": "lanzamiento"}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["phase"] == "lanzamiento"
        assert body["target_multiplier"] == 1.7
        assert body["acos_equilibrio"] is not None
        assert abs(body["acos_equilibrio"] - 35.0) < 0.5
        assert abs(body["target_acos"] - 35.0 * 1.7) < 0.5
        assert "counts" in body
        for k in ("pause", "scale", "hold", "investigate"):
            assert k in body["counts"]
            assert k in body["actions"]

    def test_phase_dominio_multiplier(self, session, ds):
        r = session.get(f"{API}/datasets/{ds['id']}/autopilot",
                        params={"phase": "dominio"}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["phase"] == "dominio"
        assert body["target_multiplier"] == 1.2

    def test_phase_beneficio_multiplier(self, session, ds):
        r = session.get(f"{API}/datasets/{ds['id']}/autopilot",
                        params={"phase": "beneficio"}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["phase"] == "beneficio"
        assert body["target_multiplier"] == 0.5

    def test_invalid_phase_400(self, session, ds):
        r = session.get(f"{API}/datasets/{ds['id']}/autopilot",
                        params={"phase": "foo"}, timeout=30)
        assert r.status_code == 400

    def test_beneficio_has_more_pauses_than_dominio_and_lanzamiento(self, session, ds):
        def pauses(phase):
            r = session.get(f"{API}/datasets/{ds['id']}/autopilot",
                            params={"phase": phase}, timeout=30)
            assert r.status_code == 200
            return r.json()["counts"]["pause"]
        lanz = pauses("lanzamiento")
        dom = pauses("dominio")
        ben = pauses("beneficio")
        # With our seed data, beneficio should pause MORE than dominio/lanzamiento.
        assert ben >= dom, f"beneficio ({ben}) should be >= dominio ({dom})"
        assert ben > lanz, f"beneficio ({ben}) should be > lanzamiento ({lanz})"

    def test_hard_pause_rules_per_phase(self, session, ds):
        # term_pause_lanz: clicks=13, orders=0 → pause in ALL phases
        # term_pause_dom_ben: clicks=9, orders=0 → pause in dom+ben (thresholds 8 and 5)
        # term_pause_ben_only: clicks=6, orders=0 → pause in beneficio only (threshold 5)
        for phase, expected_pauses in [
            ("lanzamiento", {"term_pause_lanz"}),
            ("dominio", {"term_pause_lanz", "term_pause_dom_ben"}),
            ("beneficio", {"term_pause_lanz", "term_pause_dom_ben", "term_pause_ben_only"}),
        ]:
            r = session.get(f"{API}/datasets/{ds['id']}/autopilot",
                            params={"phase": phase}, timeout=30)
            body = r.json()
            pause_terms = {a["term"] for a in body["actions"]["pause"]}
            assert expected_pauses.issubset(pause_terms), (
                f"Phase {phase}: expected {expected_pauses} ⊆ pauses, got {pause_terms}"
            )

    def test_scale_rule_lanzamiento_plus20(self, session, ds):
        # term_scale_lanz has clicks=20, orders=5, ACoS=10% well below target (lanz ~59.5%)
        r = session.get(f"{API}/datasets/{ds['id']}/autopilot",
                        params={"phase": "lanzamiento"}, timeout=30)
        body = r.json()
        scales = {a["term"]: a for a in body["actions"]["scale"]}
        assert "term_scale_lanz" in scales
        assert scales["term_scale_lanz"]["bid_delta_pct"] == 20

    def test_scale_rule_dominio_plus15(self, session, ds):
        # term_scale_dom: ROAS 5, orders=3, ACoS 20% below dominio target ~42%
        r = session.get(f"{API}/datasets/{ds['id']}/autopilot",
                        params={"phase": "dominio"}, timeout=30)
        body = r.json()
        scales = {a["term"]: a for a in body["actions"]["scale"]}
        assert "term_scale_dom" in scales
        assert scales["term_scale_dom"]["bid_delta_pct"] == 15

    def test_scale_rule_beneficio_plus10(self, session, ds):
        # term_scale_ben: ROAS 12, orders=6, ACoS ~8.3% below beneficio target ~17.5%
        r = session.get(f"{API}/datasets/{ds['id']}/autopilot",
                        params={"phase": "beneficio"}, timeout=30)
        body = r.json()
        scales = {a["term"]: a for a in body["actions"]["scale"]}
        assert "term_scale_ben" in scales
        assert scales["term_scale_ben"]["bid_delta_pct"] == 10


class TestAutopilotExportPhases:
    def test_export_csv_differs_by_phase(self, session, ds):
        r_d = session.get(f"{API}/datasets/{ds['id']}/export/autopilot",
                          params={"phase": "dominio"}, timeout=30)
        r_b = session.get(f"{API}/datasets/{ds['id']}/export/autopilot",
                          params={"phase": "beneficio"}, timeout=30)
        assert r_d.status_code == 200
        assert r_b.status_code == 200
        assert "text/csv" in r_d.headers.get("content-type", "")
        csv_d = r_d.text
        csv_b = r_b.text
        assert csv_d != csv_b
        # Both must contain the header
        assert csv_d.splitlines()[0].startswith("Product,Entity,Operation")
        # Beneficio should have MORE 'Pause' rows than Dominio
        count_d = csv_d.count(",Pause,")
        count_b = csv_b.count(",Pause,")
        assert count_b > count_d, f"beneficio pauses ({count_b}) must exceed dominio ({count_d})"


class TestKeywordInlineEditCampaignMatch:
    def test_put_keyword_campaign_reflects_in_unified(self, session, ds):
        payload = {"term": "term_scale_dom", "campaign": "TEST_NewCamp"}
        r = session.put(f"{API}/datasets/{ds['id']}/keyword", json=payload, timeout=30)
        assert r.status_code == 200
        assert r.json().get("ok") is True
        # Verify persistence via keywords-unified
        u = session.get(f"{API}/datasets/{ds['id']}/keywords-unified", timeout=30).json()
        row = next(r for r in u["rows"] if r["term"] == "term_scale_dom")
        assert row["campaign"] == "TEST_NewCamp"

    def test_put_keyword_match_type_reflects_in_unified(self, session, ds):
        payload = {"term": "term_scale_dom", "match_type": "phrase"}
        r = session.put(f"{API}/datasets/{ds['id']}/keyword", json=payload, timeout=30)
        assert r.status_code == 200
        u = session.get(f"{API}/datasets/{ds['id']}/keywords-unified", timeout=30).json()
        row = next(r for r in u["rows"] if r["term"] == "term_scale_dom")
        assert row["match_type"] == "phrase"
        # Campaign set in previous test should still be present
        assert row["campaign"] == "TEST_NewCamp"

    def test_put_keyword_campaign_and_match_together(self, session, ds):
        payload = {"term": "term_scale_ben", "campaign": "TEST_CampB", "match_type": "exact"}
        r = session.put(f"{API}/datasets/{ds['id']}/keyword", json=payload, timeout=30)
        assert r.status_code == 200
        u = session.get(f"{API}/datasets/{ds['id']}/keywords-unified", timeout=30).json()
        row = next(r for r in u["rows"] if r["term"] == "term_scale_ben")
        assert row["campaign"] == "TEST_CampB"
        assert row["match_type"] == "exact"
