import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription,
} from "./ui/sheet";
import { Button } from "./ui/button";
import { fmtMoney, fmtPct, fmtInt, getMarketplace } from "../lib/format";
import { useData } from "../context/DataContext";
import { Sparkles, AlertTriangle, MessageSquare, Megaphone, Lightbulb } from "lucide-react";
import {
  ACTION_LABELS, ACTION_STYLES,
  priorityLabel, confidenceLabel, riskLabel,
} from "../lib/recommendations";

function Block({ icon: Icon, title, children, testid }) {
  return (
    <div className="space-y-1" data-testid={testid}>
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
        <Icon className="size-3" /> {title}
      </div>
      <div className="text-sm">{children}</div>
    </div>
  );
}

function Metric({ label, value, accent, testid }) {
  return (
    <div className="border border-border rounded-md p-2 bg-background" data-testid={testid}>
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">{label}</div>
      <div className={`num text-sm font-semibold mt-0.5 ${accent || ""}`}>{value}</div>
    </div>
  );
}

export default function ActionDetailDrawer({ open, rec, onClose }) {
  const { marketplace } = useData();
  const sym = getMarketplace(marketplace).symbol;

  if (!rec) return null;
  const m = rec.metrics || {};
  const style = ACTION_STYLES[rec.action_type] || ACTION_STYLES.WAIT_FOR_DATA;
  const label = ACTION_LABELS[rec.action_type] || rec.action_type;
  const score = typeof rec.priority_score === "number" ? Math.round(rec.priority_score) : "—";
  const recoverable = rec.is_recoverable_with_next_sale;

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        side="right"
        className="p-0 sm:max-w-none w-auto overflow-hidden"
        style={{ width: "640px", maxWidth: "95vw" }}
        data-testid="action-detail-drawer"
      >
        <div className="h-full overflow-y-auto px-6 py-5 space-y-5">
          <SheetHeader>
            <div className="flex items-center gap-2 flex-wrap">
              <SheetTitle className="font-heading text-xl break-words">{rec.term || "—"}</SheetTitle>
              <span
                className={`inline-flex items-center rounded-md border text-[11px] py-0.5 px-2 ${style.cls}`}
                data-testid="drawer-action-type"
                data-action-type={rec.action_type}
              >
                {label}
              </span>
            </div>
            <SheetDescription>
              {rec.campaign ? `Campaña: ${rec.campaign}` : "Sin campaña"}
              {rec.match_type ? ` · ${rec.match_type}` : ""}
              {rec.ad_group ? ` · ${rec.ad_group}` : ""}
            </SheetDescription>
          </SheetHeader>

          <div className="flex flex-wrap gap-1.5 text-[10px]">
            <span className="px-2 py-0.5 rounded border bg-muted text-muted-foreground border-border" data-testid="drawer-priority">
              Prioridad: <span className="font-semibold">{priorityLabel(rec.priority)}</span>
            </span>
            <span className="px-2 py-0.5 rounded border bg-muted text-muted-foreground border-border" data-testid="drawer-confidence">
              Confianza: <span className="font-semibold">{confidenceLabel(rec.confidence)}</span>
            </span>
            <span className="px-2 py-0.5 rounded border bg-muted text-muted-foreground border-border" data-testid="drawer-risk">
              Riesgo: <span className="font-semibold">{riskLabel(rec.risk)}</span>
            </span>
            <span className="px-2 py-0.5 rounded border bg-muted text-muted-foreground border-border num" data-testid="drawer-score">
              Score: <span className="font-semibold">{score}</span>
            </span>
            {recoverable != null && (
              <span
                className={`px-2 py-0.5 rounded border ${
                  recoverable
                    ? "bg-green-100 text-green-700 border-green-300 dark:bg-green-500/10 dark:text-green-400"
                    : "bg-red-100 text-red-700 border-red-300 dark:bg-red-500/10 dark:text-red-400"
                }`}
                data-testid="drawer-recoverable"
                data-value={recoverable ? "true" : "false"}
              >
                {recoverable ? "Recuperable con +1 venta" : "No recuperable con +1 venta"}
              </span>
            )}
          </div>

          {(rec.targeting || rec.customer_search_term) && (
            <div className="text-xs text-muted-foreground space-y-0.5" data-testid="drawer-context">
              {rec.targeting && <div>Targeting: <span className="text-foreground">{rec.targeting}</span></div>}
              {rec.customer_search_term && <div>Search term: <span className="text-foreground">{rec.customer_search_term}</span></div>}
            </div>
          )}

          {rec.detected_problem && (
            <Block icon={AlertTriangle} title="Problema detectado" testid="drawer-problem">
              <span className="italic text-foreground/90">{rec.detected_problem}</span>
            </Block>
          )}
          {rec.reason && (
            <Block icon={MessageSquare} title="Razón" testid="drawer-reason">
              {rec.reason}
            </Block>
          )}
          {rec.recommended_action && (
            <Block icon={Lightbulb} title="Acción recomendada" testid="drawer-recommended">
              {rec.recommended_action}
            </Block>
          )}
          {rec.expected_impact && (
            <Block icon={Sparkles} title="Impacto esperado" testid="drawer-impact">
              {rec.expected_impact}
            </Block>
          )}
          {rec.amazon_instruction && (
            <Block icon={Megaphone} title="Cómo aplicarlo en Amazon Ads" testid="drawer-amazon">
              <span className="text-foreground/90">{rec.amazon_instruction}</span>
            </Block>
          )}

          <div className="space-y-2">
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
              Métricas
            </div>
            <div className="grid grid-cols-3 gap-2">
              <Metric label="Impr." value={m.impressions == null ? "—" : fmtInt(m.impressions)} />
              <Metric label="Clicks" value={m.clicks == null ? "—" : fmtInt(m.clicks)} />
              <Metric label="Pedidos" value={m.orders == null ? "—" : fmtInt(m.orders)} />
              <Metric label="Gasto" value={m.spend == null ? "—" : fmtMoney(m.spend, sym)} />
              <Metric label="Ventas" value={m.sales == null ? "—" : fmtMoney(m.sales, sym)} />
              <Metric label="CPC real" value={m.cpc_real == null ? "—" : fmtMoney(m.cpc_real, sym)} />
              <Metric label="ACoS" value={m.acos == null ? "—" : fmtPct(m.acos)} />
              <Metric label="ACoS PE" value={m.acos_pe_kdp == null ? "—" : fmtPct(m.acos_pe_kdp)} />
              <Metric label="ACoS +1 venta" value={m.acos_siguiente_con_venta == null ? "—" : fmtPct(m.acos_siguiente_con_venta)} />
              <Metric label="Clicks PE" value={m.clicks_pe == null ? "—" : m.clicks_pe.toFixed(2)} />
              <Metric label="Clicks fase" value={m.clicks_fase == null ? "—" : m.clicks_fase.toFixed(2)} />
              <Metric label="CVR" value={m.cvr == null ? "—" : `${m.cvr.toFixed(1)}%`} />
              <Metric
                label="Consumo PE"
                value={m.consumo_pe == null ? "—" : `${(m.consumo_pe * 100).toFixed(0)}%`}
                accent={m.consumo_pe != null && m.consumo_pe > 1 ? "text-red-600 dark:text-red-400" : ""}
                testid="drawer-consumo-pe"
              />
              <Metric
                label="Consumo fase"
                value={m.consumo_fase == null ? "—" : `${(m.consumo_fase * 100).toFixed(0)}%`}
                accent={m.consumo_fase != null && m.consumo_fase > 1 ? "text-red-600 dark:text-red-400" : ""}
              />
              <Metric
                label="Beneficio KDP"
                value={m.beneficio_kdp == null ? "—" : fmtMoney(m.beneficio_kdp, sym)}
                accent={
                  m.beneficio_kdp == null ? "" :
                  m.beneficio_kdp < 0 ? "text-destructive" : "text-green-600 dark:text-green-400"
                }
                testid="drawer-beneficio-kdp"
              />
            </div>
            <div className="text-[10px] text-muted-foreground italic">
              CPC: {m.cpc_source || "n/d"} · Relevancia: {m.relevance || "unreviewed"} · Fase: {rec.phase}
            </div>
          </div>

          <div className="pt-3 border-t border-border flex justify-end">
            <Button variant="outline" onClick={onClose} className="rounded-md" data-testid="drawer-close">
              Cerrar
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
