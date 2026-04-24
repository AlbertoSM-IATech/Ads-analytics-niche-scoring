"""Autopilot rule engine: classify each keyword into pause / scale / hold / investigate."""
from __future__ import annotations
from typing import Optional


def classify_action(
    *,
    acos_eq: Optional[float],
    acos_actual: Optional[float],
    acos_siguiente: Optional[float],
    roas: float,
    clicks: float,
    orders: float,
    spend: float,
    sales: float,
    cpc: float,
    phase: str = "dominio",
) -> tuple[str, str, Optional[float]]:
    """Return (action, rationale, suggested_bid_delta_pct).
    Phase defines tolerance multiplier over the break-even ACoS:
      - lanzamiento: 1.7  (focus on visibility, more tolerance)
      - dominio:     1.2  (moderate, keep rentable terms)
      - beneficio:   0.5  (aggressive, only very rentable)
    """
    multipliers = {"lanzamiento": 1.7, "dominio": 1.2, "beneficio": 0.5}
    mult = multipliers.get(phase, 1.2)
    phase_label = {"lanzamiento": "Lanzamiento", "dominio": "Dominio", "beneficio": "Beneficio"}.get(phase, phase)

    # Hard pause: 0 orders with enough clicks to conclude it's wasted
    hard_pause_clicks = {"lanzamiento": 12, "dominio": 8, "beneficio": 5}[phase] if phase in multipliers else 8
    if clicks >= hard_pause_clicks and orders == 0:
        return (
            "pause",
            f"{int(clicks)} clicks sin ventas en fase {phase_label}. Añade como negativa o pausa.",
            None,
        )

    if acos_eq is None:
        if clicks >= 10 and orders == 0:
            return ("pause", "Muchos clicks sin venta y ACoS de equilibrio sin configurar.", None)
        if roas >= 3:
            return ("scale", f"ROAS {roas:.2f} muy alto; sube puja con cuidado.", 10)
        return ("hold", "Datos insuficientes; mantén puja.", None)

    target_acos = acos_eq * mult
    bid_down = {"lanzamiento": -15, "dominio": -20, "beneficio": -30}[phase] if phase in multipliers else -20

    # En pérdida: ACoS actual por encima del target de la fase
    if acos_actual is not None and acos_actual > target_acos:
        if acos_siguiente is not None and acos_siguiente <= target_acos:
            # Recuperable con la fase actual
            return (
                "hold" if phase != "beneficio" else "pause",
                f"ACoS {acos_actual:.1f}% > objetivo fase {phase_label} ({target_acos:.1f}%) pero recuperable con siguiente venta.",
                bid_down // 2 if phase != "beneficio" else bid_down,
            )
        # No recuperable — pausar o bajar puja según fase
        if phase == "beneficio" or clicks >= hard_pause_clicks:
            return (
                "pause",
                f"ACoS {acos_actual:.1f}% > objetivo {phase_label} ({target_acos:.1f}%) y no recupera. Pausar.",
                None,
            )
        return (
            "investigate",
            f"ACoS {acos_actual:.1f}% > objetivo {phase_label} ({target_acos:.1f}%); pocos clicks aún, observar.",
            bid_down,
        )

    # Bajo objetivo de fase (rentable según fase)
    if acos_actual is not None and acos_actual <= target_acos:
        if phase == "lanzamiento":
            # Lanzamiento: si hay tracción, escalar agresivamente
            if clicks >= 15 or orders >= 2:
                return ("scale", f"Fase Lanzamiento y ACoS {acos_actual:.1f}% bajo objetivo. Sube puja.", 20)
            return ("hold", "Fase Lanzamiento: mantén puja y reúne datos.", None)
        if phase == "dominio":
            if roas >= 4 and orders >= 3:
                return ("scale", f"ROAS {roas:.2f} en Dominio. Sube puja 15%.", 15)
            if roas >= 2 and orders >= 1:
                return ("scale", f"ROAS {roas:.2f}. Sube puja 10%.", 10)
            return ("hold", "Dominio: mantener puja.", None)
        # beneficio
        if roas >= 5 and orders >= 5:
            return ("scale", f"Beneficio: ROAS {roas:.2f} excelente. +10% puja.", 10)
        return ("hold", "Beneficio: mantener rentabilidad sin aumentar gasto.", None)

    return ("hold", "Sin señal clara. Mantener puja actual.", None)


