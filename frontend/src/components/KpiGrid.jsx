import { fmtInt, fmtPct, fmtMoney, getMarketplace } from "../lib/format";
import { useData } from "../context/DataContext";

const Tile = ({ label, value, accent, testid }) => (
  <div
    className="border border-border p-4 rounded-sm bg-card"
    data-testid={testid}
  >
    <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
      {label}
    </div>
    <div
      className={`mono text-2xl md:text-3xl font-semibold mt-1 tracking-tighter ${
        accent || ""
      }`}
    >
      {value}
    </div>
  </div>
);

export default function KpiGrid({ kpis }) {
  const { marketplace } = useData();
  const sym = getMarketplace(marketplace).symbol;
  if (!kpis)
    return (
      <div className="border border-border p-6 rounded-sm text-sm text-muted-foreground">
        Importa un CSV para ver KPIs.
      </div>
    );
  return (
    <div
      className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3"
      data-testid="kpi-grid"
    >
      <Tile label="Impresiones" value={fmtInt(kpis.impressions)} testid="kpi-impressions" />
      <Tile label="Clicks" value={fmtInt(kpis.clicks)} testid="kpi-clicks" />
      <Tile label="CTR" value={fmtPct(kpis.ctr)} testid="kpi-ctr" />
      <Tile label="Gasto" value={fmtMoney(kpis.spend, sym)} testid="kpi-spend" />
      <Tile label="Ventas" value={fmtMoney(kpis.sales, sym)} testid="kpi-sales" />
      <Tile label="Pedidos" value={fmtInt(kpis.orders)} testid="kpi-orders" />
      <Tile label="CPC" value={fmtMoney(kpis.cpc, sym)} testid="kpi-cpc" />
      <Tile
        label="ACoS"
        value={fmtPct(kpis.acos)}
        accent={kpis.acos > 40 ? "text-destructive" : kpis.acos > 25 ? "text-[hsl(var(--warning))]" : "text-[hsl(var(--success))]"}
        testid="kpi-acos"
      />
      <Tile
        label="ROAS"
        value={kpis.roas?.toFixed(2) || "0.00"}
        accent={kpis.roas >= 3 ? "text-[hsl(var(--success))]" : kpis.roas >= 1.5 ? "" : "text-destructive"}
        testid="kpi-roas"
      />
      <Tile label="CVR" value={fmtPct(kpis.cvr)} testid="kpi-cvr" />
    </div>
  );
}
