import { useEffect, useState } from "react";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription,
} from "./ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Badge } from "./ui/badge";
import { Checkbox } from "./ui/checkbox";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "./ui/select";
import {
  Camera, Save, Trash2, Loader2, BookOpen, Megaphone, Sparkles, AlertCircle,
  MousePointerClick, ShoppingBag, TrendingUp, Plane, PauseCircle, Shield, HelpCircle,
  ChevronDown, ChevronUp,
} from "lucide-react";
import {
  getKeywordDetail, snapshotAll, getSnapshots,
  upsertKeyword, deleteKeywordOverride, getCampaignsList, getAutopilot,
} from "../lib/api";
import { useData } from "../context/DataContext";
import { toast } from "sonner";
import { fmtInt, fmtPct, fmtMoney, getMarketplace } from "../lib/format";
import { InfoTooltip } from "./InfoTooltip";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
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

const SCORE_COLOR = (n) =>
  n >= 80 ? "bg-green-500" : n >= 65 ? "bg-blue-500" : n >= 45 ? "bg-amber-500" : n >= 25 ? "bg-orange-500" : "bg-red-500";
const SCORE_LABEL = {
  "excelente": "Excelente",
  "bueno": "Bueno",
  "medio": "Medio",
  "bajo": "Bajo",
  "muy-bajo": "Muy bajo",
};

const DEMAND_CHECKS = [
  { id: "self_contained", label: "Nicho autocontenido" },
  { id: "amazon_suggestion", label: "Sugerido por Amazon" },
  { id: "selling_well", label: "Libros vendiendo bien" },
  { id: "indie_authors", label: "Indies con ventas" },
  { id: "matches_intent", label: "Top 10 coincide con intención" },
  { id: "variants", label: "Potencial de variantes" },
];
const COMP_CHECKS = [
  { id: "low_results", label: "< 3.000 resultados" },
  { id: "profitable_books", label: "Libros rentables visibles" },
  { id: "books_under_100_reviews", label: "Libros con < 100 reviews" },
];

function Metric({ label, value, tooltip, accent, testid }) {
  return (
    <div className="border border-border rounded-md p-3 bg-card" data-testid={testid}>
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
        {label} {tooltip && <InfoTooltip content={tooltip} />}
      </div>
      <div className={`num text-lg font-semibold mt-1 ${accent || ""}`}>{value}</div>
    </div>
  );
}

function SimBox({ label, now, next, accent }) {
  return (
    <div className="bg-background border border-border rounded p-2">
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className="flex items-center gap-1 mt-0.5 text-xs">
        <span className="num text-muted-foreground">{now}</span>
        <span className="text-muted-foreground">→</span>
        <span className={`num font-semibold ${accent || ""}`}>{next}</span>
      </div>
    </div>
  );
}

