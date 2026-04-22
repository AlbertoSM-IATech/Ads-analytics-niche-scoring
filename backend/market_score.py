"""Market Score 0-100 calculation (simplified Niche Study algorithm)."""
from __future__ import annotations
from typing import Optional


def _band_score(value: float, bands: list[tuple[float, float]]) -> float:
    """Return a score 0..max by finding the band. Bands: [(threshold, points), ...] sorted asc."""
    for threshold, pts in bands:
        if value <= threshold:
            return pts
    return bands[-1][1]


def calculate_market_score(
    search_volume: Optional[float],
    competitors: Optional[float],
    price: Optional[float],
    royalties: Optional[float],
    demand_checks: int = 0,          # 0..6 checkboxes
    competition_checks: int = 0,     # 0..3 checkboxes
) -> dict:
    """Return {'total': 0-100, 'breakdown': {...}}."""
    vol = float(search_volume or 0)
    comp = float(competitors or 0)
    p = float(price or 0)
    r = float(royalties or 0)

    # Volume: 0..25 pts
    vol_pts = _band_score(vol, [
        (100, 2), (500, 6), (1000, 12), (3000, 18),
        (8000, 22), (50000, 25), (float("inf"), 20),  # too high = saturated
    ])

    # Competitors: 0..25 pts (less is better)
    if comp <= 0:
        comp_pts = 10
    else:
        comp_pts = _band_score(comp, [
            (500, 25), (1500, 22), (3000, 18), (8000, 12),
            (20000, 6), (float("inf"), 2),
        ])

    # Price: 0..15 pts (sweet spot 7-20)
    if p <= 0:
        price_pts = 0
    elif 7 <= p <= 20:
        price_pts = 15
    elif 4 <= p <= 7 or 20 < p <= 30:
        price_pts = 10
    else:
        price_pts = 5

    # Royalties: 0..10 pts (higher is better, within reason)
    if r <= 0:
        roy_pts = 0
    else:
        ratio = (r / p) if p else 0
        if ratio >= 0.5:
            roy_pts = 10
        elif ratio >= 0.35:
            roy_pts = 7
        elif ratio >= 0.2:
            roy_pts = 4
        else:
            roy_pts = 2

    # Checklists
    demand_pts = min(int(demand_checks or 0), 6) * 2   # 0..12
    comp_checks_pts = min(int(competition_checks or 0), 3) * 4  # 0..12 (approx)

    total = vol_pts + comp_pts + price_pts + roy_pts + demand_pts + comp_checks_pts
    total = max(0, min(100, round(total)))
    return {
        "total": total,
        "breakdown": {
            "volume": {"points": vol_pts, "max": 25},
            "competitors": {"points": comp_pts, "max": 25},
            "price": {"points": price_pts, "max": 15},
            "royalties": {"points": roy_pts, "max": 10},
            "demand": {"points": demand_pts, "max": 12},
            "competition_checks": {"points": comp_checks_pts, "max": 12},
        },
        "label": label_for_score(total),
    }


def label_for_score(score: int) -> str:
    if score >= 80:
        return "excelente"
    if score >= 65:
        return "bueno"
    if score >= 45:
        return "medio"
    if score >= 25:
        return "bajo"
    return "muy-bajo"


def acos_siguiente_sin_venta_pct(
    spend: Optional[float],
    cpc: Optional[float],
    sales: Optional[float],
) -> Optional[float]:
    """ACOS si el siguiente click NO genera venta (peor caso)."""
    if spend is None or cpc is None or sales is None or sales <= 0:
        return None
    return ((spend + cpc) / sales) * 100
