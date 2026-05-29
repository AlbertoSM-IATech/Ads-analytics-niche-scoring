import { useEffect, useMemo, useState } from "react";
import { useData } from "../context/DataContext";
import { updateBook, getEconomyDiagnosis } from "../lib/api";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "./ui/select";
import {
  BookOpen, Save, Loader2, Calculator, Target, TrendingUp, AlertTriangle,
  CheckCircle2, ShieldAlert, Info,
} from "lucide-react";
import { toast } from "sonner";
import { InfoTooltip } from "./InfoTooltip";

// -----------------------------------------------------------------------------
// Constants mirror backend/kdp_economy.py — keep both in sync if values ever change.
// -----------------------------------------------------------------------------
const MARKETPLACES = [
  { code: "ES", label: "España", currency: "EUR", symbol: "€" },
  { code: "COM", label: "Estados Unidos", currency: "USD", symbol: "$" },
  { code: "DE", label: "Alemania", currency: "EUR", symbol: "€" },
  { code: "FR", label: "Francia", currency: "EUR", symbol: "€" },
  { code: "IT", label: "Italia", currency: "EUR", symbol: "€" },
  { code: "UK", label: "Reino Unido", currency: "GBP", symbol: "£" },
  { code: "CA", label: "Canadá", currency: "CAD", symbol: "C$" },
  { code: "AU", label: "Australia", currency: "AUD", symbol: "A$" },
  { code: "JP", label: "Japón", currency: "JPY", symbol: "¥" },
];

const FORMAT_TYPES = [
  { value: "EBOOK", label: "eBook" },
  { value: "PRINT", label: "Impreso (tapa blanda / dura)" },
];

const BOOK_FORMATS = [
  { value: "PAPERBACK", label: "Tapa blanda" },
  { value: "HARDCOVER", label: "Tapa dura" },
];

const INTERIORS = [
  { value: "BN", label: "B/N (tinta negra)" },
  { value: "COLOR_PREMIUM", label: "Color Premium" },
  { value: "COLOR_STANDARD", label: "Color Standard" },
];

const SIZES = [
  { value: "SMALL", label: "≤ 6 × 9 in (SMALL)" },
  { value: "LARGE", label: "> 6 × 9 in (LARGE)" },
];

const ROYALTY_EBOOK = [
  { value: 70, label: "70%" },
  { value: 35, label: "35%" },
];

