import { useState } from "react";
import { Sparkles, Loader2, AlertTriangle, Info, AlertOctagon } from "lucide-react";
import { Button } from "./ui/button";
import { getAiRecs } from "../lib/api";
import { toast } from "sonner";

const iconFor = (sev) =>
  sev === "critical" ? AlertOctagon : sev === "warning" ? AlertTriangle : Info;

const colorFor = (sev) =>
  sev === "critical"
    ? "text-destructive border-destructive/40"
    : sev === "warning"
    ? "text-[hsl(var(--warning))] border-[hsl(var(--warning))]/40"
    : "text-primary border-primary/40";

export default function AiPanel({ datasetId, initialRecs }) {
  const [recs, setRecs] = useState(initialRecs || null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try {
      const r = await getAiRecs(datasetId);
      setRecs(r.data);
      toast.success("Recomendaciones generadas");
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="terminal-border border border-border p-5 rounded-sm bg-card" data-testid="ai-panel">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Sparkles className="size-5 text-[hsl(var(--accent))]" />
          <h3 className="font-bold tracking-tight">IA · Claude Sonnet 4.5</h3>
          <span className="text-[10px] uppercase tracking-widest text-muted-foreground">
            Recomendaciones de optimización
          </span>
        </div>
        <Button
          size="sm"
          onClick={run}
          disabled={loading || !datasetId}
          className="rounded-sm"
          data-testid="generate-ai-btn"
        >
          {loading ? <Loader2 className="size-4 animate-spin" /> : "Generar"}
        </Button>
      </div>

      {!recs && !loading && (
        <div className="text-sm text-muted-foreground" data-testid="ai-empty">
          Pulsa <span className="font-medium text-foreground">Generar</span> para obtener un análisis personalizado con Claude.
        </div>
      )}

      {recs?.recommendations?.length > 0 && (
        <ul className="space-y-2" data-testid="ai-recs">
          {recs.recommendations.map((r, i) => {
            const Icon = iconFor(r.severity);
            return (
              <li
                key={i}
                className={`border-l-2 pl-3 py-2 ${colorFor(r.severity)}`}
                data-testid={`ai-rec-${i}`}
              >
                <div className="flex items-center gap-2">
                  <Icon className="size-4" />
                  <div className="font-medium text-sm text-foreground">{r.title}</div>
                </div>
                <div className="text-xs text-muted-foreground mt-1">{r.detail}</div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
