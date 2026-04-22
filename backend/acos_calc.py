"""Calculations for break-even ACoS and next-click metrics.
Mirrors the original mockup's acosEquilibrio.ts logic.
"""
from __future__ import annotations
from typing import Optional


def acos_equilibrio_pct(price: Optional[float], royalties: Optional[float]) -> Optional[float]:
    if not price or price <= 0 or royalties is None:
        return None
    return (royalties / price) * 100


def acos_actual_pct(spend: Optional[float], sales: Optional[float]) -> Optional[float]:
    if spend is None or sales is None or sales <= 0:
        return None
    return (spend / sales) * 100


def acos_siguiente_click_pct(
    spend: Optional[float],
    cpc: Optional[float],
    sales: Optional[float],
    price: Optional[float],
) -> Optional[float]:
    if spend is None or cpc is None or sales is None or not price or price <= 0:
        return None
    ventas_next = sales + price
    gasto_next = spend + cpc
    if ventas_next <= 0:
        return None
    return (gasto_next / ventas_next) * 100


def beneficio_ahora(sales: Optional[float], spend: Optional[float]) -> Optional[float]:
    if sales is None or spend is None:
        return None
    return sales - spend


def beneficio_siguiente_click(
    orders: Optional[float],
    price: Optional[float],
    spend: Optional[float],
    cpc: Optional[float],
) -> Optional[float]:
    if orders is None or not price or price <= 0 or spend is None or cpc is None:
        return None
    ventas_next = (orders + 1) * price
    gasto_next = spend + cpc
    return ventas_next - gasto_next


def conversion_pct(orders: Optional[float], clicks: Optional[float]) -> Optional[float]:
    if orders is None or clicks is None or clicks <= 0:
        return None
    return (orders / clicks) * 100


def guias_fase(acos_eq: Optional[float]) -> dict[str, Optional[float]]:
    if acos_eq is None:
        return {"lanzamiento": None, "dominio": None, "beneficio": None}
    return {
        "lanzamiento": acos_eq * 1.7,
        "dominio": acos_eq * 1.2,
        "beneficio": acos_eq * 0.5,
    }


def determinar_badge(
    acos_eq: Optional[float],
    acos_actual: Optional[float],
    acos_next: Optional[float],
) -> str:
    """Return one of: 'bajo-pe' | 'recuperable' | 'en-perdida' | 'sin-datos'."""
    if acos_eq is None or (acos_actual is None and acos_next is None):
        return "sin-datos"
    if acos_actual is not None and acos_actual <= acos_eq:
        return "bajo-pe"
    if acos_actual is not None and acos_actual > acos_eq:
        if acos_next is not None and acos_next <= acos_eq:
            return "recuperable"
        return "en-perdida"
    return "sin-datos"
