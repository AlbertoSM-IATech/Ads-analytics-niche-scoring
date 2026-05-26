"""Phase 3A — Backend recommendations engine.

PARALLEL, READ-ONLY motor based on the bridge doc §17. Consumes the already
enriched rows from /keywords-unified (which already include Phase 2A economic
metrics and Phase 2B `relevance`). Emits a list of `Recommendation` objects
with deterministic IDs, transparent `priority_score`, and conservative defaults.

DESIGN RULES (do not touch without product approval):
  - Does NOT import or reference autopilot.py — zero coupling.
  - Does NOT modify any database state.
  - Is NOT a replacement for the existing `suggest_negative` heuristic; both
    live side-by-side until Fase 4 validates this engine.
  - NEGATIVE_PHRASE_CANDIDATE is conservative: closed bilingual pattern list,
    requires orders=0 + clicks>=3 + consumo_fase>=0.5.
  - REVIEW_CAMPAIGN and PAUSE_TARGET are reserved in the schema but not yet
    emitted by any rule (deferred to Fase 3B).

Schema mirrors Recommendation §17 of profit-navigator-bridge.md.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================================
# Constants
# ============================================================================

# Closed bilingual list of clearly irrelevant patterns. Kept narrow to avoid
# blocking valid traffic. Single ambiguous words like "free" or "used" are
# intentionally NOT here — they need at least one disambiguating partner.
IRRELEVANT_PATTERNS: tuple[str, ...] = (
    # Spanish
    "pdf gratis",
    "descargar gratis",
    "leer online",
    "libro gratis",
    "gratis pdf",
    "segunda mano",
    "libro usado",
    # English
    "free pdf",
    "download free",
    "read online",
    "used book",
    "second hand",
    "free download",
)

ALL_ACTIONS = (
    "WAIT_FOR_DATA", "OBSERVE", "LOWER_BID", "HOLD", "SCALE",
    "MOVE_TO_EXACT", "NEGATIVE_EXACT_CANDIDATE", "NEGATIVE_PHRASE_CANDIDATE",
    "REVIEW_CAMPAIGN", "PAUSE_TARGET",
)

# Match types that are eligible for MOVE_TO_EXACT promotion.
PROMOTABLE_MATCH_TYPES = frozenset({"broad", "phrase", "auto"})

# Recoverability buffer over ACoS PE — see bridge §13.
RECOVERY_BUFFER = 1.10

# Minimum signal to make any non-trivial recommendation.
MIN_CLICKS_FOR_DECISION = 3
MIN_CONSUMO_FOR_PHRASE_NEGATIVE = 0.5


# ============================================================================
# Pydantic schema
# ============================================================================

class RecommendationMetrics(BaseModel):
    impressions: Optional[int] = None
    clicks: Optional[float] = None
    spend: Optional[float] = None
    sales: Optional[float] = None
    orders: Optional[int] = None
    cpc_real: Optional[float] = None
    cpc_source: Optional[str] = None
    acos: Optional[float] = None
    roas: Optional[float] = None
    cvr: Optional[float] = None
    clicks_pe: Optional[float] = None
    clicks_fase: Optional[float] = None
    consumo_pe: Optional[float] = None
    consumo_fase: Optional[float] = None
    acos_pe_kdp: Optional[float] = None
    acos_siguiente_con_venta: Optional[float] = None
    beneficio_kdp: Optional[float] = None
    relevance: str = "unreviewed"


class Recommendation(BaseModel):
    id: str
    priority: str                                 # high|medium|low
    action_type: str                              # one of ALL_ACTIONS
    term: Optional[str] = None
    customer_search_term: Optional[str] = None
    targeting: Optional[str] = None
    match_type: Optional[str] = None
    campaign: Optional[str] = None
    campaigns: list[str] = Field(default_factory=list)
    ad_group: Optional[str] = None
    metrics: RecommendationMetrics
    detected_problem: str
    recommended_action: str
    reason: str
    expected_impact: Optional[str] = None
    confidence: str
    risk: str
    amazon_instruction: str
    priority_score: float
    phase: str
    is_recoverable_with_next_sale: Optional[bool] = None


# ============================================================================
# Helpers
# ============================================================================

def normalize_match_type(value: Optional[str]) -> Optional[str]:
    """Normalize Amazon-style match type strings to the canonical form."""
    if not value:
        return None
    v = str(value).strip().lower()
    mapping = {
        "automatic": "auto",
        "broad match": "broad",
        "phrase match": "phrase",
        "exact match": "exact",
    }
    return mapping.get(v, v)


def _matches_irrelevant_pattern(term: Optional[str]) -> Optional[str]:
    """Return the first matching irrelevant phrase pattern, or None."""
    if not term:
        return None
    t = term.lower()
    for p in IRRELEVANT_PATTERNS:
        if p in t:
            return p
    return None


def _calc_cpc_max_rentable(regalia_neta_kdp: Optional[float]) -> Optional[float]:
    """CPC máximo orientativo = regalía / 10. None if no royalty resolved."""
    if regalia_neta_kdp is None or regalia_neta_kdp <= 0:
        return None
    return regalia_neta_kdp / 10.0


def _is_recoverable(acos_siguiente_con_venta: Optional[float],
                    acos_pe_kdp: Optional[float]) -> Optional[bool]:
    """True if the next-sale projected ACoS lands within the recoverability buffer.

    None when we don't have enough info to decide.
    """
    if acos_siguiente_con_venta is None or acos_pe_kdp is None or acos_pe_kdp <= 0:
        return None
    return acos_siguiente_con_venta <= acos_pe_kdp * RECOVERY_BUFFER


def _priority_score(row: dict, action_type: str, is_recoverable: Optional[bool]) -> float:
    consumo_pe = min(row.get("consumo_pe") or 0, 3.0)
    p_consumo = consumo_pe * 18                                          # 0..54

    spend = row.get("spend") or 0
    p_spend = min(spend / 20.0, 1.0) * 15                                # 0..15

    p_unrecoverable = 12 if is_recoverable is False else 0

    orders = row.get("orders") or 0
    over_pe = (row.get("consumo_pe") or 0) > 1.0
    p_zero_orders_over_pe = 10 if (orders == 0 and over_pe) else 0

    rel = (row.get("relevance") or "unreviewed")
    p_relevance = {"low": 8, "medium": 4, "unreviewed": 2, "high": 0}.get(rel, 2)

    benef = row.get("beneficio_kdp")
    p_negative_profit = 8 if (benef is not None and benef < 0) else 0

    positive_floor = 25 if action_type in ("HOLD", "SCALE", "MOVE_TO_EXACT") else 0

    score = max(positive_floor,
                p_consumo + p_spend + p_unrecoverable +
                p_zero_orders_over_pe + p_relevance + p_negative_profit)
    return round(min(score, 100.0), 2)


def _priority_bucket(score: float) -> str:
    if score >= 70: return "high"
    if score >= 40: return "medium"
    return "low"


def _det_id(dataset_id: str, term: Optional[str], action_type: str) -> str:
    raw = f"{dataset_id}|{term or ''}|{action_type}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _fmt_pct(v):
    return "—" if v is None else f"{v * 100:.0f}%"


def _fmt_money(v, sym):
    return "—" if v is None else f"{sym}{v:,.2f}"


# ============================================================================
# Decision rules
# ============================================================================

def decide(row: dict, *, dataset_id: str, phase: str, regalia_source: str,
           sym: str = "$") -> Optional[Recommendation]:
    """Evaluate one enriched row and return a single Recommendation, or None."""
    term = row.get("term") or row.get("customer_search_term") or row.get("targeting")
    clicks = row.get("clicks") or 0
    orders = row.get("orders") or 0
    spend = row.get("spend") or 0
    consumo_pe = row.get("consumo_pe")
    consumo_fase = row.get("consumo_fase")
    cpc_real = row.get("cpc_real")
    cpc_source = row.get("cpc_source") or "none"
    acos = row.get("acos_actual")
    acos_pe_kdp = row.get("acos_pe_kdp")
    acos_next = row.get("acos_siguiente_con_venta")
    benef_kdp = row.get("beneficio_kdp")
    relevance = row.get("relevance") or "unreviewed"
    mt = normalize_match_type(row.get("match_type"))
    cpc_max_rentable = _calc_cpc_max_rentable(row.get("regalia_neta_kdp"))
    recoverable = _is_recoverable(acos_next, acos_pe_kdp)

    metrics = RecommendationMetrics(
        impressions=row.get("impressions"),
        clicks=clicks,
        spend=spend,
        sales=row.get("sales"),
        orders=orders,
        cpc_real=cpc_real,
        cpc_source=cpc_source,
        acos=acos,
        roas=(row.get("sales") / spend) if (spend and spend > 0) else None,
        cvr=row.get("cvr"),
        clicks_pe=row.get("clicks_pe"),
        clicks_fase=row.get("clicks_fase"),
        consumo_pe=consumo_pe,
        consumo_fase=consumo_fase,
        acos_pe_kdp=acos_pe_kdp,
        acos_siguiente_con_venta=acos_next,
        beneficio_kdp=benef_kdp,
        relevance=relevance,
    )

    def make(action_type, *, detected_problem, recommended_action, reason,
             confidence, risk, amazon_instruction, expected_impact=None):
        return Recommendation(
            id=_det_id(dataset_id, term, action_type),
            priority=_priority_bucket(_priority_score(row, action_type, recoverable)),
            action_type=action_type,
            term=term,
            customer_search_term=row.get("customer_search_term"),
            targeting=row.get("targeting"),
            match_type=mt,
            campaign=row.get("campaign"),
            campaigns=row.get("campaigns") or [],
            ad_group=row.get("ad_group"),
            metrics=metrics,
            detected_problem=detected_problem,
            recommended_action=recommended_action,
            reason=reason,
            expected_impact=expected_impact,
            confidence=confidence,
            risk=risk,
            amazon_instruction=amazon_instruction,
            priority_score=_priority_score(row, action_type, recoverable),
            phase=phase,
            is_recoverable_with_next_sale=recoverable,
        )

    # ------------------------------------------------------------------ G1
    if regalia_source == "none" or cpc_source == "none" or clicks < MIN_CLICKS_FOR_DECISION:
        return make("WAIT_FOR_DATA",
            detected_problem="Datos insuficientes para decidir.",
            recommended_action="Esperar a tener al menos 3 clicks y economía resuelta.",
            reason=("Sin economía KDP/legacy resuelta o sin CPC real/referencia." if regalia_source == "none" or cpc_source == "none"
                    else f"Solo {clicks} clicks — por debajo del umbral mínimo de {MIN_CLICKS_FOR_DECISION}."),
            confidence="low", risk="low",
            amazon_instruction="No realizar cambios. Continuar acumulando datos.")

    # ------------------------------------------------------------------ G2
    pattern = _matches_irrelevant_pattern(term)
    if (pattern and orders == 0 and clicks >= 3
            and consumo_fase is not None and consumo_fase >= MIN_CONSUMO_FOR_PHRASE_NEGATIVE):
        return make("NEGATIVE_PHRASE_CANDIDATE",
            detected_problem=f"Término contiene patrón irrelevante: «{pattern}».",
            recommended_action=f"Evaluar añadir «{pattern}» como negativa de frase.",
            reason=(f"Patrón irrelevante repetido sin pedidos ({clicks} clicks, "
                    f"consumo fase {_fmt_pct(consumo_fase)})."),
            confidence="medium", risk="high",
            amazon_instruction=f"Revisar manualmente: añadir negativa de frase «{pattern}» "
                               "en el ad group/campaña afectados. Verificar antes que no bloquea tráfico válido.")

    # ------------------------------------------------------------------ G2.5 — PAUSE_TARGET (Phase 4C)
    # PER-ROW, severe action. Only applies to BIDDED targets (row.targeting set)
    # that are NOT search-term harvests (customer_search_term must be None).
    # Requires extreme signals; preempts NEGATIVE_EXACT_CANDIDATE when triggered.
    # NEVER fires with relevance in {"high", "medium"} — uncertainty is unacceptable
    # for a pause. Stricter thresholds for "unreviewed" than for "low".
    regalia_for_pause = row.get("regalia_neta_kdp")
    if (row.get("targeting") and not row.get("customer_search_term")
            and orders == 0 and cpc_source == "real" and recoverable is False
            and consumo_pe is not None and regalia_for_pause and regalia_for_pause > 0):
        pause_meets = False
        pause_conf = None
        pause_risk = None
        if relevance == "low":
            pause_meets = (clicks >= 8 and consumo_pe >= 2.0
                           and spend >= regalia_for_pause * 1.5)
            pause_conf, pause_risk = "high", "medium"
        elif relevance == "unreviewed":
            pause_meets = (clicks >= 12 and consumo_pe >= 2.5
                           and spend >= regalia_for_pause * 2.0)
            pause_conf, pause_risk = "medium", "high"
        if pause_meets:
            return make("PAUSE_TARGET",
                detected_problem=(f"Target con {clicks} clicks sin pedidos y consumo PE "
                                  f"{_fmt_pct(consumo_pe)}; gasto {_fmt_money(spend, sym)}."),
                recommended_action="Pausar el target en Amazon Ads. Acción excepcional: más severa que negativa.",
                reason=(f"{clicks} clicks sin pedidos, consumo PE {_fmt_pct(consumo_pe)}, "
                        f"gasto {_fmt_money(spend, sym)}; no recuperable con +1 venta "
                        f"({acos_next:.1f}% vs PE×1.10 {acos_pe_kdp * RECOVERY_BUFFER:.1f}%); "
                        f"relevancia: {relevance}."),
                confidence=pause_conf, risk=pause_risk,
                expected_impact=f"Detener gasto futuro en este target (histórico {_fmt_money(spend, sym)}).",
                amazon_instruction=(f"Pausar el target «{term}» en la campaña «{row.get('campaign') or '—'}». "
                                    "Más severo que negativa: detiene el bid completo del target. "
                                    "Reversible — puedes reactivar el target si la situación cambia."))

    # ------------------------------------------------------------------ G3
    if (orders == 0 and consumo_pe is not None and consumo_pe >= 1.25
            and recoverable is False and relevance == "low"):
        return make("NEGATIVE_EXACT_CANDIDATE",
            detected_problem=f"Supera ampliamente el PE ({_fmt_pct(consumo_pe)}) y siguiente venta no recupera.",
            recommended_action="Añadir como negativa exacta. Prioridad alta.",
            reason=(f"Consumo PE {_fmt_pct(consumo_pe)}, sin pedidos, relevancia baja, "
                    f"siguiente venta proyectada ({acos_next:.1f}%) > ACoS PE × 1.10 ({acos_pe_kdp * RECOVERY_BUFFER:.1f}%)."),
            confidence="high", risk="medium",
            expected_impact=f"Ahorrar ~{_fmt_money(spend, sym)} de gasto futuro en este término.",
            amazon_instruction=f"En la campaña «{row.get('campaign') or '—'}», añadir «{term}» como Negative Exact.")

    # ------------------------------------------------------------------ G4
    if (orders == 0 and consumo_pe is not None and consumo_pe > 1.0
            and recoverable is False and relevance != "high"):
        return make("NEGATIVE_EXACT_CANDIDATE",
            detected_problem=f"Supera el PE ({_fmt_pct(consumo_pe)}) y siguiente venta no recupera.",
            recommended_action="Evaluar añadir como negativa exacta.",
            reason=(f"Consumo PE {_fmt_pct(consumo_pe)}, sin pedidos. "
                    f"Próxima venta proyectada {acos_next:.1f}% > ACoS PE×1.10."),
            confidence="medium", risk="medium",
            amazon_instruction=f"Considerar añadir «{term}» como Negative Exact tras revisar relevancia.")

    # ------------------------------------------------------------------ G5
    if (orders == 0 and consumo_pe is not None and consumo_pe > 1.0
            and recoverable is True):
        return make("OBSERVE",
            detected_problem=f"Supera el PE ({_fmt_pct(consumo_pe)}) pero siguiente venta podría recuperar.",
            recommended_action="Observar 1-3 clicks más o bajar puja ligeramente.",
            reason=(f"Aunque el consumo PE es {_fmt_pct(consumo_pe)}, la simulación de siguiente venta "
                    f"({acos_next:.1f}%) cae dentro del buffer del 10% sobre ACoS PE."),
            confidence="medium", risk="low",
            amazon_instruction="Mantener observación. Si en los siguientes 3 clicks no convierte, reevaluar.")

    # ------------------------------------------------------------------ G6
    if (orders == 0 and consumo_fase is not None and consumo_fase > 1.0
            and (consumo_pe is None or consumo_pe <= 1.0)):
        return make("LOWER_BID",
            detected_problem=f"Supera tolerancia de fase ({_fmt_pct(consumo_fase)}) sin haber roto el PE puro.",
            recommended_action="Bajar puja 10-20%.",
            reason=(f"Consumo fase {_fmt_pct(consumo_fase)} > 100%, pero consumo PE "
                    f"{_fmt_pct(consumo_pe) if consumo_pe is not None else '—'} todavía no excede 100%."),
            confidence="medium", risk="low",
            amazon_instruction=f"En la campaña «{row.get('campaign') or '—'}», bajar puja "
                               f"de {term} aprox. 15%.")

    # ------------------------------------------------------------------ G7
    if (orders == 0 and consumo_fase is not None and 0.80 <= consumo_fase < 1.0):
        # Lower bid when relevance is suspect OR cpc is above the max rentable.
        cpc_alto = (cpc_max_rentable is not None
                    and cpc_real is not None
                    and cpc_real > cpc_max_rentable)
        action = "LOWER_BID" if (relevance in ("low", "medium") or cpc_alto) else "OBSERVE"
        return make(action,
            detected_problem=f"Zona de advertencia: consumo fase {_fmt_pct(consumo_fase)}.",
            recommended_action=("Bajar puja para alargar la pista de datos."
                                if action == "LOWER_BID" else "Observar; aún no es zona crítica."),
            reason=(f"Consumo fase entre 80-100% sin pedidos. "
                    f"{'CPC real supera CPC máx rentable' if cpc_alto else f'Relevancia: {relevance}.'}"),
            confidence="medium", risk="low",
            amazon_instruction=("Bajar puja 10%." if action == "LOWER_BID"
                                else "Esperar a que cierre la fase actual."))

    # ------------------------------------------------------------------ G8
    if (orders == 0 and consumo_fase is not None and 0.5 <= consumo_fase < 0.80):
        return make("OBSERVE",
            detected_problem=f"Consumo fase moderado ({_fmt_pct(consumo_fase)}).",
            recommended_action="Continuar observando.",
            reason="El término ha empezado a consumir margen pero no entra en zona peligrosa.",
            confidence="low", risk="low",
            amazon_instruction="No realizar cambios. Acumular más datos.")

    # ------------------------------------------------------------------ G9
    if (orders == 0 and consumo_fase is not None and consumo_fase < 0.5):
        return make("WAIT_FOR_DATA",
            detected_problem=f"Consumo fase bajo ({_fmt_pct(consumo_fase)}).",
            recommended_action="Esperar datos.",
            reason="Aún quedan clicks dentro del presupuesto-fase. Demasiado pronto para decidir.",
            confidence="low", risk="low",
            amazon_instruction="No realizar cambios.")

    # --------------------------------- Positive actions (orders > 0) ----
    # G9.5 — Phase 3A.1: orders>0 but losing money on KDP economics + over PE.
    # Conviene reducir puja antes de evaluar SCALE/HOLD: el término convierte pero
    # cada conversión deja pérdida real. NUNCA negativizar (vende → señal de intención).
    if (orders > 0 and benef_kdp is not None and benef_kdp < 0
            and consumo_pe is not None and consumo_pe > 1.0):
        # Reference CPC means the loss estimate is based on the niche reference,
        # not real Ads data → lower the confidence.
        conf = "low" if cpc_source == "reference" else "medium"
        return make("LOWER_BID",
            detected_problem=(f"Vende pero el beneficio KDP es negativo "
                              f"({_fmt_money(benef_kdp, sym)}) y supera el PE "
                              f"({_fmt_pct(consumo_pe)})."),
            recommended_action="Reducir puja 10-20% y seguir observando. "
                               "NO negativizar porque convierte; pero cada venta deja pérdida.",
            reason=(f"{orders} pedidos pero beneficio KDP "
                    f"{_fmt_money(benef_kdp, sym)}; consumo PE "
                    f"{_fmt_pct(consumo_pe)}. "
                    f"ACoS actual {acos:.1f}% vs ACoS PE {acos_pe_kdp:.1f}%."),
            confidence=conf, risk="medium",
            expected_impact="Reducir gasto por click manteniendo conversiones; mejorar margen.",
            amazon_instruction=(f"Revisa «{term}» en Amazon Ads y reduce la puja "
                                f"un 10-20%. Mantén seguimiento tras nuevos clicks. "
                                "No añadir como negativa."))

    # G9.6 — Phase 3A.1 variant: orders>0, profit<0, but PE not yet exceeded.
    # Insufficient signal for LOWER_BID; ask for observation.
    if (orders > 0 and benef_kdp is not None and benef_kdp < 0
            and (consumo_pe is None or consumo_pe <= 1.0)):
        conf = "low" if cpc_source == "reference" else "medium"
        return make("OBSERVE",
            detected_problem=f"Vende pero el beneficio KDP es negativo ({_fmt_money(benef_kdp, sym)}).",
            recommended_action="Observar 2-3 clicks más antes de actuar.",
            reason=(f"{orders} pedidos, beneficio KDP "
                    f"{_fmt_money(benef_kdp, sym)}, consumo PE "
                    f"{_fmt_pct(consumo_pe)}. Todavía no supera el PE — "
                    f"la rentabilidad podría mejorar con más conversiones."),
            confidence=conf, risk="low",
            amazon_instruction="No realizar cambios. Acumular más datos.")

    # G10
    if (orders > 0 and mt in PROMOTABLE_MATCH_TYPES
            and row.get("customer_search_term") and acos is not None and acos_pe_kdp is not None
            and acos <= acos_pe_kdp and benef_kdp is not None and benef_kdp > 0):
        return make("MOVE_TO_EXACT",
            detected_problem="Search term rentable desde match no-exacto.",
            recommended_action=f"Mover «{row.get('customer_search_term')}» a una campaña/ad group exacta.",
            reason=(f"{orders} pedidos, ACoS {acos:.1f}% ≤ ACoS PE {acos_pe_kdp:.1f}%, "
                    f"beneficio KDP {_fmt_money(benef_kdp, sym)} desde match {mt}."),
            confidence="high", risk="low",
            expected_impact="Control directo de puja y mejor escalado del término.",
            amazon_instruction=f"Crear/usar campaña EXACT y añadir «{row.get('customer_search_term')}» allí. "
                               f"Considerar negativa exacta en la campaña {mt} de origen.")

    # G11
    if (orders > 0 and acos is not None and acos_pe_kdp is not None
            and acos <= acos_pe_kdp * 0.8
            and benef_kdp is not None and benef_kdp > 0
            and consumo_pe is not None and consumo_pe < 0.7):
        return make("SCALE",
            detected_problem="Término rentable con margen y bajo consumo.",
            recommended_action="Subir puja 10-15% o presupuesto de campaña.",
            reason=(f"ACoS {acos:.1f}% ≤ 80% del PE ({acos_pe_kdp:.1f}%), "
                    f"beneficio {_fmt_money(benef_kdp, sym)}, consumo PE {_fmt_pct(consumo_pe)}."),
            confidence="high", risk="low",
            expected_impact="Más impresiones manteniendo rentabilidad.",
            amazon_instruction=f"Subir puja en «{term}» aprox. 12%.")

    # G12 — default for keywords with sales
    if orders > 0:
        return make("HOLD",
            detected_problem=("Término rentable, mantener." if (benef_kdp is not None and benef_kdp >= 0)
                              else "Pedidos presentes pero beneficio aún ajustado."),
            recommended_action="Mantener.",
            reason=(f"{orders} pedidos, beneficio KDP {_fmt_money(benef_kdp, sym)}."),
            confidence="medium", risk="low",
            amazon_instruction="No cambiar configuración.")

    # Fallback (should rarely hit): default to WAIT_FOR_DATA
    return make("WAIT_FOR_DATA",
        detected_problem="Estado no clasificable con datos disponibles.",
        recommended_action="Esperar más datos.",
        reason="No se cumple ninguna regla de decisión.",
        confidence="low", risk="low",
        amazon_instruction="No realizar cambios.")


def build_recommendations(rows: list[dict], *, dataset_id: str, phase: str,
                          regalia_source: str, sym: str = "$") -> list[Recommendation]:
    """Produce a sorted list of recommendations from enriched rows.

    Phase 4C: a second pass groups rows by campaign and emits REVIEW_CAMPAIGN
    recommendations when aggregate signals are strong. Per-row recommendations
    are computed first and unchanged by the campaign pass.
    """
    out: list[Recommendation] = []
    for r in rows:
        rec = decide(r, dataset_id=dataset_id, phase=phase, regalia_source=regalia_source, sym=sym)
        if rec is not None:
            out.append(rec)

    # Phase 4C — campaign-level aggregation pass.
    by_camp = aggregate_by_campaign(rows, out)
    for _camp_name, agg in by_camp.items():
        camp_rec = decide_campaign(agg, dataset_id=dataset_id, phase=phase,
                                   regalia_source=regalia_source, sym=sym)
        if camp_rec is not None:
            out.append(camp_rec)

    out.sort(key=lambda x: (-x.priority_score, x.action_type))
    return out


# ============================================================================
# Phase 4C — Campaign-level aggregations
# ============================================================================

# Minimum number of rows in a campaign before REVIEW_CAMPAIGN can fire.
MIN_ROWS_FOR_CAMPAIGN_REVIEW = 3
# If WAIT_FOR_DATA dominates this fraction, the campaign is too young to review.
MAX_WAIT_FRACTION_FOR_REVIEW = 0.70
# ACoS buffer above PE for B1 condition.
CAMPAIGN_ACOS_BUFFER = 1.20
# Minimum gasto absoluto multiplier on the resolved royalty.
CAMPAIGN_SPEND_MULT = 5.0
CAMPAIGN_SPEND_FLOOR = 5.0


def aggregate_by_campaign(rows: list[dict],
                          per_row_recs: list[Recommendation]) -> dict[str, dict]:
    """Group rows + their per-row action_type into per-campaign stats.

    Returns a dict keyed by campaign name. Each entry is a flat dict ready to
    feed into ``decide_campaign``. Rows without a campaign are skipped.
    """
    rec_by_term: dict[str, Recommendation] = {}
    for r in per_row_recs:
        if r.term and r.action_type != "REVIEW_CAMPAIGN":
            rec_by_term[r.term] = r

    by_camp: dict[str, dict] = {}
    for row in rows:
        camp = row.get("campaign")
        if not camp:
            continue
        agg = by_camp.setdefault(camp, {
            "campaign": camp,
            "rows": [],
            "total_spend": 0.0,
            "total_sales": 0.0,
            "total_clicks": 0,
            "total_orders": 0,
            "total_beneficio_kdp": 0.0,
            "has_beneficio": False,
            "n_wait_for_data": 0,
            "n_actionable_negative": 0,
            "n_actionable_positive": 0,
            "acos_pe_kdp": None,
            "regalia_neta_kdp": None,
        })
        agg["rows"].append(row)
        agg["total_spend"] += row.get("spend") or 0
        agg["total_sales"] += row.get("sales") or 0
        agg["total_clicks"] += row.get("clicks") or 0
        agg["total_orders"] += row.get("orders") or 0
        b = row.get("beneficio_kdp")
        if b is not None:
            agg["total_beneficio_kdp"] += b
            agg["has_beneficio"] = True
        if agg["acos_pe_kdp"] is None and row.get("acos_pe_kdp") is not None:
            agg["acos_pe_kdp"] = row.get("acos_pe_kdp")
        if agg["regalia_neta_kdp"] is None and row.get("regalia_neta_kdp") is not None:
            agg["regalia_neta_kdp"] = row.get("regalia_neta_kdp")

        term_key = row.get("term") or row.get("customer_search_term") or row.get("targeting")
        rec = rec_by_term.get(term_key) if term_key else None
        if rec:
            at = rec.action_type
            if at == "WAIT_FOR_DATA":
                agg["n_wait_for_data"] += 1
            elif at in ("LOWER_BID", "NEGATIVE_EXACT_CANDIDATE",
                        "NEGATIVE_PHRASE_CANDIDATE", "PAUSE_TARGET"):
                agg["n_actionable_negative"] += 1
            elif at in ("SCALE", "MOVE_TO_EXACT", "HOLD"):
                agg["n_actionable_positive"] += 1

    for agg in by_camp.values():
        agg["n_rows"] = len(agg["rows"])
        if agg["total_sales"] > 0:
            agg["agg_acos"] = agg["total_spend"] / agg["total_sales"] * 100
        else:
            agg["agg_acos"] = None

    return by_camp


def decide_campaign(agg: dict, *, dataset_id: str, phase: str,
                    regalia_source: str, sym: str = "$") -> Optional[Recommendation]:
    """Emit a REVIEW_CAMPAIGN recommendation for an aggregated campaign, or None.

    Conservative: requires minimum rows, low wait-for-data ratio, meaningful
    spend, and at least one of two evidence conditions (B1: aggregate loss +
    high ACoS; B2: many negative signals + zero positives).
    """
    import math

    n_rows = agg["n_rows"]
    if n_rows < MIN_ROWS_FOR_CAMPAIGN_REVIEW:
        return None
    if agg["n_wait_for_data"] / n_rows >= MAX_WAIT_FRACTION_FOR_REVIEW:
        return None
    if agg["acos_pe_kdp"] is None:
        return None

    regalia = agg["regalia_neta_kdp"] or 0
    spend_threshold = max(CAMPAIGN_SPEND_FLOOR, regalia * CAMPAIGN_SPEND_MULT)
    if agg["total_spend"] < spend_threshold:
        return None

    acos_pe = agg["acos_pe_kdp"]
    agg_acos = agg["agg_acos"]
    benef = agg["total_beneficio_kdp"]

    cond_b1 = (
        agg["has_beneficio"] and benef < 0
        and agg_acos is not None and agg_acos > acos_pe * CAMPAIGN_ACOS_BUFFER
    )
    threshold_negative = max(2, math.ceil(n_rows * 0.4))
    cond_b2 = (
        agg["n_actionable_negative"] >= threshold_negative
        and agg["n_actionable_positive"] == 0
    )

    if not (cond_b1 or cond_b2):
        return None

    if cond_b1:
        conf = "high" if (regalia > 0 and agg["total_spend"] > regalia * 10) else "medium"
    else:
        conf = "low"

    # priority_score — bounded at 90 (campaign actions are contextual, not urgent).
    p_neg = agg["n_actionable_negative"] * 8
    consumo_proxy = (agg["total_spend"] / (regalia * n_rows)) if regalia > 0 else 0
    p_consumo = min(consumo_proxy, 3.0) * 12
    p_spend = min(agg["total_spend"] / 20.0, 1.0) * 10
    p_negative_profit = 12 if (agg["has_beneficio"] and benef < 0) else 0
    score = round(min(p_neg + p_consumo + p_spend + p_negative_profit, 90.0), 2)
    bucket = "high" if score >= 70 else "medium" if score >= 40 else "low"

    metrics = RecommendationMetrics(
        clicks=agg["total_clicks"],
        spend=agg["total_spend"],
        sales=agg["total_sales"],
        orders=agg["total_orders"],
        acos=agg_acos,
        acos_pe_kdp=acos_pe,
        beneficio_kdp=benef if agg["has_beneficio"] else None,
        relevance="unreviewed",
    )

    reasons_parts = []
    if cond_b1:
        reasons_parts.append(
            f"Beneficio KDP agregado {_fmt_money(benef, sym)}; "
            f"ACoS agregado {agg_acos:.1f}% supera ACoS PE × 1.20 ({acos_pe * CAMPAIGN_ACOS_BUFFER:.1f}%)."
        )
    if cond_b2:
        reasons_parts.append(
            f"{agg['n_actionable_negative']} de {n_rows} keywords con señales negativas "
            f"(LOWER_BID/NEGATIVE/PAUSE) y ninguna positiva."
        )

    return Recommendation(
        id=_det_id(dataset_id, agg["campaign"], "REVIEW_CAMPAIGN"),
        priority=bucket,
        action_type="REVIEW_CAMPAIGN",
        term=None,
        customer_search_term=None,
        targeting=None,
        match_type=None,
        campaign=agg["campaign"],
        campaigns=[agg["campaign"]],
        ad_group=None,
        metrics=metrics,
        detected_problem=(f"Campaña con señales agregadas problemáticas "
                          f"({n_rows} keywords, gasto {_fmt_money(agg['total_spend'], sym)})."),
        recommended_action=("Revisar la campaña: estructura, pujas, targeting, presupuesto. "
                            "Antes de acciones individuales."),
        reason=" ".join(reasons_parts) or "Múltiples señales negativas agregadas en la campaña.",
        expected_impact="Detectar problemas estructurales antes de actuar fila a fila.",
        confidence=conf,
        risk="medium",
        amazon_instruction=(f"Abre la campaña «{agg['campaign']}» en Amazon Ads y revisa: pujas globales, "
                            "estructura de ad groups, targeting/coincidencias, presupuesto diario."),
        priority_score=score,
        phase=phase,
        is_recoverable_with_next_sale=None,
    )


def summarize_by_action(recs: list[Recommendation]) -> dict[str, int]:
    """Count recommendations grouped by action_type. Reserved types appear as 0."""
    counts = {a: 0 for a in ALL_ACTIONS}
    for r in recs:
        counts[r.action_type] = counts.get(r.action_type, 0) + 1
    return counts