const RISK_STYLES = {
  low:    { cls: "bg-green-100 text-green-700 border-green-200 dark:bg-green-500/10 dark:text-green-400", label: "Bajo riesgo", icon: CheckCircle2 },
  medium: { cls: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400", label: "Riesgo medio", icon: AlertTriangle },
  high:   { cls: "bg-red-100 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-400", label: "Riesgo alto", icon: ShieldAlert },
};
const VIABILITY_STYLES = {
  viable:       { cls: "bg-green-600 hover:bg-green-600 text-white", label: "Viable" },
  adjustable:   { cls: "bg-amber-500 hover:bg-amber-500 text-white", label: "Ajustable" },
  "not-viable": { cls: "bg-red-600 hover:bg-red-600 text-white", label: "No viable" },
};

function fmtNum(v, digits = 2, sym = "") {
  if (v == null || Number.isNaN(Number(v))) return "—";
  const s = Number(v).toLocaleString("es-ES", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  return sym ? `${s} ${sym}` : s;
}

export default function BookEconomyKDP() {
  const { active, loadActive, marketplace } = useData();
  const [form, setForm] = useState({
    format_type: "",
    book_format: "",
    interior_type: "",
    book_size: "",
    pages: "",
    iva_type: "",
    royalty_rate_ebook: 70,
    tamano_mb: "",
    cpc_referencia: "",
    margen_objetivo_pct: 30,
  });
  const [kdpMarketplace, setKdpMarketplace] = useState(marketplace?.toUpperCase?.() || "COM");
  const [diag, setDiag] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // Hydrate form from the active dataset
  useEffect(() => {
    if (!active) return;
    const eco = active.book_economy || {};
    setForm((f) => ({
      ...f,
      format_type: eco.format_type || "",
      book_format: eco.book_format || "",
      interior_type: eco.interior_type || "",
      book_size: eco.book_size || "",
      pages: eco.pages ?? "",
      iva_type: eco.iva_type ?? "",
      royalty_rate_ebook: eco.royalty_rate_ebook ?? 70,
      tamano_mb: eco.tamano_mb ?? "",
      cpc_referencia: eco.cpc_referencia ?? "",
      margen_objetivo_pct: eco.margen_objetivo_pct ?? 30,
    }));
    setKdpMarketplace((active.marketplace || marketplace || "COM").toUpperCase() === "US"
      ? "COM"
      : (active.marketplace || marketplace || "COM").toUpperCase());
  }, [active, marketplace]);

  // Load diagnosis on mount & whenever the user presses Calcular
  const refreshDiagnosis = async () => {
    if (!active?.id) return;
    setLoading(true);
    try {
      const r = await getEconomyDiagnosis(active.id);
      setDiag(r.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };

  useEffect(() => { refreshDiagnosis(); /* eslint-disable-next-line */ }, [active?.id]);

  const isPrint = form.format_type === "PRINT";
  const isEbook = form.format_type === "EBOOK";
  const isSpain = kdpMarketplace === "ES";

  const handleSave = async () => {
    if (!active) return;
    setSaving(true);
    try {
      // Merge KDP fields onto existing economy object without losing legacy keys
      const legacy = active.book_economy || {};
      const economy = {
        // legacy (preserved)
        precio_libro: Number(legacy.precio_libro) || 0,
        regalias_por_venta: Number(legacy.regalias_por_venta) || 0,
        mult_lanzamiento: Number(legacy.mult_lanzamiento) || 1.7,
        mult_dominio: Number(legacy.mult_dominio) || 1.2,
        mult_beneficio: Number(legacy.mult_beneficio) || 0.5,
        // KDP
        format_type: form.format_type || null,
        book_format: isPrint ? (form.book_format || null) : null,
        interior_type: isPrint ? (form.interior_type || null) : null,
        book_size: isPrint ? (form.book_size || null) : null,
        pages: isPrint ? (Number(form.pages) || null) : null,
        iva_type: isSpain && form.iva_type !== "" ? Number(form.iva_type) : null,
        royalty_rate_ebook: isEbook ? Number(form.royalty_rate_ebook) : null,
        tamano_mb: isEbook && form.royalty_rate_ebook === 70 ? (Number(form.tamano_mb) || null) : null,
        cpc_referencia: form.cpc_referencia !== "" ? Number(form.cpc_referencia) : null,
        margen_objetivo_pct: Number(form.margen_objetivo_pct) || 30,
      };
      await updateBook(active.id, {
        info: active.book_info || { title: "", subtitle: "", description: "", categories: [] },
        economy,
      });
      await loadActive(active.id);
      await refreshDiagnosis();
      toast.success("Configuración KDP guardada y diagnóstico recalculado");
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    } finally { setSaving(false); }
  };

  const sym = useMemo(() => {
    const mp = MARKETPLACES.find((m) => m.code === kdpMarketplace);
    return mp?.symbol || "";
  }, [kdpMarketplace]);

  if (!active) return null;

  const o = diag?.outputs || {};
  const d = diag?.diagnosis;
  const risk = d ? RISK_STYLES[d.risk_level] : null;
  const viab = d ? VIABILITY_STYLES[d.viability_status] : null;
  const legacyMode = diag?.mode === "legacy";

  return (
    <div className="border border-border rounded-lg bg-card p-6 space-y-5" data-testid="book-economy-kdp">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="font-heading text-lg font-semibold flex items-center gap-2">
          <Calculator className="size-5 text-coral" />
          Configuración económica KDP
          <InfoTooltip content="Configura el formato, interior y páginas del libro para que la app calcule regalía neta, ACoS de equilibrio, CPC máximo rentable y PVP mínimo. Si no lo configuras, el módulo Ads sigue funcionando con precio y regalías simples." />
        </h3>
        {legacyMode && (
          <Badge variant="outline" className="rounded-md text-xs gap-1">
            <Info className="size-3" /> Modo legacy (sin config KDP)
          </Badge>
        )}
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
        <div>
          <Label className="text-xs flex items-center gap-1">
            Marketplace KDP
            <InfoTooltip content="marketplace" />
          </Label>
          <Select value={kdpMarketplace} onValueChange={setKdpMarketplace}>
            <SelectTrigger className="rounded-md mt-1" data-testid="kdp-marketplace"><SelectValue /></SelectTrigger>
            <SelectContent>
              {MARKETPLACES.map((m) => (
                <SelectItem key={m.code} value={m.code}>{m.code} — {m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="text-[10px] text-muted-foreground mt-1">
            Threshold regalía: {diag?.marketplace_config?.royalty_threshold ?? "—"} {sym}
          </div>
        </div>
        <div>
          <Label className="text-xs flex items-center gap-1">
            Formato
            <InfoTooltip content="formato" />
          </Label>
          <Select value={form.format_type} onValueChange={(v) => setForm({ ...form, format_type: v })}>
            <SelectTrigger className="rounded-md mt-1" data-testid="kdp-format-type"><SelectValue placeholder="Selecciona formato…" /></SelectTrigger>
            <SelectContent>
              {FORMAT_TYPES.map((f) => (
                <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {isPrint && (
          <div>
            <Label className="text-xs">Sub-tipo impreso</Label>
            <Select value={form.book_format} onValueChange={(v) => setForm({ ...form, book_format: v })}>
              <SelectTrigger className="rounded-md mt-1" data-testid="kdp-book-format"><SelectValue placeholder="Tapa blanda / dura" /></SelectTrigger>
              <SelectContent>
                {BOOK_FORMATS.map((f) => (
                  <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        {isPrint && (
          <>
            <div>
              <Label className="text-xs flex items-center gap-1">
                Tipo de interior
                <InfoTooltip content="tipo_impresion" />
              </Label>
              <Select value={form.interior_type} onValueChange={(v) => setForm({ ...form, interior_type: v })}>
                <SelectTrigger className="rounded-md mt-1" data-testid="kdp-interior-type"><SelectValue placeholder="BN / Color" /></SelectTrigger>
                <SelectContent>
                  {INTERIORS.map((i) => (
                    <SelectItem key={i.value} value={i.value}>{i.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {form.book_format === "HARDCOVER" && form.interior_type === "COLOR_STANDARD" && (
                <div className="text-[10px] text-destructive mt-1">⚠︎ Hardcover no compatible con Color Standard.</div>
              )}
            </div>
            <div>
              <Label className="text-xs">Tamaño</Label>
              <Select value={form.book_size} onValueChange={(v) => setForm({ ...form, book_size: v })}>
                <SelectTrigger className="rounded-md mt-1" data-testid="kdp-book-size"><SelectValue placeholder="SMALL / LARGE" /></SelectTrigger>
                <SelectContent>
                  {SIZES.map((s) => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs flex items-center gap-1">
                Páginas
                <InfoTooltip content="pages" />
              </Label>
              <Input
                type="number" min={24} max={828} step={1}
                value={form.pages}
                onChange={(e) => setForm({ ...form, pages: e.target.value })}
                placeholder="ej. 220"
                className="rounded-md mt-1 num"
                data-testid="kdp-pages"
              />
            </div>
          </>
        )}
        {isEbook && (
          <>
            <div>
              <Label className="text-xs">Regalía eBook</Label>
              <Select value={String(form.royalty_rate_ebook)} onValueChange={(v) => setForm({ ...form, royalty_rate_ebook: Number(v) })}>
                <SelectTrigger className="rounded-md mt-1" data-testid="kdp-royalty-ebook"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {ROYALTY_EBOOK.map((r) => (
                    <SelectItem key={r.value} value={String(r.value)}>{r.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {form.royalty_rate_ebook === 70 && (
              <div>
                <Label className="text-xs flex items-center gap-1">
                  Tamaño archivo (MB)
                  <InfoTooltip content="Solo se aplica con regalía 70%. El coste de entrega es ceil(MB) × 0.12." />
                </Label>
                <Input
                  type="number" min={0} step={0.1}
                  value={form.tamano_mb}
                  onChange={(e) => setForm({ ...form, tamano_mb: e.target.value })}
                  placeholder="ej. 2.3"
                  className="rounded-md mt-1 num"
                  data-testid="kdp-tamano-mb"
                />
              </div>
            )}
          </>
        )}
        {isSpain && (
          <div>
            <Label className="text-xs">IVA (solo ES)</Label>
            <Select value={String(form.iva_type ?? "")} onValueChange={(v) => setForm({ ...form, iva_type: v })}>
              <SelectTrigger className="rounded-md mt-1" data-testid="kdp-iva-type"><SelectValue placeholder="4% / 21%" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="4">4% (libro físico/eBook estándar)</SelectItem>
                <SelectItem value="21">21%</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}
        <div>
          <Label className="text-xs flex items-center gap-1">
            CPC de referencia ({sym})
            <InfoTooltip content="CPC de referencia del nicho; se usa para calcular los Clicks PE base antes de tener datos reales de Ads. Cuando importes reportes, la app priorizará el CPC real." />
          </Label>
          <Input
            type="number" min={0} step={0.01}
            value={form.cpc_referencia}
            onChange={(e) => setForm({ ...form, cpc_referencia: e.target.value })}
            placeholder="ej. 0.45"
            className="rounded-md mt-1 num"
            data-testid="kdp-cpc-ref"
          />
        </div>
        <div>
          <Label className="text-xs">Margen objetivo (%)</Label>
          <Input
            type="number" min={1} max={70} step={1}
            value={form.margen_objetivo_pct}
            onChange={(e) => setForm({ ...form, margen_objetivo_pct: e.target.value })}
            className="rounded-md mt-1 num"
            data-testid="kdp-margen-objetivo"
          />
        </div>
      </div>

      <div className="flex items-center gap-2 pt-1">
        <Button onClick={handleSave} disabled={saving} className="rounded-md bg-coral hover:bg-coral-500 text-white" data-testid="save-kdp-btn">
          {saving ? <Loader2 className="size-4 animate-spin mr-2" /> : <Save className="size-4 mr-2" />}
          Guardar y recalcular
        </Button>
        {loading && <span className="text-xs text-muted-foreground inline-flex items-center gap-1"><Loader2 className="size-3 animate-spin" /> Calculando…</span>}
      </div>

      {/* ===== Outputs ===== */}
      {diag && (
        <div className="border-t border-border pt-5 space-y-4" data-testid="kdp-diagnosis">
          {diag.error && (
            <div className="border border-destructive/40 bg-destructive/5 p-3 rounded-md text-sm flex items-start gap-2">
              <AlertTriangle className="size-4 text-destructive mt-0.5" />
              <span>{diag.error}</span>
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MetricBox label="Regalía neta" value={fmtNum(o.regalia_neta, 2, sym)} accent="text-coral" tooltip="regalia_neta" testid="out-regalia" />
            <MetricBox label="ACoS de equilibrio" value={o.acos_pe == null ? "—" : `${fmtNum(o.acos_pe, 2)}%`} accent="text-coral" tooltip="acos_eq" testid="out-acos-pe" />
            <MetricBox label="CPC máx rentable" value={fmtNum(o.cpc_max_rentable, 2, sym)} tooltip="CPC máximo orientativo = regalía / 10. Umbral del mínimo de 10 clicks por venta." testid="out-cpc-max" />
            <MetricBox label="Clicks PE base" value={fmtNum(o.clicks_pe_base, 2)} tooltip="clicks_pe" testid="out-clicks-pe" />
            {!legacyMode && (
              <>
                <MetricBox label="Precio sin IVA" value={fmtNum(o.precio_sin_iva, 2, sym)} testid="out-precio-sin-iva" />
                <MetricBox label="Coste impresión" value={fmtNum(o.coste_impresion, 2, sym)} testid="out-coste-impresion" />
                <MetricBox label="% Regalía aplicada" value={o.royalty_rate_used_pct == null ? "—" : `${o.royalty_rate_used_pct}%`} testid="out-royalty-rate" />
                <MetricBox label="PVP mínimo" value={fmtNum(o.pvp_minimo_recomendado, 2, sym)} tooltip="pvp_minimo" testid="out-pvp-minimo" />
              </>
            )}
          </div>

          {d && (
            <div className="grid md:grid-cols-[1fr_1fr] gap-3">
              <div className="border border-border rounded-md p-4 bg-background space-y-2" data-testid="kdp-score-block">
                <div className="flex items-center justify-between">
                  <div className="text-xs uppercase tracking-widest text-muted-foreground font-semibold flex items-center gap-1.5">
                    <Target className="size-3.5" /> Score económico
                    <InfoTooltip content="score_economico" />
                  </div>
                  <Badge className="text-lg px-3 py-0.5 bg-coral hover:bg-coral text-white num" data-testid="kdp-score-total">{d.score_total}</Badge>
                </div>
                <div className="space-y-1.5">
                  {Object.entries(d.score_breakdown).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between text-xs">
                      <span className="capitalize">{k.replace(/_/g, " ")}</span>
                      <span className="num font-semibold">{v.points}/{v.max}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="border border-border rounded-md p-4 bg-background space-y-3" data-testid="kdp-diagnosis-block">
                <div className="text-xs uppercase tracking-widest text-muted-foreground font-semibold flex items-center gap-1.5">
                  <TrendingUp className="size-3.5" /> Diagnóstico
                </div>
                <div className="flex flex-wrap gap-2">
                  {risk && (
                    <span className={`badge-pill inline-flex items-center gap-1 ${risk.cls}`} data-testid="risk-level-badge">
                      <risk.icon className="size-3" /> {risk.label}
                    </span>
                  )}
                  {viab && (
                    <Badge className={`${viab.cls} rounded-md`} data-testid="viability-badge">{viab.label}</Badge>
                  )}
                </div>
                <div className="text-xs space-y-1">
                  <div>Clicks: <span className="font-semibold">{d.labels?.clicks}</span></div>
                  <div>Margen: <span className="font-semibold">{d.labels?.margen}</span></div>
                  <div>PVP: <span className="font-semibold">{d.labels?.pvp}</span></div>
                </div>
              </div>
            </div>
          )}

          {diag.notes && diag.notes.length > 0 && (
            <div className="text-[11px] text-muted-foreground italic border-t border-border pt-2">
              {diag.notes[0]}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MetricBox({ label, value, tooltip, accent, testid }) {
  return (
    <div className="border border-border rounded-md bg-background p-3" data-testid={testid}>
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold flex items-center gap-1">
        {label} {tooltip && <InfoTooltip content={tooltip} />}
      </div>
      <div className={`num text-lg font-semibold mt-0.5 ${accent || ""}`}>{value}</div>
    </div>
  );
}
