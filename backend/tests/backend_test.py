"""
Backend tests for Amazon Ads Analytics API.
Covers:
- Health
- CSV (EN) import + auto-mapping + KPIs
- CSV (ES) import
- XLSX import
- Invalid file 400
- Datasets list / get / delete
- Campaigns aggregation
- Search terms with suggest_negative flag
- Timeseries (date / campaign fallback)
- AI recommendations (Claude via Emergent LLM)
"""
import io
import os
import time
import pytest
import requests
import pandas as pd

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://amazon-ads-importer.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# ---------- Sample data ----------
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

CSV_ES = (
    "Nombre de la campaña,Grupo de anuncios,Término de búsqueda,Palabra clave,Tipo de concordancia,"
    "Impresiones,Clics,CTR,CPC,Gasto,Ventas totales,Pedidos,ACOS,ROAS\n"
    "Campaña 1,G1,meditación diaria,meditacion,broad,2000,30,1.50%,0.35,10.50,45.00,2,23.33,4.28\n"
    "Campaña 2,G2,libros zen,zen,exact,1500,25,1.66%,0.40,10.00,30.00,1,33.33,3.0\n"
)


def _build_xlsx_bytes() -> bytes:
    df = pd.DataFrame(
        [
            ["Camp X", "Grp 1", "kw1", "kw1", "broad", 1000, 50, 5.0, 0.5, 25.0, 100.0, 4, 25.0, 4.0],
            ["Camp Y", "Grp 2", "kw2", "kw2", "exact", 2000, 80, 4.0, 0.4, 32.0, 200.0, 6, 16.0, 6.25],
        ],
        columns=[
            "Campaign Name", "Ad Group Name", "Customer Search Term", "Keyword Text",
            "Match Type", "Impressions", "Clicks", "Click-Thru Rate (CTR)",
            "Cost Per Click (CPC)", "Spend", "7 Day Total Sales",
            "7 Day Total Orders (#)", "Total Advertising Cost of Sales (ACOS)",
            "Total Return on Advertising Spend (ROAS)",
        ],
    )
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    return s


@pytest.fixture(scope="session")
def en_dataset(session):
    files = {"file": ("sp_search_term_en.csv", CSV_EN.encode("utf-8"), "text/csv")}
    data = {"marketplace": "us", "dataset_name": "TEST_EN_SearchTerm"}
    r = session.post(f"{API}/imports/upload", files=files, data=data, timeout=60)
    assert r.status_code == 200, r.text
    j = r.json()
    yield j
    session.delete(f"{API}/datasets/{j['id']}", timeout=30)


@pytest.fixture(scope="session")
def es_dataset(session):
    files = {"file": ("reporte_es.csv", CSV_ES.encode("utf-8"), "text/csv")}
    data = {"marketplace": "es", "dataset_name": "TEST_ES_SearchTerm"}
    r = session.post(f"{API}/imports/upload", files=files, data=data, timeout=60)
    assert r.status_code == 200, r.text
    j = r.json()
    yield j
    session.delete(f"{API}/datasets/{j['id']}", timeout=30)


