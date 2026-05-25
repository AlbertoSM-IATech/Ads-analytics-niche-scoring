import { ACTION_LABELS, ACTION_STYLES } from "../lib/recommendations";

// All action types we render in the breakdown, in the order we want them shown.
const ACTION_ORDER = [
  "SCALE",
  "MOVE_TO_EXACT",
  "HOLD",
  "OBSERVE",
  "LOWER_BID",
  "NEGATIVE_EXACT_CANDIDATE",
  "NEGATIVE_PHRASE_CANDIDATE",
  "WAIT_FOR_DATA",
  "REVIEW_CAMPAIGN",
  "PAUSE_TARGET",
];

function Kpi({ label, value, accent, testid }) {
  return (
    <div className="border border-border rounded-lg bg-card p-3 min-w-[110px]" data-testid={testid}>
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">{label}</div>
      <div className={`num text-2xl font-semibold mt-1 ${accent || ""}`}>{value}</div>
    </div>
  );
}

export default function ActionsSummary({ recommendations, byAction, onPickActionType, activeActionType }) {
  const total = recommendations?.length || 0;
  const byPriority = { high: 0, medium: 0, low: 0 };
  for (const r of recommendations || []) {
    if (byPriority[r.priority] != null) byPriority[r.priority] += 1;
  }
  // Use backend by_action (covers reserved types as 0); fallback to computed.
  const counts = byAction || {};

  return (
    <div className="space-y-3" data-testid="actions-summary">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Kpi label="Total" value={total} testid="kpi-total" />
        <Kpi label="Alta" value={byPriority.high} accent="text-red-600 dark:text-red-400" testid="kpi-high" />
        <Kpi label="Media" value={byPriority.medium} accent="text-amber-600 dark:text-amber-400" testid="kpi-medium" />
        <Kpi label="Baja" value={byPriority.low} accent="text-muted-foreground" testid="kpi-low" />
      </div>

      <div className="border border-border rounded-lg bg-card p-3">
        <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold mb-2">
          Desglose por acción
        </div>
        <div className="flex flex-wrap gap-1.5">
          {ACTION_ORDER.map((a) => {
            const n = counts[a] || 0;
            const style = ACTION_STYLES[a] || ACTION_STYLES.WAIT_FOR_DATA;
            const dim = n === 0 ? "opacity-40" : "";
            const isActive = activeActionType === a;
            return (
              <button
                key={a}
                onClick={() => onPickActionType?.(isActive ? "" : a)}
                className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] transition-all ${style.cls} ${dim} ${
                  isActive ? "ring-2 ring-offset-1 ring-coral/60" : ""
                }`}
                data-testid={`chip-${a}`}
                data-count={n}
                data-active={isActive ? "true" : "false"}
              >
                <span>{ACTION_LABELS[a]}</span>
                <span className="num font-semibold">{n}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
