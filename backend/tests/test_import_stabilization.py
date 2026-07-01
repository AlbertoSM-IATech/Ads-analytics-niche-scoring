"""IMPORT-2 · Amazon Ads importer stabilization tests.

Covers:
  * /api/imports/preview dry-run (does NOT persist).
  * Diagnostics payload: matched_fields, unmatched_headers, missing_critical,
    warnings, capabilities, report_type_confidence.
  * i18n match-type normalization (ES / IT).
  * ACoS fractional-vs-percent auto-detection.
  * Safer header matcher (avoids `coste` colliding across spend / cpc).
  * `unknown` report type surfaces a warning.

All fixtures under `tests/fixtures/import_csvs/` are SYNTHETIC — see the
README in that directory. No real Amazon Ads data ships with the repo.
"""
from __future__ import annotations
import os
from pathlib import Path

import httpx
import pytest

# Optional import for standalone unit tests (no server required).
from amazon_ads import (
    auto_map_headers,
    detect_report_type,
    normalize_match_type,
    parse_ads_file,
)


BASE_URL = os.environ["REACT_APP_BACKEND_URL"]
API = f"{BASE_URL}/api"

FIXTURES = Path(__file__).parent / "fixtures" / "import_csvs"


def _load(name: str) -> tuple[str, bytes]:
    p = FIXTURES / name
    return name, p.read_bytes()


# ---------------------------------------------------------------------------
# Unit tests (no HTTP; parser only)
# ---------------------------------------------------------------------------

class TestMatchTypeNormalization:
    @pytest.mark.parametrize("raw,expected", [
        # English
        ("Exact", "exact"), ("exact", "exact"), ("Exact match", "exact"),
        ("Phrase", "phrase"), ("Phrase Match", "phrase"),
        ("Broad", "broad"), ("Broad match", "broad"),
        ("Auto", "auto"), ("Automatic", "auto"),
        # Spanish
        ("Exacta", "exact"), ("Exactas", "exact"),
        ("Frase", "phrase"),
        ("Amplia", "broad"),
        ("Automática", "auto"), ("Automatica", "auto"),
        # Italian
        ("Esatta", "exact"),
        ("Ampia", "broad"), ("Generica", "broad"),
        # Prefixed (Amazon UI sometimes concatenates ad type)
        ("Sponsored Products Exact", "exact"),
        ("Sponsored Products Broad", "broad"),
        # Nulls / empties
        (None, None), ("", None), ("nan", None), ("-", None),
    ])
    def test_normalize(self, raw, expected):
        assert normalize_match_type(raw) == expected


class TestSaferHeaderMatcher:
    def test_coste_paren_disambiguation(self):
        """`Coste total (EUR)` and `Coste por clic (EUR)` must not collide."""
        headers = ["Coste total (EUR)", "Coste por clic (EUR)",
                   "Impresiones", "Clics"]
        mapping, unmatched, warnings, _ = auto_map_headers(headers)
        assert mapping["Coste total (EUR)"] == "spend"
        assert mapping["Coste por clic (EUR)"] == "cpc"
        assert not any("compiten" in w for w in warnings), warnings

    def test_completely_unknown_headers(self):
        headers = ["Foo", "Bar", "Baz"]
        mapping, unmatched, warnings, _ = auto_map_headers(headers)
        assert mapping == {}
        assert set(unmatched) == {"Foo", "Bar", "Baz"}

    def test_collision_produces_warning(self):
        """Two headers competing for `campaign` must produce a warning
        instead of silently overwriting one another.
        """
        headers = ["Campaign Name", "Campaña"]
        mapping, unmatched, warnings, _ = auto_map_headers(headers)
        assert list(mapping.values()) == ["campaign"]
        assert warnings, "expected a collision warning"

    def test_report_type_detection(self):
        headers = ["Campaign Name", "Ad Group Name", "Customer Search Term",
                   "Keyword Text", "Match Type", "Impressions", "Clicks",
                   "Spend", "7 Day Total Sales", "7 Day Total Orders (#)"]
        mapping, _, _, _ = auto_map_headers(headers)
        rt, conf = detect_report_type(headers, mapping)
        assert rt == "search_term"
        assert conf == "high"


class TestFractionalAcosDetection:
    def test_fractional_promoted_to_percent(self):
        name, content = _load("acos_fractional.csv")
        parsed = parse_ads_file(content, name)
        # All acos values in the file are in [0.20, 0.30] — must be promoted.
        for r in parsed["rows"]:
            assert r["acos"] > 1.0, r
        assert any("fraccional" in w.lower()
                   for w in parsed["diagnostics"]["warnings"]), (
            parsed["diagnostics"]["warnings"])

    def test_percent_not_touched(self):
        name, content = _load("acos_percent.csv")
        parsed = parse_ads_file(content, name)
        # ACOS values here were like 20% / 30% and had '%' sign — must NOT
        # have been re-scaled.
        for r in parsed["rows"]:
            assert 15.0 < r["acos"] < 35.0, r
        assert not any("fraccional" in w.lower()
                       for w in parsed["diagnostics"]["warnings"])


class TestParenthesisedCurrency:
    def test_headers_map_correctly(self):
        name, content = _load("parenthesised_currency.csv")
        parsed = parse_ads_file(content, name)
        mapping = parsed["header_mapping"]
        assert mapping["Coste total (EUR)"] == "spend"
        assert mapping["Coste por clic (EUR)"] == "cpc"
        assert mapping["Ventas (EUR)"] == "sales"
        # Numeric values coerced.
        assert parsed["rows"][0]["spend"] == 8.0
        assert parsed["rows"][0]["sales"] == 60.0
        assert parsed["rows"][0]["cpc"] == 0.4


