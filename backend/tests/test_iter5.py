"""Iteration 5 backend tests: simulation in keyword-detail, Campaign Plans CRUD,
plan summary with phase target, and export/negatives CSV (Amazon Bulk Sheet).
"""
import os
import csv
import io
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

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
BOOK_ECONOMY = {"precio_libro": 14.99, "regalias_por_venta": 4.50}
BOOK_INFO = {"title": "Iter5", "subtitle": "", "description": "", "categories": []}


@pytest.fixture(scope="module")
def session():
    return requests.Session()


@pytest.fixture(scope="module")
def ds_id(session):
    files = {"file": ("iter5.csv", CSV_EN.encode("utf-8"), "text/csv")}
    r = session.post(f"{API}/imports/upload", files=files,
                     data={"marketplace": "us", "dataset_name": "TEST_ITER5"}, timeout=60)
    assert r.status_code == 200, r.text
    ds = r.json()["id"]
    session.put(f"{API}/datasets/{ds}/book",
                json={"info": BOOK_INFO, "economy": BOOK_ECONOMY}, timeout=30)
    yield ds
    session.delete(f"{API}/datasets/{ds}", timeout=30)


# -------- Simulation in keyword-detail --------
class TestSimulation:
    def test_simulation_present_with_price(self, session, ds_id):
        r = session.get(f"{API}/datasets/{ds_id}/keyword-detail",
                        params={"term": "mindfulness book"}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        sim = body["simulation"]
        assert sim is not None
        m = body["metrics"]
        assert sim["clicks_next"] == (m["clicks"] or 0) + 1
        assert sim["orders_next"] == (m["orders"] or 0) + 1
        expected_spend = round((m["spend"] or 0) + (m["cpc"] or 0), 2)
        expected_sales = round((m["sales"] or 0) + 14.99, 2)
        assert abs(sim["spend_next"] - expected_spend) < 0.01
        assert abs(sim["sales_next"] - expected_sales) < 0.01
        expected_acos = round(expected_spend / expected_sales * 100, 2)
        assert abs(sim["acos_next_with_sale"] - expected_acos) < 0.05
        # no-sale: spend+cpc / current sales *100
        if (m["sales"] or 0) > 0:
            expected_no = round(((m["spend"] or 0) + (m["cpc"] or 0)) / (m["sales"]) * 100, 2)
            assert abs(sim["acos_next_no_sale"] - expected_no) < 0.05

    def test_simulation_null_when_no_price(self, session):
        files = {"file": ("iter5_noprice.csv", CSV_EN.encode("utf-8"), "text/csv")}
        r = session.post(f"{API}/imports/upload", files=files,
                         data={"marketplace": "us", "dataset_name": "TEST_ITER5_NOPRICE"}, timeout=60)
        ds = r.json()["id"]
        try:
            g = session.get(f"{API}/datasets/{ds}/keyword-detail",
                            params={"term": "mindfulness book"}, timeout=30)
            assert g.status_code == 200
            assert g.json()["simulation"] is None
        finally:
            session.delete(f"{API}/datasets/{ds}", timeout=30)

    def test_simulation_no_sale_null_when_no_sales(self, session, ds_id):
        r = session.get(f"{API}/datasets/{ds_id}/keyword-detail",
                        params={"term": "buddha quotes"}, timeout=30)
        assert r.status_code == 200
        sim = r.json()["simulation"]
        assert sim is not None
        # sales=0 → acos_next_no_sale must be None
        assert sim["acos_next_no_sale"] is None


# -------- Campaign Plans CRUD --------
class TestCampaignPlansCRUD:
    def test_list_empty(self, session, ds_id):
        r = session.get(f"{API}/datasets/{ds_id}/plans", timeout=30)
        assert r.status_code == 200
        assert r.json() == {}

    def test_create_plan(self, session, ds_id):
        payload = {
            "name": "TEST_plan_lanzamiento",
            "phase": "lanzamiento",
            "target_acos": 40.0,
            "daily_budget": 10.0,
            "keyword_terms": ["mindfulness book", "yoga mat"],
            "notes": "initial plan",
        }
        r = session.post(f"{API}/datasets/{ds_id}/plans", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        plan = r.json()
        assert "id" in plan and len(plan["id"]) > 10
        assert "created_at" in plan
        assert plan["name"] == "TEST_plan_lanzamiento"
        assert plan["phase"] == "lanzamiento"
        assert plan["keyword_terms"] == ["mindfulness book", "yoga mat"]
        # GET verifies persistence
        lst = session.get(f"{API}/datasets/{ds_id}/plans", timeout=30).json()
        assert plan["id"] in lst
        assert lst[plan["id"]]["name"] == "TEST_plan_lanzamiento"

    def test_create_empty_name_400(self, session, ds_id):
        r = session.post(f"{API}/datasets/{ds_id}/plans",
                         json={"name": "  ", "phase": "lanzamiento"}, timeout=30)
        assert r.status_code == 400

    def test_create_unknown_dataset_404(self, session):
        r = session.post(f"{API}/datasets/nope-xxx/plans",
                         json={"name": "x", "phase": "lanzamiento"}, timeout=30)
        assert r.status_code == 404

    def test_update_plan(self, session, ds_id):
        # create then update
        c = session.post(f"{API}/datasets/{ds_id}/plans",
                         json={"name": "TEST_upd", "phase": "lanzamiento",
                               "keyword_terms": ["mindfulness book"]}, timeout=30)
        pid = c.json()["id"]
        u = session.put(f"{API}/datasets/{ds_id}/plans/{pid}",
                        json={"phase": "dominio",
                              "keyword_terms": ["mindfulness book", "yoga mat"]},
                        timeout=30)
        assert u.status_code == 200
        updated = u.json()
        assert updated["phase"] == "dominio"
        assert updated["keyword_terms"] == ["mindfulness book", "yoga mat"]
        # GET verification
        lst = session.get(f"{API}/datasets/{ds_id}/plans", timeout=30).json()
        assert lst[pid]["phase"] == "dominio"
        # cleanup
        session.delete(f"{API}/datasets/{ds_id}/plans/{pid}", timeout=30)

    def test_delete_plan(self, session, ds_id):
        c = session.post(f"{API}/datasets/{ds_id}/plans",
                         json={"name": "TEST_del", "phase": "beneficio"}, timeout=30)
        pid = c.json()["id"]
        d = session.delete(f"{API}/datasets/{ds_id}/plans/{pid}", timeout=30)
        assert d.status_code == 200
        assert d.json()["deleted"] == pid
        lst = session.get(f"{API}/datasets/{ds_id}/plans", timeout=30).json()
        assert pid not in lst

    def test_update_unknown_dataset_404(self, session):
        r = session.put(f"{API}/datasets/nope/plans/whatever",
                        json={"phase": "dominio"}, timeout=30)
        assert r.status_code == 404


# -------- Plan Summary --------
class TestPlanSummary:
    def test_summary_totals_and_phase_target(self, session, ds_id):
        # ensure book_economy
        session.put(f"{API}/datasets/{ds_id}/book",
                    json={"info": BOOK_INFO, "economy": BOOK_ECONOMY}, timeout=30)
        c = session.post(f"{API}/datasets/{ds_id}/plans",
                         json={"name": "TEST_summary", "phase": "lanzamiento",
                               "target_acos": 55.0,
                               "keyword_terms": ["mindfulness book", "yoga mat", "missing_kw"]},
                         timeout=30)
        pid = c.json()["id"]
        try:
            r = session.get(f"{API}/datasets/{ds_id}/plans/{pid}/summary", timeout=30)
            assert r.status_code == 200
            body = r.json()
            assert "plan" in body and "totals" in body and "rows" in body
            t = body["totals"]
            # mindfulness: clicks 45, spend 27.90, sales 89.97, orders 3
            # yoga mat: clicks 30, spend 12.00, sales 60.00, orders 2
            assert t["clicks"] == 75
            assert abs(t["spend"] - 39.90) < 0.01
            assert abs(t["sales"] - 149.97) < 0.01
            assert t["orders"] == 5
            # acos = 39.90/149.97*100
            assert abs(t["acos"] - (39.90 / 149.97 * 100)) < 0.1
            assert abs(t["roas"] - (149.97 / 39.90)) < 0.01
            assert t["keyword_count"] == 3
            assert t["keywords_with_data"] == 2
            # acos_equilibrio = 4.50/14.99*100 ≈ 30.02
            eq = 4.50 / 14.99 * 100
            assert abs(t["acos_equilibrio"] - eq) < 0.05
            # phase lanzamiento multiplier 1.7
            assert abs(t["phase_target_acos"] - round(eq * 1.7, 2)) < 0.05
            assert t["target_acos"] == 55.0
            assert len(body["rows"]) == 2
        finally:
            session.delete(f"{API}/datasets/{ds_id}/plans/{pid}", timeout=30)

    def test_phase_multipliers(self, session, ds_id):
        session.put(f"{API}/datasets/{ds_id}/book",
                    json={"info": BOOK_INFO, "economy": BOOK_ECONOMY}, timeout=30)
        eq = 4.50 / 14.99 * 100
        multipliers = {"lanzamiento": 1.7, "dominio": 1.2, "beneficio": 0.5}
        for phase, mul in multipliers.items():
            c = session.post(f"{API}/datasets/{ds_id}/plans",
                             json={"name": f"TEST_{phase}", "phase": phase,
                                   "keyword_terms": ["mindfulness book"]}, timeout=30)
            pid = c.json()["id"]
            s = session.get(f"{API}/datasets/{ds_id}/plans/{pid}/summary", timeout=30).json()
            assert abs(s["totals"]["phase_target_acos"] - round(eq * mul, 2)) < 0.05
            session.delete(f"{API}/datasets/{ds_id}/plans/{pid}", timeout=30)

    def test_summary_plan_404(self, session, ds_id):
        r = session.get(f"{API}/datasets/{ds_id}/plans/nonexistent/summary", timeout=30)
        assert r.status_code == 404


# -------- Export Negatives CSV --------
class TestExportNegatives:
    def test_csv_header_and_rows(self, session, ds_id):
        r = session.get(f"{API}/datasets/{ds_id}/export/negatives",
                        params={"min_clicks": 6}, timeout=30)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        reader = list(csv.reader(io.StringIO(r.text)))
        assert reader[0] == ["Product", "Entity", "Operation", "Campaign Id", "Ad Group Id",
                             "Campaign Name", "Ad Group Name", "Match Type", "Keyword Text"]
        # Candidates: clicks >= 6 AND orders == 0
        # buddha quotes: 20c, 0o → YES
        # no sales term: 10c, 0o → YES
        # mindfulness book: 3 orders → NO
        # yoga mat: 2 orders → NO
        term_col = [row[8] for row in reader[1:]]
        assert "buddha quotes" in term_col
        assert "no sales term" in term_col
        assert "mindfulness book" not in term_col
        assert "yoga mat" not in term_col
        # All data rows must have negativeExact match type and Sponsored Products entity
        for row in reader[1:]:
            assert row[0] == "Sponsored Products"
            assert row[1] == "Negative Keyword"
            assert row[2] == "Create"
            assert row[7] == "negativeExact"

    def test_min_clicks_filter(self, session, ds_id):
        # raising min_clicks to 15 leaves only 'buddha quotes' (20c)
        r = session.get(f"{API}/datasets/{ds_id}/export/negatives",
                        params={"min_clicks": 15}, timeout=30)
        assert r.status_code == 200
        reader = list(csv.reader(io.StringIO(r.text)))
        term_col = [row[8] for row in reader[1:]]
        assert "buddha quotes" in term_col
        assert "no sales term" not in term_col

    def test_export_404(self, session):
        r = session.get(f"{API}/datasets/nope/export/negatives", timeout=30)
        assert r.status_code == 404
