"""Unit tests for backend/kdp_economy.py — Phase 1.

Pure functions only; no DB required.
"""
import math
import pytest

from kdp_economy import (
    MARKETPLACE_CONFIG, normalize_mp, calc_precio_sin_iva, calc_delivery_cost,
    calc_coste_impresion, calc_regalia_neta, calc_acos_pe, calc_cpc_max_rentable,
    calc_clicks_pe_base, calc_tasa_conv_breakeven, beneficio_kdp, calc_pvp_minimo,
    diagnose, compute_full_diagnosis, KdpEconomyError,
    _score_clicks, _score_acos_pe, _score_pvp_vs_min,
)


# ---------- Marketplace normalization ----------

def test_normalize_mp_lowercase_us_maps_to_com():
    assert normalize_mp("us") == "COM"


def test_normalize_mp_lowercase_es_maps_to_upper():
    assert normalize_mp("es") == "ES"


def test_normalize_mp_unknown_falls_back_to_com():
    assert normalize_mp("xx") == "COM"


# ---------- Precio sin IVA ----------

def test_precio_sin_iva_es_con_iva_4():
    # ES, IVA 4% → 12.99 / 1.04 = 12.490384...
    assert calc_precio_sin_iva(12.99, "ES", 4) == pytest.approx(12.99 / 1.04, rel=1e-6)


def test_precio_sin_iva_es_iva_21():
    assert calc_precio_sin_iva(12.99, "ES", 21) == pytest.approx(12.99 / 1.21, rel=1e-6)


def test_precio_sin_iva_us_sin_iva():
    # IVA only applies on ES (per product rule)
    assert calc_precio_sin_iva(14.99, "COM", 21) == pytest.approx(14.99, rel=1e-6)


def test_precio_sin_iva_de_sin_iva_aunque_es_eu():
    # DE has iva_default_pct=7 in config but the rule is: only ES applies IVA
    assert calc_precio_sin_iva(12.99, "DE", None) == pytest.approx(12.99, rel=1e-6)


# ---------- Delivery cost ----------

def test_delivery_cost_70pct_2mb_rounds_up():
    # ceil(2) * 0.12 = 0.24 ; but if mb=1.3 → ceil=2 → 0.24
    assert calc_delivery_cost(1.3, 70) == pytest.approx(0.24)


def test_delivery_cost_35pct_always_zero():
    assert calc_delivery_cost(10, 35) == 0.0


def test_delivery_cost_zero_mb_is_zero():
    assert calc_delivery_cost(0, 70) == 0.0


# ---------- Coste impresión ----------

def test_coste_impresion_bn_small_eu_110p():
    # ES (EU) BN SMALL 110 pages: fixed 0.75, per_page 0.012
    assert calc_coste_impresion("BN", "SMALL", "ES", 110) == pytest.approx(0.75 + 110 * 0.012, rel=1e-4)


def test_coste_impresion_bn_small_com_200p():
    # COM BN SMALL 200 pages (>108): fixed 1.00, per_page 0.012
    assert calc_coste_impresion("BN", "SMALL", "COM", 200) == pytest.approx(1.00 + 200 * 0.012, rel=1e-4)


def test_coste_impresion_color_standard_au_raises():
    with pytest.raises(KdpEconomyError):
        calc_coste_impresion("COLOR_STANDARD", "SMALL", "AU", 120)


def test_coste_impresion_color_standard_jp_raises():
    with pytest.raises(KdpEconomyError):
        calc_coste_impresion("COLOR_STANDARD", "SMALL", "JP", 120)


def test_coste_impresion_hardcover_es_adds_572():
    base = calc_coste_impresion("BN", "SMALL", "ES", 150)
    with_hc = calc_coste_impresion("BN", "SMALL", "ES", 150, book_format="HARDCOVER")
    assert with_hc == pytest.approx(base + 5.72, rel=1e-4)


def test_coste_impresion_hardcover_color_standard_raises():
    with pytest.raises(KdpEconomyError):
        calc_coste_impresion("COLOR_STANDARD", "SMALL", "ES", 120, book_format="HARDCOVER")


def test_coste_impresion_color_standard_below_72_raises():
    with pytest.raises(KdpEconomyError):
        calc_coste_impresion("COLOR_STANDARD", "SMALL", "ES", 60)


def test_coste_impresion_over_max_raises():
    with pytest.raises(KdpEconomyError):
        calc_coste_impresion("BN", "SMALL", "ES", 900)


# ---------- Regalía neta ----------

def test_regalia_neta_ebook_70_con_delivery():
    # COM, ebook 70%, pvp=2.99, mb=1
    r = calc_regalia_neta(format_type="EBOOK", pvp=2.99, marketplace="COM",
                          royalty_rate_ebook=70, tamano_mb=1)
    expected = 2.99 * 0.7 - 1 * 0.12
    assert r["regalia_neta"] == pytest.approx(expected, rel=1e-4)
    assert r["royalty_rate_used_pct"] == 70


