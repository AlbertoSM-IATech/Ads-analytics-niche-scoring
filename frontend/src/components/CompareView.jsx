import { useEffect, useMemo, useState } from "react";
import { compareDatasets } from "../lib/api";
import { useData } from "../context/DataContext";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "./ui/select";
import { fmtInt, fmtPct, fmtMoney, getMarketplace } from "../lib/format";
import { GitCompare, ArrowRight, TrendingUp, TrendingDown } from "lucide-react";

function Delta({ value, sym, pct, invertGood = false }) {
  if (value == null) return <span className="text-muted-foreground">—</span>;
  const isPos = value > 0;
  const good = invertGood ? !isPos : isPos;
  const cls = value === 0 ? "text-muted-foreground" : good ? "text-green-600 dark:text-green-400" : "text-destructive";
  const fn = sym ? (v) => fmtMoney(v, sym) : (pct ? fmtPct : fmtInt);
  return (
    <span className={`num font-semibold ${cls}`}>
      {isPos ? "+" : ""}{fn(value)}
    </span>
  );
}

export default function CompareView() {
  const { datasetsForMp, active, marketplace } = useData();
  const sym = getMarketplace(marketplace).symbol;
  const [bId, setBId] = useState(null);
  const [data, setData] = useState(null);

  const options = useMemo(
    () => datasetsForMp.filter((d) => d.id !== active?.id),
    [datasetsForMp, active]
  );

  useEffect(() => {
    if (options.length && !bId) setBId(options[0].id);
  }, [options, bId]);

  useEffect(() => {
    if (!active || !bId) return;
    compareDatasets(active.id, bId).then((r) => setData(r.data));
  }, [active, bId]);

  if (!active) return null;
  if (!options.length) {
    return (
      <div className="border border-dashed border-border p-8 text-center rounded-lg bg-card" data-testid="compare-empty">
        Necesitas al menos 2 datasets del mismo marketplace para comparar.
      </div>
    );
  }

  return (
    <div className="space-y-5 animate-fade-in" data-testid="compare-view">
      <div className="flex items-center flex-wrap gap-3">
        <GitCompare className="size-5 text-coral" />
        <div className="text-sm font-semibold truncate">{active.name}</div>
        <ArrowRight className="size-4 text-muted-foreground" />
        <Select value={bId || ""} onValueChange={setBId}>
          <SelectTrigger className="w-[280px] rounded-md" data-testid="compare-b-select">
            <SelectValue placeholder="Elige dataset…" />
          </SelectTrigger>
          <SelectContent>
            {options.map((d) => (
              <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {[
              ["impressions", "Impresiones", null, false],
              ["clicks", "Clicks", null, false],
              ["spend", "Gasto", sym, true],
              ["sales", "Ventas", sym, false],
              ["orders", "Pedidos", null, false],
              ["acos", "ACoS", null, true],
              ["roas", "ROAS", null, false],
              ["ctr", "CTR", null, false],
              ["cpc", "CPC", sym, true],
            ].map(([k, label, s, invertGood]) => (
              <div key={k} className="border border-border rounded-lg p-4 bg-card" data-testid={`cmp-${k}`}>
                <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">{label}</div>
                <div className="mt-2">
                  <Delta value={data.kpi_delta[k]} sym={s} pct={k === "acos" || k === "ctr"} invertGood={invertGood} />
                </div>
                <div className="text-[10px] text-muted-foreground num mt-1">
                  A: {s ? fmtMoney(data.a.kpis[k] || 0, s) : (k === "acos" || k === "ctr" ? fmtPct(data.a.kpis[k]) : fmtInt(data.a.kpis[k]))}
                  {" · "}B: {s ? fmtMoney(data.b.kpis[k] || 0, s) : (k === "acos" || k === "ctr" ? fmtPct(data.b.kpis[k]) : fmtInt(data.b.kpis[k]))}
                </div>
              </div>
            ))}
          </div>

          <div className="border border-border rounded-lg overflow-x-auto bg-card">
            <div className="px-4 py-3 border-b border-border flex items-center gap-2">
              <h3 className="text-sm font-semibold">Movers (top 30 por cambio)</h3>
              <span className="text-xs text-muted-foreground">Compara B − A para cada término</span>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-[10px] uppercase tracking-widest text-muted-foreground">
                <tr>
                  <th className="text-left px-3 py-2.5">Término</th>
                  <th className="text-right px-3 py-2.5">Gasto A</th>
                  <th className="text-right px-3 py-2.5">Gasto B</th>
                  <th className="text-right px-3 py-2.5">Δ Gasto</th>
                  <th className="text-right px-3 py-2.5">Ventas A</th>
                  <th className="text-right px-3 py-2.5">Ventas B</th>
                  <th className="text-right px-3 py-2.5">Δ Ventas</th>
                  <th className="text-right px-3 py-2.5">Δ ACoS</th>
                </tr>
              </thead>
              <tbody>
                {data.movers.map((r, i) => (
                  <tr key={i} className="border-t border-border hover:bg-muted/30" data-testid={`cmp-row-${i}`}>
                    <td className="px-3 py-2 max-w-[260px] truncate">{r.term}</td>
                    <td className="px-3 py-2 num text-right">{fmtMoney(r.a_spend, sym)}</td>
                    <td className="px-3 py-2 num text-right">{fmtMoney(r.b_spend, sym)}</td>
                    <td className="px-3 py-2 text-right"><Delta value={r.delta_spend} sym={sym} invertGood /></td>
                    <td className="px-3 py-2 num text-right">{fmtMoney(r.a_sales, sym)}</td>
                    <td className="px-3 py-2 num text-right">{fmtMoney(r.b_sales, sym)}</td>
                    <td className="px-3 py-2 text-right"><Delta value={r.delta_sales} sym={sym} /></td>
                    <td className="px-3 py-2 text-right"><Delta value={r.delta_acos} pct invertGood /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
