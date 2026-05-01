"""KDP Economy module — Phase 1.

Pure, DB-less functions that model Amazon KDP book economics:
  - marketplace configuration (9 marketplaces, royalty threshold per MP)
  - printing tier tables (EU / US / UK / CA / AU / JP + hardcover surcharge)
  - delivery cost (eBook 70%)
  - regalía neta (net royalty)
  - ACoS de equilibrio (a.k.a. BACOS / break-even ACOS)
  - CPC máximo rentable
  - clicks PE base
  - tasa de conversión breakeven
  - PVP mínimo recomendado
  - diagnosis (risk level, viability status, orientative score)

Internal marketplace codes are UPPERCASE: ES, COM, DE, FR, IT, UK, CA, AU, JP.
The `normalize_mp()` helper accepts lowercase (legacy from frontend) and
returns the canonical uppercase form.

This module does NOT read or write the database.
It is consumed by server.py via a single read-only endpoint.
"""
from __future__ import annotations

from math import ceil
from typing import Literal, Optional


FormatType = Literal["EBOOK", "PRINT"]
BookFormat = Literal["PAPERBACK", "HARDCOVER"]
InteriorType = Literal["BN", "COLOR_PREMIUM", "COLOR_STANDARD"]
BookSize = Literal["SMALL", "LARGE"]


# ---------- Marketplace configuration ----------

MARKETPLACE_CONFIG: dict[str, dict] = {
    "ES":  {"name": "España",         "currency": "EUR", "symbol": "€",  "iva_default_pct": 4,   "royalty_threshold": 9.99,  "region": "EU"},
    "COM": {"name": "Estados Unidos", "currency": "USD", "symbol": "$",  "iva_default_pct": 0,   "royalty_threshold": 9.99,  "region": "COM"},
    "DE":  {"name": "Alemania",       "currency": "EUR", "symbol": "€",  "iva_default_pct": 7,   "royalty_threshold": 9.99,  "region": "EU"},
    "FR":  {"name": "Francia",        "currency": "EUR", "symbol": "€",  "iva_default_pct": 5.5, "royalty_threshold": 9.99,  "region": "EU"},
    "IT":  {"name": "Italia",         "currency": "EUR", "symbol": "€",  "iva_default_pct": 4,   "royalty_threshold": 9.99,  "region": "EU"},
    "UK":  {"name": "Reino Unido",    "currency": "GBP", "symbol": "£",  "iva_default_pct": 0,   "royalty_threshold": 9.99,  "region": "UK"},
    "CA":  {"name": "Canadá",         "currency": "CAD", "symbol": "C$", "iva_default_pct": 0,   "royalty_threshold": 12.99, "region": "CA"},
    "AU":  {"name": "Australia",      "currency": "AUD", "symbol": "A$", "iva_default_pct": 0,   "royalty_threshold": 14.99, "region": "AU"},
    "JP":  {"name": "Japón",          "currency": "JPY", "symbol": "¥",  "iva_default_pct": 0,   "royalty_threshold": 1250,  "region": "JP"},
}


# Aliases between legacy lowercase codes and KDP uppercase codes.
# Ads Analytics V2 historically stored "us" for Amazon.com.
_MP_ALIASES = {"us": "COM", "com": "COM"}


def normalize_mp(marketplace: Optional[str]) -> str:
    """Return canonical uppercase marketplace code. Defaults to 'COM'."""
    if not marketplace:
        return "COM"
    key = str(marketplace).strip()
    if key.lower() in _MP_ALIASES:
        return _MP_ALIASES[key.lower()]
    up = key.upper()
    return up if up in MARKETPLACE_CONFIG else "COM"


def mp_config(marketplace: str) -> dict:
    mp = normalize_mp(marketplace)
    return {"code": mp, **MARKETPLACE_CONFIG[mp]}


# ---------- Printing tiers ----------

# Structure: list of (min_pages, max_pages, fixed_cost, per_page_cost)
# Chosen by region → interior → size. First matching tier wins.

