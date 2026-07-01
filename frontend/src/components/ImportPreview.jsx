import { AlertTriangle, CheckCircle2, XCircle, Info } from "lucide-react";
import { Button } from "./ui/button";

/**
 * IMPORT-2 · Minimal preview UI.
 *
 * Renders the diagnostics payload returned by POST /api/imports/preview:
 *   - report_type + confidence
 *   - matched fields (canonical names)
 *   - unmatched headers (surfaced verbatim so the user knows what was ignored)
 *   - missing critical fields
 *   - warnings (collisions, fractional ACOS, unknown type, ...)
 *   - capabilities (feature-flags derived from what was mapped)
 *
 * The confirm button is disabled when the report is `unknown` or when
 * critical fields are missing. The user can still choose to import anyway
 * via the escape hatch (secondary link) — this preserves autonomy while
 * making silent misfires impossible.
 */
const CONF_STYLE = {
  high:   { label: "Alta",     color: "text-green-600 dark:text-green-400" },
  medium: { label: "Media",    color: "text-amber-600 dark:text-amber-400" },
  low:    { label: "Baja",     color: "text-red-600 dark:text-red-400" },
  unknown:{ label: "Desconocida", color: "text-red-600 dark:text-red-400" },
};

const CAP_LABELS = {
  ads_performance: "Métricas de rendimiento",
  profitability:   "Rentabilidad (ACoS/ROAS)",
  negatives:       "Sugerencia de negativas",
  bid_changes:     "Cambios de puja",
  tacos:           "TACoS",
  bulk:            "Bulk sheet",
};

export function ImportPreview({ preview, onConfirm, onCancel, busy }) {
  if (!preview) return null;
  const d = preview.diagnostics || {};
  const conf = CONF_STYLE[d.report_type_confidence] || CONF_STYLE.unknown;
  const hasCritical = (d.missing_critical || []).length > 0;
  const isUnknown = d.report_type === "unknown";
  const blockConfirm = hasCritical || isUnknown;

  return (
    <div
      className="border border-border rounded-lg bg-card p-5 space-y-4"
      data-testid="import-preview"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-heading text-lg font-semibold">
            Vista previa de importación
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            El archivo aún no se ha guardado. Revisa antes de confirmar.
          </div>
        </div>
        <div className="text-right text-xs">
          <div className="uppercase tracking-widest text-muted-foreground">Confianza</div>
          <div className={`font-semibold ${conf.color}`} data-testid="preview-confidence">
            {conf.label}
          </div>
        </div>
      </div>

      <div className="grid sm:grid-cols-3 gap-3 text-sm">
        <div>
          <div className="text-xs text-muted-foreground uppercase tracking-widest">
            Tipo de reporte
          </div>
          <div className="num font-medium" data-testid="preview-report-type">
            {d.report_type || "—"}
          </div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground uppercase tracking-widest">
            Filas detectadas
          </div>
          <div className="num font-medium">{preview.row_count}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground uppercase tracking-widest">
            Tipo de anuncio
          </div>
          <div className="num font-medium">{preview.ad_type}</div>
        </div>
      </div>

      {isUnknown && (
        <div className="border border-red-300 dark:border-red-500/40 bg-red-50 dark:bg-red-500/5 p-3 rounded-md flex items-start gap-2 text-sm">
          <XCircle className="size-4 text-red-600 dark:text-red-400 mt-0.5" />
          <div>
            <div className="font-medium">No se ha reconocido el tipo de reporte</div>
            <div className="text-xs text-muted-foreground">
              Revisa que sea un CSV/XLSX de Amazon Ads
              (Search Term / Campaign / Placement). No se puede importar con seguridad.
            </div>
          </div>
        </div>
      )}

      {hasCritical && !isUnknown && (
        <div
          className="border border-amber-300 dark:border-amber-500/40 bg-amber-50 dark:bg-amber-500/5 p-3 rounded-md flex items-start gap-2 text-sm"
          data-testid="preview-missing-critical"
        >
          <AlertTriangle className="size-4 text-amber-600 dark:text-amber-400 mt-0.5" />
          <div>
            <div className="font-medium">Faltan columnas críticas</div>
            <div className="text-xs text-muted-foreground">
              {d.missing_critical.join(", ")}
            </div>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <section>
          <div className="text-xs uppercase tracking-widest text-muted-foreground mb-1.5">
            Columnas reconocidas ({(d.matched_fields || []).length})
          </div>
          {(d.matched_fields || []).length ? (
            <ul className="text-xs space-y-1" data-testid="preview-matched">
              {d.matched_fields.map((f) => (
                <li key={f} className="flex items-center gap-1.5">
                  <CheckCircle2 className="size-3 text-green-600 dark:text-green-400" />
                  <span className="num">{f}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-xs text-muted-foreground">Ninguna</div>
          )}
        </section>

        <section>
          <div className="text-xs uppercase tracking-widest text-muted-foreground mb-1.5">
            Columnas no reconocidas ({(d.unmatched_headers || []).length})
          </div>
          {(d.unmatched_headers || []).length ? (
            <ul
              className="text-xs space-y-1 max-h-32 overflow-auto"
              data-testid="preview-unmatched"
            >
              {d.unmatched_headers.map((h) => (
                <li key={h} className="text-muted-foreground">· {h}</li>
              ))}
            </ul>
          ) : (
            <div className="text-xs text-muted-foreground">Ninguna</div>
          )}
        </section>
      </div>

      {(d.warnings || []).length > 0 && (
        <section data-testid="preview-warnings">
          <div className="text-xs uppercase tracking-widest text-muted-foreground mb-1.5">
            Avisos ({d.warnings.length})
          </div>
          <ul className="text-xs space-y-1">
            {d.warnings.map((w, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <Info className="size-3 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                <span>{w}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <div className="text-xs uppercase tracking-widest text-muted-foreground mb-1.5">
          Capacidades habilitadas
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 text-xs">
          {Object.entries(d.capabilities || {}).map(([k, v]) => (
            <div key={k} className="flex items-center gap-1.5">
              {v ? (
                <CheckCircle2 className="size-3 text-green-600 dark:text-green-400" />
              ) : (
                <XCircle className="size-3 text-muted-foreground/60" />
              )}
              <span className={v ? "" : "text-muted-foreground/60 line-through"}>
                {CAP_LABELS[k] || k}
              </span>
            </div>
          ))}
        </div>
      </section>

      <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
        <Button
          variant="ghost"
          onClick={onCancel}
          disabled={busy}
          data-testid="preview-cancel-btn"
        >
          Cancelar
        </Button>
        <Button
          onClick={onConfirm}
          disabled={busy || blockConfirm}
          className="rounded-md bg-coral hover:bg-coral-500 text-white"
          data-testid="preview-confirm-btn"
        >
          {busy ? "Importando…" : "Confirmar importación"}
        </Button>
      </div>
      {blockConfirm && (
        <div className="text-[11px] text-muted-foreground text-right">
          La importación está bloqueada por baja confianza. Corrige el archivo y vuelve a intentarlo.
        </div>
      )}
    </div>
  );
}

export default ImportPreview;
