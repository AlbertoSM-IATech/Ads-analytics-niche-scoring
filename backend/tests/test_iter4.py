"""Iteration 4 backend tests: Market Score, ACoS sin venta, niche fields, auto_spend.

Re-uses fixtures from backend_test.py via conftest pattern (each test creates its
own dataset to stay independent).
"""
import os
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
    "Campaign Beta,AdGroup B,yoga mat,yoga,exact,500,30,6.00%,$0.40,$12.00,$60.00,2,20.00%,5.0,2025-01-02\n"
)
BOOK_ECONOMY = {"precio_libro": 14.99, "regalias_por_venta": 4.50}
BOOK_INFO = {"title": "Test", "subtitle": "", "description": "", "categories": []}


@pytest.fixture(scope="module")
def session():
    return requests.Session()


@pytest.fixture(scope="module")
def ds_id(session):
    files = {"file": ("iter4.csv", CSV_EN.encode("utf-8"), "text/csv")}
    r = session.post(f"{API}/imports/upload", files=files,
                     data={"marketplace": "us", "dataset_name": "TEST_ITER4"}, timeout=60)
    assert r.status_code == 200, r.text
    ds = r.json()["id"]
    # set economy so badges + score work
    session.put(f"{API}/datasets/{ds}/book",
                json={"info": BOOK_INFO, "economy": BOOK_ECONOMY}, timeout=30)
    yield ds
    session.delete(f"{API}/datasets/{ds}", timeout=30)


# --------------- Market Score (pure unit tests via direct import) ---------------
class TestMarketScoreUnit:
    def test_all_zeros(self):
        from market_score import calculate_market_score
        ms = calculate_market_score(0, 0, 0, 0, 0, 0)
        # vol=2, comp=10, price=0, roy=0, demand=0, comp_checks=0 => 12
        assert ms["total"] >= 5 and ms["total"] <= 20
        assert set(ms["breakdown"].keys()) == {"volume", "competitors", "price",
                                                 "royalties", "demand", "competition_checks"}
        assert ms["label"] in ("muy-bajo", "bajo")

    def test_strong_niche(self):
        from market_score import calculate_market_score
        # vol 2000 -> 18, comp 800 -> 22, price 14.99 -> 15,
        # roy 4.50 (ratio 0.30 -> 4), demand 4 -> 8, comp_checks 2 -> 8 => 75
        ms = calculate_market_score(2000, 800, 14.99, 4.50, 4, 2)
        assert 65 <= ms["total"] <= 85
        assert ms["label"] in ("bueno", "excelente")

    def test_score_increases_with_volume(self):
        from market_score import calculate_market_score
        a = calculate_market_score(50, 1000, 10, 3, 0, 0)["total"]
        b = calculate_market_score(2000, 1000, 10, 3, 0, 0)["total"]
        assert b > a

    def test_score_increases_with_demand_and_competition_checks(self):
        from market_score import calculate_market_score
        a = calculate_market_score(2000, 800, 14.99, 4.50, 0, 0)["total"]
        b = calculate_market_score(2000, 800, 14.99, 4.50, 6, 3)["total"]
        assert b - a >= 20  # demand+comp_checks add up to 24 max

    def test_label_bands(self):
        from market_score import label_for_score
        assert label_for_score(85) == "excelente"
        assert label_for_score(70) == "bueno"
        assert label_for_score(50) == "medio"
        assert label_for_score(30) == "bajo"
        assert label_for_score(10) == "muy-bajo"


class TestAcosSinVentaUnit:
    def test_formula(self):
        from market_score import acos_siguiente_sin_venta_pct
        # spend=10, cpc=0.5, sales=20 → (10.5/20)*100 = 52.5
        assert abs(acos_siguiente_sin_venta_pct(10, 0.5, 20) - 52.5) < 0.01

    def test_none_when_no_sales(self):
        from market_score import acos_siguiente_sin_venta_pct
        assert acos_siguiente_sin_venta_pct(10, 0.5, 0) is None
        assert acos_siguiente_sin_venta_pct(10, 0.5, None) is None