_PRINTING_EU: dict = {
    "BN":             {"SMALL": [(24, 108, 2.05, 0.0), (110, 828, 0.75, 0.012)],
                       "LARGE": [(24, 108, 2.48, 0.0), (110, 828, 0.75, 0.016)]},
    "COLOR_PREMIUM":  {"SMALL": [(24, 40,  2.85, 0.0), (42,  828, 0.75, 0.0525)],
                       "LARGE": [(24, 40,  3.61, 0.0), (42,  828, 0.75, 0.0715)]},
    "COLOR_STANDARD": {"SMALL": [(72, 600, 0.75, 0.024)],
                       "LARGE": [(72, 600, 0.75, 0.035)]},
}
_PRINTING_COM: dict = {
    "BN":             {"SMALL": [(24, 108, 2.30, 0.0), (109, 828, 1.00, 0.012)],
                       "LARGE": [(24, 108, 2.84, 0.0), (109, 828, 1.00, 0.017)]},
    "COLOR_PREMIUM":  {"SMALL": [(24, 40,  3.60, 0.0), (41,  828, 1.00, 0.065)],
                       "LARGE": [(24, 40,  4.20, 0.0), (41,  828, 1.00, 0.080)]},
    "COLOR_STANDARD": {"SMALL": [(72, 600, 1.00, 0.0255)],
                       "LARGE": [(72, 600, 1.00, 0.0402)]},
}
_PRINTING_UK: dict = {
    "BN":             {"SMALL": [(24, 108, 1.93, 0.0), (109, 828, 0.85, 0.010)],
                       "LARGE": [(24, 108, 2.15, 0.0), (109, 828, 0.85, 0.012)]},
    "COLOR_PREMIUM":  {"SMALL": [(24, 40,  2.59, 0.0), (41,  828, 0.85, 0.0435)],
                       "LARGE": [(24, 40,  3.24, 0.0), (41,  828, 0.85, 0.0598)]},
    "COLOR_STANDARD": {"SMALL": [(72, 600, 0.85, 0.020)],
                       "LARGE": [(72, 600, 0.85, 0.027)]},
}
_PRINTING_CA: dict = {
    "BN":             {"SMALL": [(24, 108, 2.99, 0.0), (109, 828, 1.26, 0.016)],
                       "LARGE": [(24, 108, 3.53, 0.0), (109, 828, 1.26, 0.021)]},
    "COLOR_PREMIUM":  {"SMALL": [(24, 40,  4.66, 0.0), (41,  828, 1.26, 0.085)],
                       "LARGE": [(24, 40,  5.26, 0.0), (41,  828, 1.26, 0.100)]},
    "COLOR_STANDARD": {"SMALL": [(72, 600, 1.26, 0.037)],
                       "LARGE": [(72, 600, 1.26, 0.052)]},
}
_PRINTING_AU: dict = {
    "BN":            {"SMALL": [(24, 108, 4.74, 0.0), (109, 828, 2.42, 0.022)],
                      "LARGE": [(24, 108, 5.28, 0.0), (109, 828, 2.42, 0.027)]},
    "COLOR_PREMIUM": {"SMALL": [(24, 40,  5.82, 0.0), (41,  828, 2.42, 0.085)],
                      "LARGE": [(24, 40,  6.42, 0.0), (41,  828, 2.42, 0.100)]},
    # AU: no COLOR_STANDARD
}
_PRINTING_JP: dict = {
    "BN":            {"SMALL": [(24, 108, 422, 0.0), (109, 828, 206, 2.0)],
                      "LARGE": [(24, 108, 530, 0.0), (109, 828, 206, 3.0)]},
    "COLOR_PREMIUM": {"SMALL": [(24, 40,  475, 0.0), (41,  828, 206, 4.0)],
                      "LARGE": [(24, 40,  475, 0.0), (41,  828, 206, 5.0)]},
    # JP: no COLOR_STANDARD
}