# ---------- Tests ----------
class TestHealth:
    def test_root(self, session):
        r = session.get(f"{API}/", timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body.get("status") == "ok"
        # Publify rebranding check
        assert body.get("service") == "publify-ads"


# ---------- Publify iter 2: BookEconomy + ACoS siguiente click ----------
BOOK_INFO = {
    "title": "Mindfulness Diario",
    "subtitle": "Pequeños hábitos",
    "description": "Un libro sobre mindfulness.",
    "categories": ["Autoayuda", "Mindfulness"],
}
BOOK_ECONOMY = {"precio_libro": 14.99, "regalias_por_venta": 4.50}
# expected break-even = 4.50/14.99*100 ≈ 30.0200...%
EXPECTED_ACOS_EQ = 4.50 / 14.99 * 100


class TestBookSettings:
    def test_put_book_persists(self, session, en_dataset):
        r = session.put(
            f"{API}/datasets/{en_dataset['id']}/book",
            json={"info": BOOK_INFO, "economy": BOOK_ECONOMY},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        # GET dataset should now include book_info and book_economy
        g = session.get(f"{API}/datasets/{en_dataset['id']}", timeout=30)
        assert g.status_code == 200
        d = g.json()
        assert d["book_info"]["title"] == BOOK_INFO["title"]
        assert d["book_info"]["subtitle"] == BOOK_INFO["subtitle"]
        assert d["book_info"]["description"] == BOOK_INFO["description"]
        assert d["book_info"]["categories"] == BOOK_INFO["categories"]
        assert d["book_economy"]["precio_libro"] == BOOK_ECONOMY["precio_libro"]
        assert d["book_economy"]["regalias_por_venta"] == BOOK_ECONOMY["regalias_por_venta"]

    def test_put_book_404_unknown_dataset(self, session):
        r = session.put(
            f"{API}/datasets/does-not-exist/book",
            json={"info": BOOK_INFO, "economy": BOOK_ECONOMY},
            timeout=30,
        )
        assert r.status_code == 404


class TestKeywordsUnified:
    def test_unified_structure_and_formulas(self, session, en_dataset):
        # ensure book saved first
        session.put(
            f"{API}/datasets/{en_dataset['id']}/book",
            json={"info": BOOK_INFO, "economy": BOOK_ECONOMY},
            timeout=30,
        )
        r = session.get(f"{API}/datasets/{en_dataset['id']}/keywords-unified", timeout=30)
        assert r.status_code == 200
        body = r.json()

        # required top-level keys
        for k in ("key", "rows", "acos_equilibrio", "guias_fase", "book_economy"):
            assert k in body, f"missing '{k}' in response"

        # (a) acos_equilibrio correctness
        assert body["acos_equilibrio"] is not None
        assert abs(body["acos_equilibrio"] - EXPECTED_ACOS_EQ) < 0.01

        # guias_fase
        g = body["guias_fase"]
        assert abs(g["lanzamiento"] - EXPECTED_ACOS_EQ * 1.7) < 0.01
        assert abs(g["dominio"] - EXPECTED_ACOS_EQ * 1.2) < 0.01
        assert abs(g["beneficio"] - EXPECTED_ACOS_EQ * 0.5) < 0.01

        # book_economy echoed
        assert body["book_economy"]["precio_libro"] == BOOK_ECONOMY["precio_libro"]

        rows = body["rows"]
        assert len(rows) >= 1
        # (b) each row has required fields
        for row in rows:
            for f in ("term", "impressions", "clicks", "ctr", "cpc", "spend", "sales",
                      "orders", "acos_actual", "acos_siguiente",
                      "beneficio_ahora", "beneficio_siguiente", "cvr", "badge"):
                assert f in row, f"missing field {f} in row {row}"

        # (c) Verify acos_siguiente formula for a row with sales>0
        mindful = next(r for r in rows if r["term"] == "mindfulness book")
        # mindfulness book: spend=27.90, sales=89.97, clicks=45 → cpc=27.90/45
        expected_cpc = 27.90 / 45
        expected_acos_next = ((27.90 + expected_cpc) / (89.97 + 14.99)) * 100
        assert abs(mindful["acos_siguiente"] - expected_acos_next) < 0.5
        # beneficio_ahora = 89.97 - 27.90
        assert abs(mindful["beneficio_ahora"] - (89.97 - 27.90)) < 0.01

        # (d) badge logic: mindfulness acos_actual = 27.90/89.97*100 ≈ 31.01%
        # vs acos_eq ≈ 30.02 → acos_actual > eq; acos_next ≈ (28.52/104.96)*100 ≈ 27.17 <= eq → "recuperable"
        assert mindful["badge"] in ("recuperable", "en-perdida", "bajo-pe")
        # compute expected
        acos_actual = 27.90 / 89.97 * 100
        if acos_actual <= EXPECTED_ACOS_EQ:
            expected_badge = "bajo-pe"
        elif expected_acos_next <= EXPECTED_ACOS_EQ:
            expected_badge = "recuperable"
        else:
            expected_badge = "en-perdida"
        assert mindful["badge"] == expected_badge

        # row with orders=0 and sales=0 → acos_actual is None → badge calculated with only acos_next
        buddha = next(r for r in rows if r["term"] == "buddha quotes")
        # sales=0 → acos_actual None; acos_next computed with price → finite number
        assert buddha["acos_actual"] is None
        assert buddha["acos_siguiente"] is not None

    def test_unified_without_economy_sin_datos(self, session):
        # Upload a fresh dataset without setting book economy
        files = {"file": ("fresh.csv", CSV_EN.encode("utf-8"), "text/csv")}
        r = session.post(f"{API}/imports/upload", files=files,
                         data={"marketplace": "us", "dataset_name": "TEST_NoEco"}, timeout=60)
        assert r.status_code == 200
        ds_id = r.json()["id"]
        try:
            u = session.get(f"{API}/datasets/{ds_id}/keywords-unified", timeout=30)
            assert u.status_code == 200
            body = u.json()
            assert body["acos_equilibrio"] is None
            for row in body["rows"]:
                assert row["badge"] == "sin-datos"
                assert row["acos_siguiente"] is None
        finally:
            session.delete(f"{API}/datasets/{ds_id}", timeout=30)


class TestCampaignsWithEconomy:
    def test_campaigns_include_badge_and_acos_next(self, session, en_dataset):
        session.put(
            f"{API}/datasets/{en_dataset['id']}/book",
            json={"info": BOOK_INFO, "economy": BOOK_ECONOMY},
            timeout=30,
        )
        r = session.get(f"{API}/datasets/{en_dataset['id']}/campaigns", timeout=30)
        assert r.status_code == 200
        camps = r.json()
        for c in camps:
            assert "acos_siguiente" in c
            assert "badge" in c
            assert c["badge"] in ("bajo-pe", "recuperable", "en-perdida", "sin-datos")


class TestSearchTermsWithEconomy:
    def test_search_terms_include_badge_and_acos_next(self, session, en_dataset):
        session.put(
            f"{API}/datasets/{en_dataset['id']}/book",
            json={"info": BOOK_INFO, "economy": BOOK_ECONOMY},
            timeout=30,
        )
        r = session.get(f"{API}/datasets/{en_dataset['id']}/search-terms", timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert "acos_equilibrio" in body
        assert body["acos_equilibrio"] is not None
        for row in body["rows"]:
            assert "acos_siguiente" in row
            assert "badge" in row


class TestUploadSizeLimit:
    def test_upload_too_large_413(self, session):
        big = b"Campaign Name,Impressions,Clicks\n" + (b"x" * (26 * 1024 * 1024))
        files = {"file": ("huge.csv", big, "text/csv")}
        r = session.post(f"{API}/imports/upload", files=files,
                         data={"marketplace": "us"}, timeout=120)
        assert r.status_code == 413


class TestUploadCSVEN:
    def test_upload_returns_metadata(self, en_dataset):
        d = en_dataset
        assert d["report_type"] == "search_term"
        assert d["ad_type"] == "SP"
        assert d["row_count"] == 4
        assert d["marketplace"] == "us"
        # header mapping should include canonical fields
        mapped = set(d["header_mapping"].values())
        for f in ("campaign", "customer_search_term", "impressions", "clicks", "spend", "sales", "orders"):
            assert f in mapped, f"Missing canonical field {f} in mapping {mapped}"

    def test_kpis_computed(self, en_dataset):
        k = en_dataset["kpis"]
        # impressions = 1200+800+500+900 = 3400, clicks = 105, spend = 52.9, sales = 149.97, orders = 5
        assert k["impressions"] == 3400
        assert k["clicks"] == 105
        assert round(k["spend"], 2) == 52.90
        assert round(k["sales"], 2) == 149.97
        assert k["orders"] == 5
        # CTR = 105/3400*100
        assert round(k["ctr"], 2) == round(105 / 3400 * 100, 2)
        # CPC = spend/clicks
        assert round(k["cpc"], 2) == round(52.90 / 105, 2)
        # ACoS = spend/sales*100
        assert round(k["acos"], 2) == round(52.90 / 149.97 * 100, 2)
        # ROAS = sales/spend
        assert round(k["roas"], 2) == round(149.97 / 52.90, 2)
        # CVR = orders/clicks*100
        assert round(k["cvr"], 2) == round(5 / 105 * 100, 2)


class TestUploadCSVES:
    def test_upload_es_mapping(self, es_dataset):
        d = es_dataset
        mapped = set(d["header_mapping"].values())
        for f in ("campaign", "impressions", "clicks", "spend", "sales", "orders"):
            assert f in mapped
        assert d["row_count"] == 2
        # KPIs
        k = d["kpis"]
        assert k["impressions"] == 3500
        assert k["clicks"] == 55
        assert round(k["spend"], 2) == 20.50
        assert round(k["sales"], 2) == 75.00
        assert k["orders"] == 3


class TestUploadXLSX:
    def test_upload_xlsx(self, session):
        files = {"file": ("report.xlsx", _build_xlsx_bytes(),
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        data = {"marketplace": "us", "dataset_name": "TEST_XLSX"}
        r = session.post(f"{API}/imports/upload", files=files, data=data, timeout=60)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["row_count"] == 2
        assert j["report_type"] == "search_term"
        assert j["kpis"]["impressions"] == 3000
        # cleanup
        session.delete(f"{API}/datasets/{j['id']}", timeout=30)


class TestUploadInvalid:
    def test_invalid_file_400(self, session):
        # binary garbage that pandas can't parse
        files = {"file": ("trash.bin", b"\x00\x01\x02\x03not a csv", "application/octet-stream")}
        r = session.post(f"{API}/imports/upload", files=files, data={"marketplace": "us"}, timeout=30)
        assert r.status_code == 400, r.text

    def test_empty_csv_400(self, session):
        # Has headers but no rows
        files = {"file": ("empty.csv", b"Campaign Name,Impressions,Clicks\n", "text/csv")}
        r = session.post(f"{API}/imports/upload", files=files, data={"marketplace": "us"}, timeout=30)
        assert r.status_code == 400, r.text


class TestListDatasets:
    def test_list_excludes_internal_fields(self, session, en_dataset):
        r = session.get(f"{API}/datasets", timeout=30)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert any(it["id"] == en_dataset["id"] for it in items)
        for it in items:
            assert "_id" not in it
            assert "rows" not in it
            assert "headers_detected" not in it
            assert "header_mapping" not in it
        # ordered desc by created_at
        if len(items) >= 2:
            ts = [it["created_at"] for it in items]
            assert ts == sorted(ts, reverse=True)

    def test_list_filtered_by_marketplace(self, session, en_dataset, es_dataset):
        r = session.get(f"{API}/datasets", params={"marketplace": "es"}, timeout=30)
        assert r.status_code == 200
        items = r.json()
        for it in items:
            assert it["marketplace"] == "es"


class TestGetDataset:
    def test_get_full_dataset(self, session, en_dataset):
        r = session.get(f"{API}/datasets/{en_dataset['id']}", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == en_dataset["id"]
        assert "rows" in d and len(d["rows"]) == 4
        assert "_id" not in d

    def test_get_404(self, session):
        r = session.get(f"{API}/datasets/does-not-exist", timeout=30)
        assert r.status_code == 404


class TestCampaigns:
    def test_aggregate_by_campaign(self, session, en_dataset):
        r = session.get(f"{API}/datasets/{en_dataset['id']}/campaigns", timeout=30)
        assert r.status_code == 200
        camps = r.json()
        assert isinstance(camps, list)
        names = {c["campaign"] for c in camps}
        assert {"Campaign Alpha", "Campaign Beta"}.issubset(names)
        alpha = next(c for c in camps if c["campaign"] == "Campaign Alpha")
        # Alpha: impressions=2000, clicks=65, spend=37.90, sales=89.97
        assert alpha["impressions"] == 2000
        assert alpha["clicks"] == 65
        assert round(alpha["spend"], 2) == 37.90
        assert round(alpha["sales"], 2) == 89.97
        # derived
        assert "ctr" in alpha and "cpc" in alpha and "acos" in alpha and "roas" in alpha and "cvr" in alpha


class TestSearchTerms:
    def test_search_terms_with_negative_flag(self, session, en_dataset):
        r = session.get(f"{API}/datasets/{en_dataset['id']}/search-terms", timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["key"] == "customer_search_term"
        rows = body["rows"]
        terms = {row["customer_search_term"]: row for row in rows}
        # 'buddha quotes' has clicks=20 orders=0 → suggest_negative True (>=6 clicks, 0 orders)
        assert terms["buddha quotes"]["suggest_negative"] is True
        # 'mindfulness book' has orders=3 → False
        assert terms["mindfulness book"]["suggest_negative"] is False
        # 'no sales term' has clicks=10 orders=0 → True
        assert terms["no sales term"]["suggest_negative"] is True
        # 'yoga mat' has orders=2 → False
        assert terms["yoga mat"]["suggest_negative"] is False


class TestTimeseries:
    def test_timeseries_by_date(self, session, en_dataset):
        r = session.get(f"{API}/datasets/{en_dataset['id']}/timeseries", timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["mode"] == "date"
        pts = body["points"]
        # 3 distinct dates
        assert len(pts) == 3
        for p in pts:
            for f in ("impressions", "clicks", "spend", "sales", "orders"):
                assert f in p

    def test_timeseries_fallback_campaign(self, session, es_dataset):
        # ES dataset has no Start Date column → fallback by campaign
        r = session.get(f"{API}/datasets/{es_dataset['id']}/timeseries", timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["mode"] == "campaign"
        assert len(body["points"]) >= 1


class TestAIRecommendations:
    def test_ai_recs(self, session, en_dataset):
        r = session.post(f"{API}/datasets/{en_dataset['id']}/ai-recommendations", timeout=120)
        if r.status_code == 502:
            pytest.skip(f"AI provider unavailable: {r.text}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "recommendations" in body
        assert "generated_at" in body
        assert isinstance(body["recommendations"], list)
        assert len(body["recommendations"]) >= 1
        rec0 = body["recommendations"][0]
        assert "title" in rec0 and "severity" in rec0 and "detail" in rec0


class TestDelete:
    def test_delete_dataset(self, session):
        # create first
        files = {"file": ("temp.csv", CSV_EN.encode("utf-8"), "text/csv")}
        r = session.post(f"{API}/imports/upload", files=files,
                         data={"marketplace": "us", "dataset_name": "TEST_DELETE"}, timeout=60)
        assert r.status_code == 200
        ds_id = r.json()["id"]

        d = session.delete(f"{API}/datasets/{ds_id}", timeout=30)
        assert d.status_code == 200
        assert d.json().get("deleted") == 1

        # subsequent get → 404
        g = session.get(f"{API}/datasets/{ds_id}", timeout=30)
        assert g.status_code == 404



# ======================= Iteration 3 =======================
# Overrides (upsert/delete keyword), campaign creation, snapshots, keyword-detail,
# and keywords-unified 'summary' block.
class TestIter3Overrides:
    def test_upsert_keyword_updates_unified(self, session, en_dataset):
        ds = en_dataset["id"]
        # Set book so badges compute
        session.put(f"{API}/datasets/{ds}/book",
                    json={"info": BOOK_INFO, "economy": BOOK_ECONOMY}, timeout=30)
        payload = {
            "term": "mindfulness book",
            "clicks": 100, "cpc": 0.5, "spend": 50.0,
            "orders": 10, "sales": 200.0, "impressions": 5000,
            "match_type": "exact", "ad_type": "SP", "notes": "manual edit"
        }
        r = session.put(f"{API}/datasets/{ds}/keyword", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True

        u = session.get(f"{API}/datasets/{ds}/keywords-unified", timeout=30)
        assert u.status_code == 200
        rows = u.json()["rows"]
        row = next(r for r in rows if r["term"] == "mindfulness book")
        assert row["is_manual"] is True
        assert row["clicks"] == 100
        assert row["spend"] == 50.0
        assert row["sales"] == 200.0
        assert row["orders"] == 10
        # CTR recomputed: 100/5000*100 = 2.0
        assert abs(row["ctr"] - 2.0) < 0.01
        # acos_actual = 50/200*100 = 25
        assert abs(row["acos_actual"] - 25.0) < 0.01
        # cvr = 10/100*100 = 10
        assert abs(row["cvr"] - 10.0) < 0.01

        # dataset top-level kpis should be recomputed
        d = session.get(f"{API}/datasets/{ds}", timeout=30).json()
        assert "kpis" in d
        assert d["kpis"]["spend"] > 0

    def test_upsert_empty_term_400(self, session, en_dataset):
        r = session.put(f"{API}/datasets/{en_dataset['id']}/keyword",
                        json={"term": "   "}, timeout=30)
        assert r.status_code == 400

    def test_upsert_unknown_dataset_404(self, session):
        r = session.put(f"{API}/datasets/nope/keyword",
                        json={"term": "x", "clicks": 1}, timeout=30)
        assert r.status_code == 404

    def test_delete_keyword_restores_aggregated(self, session, en_dataset):
        ds = en_dataset["id"]
        session.put(f"{API}/datasets/{ds}/book",
                    json={"info": BOOK_INFO, "economy": BOOK_ECONOMY}, timeout=30)
        # ensure override exists (from prior test or create it)
        session.put(f"{API}/datasets/{ds}/keyword",
                    json={"term": "mindfulness book", "clicks": 999, "spend": 999.0,
                          "sales": 0.0, "orders": 0, "impressions": 100},
                    timeout=30)
        d = session.delete(f"{API}/datasets/{ds}/keyword/mindfulness book", timeout=30)
        assert d.status_code == 200
        assert d.json()["ok"] is True
        u = session.get(f"{API}/datasets/{ds}/keywords-unified", timeout=30).json()
        row = next(r for r in u["rows"] if r["term"] == "mindfulness book")
        assert row["is_manual"] is False
        # Back to original aggregated values
        assert round(row["spend"], 2) == 27.90
        assert round(row["sales"], 2) == 89.97


class TestIter3Campaign:
    def test_create_campaign_with_keywords(self, session, en_dataset):
        ds = en_dataset["id"]
        session.put(f"{API}/datasets/{ds}/book",
                    json={"info": BOOK_INFO, "economy": BOOK_ECONOMY}, timeout=30)
        payload = {
            "campaign": "TEST_NewCampaign",
            "ad_type": "SP",
            "match_type": "exact",
            "keywords": [
                {"term": "TEST_new_kw_1", "clicks": 50, "cpc": 0.30, "orders": 2,
                 "impressions": 1500, "spend": 15.0, "sales": 40.0},
                {"term": "TEST_new_kw_2", "clicks": 10, "cpc": 0.20, "orders": 0,
                 "impressions": 500, "spend": 2.0, "sales": 0.0},
            ]
        }
        r = session.post(f"{API}/datasets/{ds}/campaign", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["campaign"] == "TEST_NewCampaign"
        assert set(body["added"]) == {"TEST_new_kw_1", "TEST_new_kw_2"}

        u = session.get(f"{API}/datasets/{ds}/keywords-unified", timeout=30).json()
        terms = {r["term"]: r for r in u["rows"]}
        for t in ("TEST_new_kw_1", "TEST_new_kw_2"):
            assert t in terms
            assert terms[t]["is_manual"] is True
            assert terms[t]["campaign"] == "TEST_NewCampaign"

        # cleanup overrides
        for t in ("TEST_new_kw_1", "TEST_new_kw_2"):
            session.delete(f"{API}/datasets/{ds}/keyword/{t}", timeout=30)

    def test_create_campaign_empty_name_400(self, session, en_dataset):
        r = session.post(f"{API}/datasets/{en_dataset['id']}/campaign",
                         json={"campaign": "   ", "keywords": []}, timeout=30)
        assert r.status_code == 400


class TestIter3Snapshots:
    def test_snapshot_all_and_dedupe_same_day(self, session, en_dataset):
        ds = en_dataset["id"]
        session.put(f"{API}/datasets/{ds}/book",
                    json={"info": BOOK_INFO, "economy": BOOK_ECONOMY}, timeout=30)
        r1 = session.post(f"{API}/datasets/{ds}/snapshot-all", timeout=30)
        assert r1.status_code == 200
        terms_count = r1.json()["terms"]
        assert terms_count >= 1

        # grab snapshots for a known term
        s1 = session.get(f"{API}/datasets/{ds}/snapshots/mindfulness book",
                         timeout=30).json()
        assert s1["term"] == "mindfulness book"
        assert len(s1["snapshots"]) == 1

        # second call same day should not duplicate
        r2 = session.post(f"{API}/datasets/{ds}/snapshot-all", timeout=30)
        assert r2.status_code == 200
        s2 = session.get(f"{API}/datasets/{ds}/snapshots/mindfulness book",
                         timeout=30).json()
        assert len(s2["snapshots"]) == 1, "same-day snapshot should replace, not append"

    def test_get_snapshots_unknown_term_returns_empty(self, session, en_dataset):
        r = session.get(f"{API}/datasets/{en_dataset['id']}/snapshots/totally_unknown",
                        timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["term"] == "totally_unknown"
        assert body["snapshots"] == []

    def test_snapshot_all_404(self, session):
        r = session.post(f"{API}/datasets/does-not-exist/snapshot-all", timeout=30)
        assert r.status_code == 404


class TestIter3KeywordDetail:
    def test_keyword_detail_full_payload(self, session, en_dataset):
        ds = en_dataset["id"]
        session.put(f"{API}/datasets/{ds}/book",
                    json={"info": BOOK_INFO, "economy": BOOK_ECONOMY}, timeout=30)
        r = session.get(f"{API}/datasets/{ds}/keyword-detail",
                        params={"term": "mindfulness book"}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["term"] == "mindfulness book"
        assert body["key"] in ("customer_search_term", "targeting")
        m = body["metrics"]
        for f in ("acos_actual", "acos_siguiente", "beneficio_ahora",
                  "beneficio_siguiente", "cvr", "badge", "underlying_rows",
                  "is_manual"):
            assert f in m, f"missing {f} in metrics"
        assert m["underlying_rows"] >= 1
        assert body["acos_equilibrio"] is not None
        assert "snapshots" in body
        assert "override" in body

    def test_keyword_detail_unknown_term_is_manual_false(self, session, en_dataset):
        ds = en_dataset["id"]
        r = session.get(f"{API}/datasets/{ds}/keyword-detail",
                        params={"term": "this_does_not_exist"}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["metrics"]["underlying_rows"] == 0

    def test_keyword_detail_404(self, session):
        r = session.get(f"{API}/datasets/nope/keyword-detail",
                        params={"term": "x"}, timeout=30)
        assert r.status_code == 404


class TestIter3UnifiedSummary:
    def test_keywords_unified_has_summary_block(self, session, en_dataset):
        ds = en_dataset["id"]
        session.put(f"{API}/datasets/{ds}/book",
                    json={"info": BOOK_INFO, "economy": BOOK_ECONOMY}, timeout=30)
        u = session.get(f"{API}/datasets/{ds}/keywords-unified", timeout=30).json()
        assert "summary" in u
        BADGE_KEYS = ("bajo-pe", "recuperable", "en-perdida", "sin-datos")
        for k in BADGE_KEYS:
            assert k in u["summary"]
            assert isinstance(u["summary"][k], int)
        # Badge categories are mutually exclusive and cover every row.
        # `summary.negativas` (if present) is orthogonal and MUST NOT be summed here.
        badge_total = sum(u["summary"][k] for k in BADGE_KEYS)
        assert badge_total == len(u["rows"])
        # Complementary check: if negativas is present it must be a well-formed int
        # bounded by the number of rows (a keyword can be negative candidate AND hold a badge).
        if "negativas" in u["summary"]:
            assert isinstance(u["summary"]["negativas"], int)
            assert 0 <= u["summary"]["negativas"] <= len(u["rows"])
