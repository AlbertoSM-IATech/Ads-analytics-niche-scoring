import { useEffect, useMemo, useState } from "react";
import { getKeywordsUnified, upsertKeyword, exportNegativesUrl, getCampaignsList, getRecommendations } from "../lib/api";
import { useData } from "../context/DataContext";
import { Input } from "./ui/input";
import { Switch } from "./ui/switch";
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { fmtInt, fmtPct, fmtMoney, getMarketplace } from "../lib/format";
import { ArrowDownUp, AlertCircle, Plus, MoreHorizontal, Check, X, Pencil, Download, Ban, Filter } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import KeywordDetailSheet from "./KeywordDetailSheet";
import AddKeywordWizard from "./AddKeywordWizard";
import AddCampaignWizard from "./AddCampaignWizard";
import MultiCampaignCell from "./MultiCampaignCell";
import { InfoTooltip } from "./InfoTooltip";
import { getRelevanceDot } from "../lib/relevance";
import { mapRecommendationsByTerm, findRecForRow, ACTION_LABELS } from "../lib/recommendations";
import { RecommendationBadge } from "./RecommendationBadge";
import { toast } from "sonner";

const BADGE_STYLES = {
  "bajo-pe": { cls: "bg-green-100 text-green-700 border-green-200 dark:bg-green-500/10 dark:text-green-400 dark:border-green-500/30", label: "Bajo PE", tip: "badge_bajo_pe" },
  "recuperable": { cls: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/30", label: "Recuperable", tip: "badge_recuperable" },
  "en-perdida": { cls: "bg-red-100 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/30", label: "En pérdida", tip: "badge_en_perdida" },
  "sin-datos": { cls: "bg-neutral-100 text-neutral-600 border-neutral-200 dark:bg-neutral-700/40 dark:text-neutral-400 dark:border-neutral-600", label: "Sin datos", tip: "badge_sin_datos" },
};

// Phase UX-2.4 — compact "decision-first" column set. Heavy operational fields
// (impressions/clicks/cpc/spend/sales/orders/ctr/cvr/badges/notes) now live in
// the side panel only.
const cols = [
  { k: "term", label: "Término" },
  { k: "campaign", label: "Campañas" },
  { k: "match_type", label: "Match" },
  { k: "acos_actual", label: "ACoS", tip: "acos" },
  { k: "acos_siguiente", label: "ACoS +1", tip: "acos_siguiente" },
  { k: "clicks_pe", label: "Clicks PE", tip: "clicks_pe" },
  { k: "consumo_fase", label: "Estado", tip: "consumo_fase" },
  { k: "beneficio_kdp", label: "Beneficio KDP", tip: "beneficio_kdp" },
  { k: "_act", label: "" },
];

const ALL = "__all__";
const ACTION_OPTIONS = [
  "WAIT_FOR_DATA", "OBSERVE", "LOWER_BID", "HOLD", "SCALE",
  "MOVE_TO_EXACT", "NEGATIVE_EXACT_CANDIDATE", "NEGATIVE_PHRASE_CANDIDATE",
  "REVIEW_CAMPAIGN", "PAUSE_TARGET",
];
const RELEVANCE_OPTIONS = ["unreviewed", "high", "medium", "low"];
const RELEVANCE_LABEL = { unreviewed: "Sin revisar", high: "Alta", medium: "Media", low: "Baja" };
const MATCH_OPTIONS = ["exact", "phrase", "broad", "auto", "asin", "category"];

// Color for "Consumo fase": <50% verde, 50-80% amber, 80-100% naranja, >100% rojo.
function consumoFaseClass(v) {
  if (v == null) return "text-muted-foreground/40";
  if (v < 0.5) return "text-green-600 dark:text-green-400";
  if (v < 0.8) return "text-amber-600 dark:text-amber-400";
  if (v <= 1.0) return "text-orange-600 dark:text-orange-400";
  return "text-red-600 dark:text-red-400 font-semibold";
}

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
  const [allCampaigns, setAllCampaigns] = useState([]);
  const [recsMap, setRecsMap] = useState(new Map());
  const [q, setQ] = useState("");
  const [filterBadge, setFilterBadge] = useState(location.state?.filterBadge || null);
  const [onlyNegatives, setOnlyNegatives] = useState(false);
  // Phase UX-2.5 — extra filters
  const [fActionType, setFActionType] = useState("");
  const [fRelevance, setFRelevance] = useState("");
  const [fCampaign, setFCampaign] = useState("");
  const [fMatch, setFMatch] = useState("");
  const [fOnlyWithOrders, setFOnlyWithOrders] = useState(false);
  const [fOnlyWithoutOrders, setFOnlyWithoutOrders] = useState(false);
  const [fOnlyNegativeProfit, setFOnlyNegativeProfit] = useState(false);
  const [fOnlyConsumoOver100, setFOnlyConsumoOver100] = useState(false);
  const [sortKey, setSortKey] = useState("spend");
  const [sortDir, setSortDir] = useState("desc");
  const [selectedTerm, setSelectedTerm] = useState(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [wizKw, setWizKw] = useState(false);
  const [wizCamp, setWizCamp] = useState(false);

  const load = async () => {
    if (!datasetId) return;
    const [r, c] = await Promise.all([
      getKeywordsUnified(datasetId),
      getCampaignsList(datasetId).catch(() => ({ data: [] })),
    ]);
    setData(r.data);
    setAllCampaigns(Array.isArray(c.data) ? c.data : []);
    // Recommendations are decorative — load asynchronously, never block the table.
    getRecommendations(datasetId)
      .then((rec) => setRecsMap(mapRecommendationsByTerm(rec.data?.recommendations || [])))
      .catch(() => setRecsMap(new Map()));
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [datasetId, active?.book_economy?.precio_libro, active?.book_economy?.regalias_por_venta]);

  useEffect(() => {
    if (location.state?.filterBadge) setFilterBadge(location.state.filterBadge);
  }, [location.state]);

  const rows = useMemo(() => {
    if (!data) return [];
    let arr = data.rows.filter((r) => (r.term || "").toLowerCase().includes(q.toLowerCase()));
    if (filterBadge) arr = arr.filter((r) => r.badge === filterBadge);
    if (onlyNegatives) arr = arr.filter((r) => r.suggest_negative);
    // Phase UX-2.5 — extra filters
    if (fActionType) {
      arr = arr.filter((r) => {
        const rec = findRecForRow(recsMap, r);
        return rec && rec.action_type === fActionType;
      });
    }
    if (fRelevance) arr = arr.filter((r) => (r.relevance || "unreviewed") === fRelevance);
    if (fCampaign) {
      arr = arr.filter((r) =>
        (r.campaigns && r.campaigns.includes(fCampaign)) || r.campaign === fCampaign
      );
    }
    if (fMatch) arr = arr.filter((r) => (r.match_type || "").toLowerCase() === fMatch);
    if (fOnlyWithOrders) arr = arr.filter((r) => (r.orders || 0) > 0);
    if (fOnlyWithoutOrders) arr = arr.filter((r) => (r.orders || 0) === 0);
    if (fOnlyNegativeProfit) {
      arr = arr.filter((r) => r.beneficio_kdp != null && r.beneficio_kdp < 0);
    }
    if (fOnlyConsumoOver100) {
      arr = arr.filter((r) => r.consumo_pe != null && r.consumo_pe > 1.0);
    }
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
  }, [data, q, filterBadge, onlyNegatives, sortKey, sortDir, recsMap,
      fActionType, fRelevance, fCampaign, fMatch, fOnlyWithOrders,
      fOnlyWithoutOrders, fOnlyNegativeProfit, fOnlyConsumoOver100]);

  const activeFilterCount =
    (fActionType ? 1 : 0) + (fRelevance ? 1 : 0) + (fCampaign ? 1 : 0) +
    (fMatch ? 1 : 0) + (fOnlyWithOrders ? 1 : 0) + (fOnlyWithoutOrders ? 1 : 0) +
    (fOnlyNegativeProfit ? 1 : 0) + (fOnlyConsumoOver100 ? 1 : 0);

  const clearExtraFilters = () => {
    setFActionType(""); setFRelevance(""); setFCampaign(""); setFMatch("");
    setFOnlyWithOrders(false); setFOnlyWithoutOrders(false);
    setFOnlyNegativeProfit(false); setFOnlyConsumoOver100(false);
  };

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

  const saveCampaigns = async (term, arr) => {
    try {
      await upsertKeyword(datasetId, {
        term,
        campaigns: arr,
        campaign: arr[0] || null,
      });
      toast.success(arr.length === 0 ? "Campañas eliminadas" : `${arr.length} campaña${arr.length === 1 ? "" : "s"} asignada${arr.length === 1 ? "" : "s"}`);
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
          <Button
            variant={onlyNegatives ? "default" : "outline"}
            size="sm"
            className={`rounded-md ${onlyNegatives ? "bg-red-600 hover:bg-red-500 text-white" : ""}`}
            onClick={() => setOnlyNegatives((v) => !v)}
            data-testid="filter-negatives-btn"
          >
            <Ban className="size-3.5 mr-1" />
            {onlyNegatives ? "Mostrando negativas" : "Solo negativas"}
            {data?.summary?.negativas > 0 && (
              <span className={`ml-1.5 num text-[10px] px-1.5 rounded ${onlyNegatives ? "bg-white/20" : "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400"}`}>
                {data.summary.negativas}
              </span>
            )}
          </Button>
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="rounded-md"
                data-testid="open-filters-popover"
              >
                <Filter className="size-3.5 mr-1" />
                Filtros
                {activeFilterCount > 0 && (
                  <span className="ml-1.5 num text-[10px] px-1.5 rounded bg-coral/15 text-coral" data-testid="active-filters-count">
                    {activeFilterCount}
                  </span>
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[340px] p-4 space-y-3" align="end" data-testid="filters-popover">
              <div className="space-y-2">
                <Label className="text-[10px] uppercase tracking-widest text-muted-foreground">Recomendación</Label>
                <Select value={fActionType || ALL} onValueChange={(v) => setFActionType(v === ALL ? "" : v)}>
                  <SelectTrigger className="h-8 rounded-md text-xs" data-testid="kw-filter-action"><SelectValue placeholder="Todas" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL}>Todas</SelectItem>
                    {ACTION_OPTIONS.map((a) => <SelectItem key={a} value={a}>{ACTION_LABELS[a]}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-[10px] uppercase tracking-widest text-muted-foreground">Relevancia</Label>
                <Select value={fRelevance || ALL} onValueChange={(v) => setFRelevance(v === ALL ? "" : v)}>
                  <SelectTrigger className="h-8 rounded-md text-xs" data-testid="kw-filter-relevance"><SelectValue placeholder="Todas" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL}>Todas</SelectItem>
                    {RELEVANCE_OPTIONS.map((r) => <SelectItem key={r} value={r}>{RELEVANCE_LABEL[r]}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-[10px] uppercase tracking-widest text-muted-foreground">Campaña</Label>
                <Select value={fCampaign || ALL} onValueChange={(v) => setFCampaign(v === ALL ? "" : v)}>
                  <SelectTrigger className="h-8 rounded-md text-xs" data-testid="kw-filter-campaign"><SelectValue placeholder="Todas" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL}>Todas</SelectItem>
                    {allCampaigns.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-[10px] uppercase tracking-widest text-muted-foreground">Match</Label>
                <Select value={fMatch || ALL} onValueChange={(v) => setFMatch(v === ALL ? "" : v)}>
                  <SelectTrigger className="h-8 rounded-md text-xs" data-testid="kw-filter-match"><SelectValue placeholder="Todos" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL}>Todos</SelectItem>
                    {MATCH_OPTIONS.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5 pt-2 border-t border-border">
                <label className="flex items-center justify-between text-xs gap-2 cursor-pointer">
                  <span>Solo con pedidos</span>
                  <Switch checked={fOnlyWithOrders} onCheckedChange={(v) => { setFOnlyWithOrders(v); if (v) setFOnlyWithoutOrders(false); }} data-testid="kw-filter-with-orders" />
                </label>
                <label className="flex items-center justify-between text-xs gap-2 cursor-pointer">
                  <span>Solo sin pedidos</span>
                  <Switch checked={fOnlyWithoutOrders} onCheckedChange={(v) => { setFOnlyWithoutOrders(v); if (v) setFOnlyWithOrders(false); }} data-testid="kw-filter-without-orders" />
                </label>
                <label className="flex items-center justify-between text-xs gap-2 cursor-pointer">
                  <span>Solo beneficio KDP negativo</span>
                  <Switch checked={fOnlyNegativeProfit} onCheckedChange={setFOnlyNegativeProfit} data-testid="kw-filter-negative-profit" />
                </label>
                <label className="flex items-center justify-between text-xs gap-2 cursor-pointer">
                  <span>Solo consumo PE &gt; 100%</span>
                  <Switch checked={fOnlyConsumoOver100} onCheckedChange={setFOnlyConsumoOver100} data-testid="kw-filter-consumo-over" />
                </label>
              </div>
              {activeFilterCount > 0 && (
                <Button variant="outline" size="sm" onClick={clearExtraFilters} className="w-full rounded-md gap-1.5" data-testid="kw-filters-clear">
                  <X className="size-3.5" /> Limpiar filtros
                </Button>
              )}
            </PopoverContent>
          </Popover>
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
              const negative = !!r.suggest_negative;
              const engineRec = findRecForRow(recsMap, r);
              const hasEngineRec = !!engineRec;
              // Motor takes visual priority: don't tint the row red or show the
              // ban icon next to the term if the engine already has an opinion.
              const showLegacyAsPrimary = negative && !hasEngineRec;
              return (
                <tr
                  key={i}
                  className={`border-t border-border hover:bg-muted/30 ${r.is_manual ? "bg-coral/5" : ""} ${showLegacyAsPrimary ? "bg-red-50/60 dark:bg-red-500/5" : ""}`}
                  data-testid={`kw-row-${i}`}
                >
                  <td className="px-3 py-2 max-w-[240px]">
                    <button
                      onClick={() => openDetail(r.term)}
                      className="text-left hover:text-coral font-medium truncate block w-full inline-flex items-center gap-1.5"
                      data-testid={`kw-term-${i}`}
                    >
                      {(() => {
                        const dot = getRelevanceDot(r.relevance);
                        return (
                          <span
                            className={`size-2 rounded-full shrink-0 ${dot.cls}`}
                            title={dot.label}
                            data-testid={`rel-dot-${i}`}
                            data-relevance={r.relevance || "unreviewed"}
                          />
                        );
                      })()}
                      {showLegacyAsPrimary && <Ban className="size-3 text-red-600 shrink-0" data-testid={`neg-icon-${i}`} />}
                      <span className="truncate">{r.term}</span>
                      <RecommendationBadge rec={engineRec} testidSuffix={i} />
                    </button>
                  </td>
                  <td className="px-3 py-2">
                    <MultiCampaignCell
                      campaigns={r.campaigns || (r.campaign ? [r.campaign] : [])}
                      allCampaigns={allCampaigns}
                      onSave={(arr) => saveCampaigns(r.term, arr)}
                      testid={`edit-campaigns-${i}`}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <EditableText value={r.match_type} onSave={(v) => saveCell(r.term, "match_type", v)} testid={`edit-match-${i}`} placeholder="—" />
                  </td>
                  <td className={`px-3 py-2 num text-right ${acosColor(r.acos_actual)}`}>
                    {r.acos_actual == null ? "—" : fmtPct(r.acos_actual)}
                  </td>
                  <td className={`px-3 py-2 num text-right ${acosColor(r.acos_siguiente)}`} data-testid={`kw-acos-next-${i}`}>
                    {r.acos_siguiente == null ? "—" : fmtPct(r.acos_siguiente)}
                  </td>
                  <td className="px-3 py-2 num text-right" data-testid={`kw-clicks-pe-${i}`}>
                    {r.clicks_pe == null ? (
                      <span className="text-muted-foreground/40">—</span>
                    ) : (
                      <span className="inline-flex items-center gap-1">
                        {r.clicks_pe.toFixed(1)}
                        {r.cpc_source === "reference" && (
                          <span
                            className="text-[9px] px-1 py-0 rounded bg-muted text-muted-foreground"
                            title="CPC estimado: calculado con CPC de referencia del nicho, no con CPC real de Amazon Ads."
                          >
                            est.
                          </span>
                        )}
                      </span>
                    )}
                  </td>
                  <td className={`px-3 py-2 num text-right ${consumoFaseClass(r.consumo_fase)}`} data-testid={`kw-consumo-fase-${i}`} title={`Badge: ${b.label}`}>
                    {r.consumo_fase == null ? "—" : `${(r.consumo_fase * 100).toFixed(0)}%`}
                  </td>
                  <td className={`px-3 py-2 num text-right ${r.beneficio_kdp != null && r.beneficio_kdp < 0 ? "text-destructive" : (r.beneficio_kdp != null && r.beneficio_kdp > 0 ? "text-green-600 dark:text-green-400" : "")}`} data-testid={`kw-beneficio-kdp-${i}`}>
                    {r.beneficio_kdp == null ? (
                      r.beneficio_ahora == null
                        ? <span className="text-muted-foreground/40">—</span>
                        : <span className="text-muted-foreground" title="Sales − Spend (bruto). Configura la economía del libro para ver beneficio KDP real.">{fmtMoney(r.beneficio_ahora, sym)}</span>
                    ) : (
                      fmtMoney(r.beneficio_kdp, sym)
                    )}
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