_REGION_TO_TABLE = {
    "EU":  _PRINTING_EU,
    "COM": _PRINTING_COM,
    "UK":  _PRINTING_UK,
    "CA":  _PRINTING_CA,
    "AU":  _PRINTING_AU,
    "JP":  _PRINTING_JP,
}

# Hardcover fixed-cost surcharge per region (added on top of paperback fixed cost).
_HARDCOVER_SURCHARGE = {"EU": 5.72, "COM": 6.80, "UK": 4.95, "CA": 8.50, "AU": 10.20, "JP": 850}


# ---------- Format rules ----------

MAX_PAGES = {"BN": 828, "COLOR_PREMIUM": 828, "COLOR_STANDARD": 600}
MIN_PAGES = {"BN": 24, "COLOR_PREMIUM": 24, "COLOR_STANDARD": 72}


class KdpEconomyError(ValueError):
    pass


def _pick_tier(region: str, interior: str, size: str, pages: int) -> tuple[float, float]:
    table = _REGION_TO_TABLE.get(region)
    if table is None:
        raise KdpEconomyError(f"Región sin tarifas: {region}")
    by_interior = table.get(interior)
    if by_interior is None:
        raise KdpEconomyError(f"Interior {interior} no disponible en {region}")
    tiers = by_interior.get(size)
    if not tiers:
        raise KdpEconomyError(f"Tamaño {size} no disponible para {interior} en {region}")
    for (mn, mx, fx, pp) in tiers:
        if mn <= pages <= mx:
            return fx, pp
    raise KdpEconomyError(
        f"Páginas {pages} fuera del rango soportado ({interior}/{size}/{region})"
    )


# ---------- Formulas ----------

def calc_precio_sin_iva(pvp: float, marketplace: str, iva_type: Optional[float] = None) -> float:
    """IVA only applies in ES (per product rule). For all other marketplaces returns pvp unchanged."""
    mp = normalize_mp(marketplace)
    iva_pct = float(iva_type or MARKETPLACE_CONFIG[mp]["iva_default_pct"]) if mp == "ES" else 0.0
    return pvp / (1.0 + iva_pct / 100.0)


def calc_delivery_cost(tamano_mb: Optional[float], royalty_rate_ebook: Optional[int]) -> float:
    """Delivery cost for eBook 70% royalty. Returns 0 for 35% or missing inputs."""
    if not royalty_rate_ebook or int(royalty_rate_ebook) != 70:
        return 0.0
    mb = float(tamano_mb or 0)
    return ceil(mb) * 0.12 if mb > 0 else 0.0


def calc_coste_impresion(
    interior: InteriorType, size: BookSize, marketplace: str, pages: int,
    book_format: Optional[BookFormat] = None,
) -> float:
    """Compute printing cost for paperback; adds hardcover surcharge when book_format == 'HARDCOVER'."""
    if interior not in ("BN", "COLOR_PREMIUM", "COLOR_STANDARD"):
        raise KdpEconomyError(f"Interior inválido: {interior}")
    if size not in ("SMALL", "LARGE"):
        raise KdpEconomyError(f"Tamaño inválido: {size}")
    if not isinstance(pages, int) or pages < MIN_PAGES[interior]:
        raise KdpEconomyError(f"{interior} requiere ≥{MIN_PAGES[interior]} páginas (recibido {pages})")
    if pages > MAX_PAGES[interior]:
        raise KdpEconomyError(f"{interior} soporta máximo {MAX_PAGES[interior]} páginas (recibido {pages})")
    if book_format == "HARDCOVER" and interior == "COLOR_STANDARD":
        raise KdpEconomyError("Hardcover no compatible con COLOR_STANDARD")

    region = MARKETPLACE_CONFIG[normalize_mp(marketplace)]["region"]
    fx, pp = _pick_tier(region, interior, size, pages)
    coste = fx + (pages * pp)
    if book_format == "HARDCOVER":
        coste += _HARDCOVER_SURCHARGE[region]
    return round(coste, 4)


