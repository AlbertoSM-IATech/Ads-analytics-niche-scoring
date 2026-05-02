"""Phase 2 unit tests for compute_row_econ + resolve_regalia_neta."""
import pytest

from kdp_economy import (
    compute_row_econ, resolve_regalia_neta, PHASE_MULT_DEFAULTS,
)

# Defaults aligned with the dataset multipliers (1.7/1.2/0.5) — Phase 2 must NOT
# change these. If Phase 3 ever migrates them, this test must fail loudly.
DEFAULT_MULTIPLIERS = {"mult_lanzamiento": 1.7, "mult_dominio": 1.2, "mult_beneficio": 0.5}


# ---------- cpc_real ----------

def test_cpc_real_spend_div_clicks():
    e = compute_row_econ(clicks=20, spend=10, orders=2, sales=30,
                         regalia_neta=5, pvp=10, cpc_referencia=None,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    assert e["cpc_real"] == pytest.approx(0.5)
    assert e["cpc_source"] == "real"


def test_cpc_real_null_when_clicks_zero():
    e = compute_row_econ(clicks=0, spend=0, orders=0, sales=0,
                         regalia_neta=5, pvp=10, cpc_referencia=None,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    assert e["cpc_real"] is None


def test_cpc_real_null_when_spend_zero():
    # No spend yet (impressions only) → no real CPC
    e = compute_row_econ(clicks=10, spend=0, orders=0, sales=0,
                         regalia_neta=5, pvp=10, cpc_referencia=None,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    assert e["cpc_real"] is None


# ---------- clicks_pe ----------

def test_clicks_pe_regalia_div_cpc_real():
    e = compute_row_econ(clicks=20, spend=10, orders=1, sales=15,
                         regalia_neta=5, pvp=10, cpc_referencia=None,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    # cpc_real = 10/20 = 0.5 ; clicks_pe = 5/0.5 = 10
    assert e["clicks_pe"] == pytest.approx(10.0)


# ---------- clicks_fase: uses dataset multiplier, not new defaults ----------

def test_clicks_fase_uses_dataset_multiplier_not_new_defaults():
    """Phase 2 MUST use the dataset's own multipliers (1.7/1.2/0.5).

    If a developer later migrates defaults to 1.5/1.1/0.7 globally, this test
    will fail and remind them that Phase 2 is supposed to leave behavior
    unchanged for existing datasets.
    """
    e = compute_row_econ(clicks=20, spend=10, orders=1, sales=15,
                         regalia_neta=5, pvp=10, cpc_referencia=None,
                         phase="lanzamiento", multipliers=DEFAULT_MULTIPLIERS)
    # cpc_real = 0.5 ; clicks_fase = 5 * 1.7 / 0.5 = 17
    assert e["phase_mult_used"] == pytest.approx(1.7)
    assert e["clicks_fase"] == pytest.approx(17.0)
    assert PHASE_MULT_DEFAULTS["lanzamiento"] == 1.7   # canary


def test_clicks_fase_dominio_uses_12():
    e = compute_row_econ(clicks=20, spend=10, orders=1, sales=15,
                         regalia_neta=5, pvp=10, cpc_referencia=None,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    assert e["phase_mult_used"] == pytest.approx(1.2)
    assert e["clicks_fase"] == pytest.approx(5 * 1.2 / 0.5)


def test_clicks_fase_beneficio_uses_05():
    e = compute_row_econ(clicks=20, spend=10, orders=1, sales=15,
                         regalia_neta=5, pvp=10, cpc_referencia=None,
                         phase="beneficio", multipliers=DEFAULT_MULTIPLIERS)
    assert e["phase_mult_used"] == pytest.approx(0.5)
    assert e["clicks_fase"] == pytest.approx(5 * 0.5 / 0.5)


# ---------- consumo_pe / consumo_fase ----------

def test_consumo_pe_clicks_div_clicks_pe():
    e = compute_row_econ(clicks=8, spend=4, orders=1, sales=10,
                         regalia_neta=5, pvp=10, cpc_referencia=None,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    # cpc_real = 0.5; clicks_pe = 10; consumo_pe = 8/10 = 0.8
    assert e["consumo_pe"] == pytest.approx(0.8)


def test_consumo_fase_clicks_div_clicks_fase():
    e = compute_row_econ(clicks=8, spend=4, orders=1, sales=10,
                         regalia_neta=5, pvp=10, cpc_referencia=None,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    # cpc_real=0.5; clicks_fase = 5 * 1.2 / 0.5 = 12; consumo_fase = 8/12 ≈ 0.6667
    assert e["consumo_fase"] == pytest.approx(8 / 12, rel=1e-3)


# ---------- beneficio_kdp ----------

def test_beneficio_kdp_orders_by_regalia_minus_spend():
    e = compute_row_econ(clicks=20, spend=10, orders=3, sales=30,
                         regalia_neta=4.5, pvp=10, cpc_referencia=None,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    # 3 * 4.5 - 10 = 3.5
    assert e["beneficio_kdp"] == pytest.approx(3.5)


def test_beneficio_kdp_negative_when_losing_money():
    e = compute_row_econ(clicks=20, spend=10, orders=0, sales=0,
                         regalia_neta=4.5, pvp=10, cpc_referencia=None,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    assert e["beneficio_kdp"] == pytest.approx(-10.0)


def test_beneficio_kdp_null_without_regalia():
    """If we cannot resolve regalía, beneficio_kdp must be null — never invent."""
    e = compute_row_econ(clicks=20, spend=10, orders=2, sales=30,
                         regalia_neta=None, pvp=None, cpc_referencia=None,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    assert e["beneficio_kdp"] is None


# ---------- cpc_referencia fallback ----------

def test_cpc_source_reference_when_no_real_data_but_cpc_ref_set():
    e = compute_row_econ(clicks=0, spend=0, orders=0, sales=0,
                         regalia_neta=5, pvp=10, cpc_referencia=0.5,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    assert e["cpc_real"] is None
    assert e["cpc_source"] == "reference"
    assert e["clicks_pe"] == pytest.approx(10.0)   # 5/0.5
    # When clicks=0 and clicks_pe>0, consumo_pe = 0/10 = 0.0 (zero consumption is meaningful).
    assert e["consumo_pe"] == pytest.approx(0.0)
    # And an existing, non-yet-consumed ACoS-PE estimate is computable from cpc_ref + pvp.
    assert e["acos_siguiente_con_venta"] == pytest.approx(5.0)


def test_consumo_pe_is_zero_when_no_clicks_yet_but_clicks_pe_known():
    """A keyword with 0 clicks but a known clicks_pe correctly reports 0% consumption."""
    e = compute_row_econ(clicks=0, spend=0, orders=0, sales=0,
                         regalia_neta=5, pvp=10, cpc_referencia=0.5,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    assert e["consumo_pe"] == 0.0
    assert e["consumo_fase"] == 0.0


def test_cpc_source_none_when_nothing():
    e = compute_row_econ(clicks=0, spend=0, orders=0, sales=0,
                         regalia_neta=5, pvp=10, cpc_referencia=None,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    assert e["cpc_real"] is None
    assert e["cpc_source"] == "none"
    assert e["clicks_pe"] is None
    assert e["clicks_fase"] is None
    assert e["consumo_pe"] is None


# ---------- division by zero safety ----------

def test_division_by_zero_safe_everywhere():
    """Zero everywhere → no exceptions, all derived metrics None."""
    e = compute_row_econ(clicks=0, spend=0, orders=0, sales=0,
                         regalia_neta=0, pvp=0, cpc_referencia=0,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    for k in ("cpc_real", "regalia_neta_kdp", "acos_pe_kdp",
              "clicks_pe", "clicks_fase", "consumo_pe", "consumo_fase",
              "beneficio_kdp", "acos_siguiente_con_venta"):
        assert e[k] is None, f"{k} should be None when all inputs are 0"


# ---------- ACoS siguiente con venta ----------

def test_acos_siguiente_con_venta_with_pvp_and_real_cpc():
    e = compute_row_econ(clicks=20, spend=10, orders=1, sales=15,
                         regalia_neta=5, pvp=10, cpc_referencia=None,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    # (10 + 0.5) / (15 + 10) * 100 = 42.0
    assert e["acos_siguiente_con_venta"] == pytest.approx(42.0)


def test_acos_siguiente_con_venta_null_without_pvp():
    e = compute_row_econ(clicks=20, spend=10, orders=1, sales=15,
                         regalia_neta=5, pvp=None, cpc_referencia=None,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    assert e["acos_siguiente_con_venta"] is None


def test_acos_siguiente_con_venta_uses_reference_cpc_when_no_real():
    e = compute_row_econ(clicks=0, spend=0, orders=0, sales=0,
                         regalia_neta=5, pvp=10, cpc_referencia=0.5,
                         phase="dominio", multipliers=DEFAULT_MULTIPLIERS)
    # (0 + 0.5) / (0 + 10) * 100 = 5.0
    assert e["acos_siguiente_con_venta"] == pytest.approx(5.0)


# ---------- resolve_regalia_neta priority ----------

def test_resolve_regalia_neta_kdp_when_format_type_set():
    eco = {
        "precio_libro": 12.99, "regalias_por_venta": 1.0,
        "format_type": "PRINT", "book_format": "PAPERBACK",
        "interior_type": "BN", "book_size": "SMALL", "pages": 220, "iva_type": 4,
    }
    info = resolve_regalia_neta(eco, "ES")
    assert info["source"] == "kdp"
    assert info["regalia_neta"] > 1.0   # Should use the KDP calc, not 1.0 legacy


def test_resolve_regalia_neta_legacy_when_no_format():
    eco = {"precio_libro": 9.99, "regalias_por_venta": 3.5}
    info = resolve_regalia_neta(eco, "COM")
    assert info["source"] == "legacy"
    assert info["regalia_neta"] == 3.5
    assert info["pvp"] == 9.99


def test_resolve_regalia_neta_none_when_nothing():
    info = resolve_regalia_neta({}, "COM")
    assert info["source"] == "none"
    assert info["regalia_neta"] is None


def test_resolve_regalia_neta_kdp_falls_back_to_legacy_on_invalid_kdp():
    """If KDP config is incomplete (e.g. missing pages), fall back to legacy."""
    eco = {
        "precio_libro": 9.99, "regalias_por_venta": 3.5,
        "format_type": "PRINT",  # missing interior/size/pages
    }
    info = resolve_regalia_neta(eco, "COM")
    assert info["source"] == "legacy"
    assert info["regalia_neta"] == 3.5