def aggregate_autopilot(rows: list[dict], acos_eq: Optional[float], phase: str = "dominio") -> dict:
    buckets = {"pause": [], "scale": [], "hold": [], "investigate": []}
    for r in rows:
        action, rationale, bid_delta = classify_action(
            acos_eq=acos_eq,
            acos_actual=r.get("acos_actual"),
            acos_siguiente=r.get("acos_siguiente"),
            roas=r.get("roas", 0) or 0,
            clicks=r.get("clicks", 0) or 0,
            orders=r.get("orders", 0) or 0,
            spend=r.get("spend", 0) or 0,
            sales=r.get("sales", 0) or 0,
            cpc=r.get("cpc", 0) or 0,
            phase=phase,
        )
        rec = {
            "term": r.get("term") or r.get("customer_search_term") or r.get("targeting"),
            "campaign": r.get("campaign"),
            "clicks": r.get("clicks", 0),
            "orders": r.get("orders", 0),
            "spend": r.get("spend", 0),
            "sales": r.get("sales", 0),
            "cpc": r.get("cpc", 0),
            "roas": r.get("roas", 0),
            "acos_actual": r.get("acos_actual"),
            "acos_siguiente": r.get("acos_siguiente"),
            "badge": r.get("badge"),
            "action": action,
            "rationale": rationale,
            "bid_delta_pct": bid_delta,
        }
        buckets[action].append(rec)
    return {
        "phase": phase,
        "target_multiplier": {"lanzamiento": 1.7, "dominio": 1.2, "beneficio": 0.5}.get(phase),
        "target_acos": (acos_eq * {"lanzamiento": 1.7, "dominio": 1.2, "beneficio": 0.5}.get(phase, 1.2)) if acos_eq else None,
        "counts": {k: len(v) for k, v in buckets.items()},
        "actions": buckets,
    }


# ---- Helium10 / Publisher Rocket / ASIN importers ----
H10_VOLUME_ALIASES = [
    "search volume", "search_volume", "sv", "volumen de búsqueda",
    "volumen búsqueda", "volumen", "search volume (exact)", "volume",
]
H10_COMPETITORS_ALIASES = [
    "competing products", "competing_products", "competitors", "competidores",
    "resultados", "results", "productos competidores",
]
TERM_ALIASES = [
    "keyword phrase", "keyword", "phrase", "term", "search term", "search phrase",
    "palabra clave", "término", "termine", "keyword text",
]


def _norm(s: str) -> str:
    return str(s).strip().lower()


def parse_niche_csv(df) -> dict[str, dict]:
    """Return a dict {term_lower: {search_volume, competitors}}."""
    headers = [_norm(c) for c in df.columns]

    def find(aliases):
        for i, h in enumerate(headers):
            if h in aliases or any(a in h for a in aliases):
                return df.columns[i]
        return None

    term_col = find(TERM_ALIASES)
    vol_col = find(H10_VOLUME_ALIASES)
    comp_col = find(H10_COMPETITORS_ALIASES)
    if not term_col:
        raise ValueError("No se encontró columna de término/keyword en el CSV")
    out: dict[str, dict] = {}
    for _, row in df.iterrows():
        term = str(row[term_col]).strip()
        if not term or term.lower() in ("nan", "null"):
            continue
        entry: dict = {}
        if vol_col is not None:
            try:
                entry["search_volume"] = float(
                    str(row[vol_col]).replace(",", "").replace(".", "") if "," in str(row[vol_col]) and "." in str(row[vol_col]) else str(row[vol_col]).replace(",", "")
                )
            except (ValueError, TypeError):
                pass
        if comp_col is not None:
            try:
                entry["competitors"] = float(
                    str(row[comp_col]).replace(",", "").replace(".", "") if "," in str(row[comp_col]) and "." in str(row[comp_col]) else str(row[comp_col]).replace(",", "")
                )
            except (ValueError, TypeError):
                pass
        if entry:
            out[term.lower()] = entry
    return out