def calc_regalia_neta(
    *, format_type: FormatType, pvp: float, marketplace: str,
    iva_type: Optional[float] = None,
    royalty_rate_ebook: Optional[int] = None,
    tamano_mb: Optional[float] = None,
    book_format: Optional[BookFormat] = None,
    interior: Optional[InteriorType] = None,
    size: Optional[BookSize] = None,
    pages: Optional[int] = None,
) -> dict:
    """Return {regalia_neta, precio_sin_iva, coste_impresion, delivery_cost, royalty_rate_used_pct}.

    For EBOOK: uses royalty_rate_ebook (70 or 35) and delivery cost on 70%.
    For PRINT: uses 0.50 if pvp < royalty_threshold (marketplace-specific), else 0.60.
               Printing cost is subtracted; hardcover surcharge added when applicable.
    """
    mp = normalize_mp(marketplace)
    precio_sin_iva = calc_precio_sin_iva(pvp, mp, iva_type)

    if format_type == "EBOOK":
        rate = int(royalty_rate_ebook or 70)
        if rate not in (35, 70):
            raise KdpEconomyError("royalty_rate_ebook debe ser 35 o 70")
        delivery = calc_delivery_cost(tamano_mb, rate)
        regalia = precio_sin_iva * (rate / 100.0) - delivery
        return {
            "regalia_neta": round(regalia, 4),
            "precio_sin_iva": round(precio_sin_iva, 4),
            "coste_impresion": 0.0,
            "delivery_cost": round(delivery, 4),
            "royalty_rate_used_pct": rate,
        }

    if format_type == "PRINT":
        if interior is None or size is None or pages is None:
            raise KdpEconomyError("PRINT requiere interior, size y pages")
        coste = calc_coste_impresion(interior, size, mp, pages, book_format=book_format)
        threshold = MARKETPLACE_CONFIG[mp]["royalty_threshold"]
        rate_pct = 60 if pvp >= threshold else 50
        regalia = precio_sin_iva * (rate_pct / 100.0) - coste
        return {
            "regalia_neta": round(regalia, 4),
            "precio_sin_iva": round(precio_sin_iva, 4),
            "coste_impresion": round(coste, 4),
            "delivery_cost": 0.0,
            "royalty_rate_used_pct": rate_pct,
        }

    raise KdpEconomyError(f"format_type inválido: {format_type}")


def calc_acos_pe(regalia_neta: float, pvp: float) -> Optional[float]:
    """ACoS de Equilibrio = regalía / PVP × 100. Also known as BACOS / break-even ACoS."""
    if not pvp or pvp <= 0:
        return None
    return round((regalia_neta / pvp) * 100.0, 2)


def calc_cpc_max_rentable(regalia_neta: float) -> Optional[float]:
    """CPC máximo orientativo = regalía / 10 (umbral de 10 clicks mínimos por venta)."""
    if regalia_neta is None or regalia_neta <= 0:
        return None
    return round(regalia_neta / 10.0, 4)


def calc_clicks_pe_base(regalia_neta: float, cpc_referencia: Optional[float]) -> Optional[float]:
    """Clicks PE base = regalía / CPC_ref. Requires a reference CPC."""
    if not cpc_referencia or cpc_referencia <= 0 or regalia_neta is None or regalia_neta <= 0:
        return None
    return round(regalia_neta / cpc_referencia, 4)


def calc_tasa_conv_breakeven(regalia_neta: float, cpc_referencia: Optional[float]) -> Optional[float]:
    """Conversion rate needed to break-even = CPC / regalía."""
    if not cpc_referencia or cpc_referencia <= 0 or regalia_neta is None or regalia_neta <= 0:
        return None
    return round(cpc_referencia / regalia_neta, 4)


def beneficio_kdp(orders: float, regalia_neta: float, spend: float) -> float:
    """Correct KDP profit: orders × regalía − spend. Defined here for Fase 2+ consumers.

    NOTE: in Fase 1 this is not wired into any user-facing table.
    """
    return round((orders or 0) * (regalia_neta or 0) - (spend or 0), 4)


def _ceil_cent(x: float) -> float:
    return round(ceil(x * 100) / 100.0, 2)