def test_regalia_neta_ebook_35_sin_delivery():
    r = calc_regalia_neta(format_type="EBOOK", pvp=9.99, marketplace="COM",
                          royalty_rate_ebook=35, tamano_mb=5)
    assert r["regalia_neta"] == pytest.approx(9.99 * 0.35, rel=1e-4)
    assert r["delivery_cost"] == 0.0


def test_regalia_neta_paperback_pvp_bajo_usa_50pct():
    # COM threshold 9.99 → 9.00 pvp uses 50%
    r = calc_regalia_neta(format_type="PRINT", pvp=9.00, marketplace="COM",
                          interior="BN", size="SMALL", pages=200)
    assert r["royalty_rate_used_pct"] == 50


def test_regalia_neta_paperback_pvp_alto_usa_60pct():
    # COM threshold 9.99 → 14.99 pvp uses 60%
    r = calc_regalia_neta(format_type="PRINT", pvp=14.99, marketplace="COM",
                          interior="BN", size="SMALL", pages=200)
    assert r["royalty_rate_used_pct"] == 60


def test_regalia_neta_uses_marketplace_specific_royalty_threshold():
    """Test that the royalty threshold is read from marketplace config — NOT hardcoded to 9.99."""
    # Use a PVP that straddles different thresholds; rate must differ between marketplaces.
    # COM threshold 9.99, AU threshold 14.99 (per bridge doc)
    pvp = 12.00
    threshold_com = MARKETPLACE_CONFIG["COM"]["royalty_threshold"]
    threshold_au = MARKETPLACE_CONFIG["AU"]["royalty_threshold"]
    # Sanity: COM threshold < pvp < AU threshold → rates must differ
    assert threshold_com < pvp < threshold_au

    r_com = calc_regalia_neta(format_type="PRINT", pvp=pvp, marketplace="COM",
                              interior="BN", size="SMALL", pages=150)
    r_au = calc_regalia_neta(format_type="PRINT", pvp=pvp, marketplace="AU",
                             interior="BN", size="SMALL", pages=150)
    assert r_com["royalty_rate_used_pct"] == 60
    assert r_au["royalty_rate_used_pct"] == 50


# ---------- ACoS PE / BACOS / break-even ACoS (son iguales) ----------

def test_acos_pe_es_regalia_entre_pvp_por_100():
    assert calc_acos_pe(4.0, 10.0) == pytest.approx(40.0)


def test_acos_pe_none_pvp_zero():
    assert calc_acos_pe(4.0, 0) is None


# ---------- CPC / clicks / tasa ----------

def test_cpc_max_rentable_regalia_div_10():
    assert calc_cpc_max_rentable(5.0) == pytest.approx(0.5)


def test_clicks_pe_base_regalia_div_cpc_ref():
    assert calc_clicks_pe_base(5.0, 0.5) == pytest.approx(10.0)


def test_clicks_pe_base_sin_cpc_ref_returns_none():
    assert calc_clicks_pe_base(5.0, None) is None


def test_tasa_conv_breakeven():
    assert calc_tasa_conv_breakeven(5.0, 0.5) == pytest.approx(0.1)


# ---------- Beneficio KDP (defined but not wired in F1) ----------

def test_beneficio_kdp_correct_formula():
    # 3 ventas × 4.5 regalía − 10 gasto = 13.5 − 10 = 3.5
    assert beneficio_kdp(orders=3, regalia_neta=4.5, spend=10.0) == pytest.approx(3.5)


def test_beneficio_kdp_handles_none_as_zero():
    assert beneficio_kdp(orders=None, regalia_neta=4.5, spend=0) == 0.0


# ---------- Scoring §20 (corrected) ----------

def test_scoring_clicks_14_gives_50():
    assert _score_clicks(14) == (50, 50)


def test_scoring_clicks_13_gives_35():
    assert _score_clicks(13) == (35, 50)


def test_scoring_clicks_12_gives_25():
    assert _score_clicks(12) == (25, 50)


def test_scoring_clicks_11_gives_15():
    assert _score_clicks(11) == (15, 50)


def test_scoring_clicks_10_gives_10_not_zero():
    # Important: 10 clicks is minimum acceptable, not great but not 0.
    assert _score_clicks(10) == (10, 50)


def test_scoring_clicks_below_10_gives_0():
    assert _score_clicks(9.5) == (0, 50)


def test_scoring_clicks_none_gives_0():
    assert _score_clicks(None) == (0, 50)


def test_scoring_acos_pe_40_gives_40():
    assert _score_acos_pe(40) == (40, 40)


def test_scoring_acos_pe_35_gives_25():
    assert _score_acos_pe(35) == (25, 40)


def test_scoring_acos_pe_30_gives_15():
    assert _score_acos_pe(30) == (15, 40)


def test_scoring_acos_pe_29_gives_0():
    assert _score_acos_pe(29.9) == (0, 40)


def test_scoring_pvp_vs_pvp_min_mayor_10pts():
    assert _score_pvp_vs_min(12.99, 9.99) == (10, 10)


def test_scoring_pvp_vs_pvp_min_igual_5pts():
    assert _score_pvp_vs_min(9.99, 9.99) == (5, 10)