# --------------- Niche fields persistence via PUT /keyword ---------------
class TestNicheFieldsPersistence:
    def test_put_keyword_with_niche_fields(self, session, ds_id):
        payload = {
            "term": "mindfulness book",
            "search_volume": 2000, "competitors": 800,
            "kw_price": 14.99, "kw_royalties": 4.50,
            "demand_checks": 4, "competition_checks": 2,
            "keyword_status": "validated",
        }
        r = session.put(f"{API}/datasets/{ds_id}/keyword", json=payload, timeout=30)
        assert r.status_code == 200, r.text

        u = session.get(f"{API}/datasets/{ds_id}/keywords-unified", timeout=30).json()
        row = next(r for r in u["rows"] if r["term"] == "mindfulness book")
        assert row["search_volume"] == 2000
        assert row["competitors"] == 800
        assert row["kw_price"] == 14.99
        assert row["kw_royalties"] == 4.50
        assert row["demand_checks"] == 4
        assert row["competition_checks"] == 2
        assert row["keyword_status"] == "validated"
        # market_score must be present and reflect the data
        assert row["market_score"] >= 60
        assert row["score_label"] in ("bueno", "excelente", "medio")
        # acos_siguiente_sin_venta must be present
        assert row["acos_siguiente_sin_venta"] is not None

    def test_keyword_detail_market_score_payload(self, session, ds_id):
        # ensure niche data persisted from previous test
        r = session.get(f"{API}/datasets/{ds_id}/keyword-detail",
                        params={"term": "mindfulness book"}, timeout=30)
        assert r.status_code == 200
        m = r.json()["metrics"]
        for f in ("market_score", "market_score_breakdown", "score_label",
                  "acos_siguiente_sin_venta", "keyword_status",
                  "search_volume", "competitors", "kw_price", "kw_royalties",
                  "demand_checks", "competition_checks"):
            assert f in m, f"missing {f}"
        bd = m["market_score_breakdown"]
        for k in ("volume", "competitors", "price", "royalties", "market_structure", "catalog_signals"):
            assert k in bd
            assert "points" in bd[k] and "max" in bd[k]
        assert m["score_label"] in ("muy-bajo", "bajo", "medio", "bueno", "excelente")


# --------------- auto_spend recalculation ---------------
class TestAutoSpend:
    def test_auto_spend_overwrites_spend(self, session, ds_id):
        payload = {
            "term": "yoga mat",
            "clicks": 100, "cpc": 0.55, "spend": 999.0,  # spend will be overwritten
            "auto_spend": True,
        }
        r = session.put(f"{API}/datasets/{ds_id}/keyword", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        u = session.get(f"{API}/datasets/{ds_id}/keywords-unified", timeout=30).json()
        row = next(r for r in u["rows"] if r["term"] == "yoga mat")
        # spend should equal 100 * 0.55 = 55.0
        assert abs(row["spend"] - 55.0) < 0.01
        assert row["clicks"] == 100
        # cleanup override so other tests aren't affected
        session.delete(f"{API}/datasets/{ds_id}/keyword/yoga mat", timeout=30)

    def test_no_auto_spend_keeps_spend(self, session, ds_id):
        payload = {
            "term": "yoga mat",
            "clicks": 100, "cpc": 0.55, "spend": 999.0,
            "auto_spend": False,
        }
        r = session.put(f"{API}/datasets/{ds_id}/keyword", json=payload, timeout=30)
        assert r.status_code == 200
        u = session.get(f"{API}/datasets/{ds_id}/keywords-unified", timeout=30).json()
        row = next(r for r in u["rows"] if r["term"] == "yoga mat")
        assert abs(row["spend"] - 999.0) < 0.01
        session.delete(f"{API}/datasets/{ds_id}/keyword/yoga mat", timeout=30)


# --------------- ACOS sin venta exposed in unified rows ---------------
class TestAcosSinVentaInUnified:
    def test_acos_sin_venta_in_row(self, session, ds_id):
        u = session.get(f"{API}/datasets/{ds_id}/keywords-unified", timeout=30).json()
        for row in u["rows"]:
            assert "acos_siguiente_sin_venta" in row
            if (row.get("sales") or 0) <= 0:
                assert row["acos_siguiente_sin_venta"] is None
            else:
                # > acos_actual (worst case)
                if row.get("acos_actual") is not None:
                    assert row["acos_siguiente_sin_venta"] >= row["acos_actual"] - 0.01