def calc_pvp_minimo(
    *, format_type: FormatType, marketplace: str,
    margen_objetivo_pct: float = 30.0,
    iva_type: Optional[float] = None,
    royalty_rate_ebook: Optional[int] = None,
    tamano_mb: Optional[float] = None,
    interior: Optional[InteriorType] = None,
    size: Optional[BookSize] = None,
    pages: Optional[int] = None,
    book_format: Optional[BookFormat] = None,
) -> Optional[float]:
    """Minimum PVP that hits the target margin. Returns None when not feasible."""
    mp = normalize_mp(marketplace)
    iva_pct = float(iva_type or MARKETPLACE_CONFIG[mp]["iva_default_pct"]) if mp == "ES" else 0.0
    m = margen_objetivo_pct / 100.0

    if format_type == "EBOOK":
        rate = int(royalty_rate_ebook or 70)
        r = rate / 100.0
        denom = r - m
        if denom <= 0:
            return None
        if rate == 35 and m > 0.35:
            return None
        delivery = calc_delivery_cost(tamano_mb, rate)
        p_sin_iva_min = delivery / denom if denom > 0 else 0
        return _ceil_cent(p_sin_iva_min * (1.0 + iva_pct / 100.0))

    if format_type == "PRINT":
        if interior is None or size is None or pages is None:
            return None
        coste = calc_coste_impresion(interior, size, mp, pages, book_format=book_format)
        threshold = MARKETPLACE_CONFIG[mp]["royalty_threshold"]
        denom60 = 0.60 - m
        if denom60 <= 0:
            return None
        pvp60 = _ceil_cent((coste / denom60) * (1.0 + iva_pct / 100.0))
        if pvp60 >= threshold:
            return pvp60
        denom50 = 0.50 - m
        if denom50 <= 0:
            return threshold
        pvp50 = _ceil_cent((coste / denom50) * (1.0 + iva_pct / 100.0))
        if pvp50 >= threshold:
            return threshold
        test = threshold
        while test <= 100 + threshold:
            test_sin_iva = test / (1.0 + iva_pct / 100.0)
            test_regalias = test_sin_iva * 0.60 - coste
            test_margen = test_regalias / test_sin_iva if test_sin_iva > 0 else 0
            if test_margen >= m:
                return _ceil_cent(test)
            test += 0.10
        return None

    return None


# ---------- Scoring (§20 of bridge) ----------

def _score_clicks(clicks_pe_base: Optional[float]) -> tuple[int, int]:
    """Return (points, max=50)."""
    if clicks_pe_base is None:
        return 0, 50
    c = float(clicks_pe_base)
    if c >= 14: return 50, 50
    if c >= 13: return 35, 50
    if c >= 12: return 25, 50
    if c >= 11: return 15, 50
    if c >= 10: return 10, 50
    return 0, 50


def _score_acos_pe(acos_pe: Optional[float]) -> tuple[int, int]:
    if acos_pe is None:
        return 0, 40
    if acos_pe >= 40: return 40, 40
    if acos_pe >= 35: return 25, 40
    if acos_pe >= 30: return 15, 40
    return 0, 40


def _score_pvp_vs_min(pvp: float, pvp_min: Optional[float]) -> tuple[int, int]:
    if pvp_min is None:
        return 10, 10   # cannot compute → don't penalize
    diff = pvp - pvp_min
    if diff > 0.01: return 10, 10
    if abs(diff) <= 0.01: return 5, 10
    return 0, 10


