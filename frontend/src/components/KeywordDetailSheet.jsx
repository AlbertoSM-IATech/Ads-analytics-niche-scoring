import { useEffect, useState } from "react";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter,
} from "./ui/sheet";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Camera, Save, Trash2, Loader2 } from "lucide-react";
import {
  getKeywordDetail, snapshotAll, getSnapshots,
  upsertKeyword, deleteKeywordOverride,
} from "../lib/api";
import { useData } from "../context/DataContext";
import { toast } from "sonner";
import { fmtInt, fmtPct, fmtMoney, getMarketplace } from "../lib/format";
import { InfoTooltip } from "./InfoTooltip";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
} from "recharts";

const BADGE_STYLES = {
  "bajo-pe": "bg-green-100 text-green-700 border-green-200 dark:bg-green-500/10 dark:text-green-400 dark:border-green-500/30",
  "recuperable": "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/30",
  "en-perdida": "bg-red-100 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/30",
  "sin-datos": "bg-neutral-100 text-neutral-600 border-neutral-200 dark:bg-neutral-700/40 dark:text-neutral-400 dark:border-neutral-600",
};
const BADGE_LABEL = {
  "bajo-pe": "Bajo PE",
  "recuperable": "Recuperable",
  "en-perdida": "En pérdida",
  "sin-datos": "Sin datos",
};

function Metric({ label, value, tooltip, accent }) {
  return (
    <div className="border border-border rounded-md p-3 bg-card">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
        {label} {tooltip && <InfoTooltip content={tooltip} />}
      </div>
      <div className={`num text-lg font-semibold mt-1 ${accent || ""}`}>{value}</div>
    </div>
  );
}

