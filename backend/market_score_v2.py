"""Market Score V2 — continuous scoring algorithm.
Ported from the original repo (`/src/lib/market-score.ts` + `market-score-config.ts`).
Uses ideal anchors per marketplace that can be overridden per dataset.
"""
from __future__ import annotations
from typing import Optional


# Exact defaults from the original repo
MARKET_DEFAULTS: dict[str, dict] = {
    "default": {"idealVolume": 600, "idealCompetitors": 1000, "idealPrice": 12.99, "idealRoyalties": 4.5, "label": "Por defecto"},
    "es": {"idealVolume": 600, "idealCompetitors": 1000, "idealPrice": 12.99, "idealRoyalties": 4.5, "label": "España"},
    "us": {"idealVolume": 1000, "idealCompetitors": 1500, "idealPrice": 14.99, "idealRoyalties": 5.5, "label": "Estados Unidos"},
    "uk": {"idealVolume": 800, "idealCompetitors": 1200, "idealPrice": 12.99, "idealRoyalties": 4.5, "label": "Reino Unido"},
    "de": {"idealVolume": 700, "idealCompetitors": 1100, "idealPrice": 12.99, "idealRoyalties": 4.5, "label": "Alemania"},
    "fr": {"idealVolume": 600, "idealCompetitors": 1000, "idealPrice": 11.99, "idealRoyalties": 4.0, "label": "Francia"},
    "it": {"idealVolume": 500, "idealCompetitors": 900, "idealPrice": 10.99, "idealRoyalties": 3.5, "label": "Italia"},
    "ca": {"idealVolume": 400, "idealCompetitors": 700, "idealPrice": 12.99, "idealRoyalties": 4.0, "label": "Canadá"},
    "mx": {"idealVolume": 300, "idealCompetitors": 600, "idealPrice": 9.99, "idealRoyalties": 3.0, "label": "México"},
    "jp": {"idealVolume": 400, "idealCompetitors": 800, "idealPrice": 10.99, "idealRoyalties": 3.5, "label": "Japón"},
    "au": {"idealVolume": 300, "idealCompetitors": 600, "idealPrice": 12.99, "idealRoyalties": 4.0, "label": "Australia"},
}


WEIGHTS = {"volume": 26, "competitors": 34, "price": 8, "royalties": 8, "market_structure": 12, "catalog_signals": 12}


def get_defaults(marketplace: str) -> dict:
    return dict(MARKET_DEFAULTS.get(marketplace) or MARKET_DEFAULTS["default"])


def merge_criteria(marketplace: str, overrides: Optional[dict]) -> dict:
    """Return effective criteria (defaults + user overrides)."""
    base = get_defaults(marketplace)
    if overrides:
        for k in ("idealVolume", "idealCompetitors", "idealPrice", "idealRoyalties"):
            if overrides.get(k) is not None:
                base[k] = overrides[k]
    return base


def _volume_anchors(ideal: float) -> dict:
    return {"v0": round(ideal * 0.05), "v1": round(ideal * 0.15), "v2": round(ideal * 0.5), "ideal": ideal}


def _competitor_anchors(ideal: float) -> dict:
    return {"c0": round(ideal * 0.3), "c1": round(ideal * 0.7), "c2": round(ideal * 1.5), "ideal": ideal}


def _royalty_anchors(ideal: float) -> dict:
    return {"r0": 1.99, "r1": 3.99, "r2": 6.0, "ideal": ideal}


def _lerp(v: float, a: float, b: float) -> float:
    if v <= a:
        return 0.0
    if v >= b:
        return 1.0
    return (v - a) / (b - a)


def _volume_ratio(v: float, ideal: float) -> float:
    a = _volume_anchors(ideal)
    if v <= a["v0"]:
        return 0.0
    if v <= a["v1"]:
        return _lerp(v, a["v0"], a["v1"]) * 0.33
    if v <= a["v2"]:
        return 0.33 + _lerp(v, a["v1"], a["v2"]) * 0.33
    if v <= a["ideal"]:
        return 0.66 + _lerp(v, a["v2"], a["ideal"]) * 0.34
    return 1.0


