import { useEffect, useMemo, useState } from "react";
import { getKeywordsUnified, upsertKeyword, exportNegativesUrl } from "../lib/api";
import { useData } from "../context/DataContext";
import { Input } from "./ui/input";
import { Switch } from "./ui/switch";
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import { fmtInt, fmtPct, fmtMoney, getMarketplace } from "../lib/format";
import { ArrowDownUp, AlertCircle, Plus, MoreHorizontal, Check, X, Pencil, Download } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import KeywordDetailSheet from "./KeywordDetailSheet";
import AddKeywordWizard from "./AddKeywordWizard";
import AddCampaignWizard from "./AddCampaignWizard";
import { InfoTooltip } from "./InfoTooltip";
import { toast } from "sonner";

const BADGE_STYLES = {
  "bajo-pe": { cls: "bg-green-100 text-green-700 border-green-200 dark:bg-green-500/10 dark:text-green-400 dark:border-green-500/30", label: "Bajo PE", tip: "badge_bajo_pe" },
  "recuperable": { cls: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/30", label: "Recuperable", tip: "badge_recuperable" },
  "en-perdida": { cls: "bg-red-100 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/30", label: "En pérdida", tip: "badge_en_perdida" },
  "sin-datos": { cls: "bg-neutral-100 text-neutral-600 border-neutral-200 dark:bg-neutral-700/40 dark:text-neutral-400 dark:border-neutral-600", label: "Sin datos", tip: "badge_sin_datos" },
};

const editableKeys = new Set(["clicks", "impressions", "cpc", "spend", "orders", "sales"]);

const cols = [
  { k: "term", label: "Término" },
  { k: "campaign", label: "Campaña" },
  { k: "match_type", label: "Match" },
  { k: "impressions", label: "Impr." },
  { k: "clicks", label: "Clicks" },
  { k: "ctr", label: "CTR", tip: "ctr" },
  { k: "cpc", label: "CPC", tip: "cpc" },
  { k: "spend", label: "Gasto" },
  { k: "sales", label: "Ventas" },
  { k: "orders", label: "Ped." },
  { k: "cvr", label: "CVR", tip: "cvr" },
  { k: "acos_actual", label: "ACoS", tip: "acos" },
  { k: "acos_siguiente", label: "ACoS +1", tip: "acos_siguiente" },
  { k: "beneficio_ahora", label: "Beneficio", tip: "beneficio_ahora" },
  { k: "badge", label: "Estado" },
  { k: "_act", label: "" },
];

function EditableText({ value, onSave, testid, placeholder = "" }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(value || "");
  useEffect(() => setVal(value || ""), [value]);
  if (!editing) {
    return (
      <span
        onDoubleClick={() => setEditing(true)}
        className="cursor-text hover:text-coral transition-colors inline-block max-w-[180px] truncate"
        title="Doble click para editar"
        data-testid={testid}
      >
        {value || <span className="text-muted-foreground italic">{placeholder || "—"}</span>}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1">
      <Input
        autoFocus
        className="h-7 w-40 rounded-sm px-1"
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") { onSave(val); setEditing(false); }
          if (e.key === "Escape") { setEditing(false); setVal(value || ""); }
        }}
      />
      <button onClick={() => { onSave(val); setEditing(false); }} className="text-green-600">
        <Check className="size-3.5" />
      </button>
      <button onClick={() => { setEditing(false); setVal(value || ""); }} className="text-muted-foreground">
        <X className="size-3.5" />
      </button>
    </span>
  );
}

function EditableCell({ value, onSave, integer = false, testid }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(value ?? 0);
  useEffect(() => setVal(value ?? 0), [value]);
  if (!editing) {
    return (
      <span
        onDoubleClick={() => setEditing(true)}
        className="cursor-text hover:text-coral transition-colors"
        title="Doble click para editar"
        data-testid={testid}
      >
        {integer
          ? (Number(value) || 0).toLocaleString("es-ES", { maximumFractionDigits: 0 })
          : (Number(value) || 0).toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1">
      <Input
        autoFocus
        type="number"
        min={0}
        step={integer ? 1 : 0.01}
        className="h-7 w-24 rounded-sm num text-right px-1"
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") { onSave(integer ? Math.round(Number(val) || 0) : Number(val) || 0); setEditing(false); }
          if (e.key === "Escape") { setEditing(false); setVal(value ?? 0); }
        }}
      />
      <button onClick={() => { onSave(integer ? Math.round(Number(val) || 0) : Number(val) || 0); setEditing(false); }} className="text-green-600 hover:text-green-700">
        <Check className="size-3.5" />
      </button>
      <button onClick={() => { setEditing(false); setVal(value ?? 0); }} className="text-muted-foreground hover:text-destructive">
        <X className="size-3.5" />
      </button>
    </span>
  );
}