export default function KeywordDetailSheet({ open, onClose, term, initialTab = "ads" }) {
  const { active, marketplace, loadActive } = useData();
  const sym = getMarketplace(marketplace).symbol;
  const mpInfo = getMarketplace(marketplace);
  const [detail, setDetail] = useState(null);
  const [snaps, setSnaps] = useState([]);
  const [loading, setLoading] = useState(false);
  const [snapshotting, setSnapshotting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState(initialTab);

  // Resize state
  const [width, setWidth] = useState(
    () => Number(localStorage.getItem("kwsheet_width")) || 640
  );
  const [dragging, setDragging] = useState(false);

  // Campaigns list + autopilot per-keyword
  const [allCampaigns, setAllCampaigns] = useState([]);
  const [autopilotPhase, setAutopilotPhase] = useState(null); // null → use book phase
  const [apRec, setApRec] = useState(null);
  const [apLoading, setApLoading] = useState(false);

  // Ads fields
  const [clicks, setClicks] = useState(0);
  const [impressions, setImpressions] = useState(0);
  const [cpc, setCpc] = useState(0);
  const [spend, setSpend] = useState(0);
  const [autoSpend, setAutoSpend] = useState(true);
  const [orders, setOrders] = useState(0);
  const [sales, setSales] = useState(0);
  const [autoSales, setAutoSales] = useState(true);
  const [campaigns, setCampaigns] = useState([]);
  const [matchType, setMatchType] = useState("broad");
  const [adType, setAdType] = useState("SP");
  const [notes, setNotes] = useState("");

  // Niche fields
  const [searchVolume, setSearchVolume] = useState(0);
  const [competitors, setCompetitors] = useState(0);
  const [kwPrice, setKwPrice] = useState(0);
  const [kwRoyalties, setKwRoyalties] = useState(0);
  const [demandChecks, setDemandChecks] = useState(0);
  const [competitionChecks, setCompetitionChecks] = useState(0);
  const [kwStatus, setKwStatus] = useState("pending");
  const [demandState, setDemandState] = useState({});
  const [compState, setCompState] = useState({});
  const [showSnapsList, setShowSnapsList] = useState(false);

  useEffect(() => { setTab(initialTab); }, [initialTab, open]);

  useEffect(() => {
    if (!open || !term || !active) return;
    setLoading(true);
    getKeywordDetail(active.id, term)
      .then(async (r) => {
        setDetail(r.data);
        const m = r.data.metrics;
        setClicks(Math.round(m.clicks || 0));
        setImpressions(Math.round(m.impressions || 0));
        setCpc(m.cpc || 0);
        setSpend(m.spend || 0);
        setOrders(Math.round(m.orders || 0));
        setSales(m.sales || 0);
        setCampaigns(Array.isArray(m.campaigns) ? m.campaigns : (m.campaign ? [m.campaign] : []));
        setMatchType(m.match_type || "broad");
        setAdType(m.ad_type || "SP");
        setNotes(m.notes || "");
        setSearchVolume(m.search_volume || 0);
        setCompetitors(m.competitors || 0);
        setKwPrice(m.kw_price || 0);
        setKwRoyalties(m.kw_royalties || 0);
        setDemandChecks(m.demand_checks || 0);
        setCompetitionChecks(m.competition_checks || 0);
        setKwStatus(m.keyword_status || "pending");
        // Restore demand/competition visual checks from saved state
        const dState = (m.demand_check_flags && typeof m.demand_check_flags === "object") ? m.demand_check_flags : {};
        const cState = (m.competition_check_flags && typeof m.competition_check_flags === "object") ? m.competition_check_flags : {};
        setDemandState(dState);
        setCompState(cState);
        setAutoSpend(true); setAutoSales(true);
        // Load snapshots
        const s = await getSnapshots(active.id, term);
        setSnaps(s.data.snapshots || []);
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

  // Load campaigns list + autopilot when open
  useEffect(() => {
    if (!open || !active) return;
    getCampaignsList(active.id).then((r) => setAllCampaigns(r.data || [])).catch(() => {});
  }, [open, active]);

  useEffect(() => {
    if (!open || !active || !term) return;
    const phase = autopilotPhase || active.phase || "dominio";
    setApLoading(true);
    getAutopilot(active.id, phase)
      .then((r) => {
        const all = [...(r.data.actions?.pause || []), ...(r.data.actions?.scale || []),
                     ...(r.data.actions?.hold || []), ...(r.data.actions?.investigate || [])];
        const mine = all.find((x) => x.term === term);
        setApRec(mine ? { ...mine, phase } : { action: "hold", rationale: "Sin datos suficientes", phase });
      })
      .finally(() => setApLoading(false));
  }, [open, active, term, autopilotPhase]);

  // Auto-calc spend from clicks × CPC
  useEffect(() => {
    if (autoSpend) setSpend(Number((clicks * cpc).toFixed(2)));
  }, [clicks, cpc, autoSpend]);
  // Auto-calc sales from orders × precio del libro (de economía global)
  useEffect(() => {
    if (autoSales) {
      const p = active?.book_economy?.precio_libro || 0;
      setSales(Number((orders * p).toFixed(2)));
    }
  }, [orders, autoSales, active?.book_economy?.precio_libro]);

  const m = detail?.metrics;
  const pe = detail?.acos_equilibrio;
  const acosColor = (v) =>
    v == null ? "" : pe == null ? "" : v <= pe ? "text-green-600 dark:text-green-400" : "text-destructive";

  const handleSnapshot = async () => {
    setSnapshotting(true);
    try {
      await snapshotAll(active.id);
      const s = await getSnapshots(active.id, term);
      setSnaps(s.data.snapshots || []);
      toast.success("Snapshot guardado");
    } catch (e) { toast.error(e?.response?.data?.detail || e.message); }
    finally { setSnapshotting(false); }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await upsertKeyword(active.id, {
        term,
        clicks: Number(clicks) || 0,
        impressions: Number(impressions) || 0,
        cpc: Number(cpc) || 0,
        spend: Number(spend) || 0,
        orders: Number(orders) || 0,
        sales: Number(sales) || 0,
        auto_spend: autoSpend,
        campaigns: campaigns,
        campaign: campaigns[0] || null,
        match_type: matchType || null,
        ad_type: adType || null,
        notes,
        search_volume: Number(searchVolume) || 0,
        competitors: Number(competitors) || 0,
        kw_price: Number(kwPrice) || 0,
        kw_royalties: Number(kwRoyalties) || 0,
        demand_checks: Number(demandChecks) || 0,
        competition_checks: Number(competitionChecks) || 0,
        keyword_status: kwStatus,
        demand_check_flags: demandState,
        competition_check_flags: compState,
      });
      toast.success("Keyword guardada");
      await loadActive(active.id);
      const r = await getKeywordDetail(active.id, term);
      setDetail(r.data);
    } catch (e) { toast.error(e?.response?.data?.detail || e.message); }
    finally { setSaving(false); }
  };

  const handleDeleteOverride = async () => {
    try {
      await deleteKeywordOverride(active.id, term);
      toast.success("Ajuste manual eliminado");
      await loadActive(active.id);
      onClose();
    } catch (e) { toast.error(e?.response?.data?.detail || e.message); }
  };

  const chartData = snaps.map((s) => ({
    date: (s.ts || "").slice(5, 10),
    acos: s.acos_actual ?? 0,
    acos_next: s.acos_siguiente ?? 0,
    spend: s.spend || 0,
    sales: s.sales || 0,
  }));

  const score = m?.market_score || 0;
  const breakdown = m?.market_score_breakdown;

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        side="right"
        className="p-0 overflow-hidden sm:max-w-none w-auto"
        style={{ width: `${width}px`, maxWidth: "95vw" }}
        data-testid="kw-detail-sheet"
      >
        {/* Resize handle on the left edge */}
        <div
          className="absolute left-0 top-0 h-full w-1.5 cursor-ew-resize hover:bg-coral/60 z-50"
          data-testid="resize-handle"
          onMouseDown={(e) => {
            e.preventDefault();
            setDragging(true);
            const startX = e.clientX;
            const startW = width;
            const handleMove = (ev) => {
              const next = Math.min(Math.max(420, startW + (startX - ev.clientX)), window.innerWidth * 0.95);
              setWidth(next);
            };
            const handleUp = () => {
              setDragging(false);
              localStorage.setItem("kwsheet_width", String(width));
              document.removeEventListener("mousemove", handleMove);
              document.removeEventListener("mouseup", handleUp);
            };
            document.addEventListener("mousemove", handleMove);
            document.addEventListener("mouseup", handleUp);
          }}
        />
        <div className="h-full overflow-y-auto px-6 py-5">
        <SheetHeader>
          <div className="flex items-center gap-2 flex-wrap">
            <SheetTitle className="font-heading text-xl">{term}</SheetTitle>
            {m?.badge && (
              <span className={`badge-pill ${BADGE_STYLES[m.badge]}`} data-testid="detail-badge">
                {BADGE_LABEL[m.badge]}
              </span>
            )}
            {m?.is_manual && (
              <span className="badge-pill border-coral/40 bg-coral/10 text-coral-700 dark:text-coral-400">Manual</span>
            )}
            <span className="badge-pill bg-muted text-muted-foreground border-border">
              {mpInfo.flag} {mpInfo.name}
            </span>
          </div>
          <SheetDescription>
            {m?.campaign ? `Campaña: ${m.campaign}` : "Sin campaña"}
            {m?.match_type ? ` · ${m.match_type}` : ""}
            {m?.underlying_rows ? ` · ${m.underlying_rows} filas base` : ""}
          </SheetDescription>
        </SheetHeader>

        {loading || !m ? (
          <div className="py-12 flex justify-center"><Loader2 className="size-6 animate-spin text-coral" /></div>
        ) : (
          <Tabs value={tab} onValueChange={setTab} className="mt-4">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="nicho" className="gap-2" data-testid="tab-nicho">
                <BookOpen className="size-4" /> Estudio de KW
              </TabsTrigger>
              <TabsTrigger value="ads" className="gap-2" data-testid="tab-ads">
                <Megaphone className="size-4" /> Gestión de Ads
              </TabsTrigger>
            </TabsList>

            {/* ===== TAB NICHO ===== */}
            <TabsContent value="nicho" className="space-y-5 py-4">
              <div className="border border-border rounded-lg p-4 bg-card space-y-3" data-testid="market-score-section">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="size-4 text-coral" />
                    <h3 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">Market Score</h3>
                  </div>
                  <Badge className="text-lg px-3 py-1 bg-coral hover:bg-coral text-white" data-testid="score-badge">
                    {score}
                  </Badge>
                </div>
                <div className="h-3 bg-muted rounded-full overflow-hidden">
                  <div className={`h-full transition-all ${SCORE_COLOR(score)}`} style={{ width: `${score}%` }} />
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>0</span>
                  <span className="capitalize font-semibold">{SCORE_LABEL[m.score_label] || m.score_label}</span>
                  <span>100</span>
                </div>
                {breakdown && (
                  <div className="grid grid-cols-3 gap-2 text-xs mt-2">
                    {(() => {
                      const LABELS = {
                        volume: "Volumen",
                        competitors: "Competidores",
                        price: "Precio",
                        royalties: "Regalías",
                        demand: "Demanda",
                        competition_checks: "Competencia",
                      };
                      return Object.entries(breakdown).map(([k, v]) => (
                        <div key={k} className="border border-border rounded p-2 text-center bg-background">
                          <div className="text-muted-foreground">{LABELS[k] || k}</div>
                          <div className="num font-semibold">{v.points}/{v.max}</div>
                        </div>
                      ));
                    })()}
                  </div>
                )}
              </div>

              <div className="border border-border rounded-lg p-4 bg-card space-y-3">
                <h3 className="text-xs uppercase tracking-widest font-semibold text-muted-foreground">Datos de mercado</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs flex items-center gap-1">Volumen <InfoTooltip content="Búsquedas mensuales estimadas en Amazon." /></Label>
                    <Input type="number" min={0} step={1} value={searchVolume} onChange={(e) => setSearchVolume(e.target.value)} className="rounded-md mt-1 num" data-testid="niche-volume" />
                  </div>
                  <div>
                    <Label className="text-xs flex items-center gap-1">Competidores <InfoTooltip content="Nº de resultados en búsqueda. Menos es mejor." /></Label>
                    <Input type="number" min={0} step={1} value={competitors} onChange={(e) => setCompetitors(e.target.value)} className="rounded-md mt-1 num" data-testid="niche-competitors" />
                  </div>
                  <div>
                    <Label className="text-xs">Precio medio nicho ({sym})</Label>
                    <Input type="number" min={0} step={0.01} value={kwPrice} onChange={(e) => setKwPrice(e.target.value)} className="rounded-md mt-1 num" data-testid="niche-price" />
                  </div>
                  <div>
                    <Label className="text-xs">Regalía media ({sym})</Label>
                    <Input type="number" min={0} step={0.01} value={kwRoyalties} onChange={(e) => setKwRoyalties(e.target.value)} className="rounded-md mt-1 num" data-testid="niche-royalties" />
                  </div>
                </div>
                <div>
                  <Label className="text-xs">Estado de la keyword</Label>
                  <Select value={kwStatus} onValueChange={setKwStatus}>
                    <SelectTrigger className="rounded-md mt-1" data-testid="niche-status"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pending">Pendiente</SelectItem>
                      <SelectItem value="validated">Validada</SelectItem>
                      <SelectItem value="testing">En test</SelectItem>
                      <SelectItem value="rejected">Descartada</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="border border-border rounded-lg p-4 bg-card space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs uppercase tracking-widest font-semibold text-muted-foreground">Señales de demanda</h3>
                  <Badge variant="outline" className="num text-xs">{Object.values(demandState).filter(Boolean).length}/6</Badge>
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  {DEMAND_CHECKS.map((c) => {
                    const on = !!demandState[c.id];
                    return (
                      <label key={c.id} className="flex items-center gap-2 p-1.5 rounded hover:bg-muted/50 cursor-pointer">
                        <Checkbox
                          checked={on}
                          onCheckedChange={(v) => {
                            const ns = { ...demandState, [c.id]: !!v };
                            setDemandState(ns);
                            setDemandChecks(Object.values(ns).filter(Boolean).length);
                          }}
                          data-testid={`demand-${c.id}`}
                        />
                        <span className="text-xs">{c.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="border border-border rounded-lg p-4 bg-card space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs uppercase tracking-widest font-semibold text-muted-foreground">Señales de competencia</h3>
                  <Badge variant="outline" className="num text-xs">{Object.values(compState).filter(Boolean).length}/3</Badge>
                </div>
                <div className="grid grid-cols-1 gap-1.5">
                  {COMP_CHECKS.map((c) => {
                    const on = !!compState[c.id];
                    return (
                      <label key={c.id} className="flex items-center gap-2 p-1.5 rounded hover:bg-muted/50 cursor-pointer">
                        <Checkbox
                          checked={on}
                          onCheckedChange={(v) => {
                            const ns = { ...compState, [c.id]: !!v };
                            setCompState(ns);
                            setCompetitionChecks(Object.values(ns).filter(Boolean).length);
                          }}
                          data-testid={`comp-${c.id}`}
                        />
                        <span className="text-xs">{c.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            </TabsContent>

            {/* ===== TAB ADS ===== */}
            <TabsContent value="ads" className="space-y-5 py-4">
              {/* Quick actions from original */}
              <div className="border border-border rounded-md bg-muted/30 p-3 space-y-2" data-testid="quick-actions">
                <div className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">Acciones rápidas (simular)</div>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" className="rounded-md h-8 gap-1.5" onClick={() => setClicks(Number(clicks) + 1)} data-testid="qa-plus-click">
                    <MousePointerClick className="size-3.5" /> +1 Click
                  </Button>
                  <Button size="sm" variant="outline" className="rounded-md h-8 gap-1.5" onClick={() => setCpc(Math.round((Number(cpc) + 0.01) * 100) / 100)} data-testid="qa-plus-cpc">
                    <TrendingUp className="size-3.5" /> +0.01 CPC
                  </Button>
                  <Button size="sm" variant="outline" className="rounded-md h-8 gap-1.5" onClick={() => {
                    const newOrders = Number(orders) + 1;
                    setOrders(newOrders);
                    setClicks(Math.max(Number(clicks) + 1, newOrders));
                  }} data-testid="qa-plus-order">
                    <ShoppingBag className="size-3.5" /> +1 Pedido (con click)
                  </Button>
                </div>
              </div>

              {/* Autopilot per-keyword (uses book phase by default) */}
              <div className="border border-border rounded-md bg-card p-3 space-y-2" data-testid="kw-autopilot-card">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <Plane className="size-4 text-coral" />
                    <h3 className="text-sm font-semibold">Recomendación del Piloto</h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <Label className="text-[10px] text-muted-foreground">Fase</Label>
                    <Select
                      value={autopilotPhase || (active?.phase || "dominio")}
                      onValueChange={(v) => setAutopilotPhase(v)}
                    >
                      <SelectTrigger className="h-7 w-[140px] rounded-md text-xs" data-testid="kw-autopilot-phase">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="lanzamiento">Lanzamiento</SelectItem>
                        <SelectItem value="dominio">Dominio</SelectItem>
                        <SelectItem value="beneficio">Beneficio</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                {apLoading ? (
                  <div className="text-xs text-muted-foreground flex items-center gap-2">
                    <Loader2 className="size-3 animate-spin" /> Calculando…
                  </div>
                ) : apRec ? (
                  <div className="flex items-start gap-2" data-testid="kw-autopilot-recommendation">
                    {apRec.action === "pause" && <PauseCircle className="size-4 text-destructive mt-0.5" />}
                    {apRec.action === "scale" && <TrendingUp className="size-4 text-green-600 mt-0.5" />}
                    {apRec.action === "hold" && <Shield className="size-4 text-blue-600 mt-0.5" />}
                    {apRec.action === "investigate" && <HelpCircle className="size-4 text-amber-500 mt-0.5" />}
                    <div className="text-xs flex-1">
                      <div className="font-semibold capitalize">
                        {apRec.action === "pause" ? "Pausar" :
                         apRec.action === "scale" ? `Escalar${apRec.bid_delta_pct ? ` (${apRec.bid_delta_pct > 0 ? "+" : ""}${apRec.bid_delta_pct}%)` : ""}` :
                         apRec.action === "hold" ? "Mantener" : "Observar"}
                      </div>
                      <div className="text-muted-foreground">{apRec.rationale}</div>
                    </div>
                  </div>
                ) : null}
              </div>

              {/* Simulation card: +1 click generating a sale */}
              {detail?.simulation && (
                <div className="border border-coral/30 bg-coral/5 rounded-md p-4 space-y-2" data-testid="simulation-card">
                  <div className="flex items-center gap-2">
                    <Sparkles className="size-4 text-coral" />
                    <h3 className="text-sm font-semibold">Simulación: +1 click que genera venta</h3>
                    <InfoTooltip content="Qué pasa si el siguiente click se convierte en compra. Clicks, pedidos, gasto y ventas aumentan consecuentemente." />
                  </div>
                  <div className="grid grid-cols-5 gap-2 text-xs">
                    <SimBox label="Clicks" now={m.clicks} next={detail.simulation.clicks_next} />
                    <SimBox label="Pedidos" now={m.orders} next={detail.simulation.orders_next} />
                    <SimBox label={`Gasto (${sym})`} now={(m.spend || 0).toFixed(2)} next={detail.simulation.spend_next.toFixed(2)} />
                    <SimBox label={`Ventas (${sym})`} now={(m.sales || 0).toFixed(2)} next={detail.simulation.sales_next.toFixed(2)} />
                    <SimBox label="ACoS" now={m.acos_actual == null ? "—" : fmtPct(m.acos_actual)} next={fmtPct(detail.simulation.acos_next_with_sale)} accent={pe != null && detail.simulation.acos_next_with_sale <= pe ? "text-green-600" : "text-destructive"} />
                  </div>
                </div>
              )}

              <div className="grid grid-cols-3 gap-2">
                <Metric label="Impr." value={fmtInt(m.impressions)} />
                <Metric label="Clicks" value={fmtInt(m.clicks)} />
                <Metric label="CTR" value={fmtPct(m.ctr)} tooltip="ctr" />
                <Metric label="CPC" value={fmtMoney(m.cpc, sym)} tooltip="cpc" />
                <Metric label="Gasto" value={fmtMoney(m.spend, sym)} />
                <Metric label="Ventas" value={fmtMoney(m.sales, sym)} />
                <Metric
                  label="ACoS"
                  value={m.acos_actual == null ? "—" : fmtPct(m.acos_actual)}
                  accent={acosColor(m.acos_actual)} tooltip="acos"
                />
                <Metric
                  label="ACoS +1 (con venta)"
                  value={m.acos_siguiente == null ? "—" : fmtPct(m.acos_siguiente)}
                  accent={acosColor(m.acos_siguiente)}
                  tooltip="acos_siguiente"
                  testid="metric-acos-next-sale"
                />
                <Metric
                  label="ACoS +1 (sin venta)"
                  value={m.acos_siguiente_sin_venta == null ? "—" : fmtPct(m.acos_siguiente_sin_venta)}
                  accent={m.acos_siguiente_sin_venta != null && pe != null && m.acos_siguiente_sin_venta > pe ? "text-destructive" : ""}
                  tooltip="ACoS si el siguiente click NO genera venta: (gasto+CPC)/ventas × 100. Peor caso para decidir si pausar."
                  testid="metric-acos-next-nosale"
                />
                <Metric
                  label="Beneficio ahora"
                  value={m.beneficio_ahora == null ? "—" : fmtMoney(m.beneficio_ahora, sym)}
                  accent={m.beneficio_ahora != null && m.beneficio_ahora < 0 ? "text-destructive" : ""}
                  tooltip="beneficio_ahora"
                />
                <Metric
                  label="Benef. +1 click"
                  value={m.beneficio_siguiente == null ? "—" : fmtMoney(m.beneficio_siguiente, sym)}
                  accent={m.beneficio_siguiente != null && m.beneficio_siguiente < 0 ? "text-destructive" : ""}
                  tooltip="beneficio_siguiente"
                />
                <Metric label="CVR" value={fmtPct(m.cvr)} tooltip="cvr" />
              </div>

              <div className="border border-border rounded-md bg-card p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold">Evolución</h3>
                    <InfoTooltip content="Snapshots automáticos diarios + manuales." />
                  </div>
                  <Button size="sm" variant="outline" onClick={handleSnapshot} disabled={snapshotting} className="rounded-md" data-testid="snapshot-btn">
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
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Line type="monotone" dataKey="acos" name="ACoS" stroke="#FB923C" strokeWidth={2} dot={{ r: 2 }} />
                      <Line type="monotone" dataKey="acos_next" name="ACoS +1" stroke="#3B82F6" strokeWidth={2} dot={{ r: 2 }} strokeDasharray="3 3" />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-xs text-muted-foreground text-center py-6" data-testid="no-snapshots">
                    {chartData.length === 0 ? "Aún no hay snapshots." : "Se necesitan ≥2 snapshots para la evolución."}
                  </div>
                )}
                {snaps.length > 0 && (
                  <div className="mt-3 border-t border-border pt-2">
                    <button
                      onClick={() => setShowSnapsList(!showSnapsList)}
                      className="text-xs text-muted-foreground hover:text-coral flex items-center gap-1 w-full"
                      data-testid="toggle-snaps-list"
                    >
                      {showSnapsList ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
                      Historial de snapshots ({snaps.length})
                    </button>
                    {showSnapsList && (
                      <div className="mt-2 max-h-52 overflow-y-auto border border-border rounded-md" data-testid="snaps-list">
                        <table className="w-full text-xs">
                          <thead className="bg-muted/40 sticky top-0">
                            <tr className="text-[10px] uppercase tracking-widest text-muted-foreground">
                              <th className="text-left px-2 py-1">Fecha</th>
                              <th className="text-right px-2 py-1">Clicks</th>
                              <th className="text-right px-2 py-1">Pedidos</th>
                              <th className="text-right px-2 py-1">Gasto</th>
                              <th className="text-right px-2 py-1">Ventas</th>
                              <th className="text-right px-2 py-1">ACoS</th>
                            </tr>
                          </thead>
                          <tbody>
                            {[...snaps].reverse().map((s, i) => (
                              <tr key={i} className="border-t border-border">
                                <td className="px-2 py-1 num">{(s.ts || "").slice(0, 10)}</td>
                                <td className="px-2 py-1 num text-right">{fmtInt(s.clicks)}</td>
                                <td className="px-2 py-1 num text-right">{fmtInt(s.orders)}</td>
                                <td className="px-2 py-1 num text-right">{fmtMoney(s.spend, sym)}</td>
                                <td className="px-2 py-1 num text-right">{fmtMoney(s.sales, sym)}</td>
                                <td className="px-2 py-1 num text-right">{s.acos_actual == null ? "—" : fmtPct(s.acos_actual)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="border border-border rounded-md bg-card p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold">Métricas base (editables)</h3>
                  {m.is_manual && (
                    <Button size="sm" variant="ghost" className="text-destructive" onClick={handleDeleteOverride} data-testid="delete-override-btn">
                      <Trash2 className="size-3.5" /><span className="ml-1 text-xs">Quitar ajuste</span>
                    </Button>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Impresiones</Label>
                    <Input type="number" min={0} step={1} value={impressions} onChange={(e) => setImpressions(e.target.value)} className="rounded-md mt-1 num" data-testid="edit-impressions" />
                  </div>
                  <div>
                    <Label className="text-xs">Clicks</Label>
                    <Input type="number" min={0} step={1} value={clicks} onChange={(e) => setClicks(e.target.value)} className="rounded-md mt-1 num" data-testid="edit-clicks" />
                  </div>
                  <div>
                    <Label className="text-xs flex items-center gap-1">CPC ({sym}) <InfoTooltip content="cpc" /></Label>
                    <Input type="number" min={0} step={0.01} value={cpc} onChange={(e) => setCpc(e.target.value)} className="rounded-md mt-1 num" data-testid="edit-cpc" />
                  </div>
                  <div>
                    <Label className="text-xs flex items-center gap-1">
                      Gasto ({sym})
                      <span className="text-[10px] text-muted-foreground">
                        <label className="inline-flex items-center gap-1 cursor-pointer">
                          <input type="checkbox" checked={autoSpend} onChange={(e) => setAutoSpend(e.target.checked)} data-testid="auto-spend" />
                          auto
                        </label>
                      </span>
                    </Label>
                    <Input type="number" min={0} step={0.01} value={spend} onChange={(e) => { setAutoSpend(false); setSpend(e.target.value); }} className="rounded-md mt-1 num" data-testid="edit-spend" />
                  </div>
                  <div>
                    <Label className="text-xs">Pedidos</Label>
                    <Input type="number" min={0} step={1} value={orders} onChange={(e) => setOrders(e.target.value)} className="rounded-md mt-1 num" data-testid="edit-orders" />
                  </div>
                  <div>
                    <Label className="text-xs flex items-center gap-1">
                      Ventas ({sym})
                      <span className="text-[10px] text-muted-foreground">
                        <label className="inline-flex items-center gap-1 cursor-pointer">
                          <input type="checkbox" checked={autoSales} onChange={(e) => setAutoSales(e.target.checked)} data-testid="auto-sales" />
                          auto
                        </label>
                      </span>
                    </Label>
                    <Input type="number" min={0} step={0.01} value={sales} onChange={(e) => { setAutoSales(false); setSales(e.target.value); }} className="rounded-md mt-1 num" data-testid="edit-sales" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Match</Label>
                    <Select value={matchType} onValueChange={setMatchType}>
                      <SelectTrigger className="rounded-md mt-1" data-testid="edit-match-type"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="broad">Broad</SelectItem>
                        <SelectItem value="phrase">Phrase</SelectItem>
                        <SelectItem value="exact">Exact</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs">Tipo</Label>
                    <Select value={adType} onValueChange={setAdType}>
                      <SelectTrigger className="rounded-md mt-1" data-testid="edit-ad-type"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="SP">SP</SelectItem>
                        <SelectItem value="SB">SB</SelectItem>
                        <SelectItem value="SBV">SBV</SelectItem>
                        <SelectItem value="SD">SD</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div>
                  <Label className="text-xs">Campañas asignadas</Label>
                  <div className="flex flex-wrap gap-1.5 mt-1.5" data-testid="kw-campaigns">
                    {campaigns.map((c) => (
                      <Badge key={c} variant="outline" className="rounded-md gap-1 pr-1">
                        <span className="truncate max-w-[200px]">{c}</span>
                        <button
                          onClick={() => setCampaigns(campaigns.filter((x) => x !== c))}
                          className="hover:text-destructive ml-1"
                          data-testid={`remove-camp-${c.slice(0,20)}`}
                        >×</button>
                      </Badge>
                    ))}
                    {campaigns.length === 0 && (
                      <span className="text-xs text-muted-foreground italic">Sin campañas asignadas</span>
                    )}
                  </div>
                  <select
                    className="mt-2 w-full h-9 rounded-md border border-border bg-background px-2 text-sm"
                    value=""
                    onChange={(e) => { const v = e.target.value; if (v && !campaigns.includes(v)) setCampaigns([...campaigns, v]); e.target.value = ""; }}
                    data-testid="edit-campaign-select"
                  >
                    <option value="">{allCampaigns.length === 0 ? "No hay campañas — crea una primero" : "Añadir campaña…"}</option>
                    {allCampaigns.filter((c) => !campaigns.includes(c)).map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label className="text-xs">Notas</Label>
                  <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} className="rounded-md mt-1" rows={2} data-testid="edit-notes" />
                </div>
              </div>

              {pe == null && (
                <div className="border border-amber-300 dark:border-amber-500/40 bg-amber-50 dark:bg-amber-500/5 p-3 rounded-md flex items-start gap-2 text-xs">
                  <AlertCircle className="size-4 mt-0.5 text-amber-600" />
                  Configura el precio y regalías del libro en <span className="font-semibold mx-1">Mi libro</span> para ver ACoS de Equilibrio.
                </div>
              )}
            </TabsContent>
          </Tabs>
        )}

        <div className="mt-5 pt-3 border-t border-border flex items-center gap-2">
          <Button variant="outline" onClick={onClose} className="rounded-md">Cerrar</Button>
          <Button onClick={handleSave} disabled={saving} className="rounded-md bg-coral hover:bg-coral-500 text-white flex-1" data-testid="save-kw-btn">
            {saving ? <Loader2 className="size-4 animate-spin mr-2" /> : <Save className="size-4 mr-2" />}
            Guardar cambios
          </Button>
        </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
