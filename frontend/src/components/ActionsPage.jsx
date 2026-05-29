import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Loader2, AlertCircle, Inbox, Download } from "lucide-react";
import { toast } from "sonner";
import { getRecommendations } from "../lib/api";
import { useData } from "../context/DataContext";
import { fmtMoney, fmtInt, getMarketplace } from "../lib/format";
import { ACTION_LABELS, ACTION_STYLES, priorityLabel, confidenceLabel, riskLabel } from "../lib/recommendations";
import { downloadCsv } from "../lib/exportRecommendationsCsv";
import { Button } from "./ui/button";
import { InfoTooltip } from "./InfoTooltip";
import ActionsSummary from "./ActionsSummary";
import ActionsFilters from "./ActionsFilters";
import ActionDetailDrawer from "./ActionDetailDrawer";

const PRI_DOT = {
  high: "bg-red-500",
  medium: "bg-amber-500",
  low: "bg-neutral-400",
};

const VALID_ACTION_TYPES = new Set([
  "WAIT_FOR_DATA", "OBSERVE", "LOWER_BID", "HOLD", "SCALE",
  "MOVE_TO_EXACT", "NEGATIVE_EXACT_CANDIDATE", "NEGATIVE_PHRASE_CANDIDATE",
  "REVIEW_CAMPAIGN", "PAUSE_TARGET",
]);

const DEFAULT_FILTERS = {
  priority: "", actionType: "", confidence: "", risk: "",
  relevance: "", onlyWithOrders: false, onlyNegativeProfit: false,
};

function consumoCls(v) {
  if (v == null) return "text-muted-foreground/40";
  if (v < 0.5) return "text-green-600 dark:text-green-400";
  if (v < 0.8) return "text-amber-600 dark:text-amber-400";
  if (v <= 1.0) return "text-orange-600 dark:text-orange-400";
  return "text-red-600 dark:text-red-400 font-semibold";
}