def diagnose(
    *, regalia_neta: Optional[float], acos_pe: Optional[float],
    clicks_pe_base: Optional[float], pvp: float, pvp_minimo: Optional[float],
) -> dict:
    """Return risk_level, viability_status, score and labels per book economy."""
    margen_pct = acos_pe  # equivalent (regalia/pvp*100)
    clicks = clicks_pe_base

    # risk_level (§19.3)
    if (margen_pct is not None and margen_pct < 30) or (clicks is not None and clicks < 10):
        risk_level = "high"
    elif (margen_pct is not None and margen_pct <= 40) or (clicks is not None and clicks < 13):
        risk_level = "medium"
    else:
        risk_level = "low"

    # viability_status (§19.4)
    if regalia_neta is None or regalia_neta <= 0 or (margen_pct is not None and margen_pct < 20) or (clicks is not None and clicks < 5):
        viability_status = "not-viable"
    elif (margen_pct is not None and margen_pct < 30) or (clicks is not None and clicks < 10):
        viability_status = "adjustable"
    else:
        viability_status = "viable"

    c_pts, c_max = _score_clicks(clicks)
    a_pts, a_max = _score_acos_pe(margen_pct)
    p_pts, p_max = _score_pvp_vs_min(pvp, pvp_minimo)
    total = c_pts + a_pts + p_pts

    # labels
    if clicks is None:
        clicks_label = "—"
    elif clicks >= 13:
        clicks_label = "Excelente"
    elif clicks >= 10:
        clicks_label = "Aceptable"
    else:
        clicks_label = "En riesgo"

    if margen_pct is None:
        margen_label = "—"
    elif margen_pct >= 40:
        margen_label = "Excelente"
    elif margen_pct >= 30:
        margen_label = "Aceptable"
    else:
        margen_label = "En riesgo"

    pvp_label = "OK" if (pvp_minimo is None or pvp > pvp_minimo + 0.01) else ("Justo" if pvp_minimo and abs(pvp - pvp_minimo) <= 0.01 else "Bajo")

    return {
        "risk_level": risk_level,
        "viability_status": viability_status,
        "score_total": total,
        "score_breakdown": {
            "clicks_max":     {"points": c_pts, "max": c_max, "value": clicks},
            "acos_pe":        {"points": a_pts, "max": a_max, "value": margen_pct},
            "pvp_vs_pvp_min": {"points": p_pts, "max": p_max, "value": pvp},
        },
        "labels": {"clicks": clicks_label, "margen": margen_label, "pvp": pvp_label},
    }


# ---------- Orchestration: full diagnosis payload ----------

_REQUIRED_KDP = ("format_type",)
_REQUIRED_PRINT = ("interior_type", "book_size", "pages")