def test_scoring_pvp_vs_pvp_min_menor_0pts():
    assert _score_pvp_vs_min(8.99, 9.99) == (0, 10)


# ---------- Diagnosis (§19) ----------

def test_diagnose_high_risk_low_clicks():
    d = diagnose(regalia_neta=4, acos_pe=45, clicks_pe_base=8, pvp=12, pvp_minimo=10)
    assert d["risk_level"] == "high"


def test_diagnose_medium_risk_margen_35():
    d = diagnose(regalia_neta=4, acos_pe=35, clicks_pe_base=12, pvp=12, pvp_minimo=10)
    assert d["risk_level"] == "medium"


def test_diagnose_low_risk_all_good():
    d = diagnose(regalia_neta=5, acos_pe=45, clicks_pe_base=14, pvp=13, pvp_minimo=10)
    assert d["risk_level"] == "low"


def test_diagnose_not_viable_regalia_negativa():
    d = diagnose(regalia_neta=-1, acos_pe=-5, clicks_pe_base=2, pvp=10, pvp_minimo=12)
    assert d["viability_status"] == "not-viable"


def test_diagnose_adjustable_margen_bajo():
    d = diagnose(regalia_neta=3, acos_pe=25, clicks_pe_base=9, pvp=12, pvp_minimo=10)
    assert d["viability_status"] == "adjustable"


def test_diagnose_viable_all_green():
    d = diagnose(regalia_neta=5, acos_pe=45, clicks_pe_base=14, pvp=13, pvp_minimo=10)
    assert d["viability_status"] == "viable"


# ---------- PVP mínimo ----------

def test_pvp_minimo_ebook_70_finite():
    # With zero delivery cost, pvp_sin_iva_min = 0 / (0.7 - 0.3) = 0 ; rounded up 0.0
    # but with some mb, delivery > 0 → positive pvp_min
    pvp_min = calc_pvp_minimo(format_type="EBOOK", marketplace="COM",
                              margen_objetivo_pct=30, royalty_rate_ebook=70, tamano_mb=2)
    assert pvp_min is not None
    assert pvp_min > 0


def test_pvp_minimo_paperback_cuando_60pct_da_bajo_threshold():
    # Low printing cost → pvp calculated at 60% falls below threshold 9.99 → returns threshold
    pvp_min = calc_pvp_minimo(format_type="PRINT", marketplace="COM",
                              margen_objetivo_pct=30,
                              interior="BN", size="SMALL", pages=100)
    # Should be the threshold (9.99) since low cost books fall below it
    assert pvp_min == pytest.approx(9.99) or pvp_min >= 9.99


def test_pvp_minimo_no_factible_margen_imposible_ebook_35():
    # 35% royalty cannot give 40% margin → None
    assert calc_pvp_minimo(format_type="EBOOK", marketplace="COM",
                           margen_objetivo_pct=40, royalty_rate_ebook=35, tamano_mb=1) is None


# ---------- compute_full_diagnosis orchestration ----------

def test_compute_full_diagnosis_legacy_mode_when_no_format_type():
    book = {"precio_libro": 9.99, "regalias_por_venta": 3.5}
    r = compute_full_diagnosis(book, "ES")
    assert r["mode"] == "legacy"
    assert r["marketplace"] == "ES"
    assert r["outputs"]["acos_pe"] == pytest.approx(35.04, rel=1e-2)
    assert r["outputs"]["bacos"] == r["outputs"]["acos_pe"]
    assert r["outputs"]["break_even_acos"] == r["outputs"]["acos_pe"]
    assert "diagnosis" not in r   # legacy omits diagnosis


def test_compute_full_diagnosis_kdp_mode_returns_full_payload():
    book = {
        "precio_libro": 12.99,
        "format_type": "PRINT",
        "book_format": "PAPERBACK",
        "interior_type": "BN",
        "book_size": "SMALL",
        "pages": 220,
        "iva_type": 4,
        "cpc_referencia": 0.50,
        "margen_objetivo_pct": 30,
    }
    r = compute_full_diagnosis(book, "ES")
    assert r["mode"] == "kdp"
    assert r["marketplace"] == "ES"
    assert r["outputs"]["precio_sin_iva"] > 0
    assert r["outputs"]["regalia_neta"] is not None
    assert r["outputs"]["acos_pe"] == r["outputs"]["bacos"] == r["outputs"]["break_even_acos"]
    assert r["diagnosis"]["risk_level"] in ("low", "medium", "high")
    assert r["diagnosis"]["viability_status"] in ("viable", "adjustable", "not-viable")
    assert "score_total" in r["diagnosis"]
    assert set(r["diagnosis"]["score_breakdown"].keys()) == {"clicks_max", "acos_pe", "pvp_vs_pvp_min"}


def test_compute_full_diagnosis_accepts_lowercase_legacy_marketplace():
    book = {"precio_libro": 12.99, "regalias_por_venta": 4.5}
    r = compute_full_diagnosis(book, "us")  # legacy lowercase
    assert r["marketplace"] == "COM"