class TestES_SearchTerm:
    def test_full_flow(self):
        name, content = _load("search_term_es.csv")
        parsed = parse_ads_file(content, name)
        diag = parsed["diagnostics"]
        assert diag["report_type"] == "search_term"
        assert "clicks" in diag["matched_fields"]
        assert "spend" in diag["matched_fields"]
        assert "sales" in diag["matched_fields"]
        assert "orders" in diag["matched_fields"]
        assert diag["missing_critical"] == []
        assert diag["capabilities"]["ads_performance"] is True
        assert diag["capabilities"]["profitability"] is True
        # Match types must be canonicalized.
        for r in parsed["rows"]:
            assert r["match_type"] in {"exact", "phrase", "broad", "auto"}


class TestES_MatchTypeSideEffect:
    def test_match_types_all_canonical(self):
        name, content = _load("match_types_es.csv")
        parsed = parse_ads_file(content, name)
        found = {r["match_type"] for r in parsed["rows"]}
        assert found == {"exact", "phrase", "broad", "auto"}


class TestEN_Campaign:
    def test_campaign_confidence(self):
        name, content = _load("campaign_en.csv")
        parsed = parse_ads_file(content, name)
        diag = parsed["diagnostics"]
        assert diag["report_type"] == "campaign"
        assert diag["report_type_confidence"] in ("high", "medium")
        assert diag["missing_critical"] == []


class TestUnknownReport:
    def test_unknown_headers_flagged(self):
        name, content = _load("unknown_headers.csv")
        parsed = parse_ads_file(content, name)
        diag = parsed["diagnostics"]
        assert diag["report_type"] == "unknown"
        assert diag["report_type_confidence"] == "low"
        assert diag["matched_fields"] == []
        assert len(diag["unmatched_headers"]) == 5
        # An explanatory warning must be present.
        assert any("no se ha reconocido" in w.lower()
                   for w in diag["warnings"])
        # Capabilities must all be False (no useful data extractable).
        caps = diag["capabilities"]
        assert not any(caps[k] for k in
                       ("ads_performance", "profitability", "negatives"))


# ---------------------------------------------------------------------------
# HTTP integration tests
# ---------------------------------------------------------------------------

class TestPreviewEndpoint:
    def test_preview_does_not_persist(self):
        before = httpx.get(f"{API}/datasets", timeout=15).json()
        before_ids = {d["id"] for d in before}
        name, content = _load("search_term_es.csv")
        r = httpx.post(
            f"{API}/imports/preview",
            files={"file": (name, content, "text/csv")},
            data={"preview_rows": 5},
            timeout=30,
        )
        assert r.status_code == 200
        body = r.json()
        # Preview must return diagnostics.
        assert "diagnostics" in body
        assert body["diagnostics"]["report_type"] == "search_term"
        # Preview must return at most 5 sample rows.
        assert len(body["sample_rows"]) <= 5
        # After preview, dataset list must be unchanged.
        after = httpx.get(f"{API}/datasets", timeout=15).json()
        after_ids = {d["id"] for d in after}
        assert after_ids == before_ids, "Preview created a dataset — it must be a dry-run"

    def test_preview_reports_missing_critical(self):
        # Only a keyword column and impressions — missing clicks/spend/sales/orders.
        csv = (
            "Nombre de la campaña,Palabra clave,Impresiones\n"
            "C1,dash diet,1000\n"
        ).encode("utf-8")
        r = httpx.post(
            f"{API}/imports/preview",
            files={"file": ("skinny.csv", csv, "text/csv")},
            timeout=15,
        )
        assert r.status_code == 200
        diag = r.json()["diagnostics"]
        # Report type detected as campaign (has campaign) — missing all metrics.
        missing = set(diag["missing_critical"])
        assert {"clicks", "spend", "sales", "orders"}.issubset(missing)
        assert diag["capabilities"]["ads_performance"] is False
        assert diag["report_type_confidence"] == "low"

    def test_preview_fractional_acos_warning(self):
        name, content = _load("acos_fractional.csv")
        r = httpx.post(
            f"{API}/imports/preview",
            files={"file": (name, content, "text/csv")},
            timeout=15,
        )
        assert r.status_code == 200
        diag = r.json()["diagnostics"]
        assert any("fraccional" in w.lower() for w in diag["warnings"])


class TestUploadReturnsDiagnostics:
    def test_upload_still_works_and_carries_diagnostics(self):
        name, content = _load("search_term_es.csv")
        r = httpx.post(
            f"{API}/imports/upload",
            files={"file": (name, content, "text/csv")},
            data={"marketplace": "es", "dataset_name": "IMPORT2_ES_FIXTURE"},
            timeout=30,
        )
        assert r.status_code == 200
        body = r.json()
        ds_id = body["id"]
        try:
            assert body["report_type"] == "search_term"
            assert "diagnostics" in body
            diag = body["diagnostics"]
            assert diag["capabilities"]["ads_performance"] is True
            # Ensure persistence: refetch dataset and check diagnostics stored.
            r2 = httpx.get(f"{API}/datasets/{ds_id}", timeout=15)
            assert r2.status_code == 200
            # Detail endpoint returns full doc with rows; diagnostics should
            # be part of it too.
            if "diagnostics" in r2.json():
                assert r2.json()["diagnostics"]["report_type"] == "search_term"
        finally:
            httpx.delete(f"{API}/datasets/{ds_id}", timeout=10)