def compute_full_diagnosis(book_economy: dict, marketplace: str) -> dict:
    """Return the full payload for GET /economy-diagnosis.

    If the dataset lacks KDP fields, returns a {mode: "legacy"} payload that
    still includes basic acos_pe / cpc_max using precio_libro + regalias_por_venta.
    """
    mp = normalize_mp(marketplace)
    mp_cfg = MARKETPLACE_CONFIG[mp]

    pvp = float(book_economy.get("precio_libro") or 0)
    format_type = book_economy.get("format_type")
    cpc_ref = book_economy.get("cpc_referencia")

    # Legacy mode: no format_type → fall back to precio + regalías
    if not format_type:
        regalias = float(book_economy.get("regalias_por_venta") or 0)
        acos_pe = calc_acos_pe(regalias, pvp) if (pvp and regalias) else None
        cpc_max = calc_cpc_max_rentable(regalias)
        clicks_pe = calc_clicks_pe_base(regalias, cpc_ref) if cpc_ref else None
        return {
            "mode": "legacy",
            "marketplace": mp,
            "marketplace_config": {
                "currency": mp_cfg["currency"], "symbol": mp_cfg["symbol"],
                "iva_default_pct": mp_cfg["iva_default_pct"],
                "royalty_threshold": mp_cfg["royalty_threshold"],
            },
            "inputs": {"pvp": pvp, "regalias_por_venta": regalias, "cpc_referencia": cpc_ref},
            "outputs": {
                "regalia_neta": regalias,
                "acos_pe": acos_pe,
                "bacos": acos_pe,
                "break_even_acos": acos_pe,
                "cpc_max_rentable": cpc_max,
                "clicks_pe_base": clicks_pe,
            },
            "notes": [
                "Modo legacy: configura formato, páginas e IVA del libro para obtener el diagnóstico completo KDP."
            ],
        }

    # KDP mode
    try:
        rn = calc_regalia_neta(
            format_type=format_type, pvp=pvp, marketplace=mp,
            iva_type=book_economy.get("iva_type"),
            royalty_rate_ebook=book_economy.get("royalty_rate_ebook"),
            tamano_mb=book_economy.get("tamano_mb"),
            book_format=book_economy.get("book_format"),
            interior=book_economy.get("interior_type"),
            size=book_economy.get("book_size"),
            pages=book_economy.get("pages"),
        )
    except KdpEconomyError as e:
        return {
            "mode": "kdp",
            "marketplace": mp,
            "error": str(e),
            "marketplace_config": {
                "currency": mp_cfg["currency"], "symbol": mp_cfg["symbol"],
                "iva_default_pct": mp_cfg["iva_default_pct"],
                "royalty_threshold": mp_cfg["royalty_threshold"],
            },
            "inputs": dict(book_economy),
        }

    regalia = rn["regalia_neta"]
    acos_pe = calc_acos_pe(regalia, pvp)
    cpc_max = calc_cpc_max_rentable(regalia)
    clicks_pe = calc_clicks_pe_base(regalia, cpc_ref)
    tasa_conv = calc_tasa_conv_breakeven(regalia, cpc_ref)
    pvp_min = calc_pvp_minimo(
        format_type=format_type, marketplace=mp,
        margen_objetivo_pct=float(book_economy.get("margen_objetivo_pct") or 30.0),
        iva_type=book_economy.get("iva_type"),
        royalty_rate_ebook=book_economy.get("royalty_rate_ebook"),
        tamano_mb=book_economy.get("tamano_mb"),
        interior=book_economy.get("interior_type"),
        size=book_economy.get("book_size"),
        pages=book_economy.get("pages"),
        book_format=book_economy.get("book_format"),
    )
    diag = diagnose(
        regalia_neta=regalia, acos_pe=acos_pe,
        clicks_pe_base=clicks_pe, pvp=pvp, pvp_minimo=pvp_min,
    )

    iva_aplicado = float(book_economy.get("iva_type") or mp_cfg["iva_default_pct"]) if mp == "ES" else 0.0

    return {
        "mode": "kdp",
        "marketplace": mp,
        "marketplace_config": {
            "currency": mp_cfg["currency"], "symbol": mp_cfg["symbol"],
            "iva_default_pct": mp_cfg["iva_default_pct"],
            "royalty_threshold": mp_cfg["royalty_threshold"],
        },
        "inputs": {
            "format_type": format_type,
            "book_format": book_economy.get("book_format"),
            "interior_type": book_economy.get("interior_type"),
            "book_size": book_economy.get("book_size"),
            "pages": book_economy.get("pages"),
            "pvp": pvp,
            "iva_pct_aplicado": iva_aplicado,
            "royalty_rate_ebook": book_economy.get("royalty_rate_ebook"),
            "tamano_mb": book_economy.get("tamano_mb"),
            "cpc_referencia": cpc_ref,
            "margen_objetivo_pct": float(book_economy.get("margen_objetivo_pct") or 30.0),
        },
        "outputs": {
            "precio_sin_iva": rn["precio_sin_iva"],
            "coste_impresion": rn["coste_impresion"],
            "delivery_cost": rn["delivery_cost"],
            "royalty_rate_used_pct": rn["royalty_rate_used_pct"],
            "regalia_neta": regalia,
            "margen_pct": acos_pe,
            "acos_pe": acos_pe,
            "bacos": acos_pe,
            "break_even_acos": acos_pe,
            "cpc_max_rentable": cpc_max,
            "clicks_pe_base": clicks_pe,
            "tasa_conv_breakeven": tasa_conv,
            "pvp_minimo_recomendado": pvp_min,
        },
        "diagnosis": diag,
        "notes": [
            "Disclaimer: estimaciones orientativas basadas en tasas de referencia del sector y configuración económica del libro.",
        ],
    }
