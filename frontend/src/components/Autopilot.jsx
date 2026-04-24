import { useEffect, useState } from "react";
import { getAutopilot, exportAutopilotUrl } from "../lib/api";
import { useData } from "../context/DataContext";
import { Button } from "./ui/button";
import {
  PauseCircle, TrendingUp, Shield, HelpCircle, Download, Loader2, Plane,
  Rocket, Crown, DollarSign,
} from "lucide-react";
import { fmtInt, fmtPct, fmtMoney, getMarketplace } from "../lib/format";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { InfoTooltip } from "./InfoTooltip";

const BUCKETS = [
  { key: "pause", label: "Pausar", icon: PauseCircle, cls: "border-red-300 bg-red-50 dark:bg-red-500/5 dark:border-red-500/30 text-red-700 dark:text-red-400" },
  { key: "scale", label: "Escalar", icon: TrendingUp, cls: "border-green-300 bg-green-50 dark:bg-green-500/5 dark:border-green-500/30 text-green-700 dark:text-green-400" },
  { key: "hold", label: "Mantener", icon: Shield, cls: "border-blue-300 bg-blue-50 dark:bg-blue-500/5 dark:border-blue-500/30 text-blue-700 dark:text-blue-400" },
  { key: "investigate", label: "Observar", icon: HelpCircle, cls: "border-amber-300 bg-amber-50 dark:bg-amber-500/5 dark:border-amber-500/30 text-amber-700 dark:text-amber-400" },
];

const PHASES = [
  { key: "lanzamiento", label: "Lanzamiento", icon: Rocket, desc: "1.7× PE · visibilidad", tip: "lanzamiento" },
  { key: "dominio", label: "Dominio", icon: Crown, desc: "1.2× PE · equilibrio", tip: "dominio" },
  { key: "beneficio", label: "Beneficio", icon: DollarSign, desc: "0.5× PE · rentabilidad", tip: "beneficio_fase" },
];

export default function Autopilot({ datasetId }) {
  const { marketplace } = useData();
  const sym = getMarketplace(marketplace).symbol;
  const [phase, setPhase] = useState(
    () => localStorage.getItem("autopilot_phase") || "dominio"
  );
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("pause");

  const load = async (p = phase) => {
    setLoading(true);
    try {
      const r = await getAutopilot(datasetId, p);
      setData(r.data);
      const first = BUCKETS.find((b) => (r.data.counts[b.key] || 0) > 0);
      if (first) setTab(first.key);
    } finally { setLoading(false); }
  };

  useEffect(() => {
    localStorage.setItem("autopilot_phase", phase);
    if (datasetId) load(phase);
    /* eslint-disable-next-line */
  }, [datasetId, phase]);

  if (loading || !data) {
    return <div className="py-12 flex justify-center"><Loader2 className="size-8 animate-spin text-coral" /></div>;
  }

  return (
    <div className="space-y-5 animate-fade-in" data-testid="autopilot">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Plane className="size-5 text-coral" />
          <h2 className="font-heading text-lg font-semibold">Piloto automático</h2>
          <span className="text-xs text-muted-foreground">
            PE {data.acos_equilibrio != null ? `${data.acos_equilibrio.toFixed(1)}%` : "—"}
            {data.target_acos != null && ` · Objetivo fase: ${data.target_acos.toFixed(1)}%`}
          </span>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="rounded-md" onClick={() => load()} data-testid="refresh-autopilot">
            Recalcular
          </Button>
          <Button asChild className="rounded-md bg-coral hover:bg-coral-500 text-white" data-testid="export-autopilot-btn">
            <a href={`${exportAutopilotUrl(datasetId)}?phase=${phase}`} download>
              <Download className="size-4 mr-1.5" /> Exportar Bulk Sheet
            </a>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3" data-testid="phase-selector">
        {PHASES.map(({ key, label, icon: Icon, desc, tip }) => (
          <button
            key={key}
            onClick={() => setPhase(key)}
            className={`border rounded-lg p-4 text-left transition-all ${phase === key
              ? "border-coral bg-coral/10 ring-2 ring-coral"
              : "border-border bg-card hover:border-coral/40"}`}
            data-testid={`phase-${key}`}
          >
            <div className="flex items-center gap-2">
              <Icon className="size-4 text-coral" />
              <span className="font-semibold text-sm">{label}</span>
              <InfoTooltip content={tip} />
            </div>
            <div className="text-xs text-muted-foreground mt-1">{desc}</div>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {BUCKETS.map(({ key, label, icon: Icon, cls }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`border rounded-lg p-4 text-left transition-all ${cls} ${tab === key ? "ring-2 ring-coral" : ""}`}
            data-testid={`autopilot-${key}`}
          >
            <div className="flex items-center gap-2">
              <Icon className="size-4" />
              <span className="text-sm font-semibold">{label}</span>
            </div>
            <div className="num text-3xl font-bold mt-2">{data.counts[key] || 0}</div>
          </button>
        ))}
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="grid grid-cols-4">
          {BUCKETS.map(({ key, label }) => (
            <TabsTrigger key={key} value={key} data-testid={`tab-${key}`}>
              {label} ({data.counts[key] || 0})
            </TabsTrigger>
          ))}
        </TabsList>
        {BUCKETS.map(({ key }) => (
          <TabsContent key={key} value={key} className="py-4">
            <div className="border border-border rounded-lg overflow-x-auto bg-card">
              <table className="w-full text-sm">
                <thead className="bg-muted/40">
                  <tr className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
                    <th className="text-left px-3 py-2.5">Término</th>
                    <th className="text-right px-3 py-2.5">Clicks</th>
                    <th className="text-right px-3 py-2.5">Pedidos</th>
                    <th className="text-right px-3 py-2.5">Gasto</th>
                    <th className="text-right px-3 py-2.5">Ventas</th>
                    <th className="text-right px-3 py-2.5">ACoS</th>
                    <th className="text-right px-3 py-2.5">Puja</th>
                    <th className="text-left px-3 py-2.5">Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.actions[key] || []).map((r, i) => (
                    <tr key={i} className="border-t border-border hover:bg-muted/30" data-testid={`ap-row-${key}-${i}`}>
                      <td className="px-3 py-2 max-w-[260px]">
                        <div className="truncate font-medium">{r.term}</div>
                        {r.campaign && <div className="text-[10px] text-muted-foreground truncate">{r.campaign}</div>}
                      </td>
                      <td className="px-3 py-2 num text-right">{fmtInt(r.clicks)}</td>
                      <td className="px-3 py-2 num text-right">{fmtInt(r.orders)}</td>
                      <td className="px-3 py-2 num text-right">{fmtMoney(r.spend, sym)}</td>
                      <td className="px-3 py-2 num text-right">{fmtMoney(r.sales, sym)}</td>
                      <td className="px-3 py-2 num text-right">
                        {r.acos_actual == null ? "—" : fmtPct(r.acos_actual)}
                      </td>
                      <td className="px-3 py-2 num text-right">
                        {r.bid_delta_pct != null ? (
                          <span className={r.bid_delta_pct > 0 ? "text-green-600" : "text-destructive"}>
                            {r.bid_delta_pct > 0 ? "+" : ""}{r.bid_delta_pct}%
                          </span>
                        ) : "—"}
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">{r.rationale}</td>
                    </tr>
                  ))}
                  {(data.actions[key] || []).length === 0 && (
                    <tr>
                      <td colSpan={8} className="px-3 py-10 text-center text-sm text-muted-foreground">
                        Sin recomendaciones en este grupo.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