def _competitors_ratio(v: float, ideal: float) -> float:
    a = _competitor_anchors(ideal)
    if v <= a["c0"]:
        return 1.0
    if v <= a["c1"]:
        return 1.0 - _lerp(v, a["c0"], a["c1"]) * 0.34
    if v <= a["c2"]:
        return 0.66 - _lerp(v, a["c1"], a["c2"]) * 0.33
    beyond = min(_lerp(v, a["c2"], a["c2"] * 2), 1.0)
    return max(0.0, 0.33 - beyond * 0.33)


def _price_ratio(price: float, ideal: float) -> float:
    if price < 7.99:
        return 0.0
    if price < 9.99:
        return _lerp(price, 7.99, 9.99) * 0.4
    if price <= ideal:
        return 0.4 + _lerp(price, 9.99, ideal) * 0.6
    return 1.0


def _royalties_ratio(r: float, ideal: float) -> float:
    a = _royalty_anchors(ideal)
    if r <= a["r0"]:
        return 0.0
    if r <= a["r1"]:
        return _lerp(r, a["r0"], a["r1"]) * 0.4
    if r <= a["r2"]:
        return 0.4 + _lerp(r, a["r1"], a["r2"]) * 0.3
    if r <= a["ideal"]:
        return 0.7 + _lerp(r, a["r2"], a["ideal"]) * 0.3
    return 1.0


def calc_market_score_v2(
    search_volume: Optional[float],
    competitors: Optional[float],
    price: Optional[float],
    royalties: Optional[float],
    market_structure_checks: int = 0,
    catalog_signals_checks: int = 0,
    criteria: Optional[dict] = None,
    marketplace: str = "default",
) -> dict:
    c = criteria or get_defaults(marketplace)
    vol = float(search_volume or 0)
    comp = float(competitors or 0)
    p = float(price or 0)
    r = float(royalties or 0)

    vol_r = _volume_ratio(vol, c["idealVolume"])
    comp_r = _competitors_ratio(comp, c["idealCompetitors"])
    price_r = _price_ratio(p, c["idealPrice"]) if p else 0.0
    roy_r = _royalties_ratio(r, c["idealRoyalties"]) if r else 0.0

    vol_pts = round(vol_r * WEIGHTS["volume"], 2)
    comp_pts = round(comp_r * WEIGHTS["competitors"], 2)
    price_pts = round(price_r * WEIGHTS["price"], 2)
    roy_pts = round(roy_r * WEIGHTS["royalties"], 2)
    struct_pts = min(int(market_structure_checks or 0), 6) * 2
    # Auto-calc: <3000 competitors adds 5 pts bonus; manual checks add up to 7 more; cap at 12
    catalog_auto = 5 if 0 < comp < 3000 else 0
    cat_pts = min(catalog_auto + min(int(catalog_signals_checks or 0), 3) * 2, WEIGHTS["catalog_signals"])

    total = vol_pts + comp_pts + price_pts + roy_pts + struct_pts + cat_pts
    total = max(0, min(100, round(total)))

    return {
        "total": total,
        "breakdown": {
            "volume": {"points": vol_pts, "max": WEIGHTS["volume"], "ratio": round(vol_r, 2)},
            "competitors": {"points": comp_pts, "max": WEIGHTS["competitors"], "ratio": round(comp_r, 2)},
            "price": {"points": price_pts, "max": WEIGHTS["price"], "ratio": round(price_r, 2)},
            "royalties": {"points": roy_pts, "max": WEIGHTS["royalties"], "ratio": round(roy_r, 2)},
            "market_structure": {"points": struct_pts, "max": WEIGHTS["market_structure"], "checks": int(market_structure_checks or 0)},
            "catalog_signals": {"points": cat_pts, "max": WEIGHTS["catalog_signals"], "checks": int(catalog_signals_checks or 0)},
        },
        "label": score_label(total),
        "criteria_used": c,
    }


def score_label(score: int) -> str:
    if score >= 70:
        return "excelente"
    if score >= 50:
        return "bueno"
    if score >= 30:
        return "regular"
    return "bajo"