export default function ActionsPage({ datasetId }) {
  const { marketplace } = useData();
  const sym = getMarketplace(marketplace).symbol;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [payload, setPayload] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();

  // Initialise actionType from query string (deep-link). Invalid values are ignored.
  const initialActionType = (() => {
    const raw = searchParams.get("action_type");
    return raw && VALID_ACTION_TYPES.has(raw) ? raw : "";
  })();
  const [filters, setFilters] = useState({ ...DEFAULT_FILTERS, actionType: initialActionType });
  const [selected, setSelected] = useState(null);

  // Keep URL in sync with the actionType filter (Phase 4A.1 deep-link contract).
  useEffect(() => {
    const current = searchParams.get("action_type") || "";
    if (filters.actionType && filters.actionType !== current) {
      const next = new URLSearchParams(searchParams);
      next.set("action_type", filters.actionType);
      setSearchParams(next, { replace: true });
    } else if (!filters.actionType && current) {
      const next = new URLSearchParams(searchParams);
      next.delete("action_type");
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.actionType]);

  // External URL changes (back/forward, manual edit) → reflect in filter state.
  useEffect(() => {
    const raw = searchParams.get("action_type") || "";
    const next = raw && VALID_ACTION_TYPES.has(raw) ? raw : "";
    if (next !== filters.actionType) {
      setFilters((f) => ({ ...f, actionType: next }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  useEffect(() => {
    if (!datasetId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    getRecommendations(datasetId)
      .then((r) => { if (!cancelled) setPayload(r.data); })
      .catch((e) => { if (!cancelled) setError(e?.response?.data?.detail || e.message || "Error desconocido"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [datasetId]);

  const all = useMemo(() => payload?.recommendations || [], [payload]);

  const filtered = useMemo(() => {
    const f = filters;
    let arr = all.filter((r) => {
      if (f.priority && r.priority !== f.priority) return false;
      if (f.actionType && r.action_type !== f.actionType) return false;
      if (f.confidence && r.confidence !== f.confidence) return false;
      if (f.risk && r.risk !== f.risk) return false;
      if (f.relevance && (r.metrics?.relevance || "unreviewed") !== f.relevance) return false;
      if (f.onlyWithOrders && !(r.metrics?.orders > 0)) return false;
      if (f.onlyNegativeProfit && !(r.metrics?.beneficio_kdp != null && r.metrics.beneficio_kdp < 0)) return false;
      return true;
    });
    arr.sort((a, b) => {
      const ds = (b.priority_score || 0) - (a.priority_score || 0);
      if (ds !== 0) return ds;
      return (b.metrics?.spend || 0) - (a.metrics?.spend || 0);
    });
    return arr;
  }, [all, filters]);

  if (!datasetId) {
    return (
      <div className="border border-dashed border-border p-12 text-center rounded-lg bg-card" data-testid="actions-empty-no-dataset">
        <div className="text-sm text-muted-foreground">Importa un CSV de Amazon Ads para ver las recomendaciones.</div>
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in" data-testid="actions-page">
      {/* Top meta */}
      {payload && (
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground" data-testid="actions-meta">
          <span>Fase: <span className="text-foreground font-semibold">{payload.phase}</span></span>
          <span>·</span>
          <span>Regalía: <span className="text-foreground font-semibold">{payload.regalia_source}</span></span>
          <span>·</span>
          <span>Generado: <span className="num text-foreground">{(payload.generated_at || "").slice(0, 19).replace("T", " ")}</span></span>
          <span className="ml-auto italic">Read-only · no modifica datos</span>
        </div>
      )}

      <ActionsSummary
        recommendations={all}
        byAction={payload?.by_action}
        activeActionType={filters.actionType}
        onPickActionType={(v) => setFilters((f) => ({ ...f, actionType: v }))}
      />

      <ActionsFilters value={filters} onChange={setFilters} />

      <div className="flex items-center justify-between gap-3 flex-wrap" data-testid="actions-toolbar">
        <div className="text-[11px] text-muted-foreground" data-testid="actions-count">
          Mostrando <span className="num font-semibold text-foreground">{filtered.length}</span> de{" "}
          <span className="num font-semibold text-foreground">{all.length}</span> recomendaciones
        </div>
        <Button
          variant="outline"
          size="sm"
          className="rounded-md gap-1.5"
          disabled={filtered.length === 0}
          title={filtered.length === 0 ? "No hay acciones visibles para exportar." : undefined}
          onClick={() => {
            const { rows } = downloadCsv(filtered);
            toast.success(`CSV exportado con ${rows} ${rows === 1 ? "acción" : "acciones"}.`);
          }}
          data-testid="export-actions-csv"
          data-disabled={filtered.length === 0 ? "true" : "false"}
        >
          <Download className="size-3.5" />
          Exportar vista actual
          <InfoTooltip content="export_actions" className="ml-1" />
        </Button>
      </div>

      {loading && (
        <div className="py-12 flex justify-center" data-testid="actions-loading">
          <Loader2 className="size-6 animate-spin text-coral" />
        </div>
      )}

      {error && !loading && (
        <div className="border border-destructive/40 bg-destructive/5 p-4 rounded-md flex items-start gap-2 text-sm" data-testid="actions-error">
          <AlertCircle className="size-4 mt-0.5 text-destructive" />
          <div>
            <div className="font-semibold text-destructive">No se pudieron cargar las recomendaciones.</div>
            <div className="text-muted-foreground text-xs mt-0.5">{String(error)}</div>
          </div>
        </div>
      )}

      {!loading && !error && all.length === 0 && (
        <div className="border border-dashed border-border p-12 text-center rounded-lg bg-card flex flex-col items-center gap-2" data-testid="actions-empty">
          <Inbox className="size-6 text-muted-foreground" />
          <div className="text-sm text-muted-foreground">No hay recomendaciones accionables todavía.</div>
        </div>
      )}

      {!loading && !error && all.length > 0 && filtered.length === 0 && (
        <div className="border border-dashed border-border p-8 text-center rounded-lg bg-card" data-testid="actions-empty-filtered">
          <div className="text-sm text-muted-foreground">Ninguna recomendación coincide con los filtros actuales.</div>
        </div>
      )}

      {!loading && !error && filtered.length > 0 && (
        <div className="border border-border rounded-lg overflow-x-auto bg-card">
          <table className="w-full text-sm">
            <thead className="bg-muted/40">
              <tr className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
                <th className="text-left px-3 py-2.5">Prioridad</th>
                <th className="text-left px-3 py-2.5">Acción</th>
                <th className="text-left px-3 py-2.5">Término</th>
                <th className="text-left px-3 py-2.5">Campaña</th>
                <th className="text-right px-3 py-2.5">Clicks</th>
                <th className="text-right px-3 py-2.5">Gasto</th>
                <th className="text-right px-3 py-2.5">Ped.</th>
                <th className="text-right px-3 py-2.5">Beneficio KDP</th>
                <th className="text-right px-3 py-2.5">Cons. PE</th>
                <th className="text-right px-3 py-2.5">Cons. fase</th>
                <th className="text-left px-3 py-2.5">Recomendación</th>
                <th className="px-3 py-2.5"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r, i) => {
                const m = r.metrics || {};
                const style = ACTION_STYLES[r.action_type] || ACTION_STYLES.WAIT_FOR_DATA;
                return (
                  <tr
                    key={r.id}
                    className="border-t border-border hover:bg-muted/30 cursor-pointer"
                    data-testid={`action-row-${i}`}
                    data-action-type={r.action_type}
                    data-priority={r.priority}
                    onClick={() => setSelected(r)}
                  >
                    <td className="px-3 py-2">
                      <span className="inline-flex items-center gap-1.5 text-xs">
                        <span className={`size-2 rounded-full ${PRI_DOT[r.priority] || "bg-neutral-400"}`} />
                        {priorityLabel(r.priority)}
                        <span className="text-muted-foreground num text-[10px]">{Math.round(r.priority_score || 0)}</span>
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-flex items-center rounded-md border text-[10px] py-0 px-1.5 ${style.cls}`}
                        data-testid={`row-action-${i}`}
                      >
                        {ACTION_LABELS[r.action_type] || r.action_type}
                      </span>
                    </td>
                    <td className="px-3 py-2 max-w-[200px]">
                      {r.action_type === "REVIEW_CAMPAIGN" && !r.term ? (
                        <>
                          <div className="truncate font-medium" title={r.campaign || ""} data-testid={`row-campaign-as-term-${i}`}>
                            {r.campaign || "—"}
                          </div>
                          <div className="text-[10px] text-muted-foreground">campaña</div>
                        </>
                      ) : (
                        <>
                          <div className="truncate font-medium" title={r.term || ""}>{r.term || "—"}</div>
                          {r.match_type && (
                            <div className="text-[10px] text-muted-foreground">{r.match_type}</div>
                          )}
                        </>
                      )}
                    </td>
                    <td className="px-3 py-2 max-w-[150px]">
                      <div className="truncate text-xs" title={r.campaign || ""}>{r.campaign || "—"}</div>
                    </td>
                    <td className="px-3 py-2 num text-right">{m.clicks == null ? "—" : fmtInt(m.clicks)}</td>
                    <td className="px-3 py-2 num text-right">{m.spend == null ? "—" : fmtMoney(m.spend, sym)}</td>
                    <td className="px-3 py-2 num text-right">{m.orders == null ? "—" : fmtInt(m.orders)}</td>
                    <td className={`px-3 py-2 num text-right ${
                      m.beneficio_kdp == null ? "" :
                      m.beneficio_kdp < 0 ? "text-destructive" : "text-green-600 dark:text-green-400"
                    }`}>
                      {m.beneficio_kdp == null ? "—" : fmtMoney(m.beneficio_kdp, sym)}
                    </td>
                    <td className={`px-3 py-2 num text-right ${consumoCls(m.consumo_pe)}`}>
                      {m.consumo_pe == null ? "—" : `${(m.consumo_pe * 100).toFixed(0)}%`}
                    </td>
                    <td className={`px-3 py-2 num text-right ${consumoCls(m.consumo_fase)}`}>
                      {m.consumo_fase == null ? "—" : `${(m.consumo_fase * 100).toFixed(0)}%`}
                    </td>
                    <td className="px-3 py-2 text-xs max-w-[260px]">
                      <div className="truncate" title={r.recommended_action || ""}>{r.recommended_action || "—"}</div>
                      <div className="text-[10px] text-muted-foreground flex gap-1.5 mt-0.5">
                        <span>Conf: {confidenceLabel(r.confidence)}</span>
                        <span>·</span>
                        <span>Riesgo: {riskLabel(r.risk)}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <span className="text-xs text-coral hover:underline">Detalle →</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <ActionDetailDrawer
        open={!!selected}
        rec={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
