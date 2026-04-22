import { useState } from "react";
import { Sparkles, Loader2, AlertTriangle, Info, AlertOctagon } from "lucide-react";
import { Button } from "./ui/button";
import { getAiRecs } from "../lib/api";
import { toast } from "sonner";

const iconFor = (sev) =>
  sev === "critical" ? AlertOctagon : sev === "warning" ? AlertTriangle : Info;

const styleFor = (sev) =>
  sev === "critical"
    ? "bg-red-50 border-red-200 text-red-700 dark:bg-red-500/5 dark:border-red-500/30 dark:text-red-400"
    : sev === "warning"
    ? "bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-500/5 dark:border-amber-500/30 dark:text-amber-400"
    : "bg-blue-50 border-blue-200 text-blue-700 dark:bg-blue-500/5 dark:border-blue-500/30 dark:text-blue-400";

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
    <div className="border border-border rounded-lg bg-card p-6 relative overflow-hidden" data-testid="ai-panel">
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-coral via-coral-500 to-coral" />
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="size-10 rounded-md bg-coral/10 flex items-center justify-center">
            <Sparkles className="size-5 text-coral" />
          </div>
          <div>
            <h3 className="font-heading font-semibold text-lg">IA · Claude Sonnet 4.5</h3>
            <div className="text-xs text-muted-foreground">Recomendaciones personalizadas de optimización</div>
          </div>
        </div>
        <Button
          size="sm"
          onClick={run}
          disabled={loading || !datasetId}
          className="rounded-md bg-coral hover:bg-coral-500 text-white"
          data-testid="generate-ai-btn"
        >
          {loading ? <><Loader2 className="size-4 animate-spin mr-2" /> Analizando…</> : "Generar"}
        </Button>
      </div>

      {!recs && !loading && (
        <div className="text-sm text-muted-foreground text-center py-6 border border-dashed border-border rounded-md" data-testid="ai-empty">
          Pulsa <span className="font-semibold text-foreground">Generar</span> para obtener tu análisis.
        </div>
      )}

      {recs?.recommendations?.length > 0 && (
        <ul className="space-y-2.5" data-testid="ai-recs">
          {recs.recommendations.map((r, i) => {
            const Icon = iconFor(r.severity);
            return (
              <li
                key={i}
                className={`border rounded-md p-3.5 ${styleFor(r.severity)}`}
                data-testid={`ai-rec-${i}`}
              >
                <div className="flex items-start gap-2.5">
                  <Icon className="size-4 mt-0.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-sm text-foreground">{r.title}</div>
                    <div className="text-xs text-muted-foreground mt-1 leading-relaxed">{r.detail}</div>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
