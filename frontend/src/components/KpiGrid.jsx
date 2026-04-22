import { fmtInt, fmtPct, fmtMoney, getMarketplace } from "../lib/format";
import { useData } from "../context/DataContext";
import { InfoTooltip } from "./InfoTooltip";

const Tile = ({ label, value, accent, sub, testid, tooltip }) => (
  <div
    className="border border-border p-5 rounded-lg bg-card coral-card-hover animate-fade-in"
    data-testid={testid}
  >
    <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold flex items-center gap-1.5">
      {label}
      {tooltip && <InfoTooltip content={tooltip} />}
    </div>
    <div className={`num text-3xl font-semibold mt-2 tracking-tight ${accent || ""}`}>
      {value}
    </div>
    {sub && <div className="text-[11px] text-muted-foreground mt-1">{sub}</div>}
  </div>
);

export default function KpiGrid({ kpis, acosEquilibrio }) {
  const { marketplace } = useData();
  const sym = getMarketplace(marketplace).symbol;
  if (!kpis)
    return (
      <div className="border border-dashed border-border p-8 rounded-lg text-sm text-muted-foreground text-center bg-card">
        Importa un CSV para ver KPIs.
      </div>
    );
  const pe = acosEquilibrio;
  const acosAccent =
    pe && kpis.acos
      ? kpis.acos <= pe ? "text-green-600 dark:text-green-400"
        : kpis.acos <= pe * 1.2 ? "text-amber-500" : "text-destructive"
      : kpis.acos > 40 ? "text-destructive" : kpis.acos > 25 ? "text-amber-500" : "text-green-600 dark:text-green-400";
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4" data-testid="kpi-grid">
      <Tile label="Impresiones" value={fmtInt(kpis.impressions)} testid="kpi-impressions" />
      <Tile label="Clicks" value={fmtInt(kpis.clicks)} testid="kpi-clicks" />
      <Tile label="CTR" value={fmtPct(kpis.ctr)} testid="kpi-ctr" tooltip="ctr" />
      <Tile label="Gasto" value={fmtMoney(kpis.spend, sym)} testid="kpi-spend" />
      <Tile label="Ventas" value={fmtMoney(kpis.sales, sym)} testid="kpi-sales" />
      <Tile label="Pedidos" value={fmtInt(kpis.orders)} testid="kpi-orders" />
      <Tile label="CPC" value={fmtMoney(kpis.cpc, sym)} testid="kpi-cpc" tooltip="cpc" />
      <Tile
        label="ACoS"
        value={fmtPct(kpis.acos)}
        accent={acosAccent}
        sub={pe ? `PE: ${fmtPct(pe)}` : undefined}
        testid="kpi-acos"
        tooltip="acos"
      />
      <Tile
        label="ROAS"
        value={(kpis.roas ?? 0).toFixed(2)}
        accent={kpis.roas >= 3 ? "text-green-600 dark:text-green-400" : kpis.roas >= 1.5 ? "text-amber-500" : "text-destructive"}
        testid="kpi-roas"
        tooltip="roas"
      />
      <Tile label="CVR" value={fmtPct(kpis.cvr)} testid="kpi-cvr" tooltip="cvr" />
    </div>
  );
}