export default function KeywordsUnified({ datasetId }) {
  const { marketplace, active, loadActive } = useData();
  const sym = getMarketplace(marketplace).symbol;
  const location = useLocation();
  const [data, setData] = useState(null);
  const [q, setQ] = useState("");
  const [filterBadge, setFilterBadge] = useState(location.state?.filterBadge || null);
  const [sortKey, setSortKey] = useState("spend");
  const [sortDir, setSortDir] = useState("desc");
  const [selectedTerm, setSelectedTerm] = useState(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [wizKw, setWizKw] = useState(false);
  const [wizCamp, setWizCamp] = useState(false);

  const load = async () => {
    if (!datasetId) return;
    const r = await getKeywordsUnified(datasetId);
    setData(r.data);
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [datasetId, active?.book_economy?.precio_libro, active?.book_economy?.regalias_por_venta]);

  useEffect(() => {
    if (location.state?.filterBadge) setFilterBadge(location.state.filterBadge);
  }, [location.state]);

  const rows = useMemo(() => {
    if (!data) return [];
    let arr = data.rows.filter((r) => (r.term || "").toLowerCase().includes(q.toLowerCase()));
    if (filterBadge) arr = arr.filter((r) => r.badge === filterBadge);
    arr.sort((a, b) => {
      const av = a[sortKey] ?? 0; const bv = b[sortKey] ?? 0;
      if (typeof av === "number" || typeof bv === "number") {
        return sortDir === "asc" ? (av ?? 0) - (bv ?? 0) : (bv ?? 0) - (av ?? 0);
      }
      return sortDir === "asc"
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
    return arr;
  }, [data, q, filterBadge, sortKey, sortDir]);

  const toggleSort = (k) => {
    if (sortKey === k) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortKey(k); setSortDir("desc"); }
  };

  const pe = data?.acos_equilibrio;
  const acosColor = (v) =>
    v == null ? "" : pe == null ? "" : v <= pe ? "text-green-600 dark:text-green-400" : "text-destructive";

  const saveCell = async (term, field, value) => {
    try {
      await upsertKeyword(datasetId, { term, [field]: value });
      toast.success(`${field} actualizado`);
      await load();
      await loadActive(datasetId);
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    }
  };

  const saveCellWithAutoSpend = async (term, field, value, otherValue) => {
    try {
      const payload = { term, [field]: value };
      // Recalculate spend automatically if we have both clicks and cpc
      const clicks = field === "clicks" ? value : Number(otherValue) || 0;
      const cpc = field === "cpc" ? value : Number(otherValue) || 0;
      if (clicks && cpc) payload.spend = Number((clicks * cpc).toFixed(2));
      await upsertKeyword(datasetId, payload);
      toast.success(`${field} actualizado (gasto recalculado)`);
      await load();
      await loadActive(datasetId);
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    }
  };

  const openDetail = (term) => { setSelectedTerm(term); setSheetOpen(true); };

  return (
    <div className="space-y-4 animate-fade-in" data-testid="keywords-unified">
      {pe == null && (
        <div className="border border-amber-300 dark:border-amber-500/40 bg-amber-50 dark:bg-amber-500/5 p-3 rounded-md flex items-start gap-2 text-sm" data-testid="pe-warning">
          <AlertCircle className="size-4 mt-0.5 text-amber-600 dark:text-amber-400" />
          <div>
            Configura el <Link to="/book" className="text-coral underline">precio y regalías</Link> para calcular el ACoS de Equilibrio y el ACoS del siguiente click.
          </div>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3 justify-between">
        <div className="flex items-center gap-2 flex-wrap">
          <Input
            placeholder="Buscar keyword…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="max-w-xs rounded-md"
            data-testid="kw-filter"
          />
          {filterBadge && (
            <Button
              variant="outline"
              size="sm"
              className="rounded-md"
              onClick={() => setFilterBadge(null)}
              data-testid="clear-badge-filter"
            >
              <X className="size-3.5 mr-1" /> {BADGE_STYLES[filterBadge]?.label}
            </Button>
          )}
        </div>
        <div className="flex items-center gap-3">
          {pe != null && (
            <div className="text-xs flex items-center gap-1">
              <span className="text-muted-foreground">PE:</span>
              <span className="num font-semibold text-coral">{fmtPct(pe)}</span>
              <InfoTooltip content="pe" />
            </div>
          )}
          <span className="text-xs text-muted-foreground num">{rows.length} keywords</span>
          <Button onClick={() => setWizCamp(true)} variant="outline" size="sm" className="rounded-md" data-testid="open-camp-wizard">
            <Plus className="size-3.5 mr-1" /> Campaña
          </Button>
          <Button onClick={() => setWizKw(true)} size="sm" className="rounded-md bg-coral hover:bg-coral-500 text-white" data-testid="open-kw-wizard">
            <Plus className="size-3.5 mr-1" /> Keyword
          </Button>
          <Button asChild variant="outline" size="sm" className="rounded-md" data-testid="export-negatives-btn">
            <a href={exportNegativesUrl(datasetId, 6)} download>
              <Download className="size-3.5 mr-1" /> Negativas CSV
            </a>
          </Button>
        </div>
      </div>

      <div className="border border-border rounded-lg overflow-x-auto bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              {cols.map((c) => (
                <th
                  key={c.k}
                  onClick={() => c.k !== "_act" && c.k !== "badge" && toggleSort(c.k)}
                  className={`text-left px-3 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold ${c.k !== "_act" ? "cursor-pointer hover:text-foreground" : ""} select-none whitespace-nowrap`}
                  data-testid={`kw-col-${c.k}`}
                >
                  <span className="inline-flex items-center gap-1">
                    {c.label}
                    {c.tip && <InfoTooltip content={c.tip} />}
                    {c.k !== "_act" && c.k !== "badge" && c.k !== "term" && <ArrowDownUp className="size-3 opacity-40" />}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const b = BADGE_STYLES[r.badge] || BADGE_STYLES["sin-datos"];
              return (
                <tr key={i} className={`border-t border-border hover:bg-muted/30 ${r.is_manual ? "bg-coral/5" : ""}`} data-testid={`kw-row-${i}`}>
                  <td className="px-3 py-2 max-w-[240px]">
                    <button
                      onClick={() => openDetail(r.term)}
                      className="text-left hover:text-coral font-medium truncate block w-full"
                      data-testid={`kw-term-${i}`}
                    >
                      {r.term}
                    </button>
                  </td>
                  <td className="px-3 py-2">
                    <EditableText value={r.campaign} onSave={(v) => saveCell(r.term, "campaign", v)} testid={`edit-campaign-${i}`} placeholder="sin campaña" />
                  </td>
                  <td className="px-3 py-2">
                    <EditableText value={r.match_type} onSave={(v) => saveCell(r.term, "match_type", v)} testid={`edit-match-${i}`} placeholder="—" />
                  </td>
                  <td className="px-3 py-2 num text-right">
                    <EditableCell value={r.impressions} integer onSave={(v) => saveCell(r.term, "impressions", v)} testid={`edit-impr-${i}`} />
                  </td>
                  <td className="px-3 py-2 num text-right">
                    <EditableCell value={r.clicks} integer onSave={(v) => saveCellWithAutoSpend(r.term, "clicks", v, r.cpc)} testid={`edit-clicks-${i}`} />
                  </td>
                  <td className="px-3 py-2 num text-right">{fmtPct(r.ctr)}</td>
                  <td className="px-3 py-2 num text-right">
                    <EditableCell value={r.cpc} onSave={(v) => saveCellWithAutoSpend(r.term, "cpc", v, r.clicks)} testid={`edit-cpc-${i}`} />
                  </td>
                  <td className="px-3 py-2 num text-right">
                    <EditableCell value={r.spend} onSave={(v) => saveCell(r.term, "spend", v)} testid={`edit-spend-${i}`} />
                  </td>
                  <td className="px-3 py-2 num text-right">
                    <EditableCell value={r.sales} onSave={(v) => saveCell(r.term, "sales", v)} testid={`edit-sales-${i}`} />
                  </td>
                  <td className="px-3 py-2 num text-right">
                    <EditableCell value={r.orders} integer onSave={(v) => saveCell(r.term, "orders", v)} testid={`edit-orders-${i}`} />
                  </td>
                  <td className="px-3 py-2 num text-right">{fmtPct(r.cvr)}</td>
                  <td className={`px-3 py-2 num text-right ${acosColor(r.acos_actual)}`}>
                    {r.acos_actual == null ? "—" : fmtPct(r.acos_actual)}
                  </td>
                  <td className={`px-3 py-2 num text-right ${acosColor(r.acos_siguiente)}`} data-testid={`kw-acos-next-${i}`}>
                    {r.acos_siguiente == null ? "—" : fmtPct(r.acos_siguiente)}
                  </td>
                  <td className={`px-3 py-2 num text-right ${r.beneficio_ahora != null && r.beneficio_ahora < 0 ? "text-destructive" : ""}`}>
                    {r.beneficio_ahora == null ? "—" : fmtMoney(r.beneficio_ahora, sym)}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`badge-pill ${b.cls}`} data-testid={`kw-badge-${i}`}>
                      {b.label}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => openDetail(r.term)} data-testid={`kw-detail-${i}`}>
                      <MoreHorizontal className="size-4" />
                    </Button>
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={cols.length} className="px-3 py-10 text-center text-sm text-muted-foreground">
                  Sin keywords para mostrar
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="text-[11px] text-muted-foreground flex items-center gap-1.5">
        <Pencil className="size-3" /> Doble click en cualquier celda editable para modificar el valor.
      </p>

      <KeywordDetailSheet
        open={sheetOpen}
        onClose={() => { setSheetOpen(false); load(); }}
        term={selectedTerm}
      />
      <AddKeywordWizard open={wizKw} onOpenChange={setWizKw} onCreated={load} />
      <AddCampaignWizard open={wizCamp} onOpenChange={setWizCamp} onCreated={load} />
    </div>
  );
}