export default function KeywordDetailSheet({ open, onClose, term }) {
  const { active, marketplace, loadActive } = useData();
  const sym = getMarketplace(marketplace).symbol;
  const [detail, setDetail] = useState(null);
  const [snaps, setSnaps] = useState([]);
  const [loading, setLoading] = useState(false);
  const [snapshotting, setSnapshotting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(null);

  useEffect(() => {
    if (!open || !term || !active) return;
    setLoading(true);
    getKeywordDetail(active.id, term)
      .then(async (r) => {
        setDetail(r.data);
        setForm({
          clicks: r.data.metrics.clicks || 0,
          cpc: r.data.metrics.cpc || 0,
          spend: r.data.metrics.spend || 0,
          sales: r.data.metrics.sales || 0,
          orders: r.data.metrics.orders || 0,
          impressions: r.data.metrics.impressions || 0,
          campaign: r.data.metrics.campaign || "",
          match_type: r.data.metrics.match_type || "",
          notes: r.data.metrics.notes || "",
        });
        // load snapshots
        const s = await getSnapshots(active.id, term);
        setSnaps(s.data.snapshots || []);
        // auto-snapshot once per day
        const lastKey = `snap_${active.id}_today`;
        const today = new Date().toISOString().slice(0, 10);
        if (localStorage.getItem(lastKey) !== today) {
          try {
            await snapshotAll(active.id);
            localStorage.setItem(lastKey, today);
            const s2 = await getSnapshots(active.id, term);
            setSnaps(s2.data.snapshots || []);
          } catch (_) {}
        }
      })
      .finally(() => setLoading(false));
  }, [open, term, active]);

  const m = detail?.metrics;
  const pe = detail?.acos_equilibrio;
  const acosColor = (v) =>
    v == null ? "" : pe == null ? "" : v <= pe ? "text-green-600 dark:text-green-400" : "text-destructive";

  const handleSnapshot = async () => {
    if (!active || !term) return;
    setSnapshotting(true);
    try {
      await snapshotAll(active.id);
      const s = await getSnapshots(active.id, term);
      setSnaps(s.data.snapshots || []);
      toast.success("Snapshot guardado");
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    } finally {
      setSnapshotting(false);
    }
  };

  const handleSave = async () => {
    if (!active || !term || !form) return;
    setSaving(true);
    try {
      await upsertKeyword(active.id, {
        term,
        clicks: Number(form.clicks) || 0,
        cpc: Number(form.cpc) || 0,
        spend: Number(form.spend) || 0,
        sales: Number(form.sales) || 0,
        orders: Number(form.orders) || 0,
        impressions: Number(form.impressions) || 0,
        campaign: form.campaign || null,
        match_type: form.match_type || null,
        notes: form.notes || "",
      });
      toast.success("Keyword actualizada");
      await loadActive(active.id);
      const r = await getKeywordDetail(active.id, term);
      setDetail(r.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteOverride = async () => {
    if (!active || !term) return;
    try {
      await deleteKeywordOverride(active.id, term);
      toast.success("Ajuste manual eliminado");
      await loadActive(active.id);
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    }
  };

  const chartData = snaps.map((s) => ({
    date: (s.ts || "").slice(5, 10),
    acos: s.acos_actual ?? 0,
    acos_next: s.acos_siguiente ?? 0,
    spend: s.spend || 0,
    sales: s.sales || 0,
  }));

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-xl overflow-y-auto"
        data-testid="kw-detail-sheet"
      >
        <SheetHeader>
          <div className="flex items-center gap-2">
            <SheetTitle className="font-heading text-xl">{term}</SheetTitle>
            {m?.badge && (
              <span className={`badge-pill ${BADGE_STYLES[m.badge]}`} data-testid="detail-badge">
                {BADGE_LABEL[m.badge]}
              </span>
            )}
            {m?.is_manual && (
              <span className="badge-pill border-coral/40 bg-coral/10 text-coral-700 dark:text-coral-400">
                Manual
              </span>
            )}
          </div>
          <SheetDescription>
            {m?.campaign ? `Campaña: ${m.campaign}` : "Sin campaña asignada"}
            {m?.match_type ? ` · ${m.match_type}` : ""}
            {m?.underlying_rows ? ` · ${m.underlying_rows} filas base` : ""}
          </SheetDescription>
        </SheetHeader>

        {loading || !m ? (
          <div className="py-12 flex justify-center"><Loader2 className="size-6 animate-spin text-coral" /></div>
        ) : (
          <div className="space-y-5 mt-5">
            {/* KPI grid */}
            <div className="grid grid-cols-3 gap-2">
              <Metric label="Impr." value={fmtInt(m.impressions)} />
              <Metric label="Clicks" value={fmtInt(m.clicks)} />
              <Metric label="CTR" value={fmtPct(m.ctr)} tooltip="ctr" />
              <Metric label="CPC" value={fmtMoney(m.cpc, sym)} tooltip="cpc" />
              <Metric label="Gasto" value={fmtMoney(m.spend, sym)} />
              <Metric label="Ventas" value={fmtMoney(m.sales, sym)} />
              <Metric label="Pedidos" value={fmtInt(m.orders)} />
              <Metric label="CVR" value={fmtPct(m.cvr)} tooltip="cvr" />
              <Metric label="ROAS" value={(m.roas ?? 0).toFixed(2)} tooltip="roas" />
              <Metric label="ACoS" value={m.acos_actual == null ? "—" : fmtPct(m.acos_actual)} accent={acosColor(m.acos_actual)} tooltip="acos" />
              <Metric
                label="ACoS +1 click"
                value={m.acos_siguiente == null ? "—" : fmtPct(m.acos_siguiente)}
                accent={acosColor(m.acos_siguiente)}
                tooltip="acos_siguiente"
              />
              <Metric
                label="Beneficio"
                value={m.beneficio_ahora == null ? "—" : fmtMoney(m.beneficio_ahora, sym)}
                accent={m.beneficio_ahora != null && m.beneficio_ahora < 0 ? "text-destructive" : ""}
                tooltip="beneficio_ahora"
              />
            </div>

            {/* Snapshots chart */}
            <div className="border border-border rounded-md bg-card p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold">Evolución</h3>
                  <InfoTooltip content="Snapshots automáticos diarios + manuales. Se capturan los valores agregados de la keyword para ver tendencias." />
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleSnapshot}
                  disabled={snapshotting}
                  className="rounded-md"
                  data-testid="snapshot-btn"
                >
                  {snapshotting ? <Loader2 className="size-3.5 animate-spin" /> : <Camera className="size-3.5" />}
                  <span className="ml-1.5 text-xs">Snapshot</span>
                </Button>
              </div>
              {chartData.length > 1 ? (
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart data={chartData}>
                    <CartesianGrid stroke="hsl(var(--border))" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} axisLine={{ stroke: "hsl(var(--border))" }} tickLine={false} />
                    <YAxis tick={{ fontSize: 10 }} axisLine={{ stroke: "hsl(var(--border))" }} tickLine={false} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 11 }} />
                    <Line type="monotone" dataKey="acos" name="ACoS" stroke="#FB923C" strokeWidth={2} dot={{ r: 2 }} />
                    <Line type="monotone" dataKey="acos_next" name="ACoS +1" stroke="#3B82F6" strokeWidth={2} dot={{ r: 2 }} strokeDasharray="3 3" />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-xs text-muted-foreground text-center py-6" data-testid="no-snapshots">
                  {chartData.length === 0
                    ? "Aún no hay snapshots. Vuelve mañana o genera uno ahora."
                    : "Se necesita al menos 2 snapshots para ver la evolución."}
                </div>
              )}
            </div>

            {/* Edit form */}
            <div className="border border-border rounded-md bg-card p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">Edición manual</h3>
                {m.is_manual && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-destructive"
                    onClick={handleDeleteOverride}
                    data-testid="delete-override-btn"
                  >
                    <Trash2 className="size-3.5" />
                    <span className="ml-1 text-xs">Quitar ajuste</span>
                  </Button>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  ["clicks", "Clicks"],
                  ["impressions", "Impresiones"],
                  ["cpc", "CPC"],
                  ["spend", "Gasto"],
                  ["orders", "Pedidos"],
                  ["sales", "Ventas"],
                ].map(([k, label]) => (
                  <div key={k}>
                    <Label className="text-xs">{label}</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={form?.[k] ?? 0}
                      onChange={(e) => setForm({ ...form, [k]: e.target.value })}
                      className="rounded-md mt-1 num"
                      data-testid={`edit-${k}`}
                    />
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Campaña</Label>
                  <Input
                    value={form?.campaign || ""}
                    onChange={(e) => setForm({ ...form, campaign: e.target.value })}
                    className="rounded-md mt-1"
                    data-testid="edit-campaign"
                  />
                </div>
                <div>
                  <Label className="text-xs">Match type</Label>
                  <Input
                    value={form?.match_type || ""}
                    onChange={(e) => setForm({ ...form, match_type: e.target.value })}
                    placeholder="broad / phrase / exact"
                    className="rounded-md mt-1"
                    data-testid="edit-match-type"
                  />
                </div>
              </div>
              <div>
                <Label className="text-xs">Notas</Label>
                <Textarea
                  value={form?.notes || ""}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  className="rounded-md mt-1"
                  rows={2}
                  data-testid="edit-notes"
                />
              </div>
            </div>
          </div>
        )}

        <SheetFooter className="mt-4">
          <Button
            onClick={handleSave}
            disabled={saving || !form}
            className="w-full rounded-md bg-coral hover:bg-coral-500 text-white"
            data-testid="save-kw-btn"
          >
            {saving ? <Loader2 className="size-4 animate-spin mr-2" /> : <Save className="size-4 mr-2" />}
            Guardar cambios
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
