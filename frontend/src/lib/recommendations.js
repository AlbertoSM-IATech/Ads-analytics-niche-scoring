// Phase 3B — Frontend recommendations helpers.
// Strictly UI-side: labels, color styles, and lookup utilities for the badge
// and the side-panel block. Does not modify any backend behaviour.

export const ACTION_LABELS = {
  WAIT_FOR_DATA: "Esperar datos",
  OBSERVE: "Observar",
  LOWER_BID: "Bajar puja",
  HOLD: "Mantener",
  SCALE: "Escalar",
  MOVE_TO_EXACT: "Mover a exacta",
  NEGATIVE_EXACT_CANDIDATE: "Negativa exacta",
  NEGATIVE_PHRASE_CANDIDATE: "Negativa frase",
  REVIEW_CAMPAIGN: "Revisar campaña",
  PAUSE_TARGET: "Pausar target",
};

export const ACTION_STYLES = {
  WAIT_FOR_DATA: { cls: "bg-neutral-100 text-neutral-600 border-neutral-300 dark:bg-neutral-700/40 dark:text-neutral-400 dark:border-neutral-600" },
  OBSERVE:       { cls: "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/30" },
  LOWER_BID:     { cls: "bg-amber-100 text-amber-700 border-amber-300 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/30" },
  HOLD:          { cls: "bg-green-50 text-green-700 border-green-200 dark:bg-green-500/10 dark:text-green-400 dark:border-green-500/30" },
  SCALE:         { cls: "bg-green-500/20 text-green-700 border-green-400 dark:text-green-400 dark:border-green-500/40 font-semibold" },
  MOVE_TO_EXACT: { cls: "bg-sky-100 text-sky-700 border-sky-300 dark:bg-sky-500/10 dark:text-sky-400 dark:border-sky-500/30" },
  NEGATIVE_EXACT_CANDIDATE: { cls: "bg-red-100 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/30" },
  NEGATIVE_PHRASE_CANDIDATE: { cls: "bg-orange-100 text-orange-700 border-orange-300 dark:bg-orange-500/10 dark:text-orange-400 dark:border-orange-500/30" },
  REVIEW_CAMPAIGN: { cls: "bg-purple-100 text-purple-700 border-purple-300 dark:bg-purple-500/10 dark:text-purple-400 dark:border-purple-500/30" },
  PAUSE_TARGET:    { cls: "bg-zinc-200 text-zinc-700 border-zinc-300 dark:bg-zinc-700/40 dark:text-zinc-400 dark:border-zinc-600" },
};

const PRIORITY_LABELS = { high: "Alta", medium: "Media", low: "Baja" };
const CONF_RISK_LABELS = { high: "Alta", medium: "Media", low: "Baja" };

export function priorityLabel(p) { return PRIORITY_LABELS[p] || p || "—"; }
export function confidenceLabel(c) { return CONF_RISK_LABELS[c] || c || "—"; }
export function riskLabel(r) { return CONF_RISK_LABELS[r] || r || "—"; }

/**
 * Build a Map<key, recommendation> from the backend response.
 * Key priority (defensive fallback): rec.term → rec.customer_search_term → rec.targeting.
 * If multiple recommendations share the same key, the one with the highest
 * priority_score wins.
 * `targeting` and `customer_search_term` are kept on each rec untouched —
 * we only use them as a visual lookup fallback.
 */
export function mapRecommendationsByTerm(recs) {
  const m = new Map();
  for (const r of recs || []) {
    const key = r?.term || r?.customer_search_term || r?.targeting;
    if (!key) continue;
    const existing = m.get(key);
    if (!existing || (r.priority_score ?? 0) > (existing.priority_score ?? 0)) {
      m.set(key, r);
    }
  }
  return m;
}

/**
 * Resolve the row's recommendation using the same fallback chain.
 * Returns null when no recommendation matches.
 */
export function findRecForRow(map, row) {
  if (!map || !row) return null;
  return (
    map.get(row.term) ||
    map.get(row.customer_search_term) ||
    map.get(row.targeting) ||
    null
  );
}
