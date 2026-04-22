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
        assert r.json().get("status") == "ok"


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
