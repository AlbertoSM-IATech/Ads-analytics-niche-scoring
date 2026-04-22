import { useEffect, useMemo, useState } from "react";
import { getSearchTerms } from "../lib/api";
import { fmtInt, fmtPct, fmtMoney, getMarketplace } from "../lib/format";
import { useData } from "../context/DataContext";
import { Input } from "./ui/input";
import { Badge } from "./ui/badge";
import { Switch } from "./ui/switch";
import { Label } from "./ui/label";
import { Ban } from "lucide-react";

export default function SearchTermsTable({ datasetId }) {
  const { marketplace } = useData();
  const sym = getMarketplace(marketplace).symbol;
  const [rows, setRows] = useState([]);
  const [key, setKey] = useState("customer_search_term");
  const [q, setQ] = useState("");
  const [onlyNegatives, setOnlyNegatives] = useState(false);

  useEffect(() => {
    if (!datasetId) return;
    getSearchTerms(datasetId).then((r) => {
      setRows(r.data.rows || []);
      setKey(r.data.key);
    });
  }, [datasetId]);

  const filtered = useMemo(() => {
    return rows
      .filter((r) => (r[key] || "").toLowerCase().includes(q.toLowerCase()))
      .filter((r) => (onlyNegatives ? r.suggest_negative : true))
      .sort((a, b) => b.spend - a.spend);
  }, [rows, key, q, onlyNegatives]);

  const keyLabel = key === "customer_search_term" ? "Término del cliente" : "Targeting";

  return (
    <div className="space-y-3" data-testid="search-terms-table">
      <div className="flex flex-wrap items-center gap-4 justify-between">
        <Input
          placeholder="Buscar término…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs rounded-sm"
          data-testid="term-filter"
        />
        <div className="flex items-center gap-2">
          <Switch
            checked={onlyNegatives}
            onCheckedChange={setOnlyNegatives}
            id="only-neg"
            data-testid="toggle-only-negatives"
          />
          <Label htmlFor="only-neg" className="text-xs">
            Solo candidatas a keyword negativa
          </Label>
        </div>
      </div>
      <div className="border border-border rounded-sm overflow-x-auto bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/40">
            <tr className="text-[10px] uppercase tracking-widest text-muted-foreground">
              <th className="text-left px-3 py-2">{keyLabel}</th>
              <th className="text-right px-3 py-2">Impr.</th>
              <th className="text-right px-3 py-2">Clicks</th>
              <th className="text-right px-3 py-2">CTR</th>
              <th className="text-right px-3 py-2">Gasto</th>
              <th className="text-right px-3 py-2">Ventas</th>
              <th className="text-right px-3 py-2">Pedidos</th>
              <th className="text-right px-3 py-2">ACoS</th>
              <th className="text-left px-3 py-2">Señal</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r, i) => (
              <tr
                key={i}
                className="border-t border-border hover:bg-muted/30"
                data-testid={`term-row-${i}`}
              >
                <td className="px-3 py-2 max-w-[280px] truncate">{r[key] || "—"}</td>
                <td className="px-3 py-2 mono text-right">{fmtInt(r.impressions)}</td>
                <td className="px-3 py-2 mono text-right">{fmtInt(r.clicks)}</td>
                <td className="px-3 py-2 mono text-right">{fmtPct(r.ctr)}</td>
                <td className="px-3 py-2 mono text-right">{fmtMoney(r.spend, sym)}</td>
                <td className="px-3 py-2 mono text-right">{fmtMoney(r.sales, sym)}</td>
                <td className="px-3 py-2 mono text-right">{fmtInt(r.orders)}</td>
                <td className={`px-3 py-2 mono text-right ${r.acos > 40 ? "text-destructive" : ""}`}>
                  {fmtPct(r.acos)}
                </td>
                <td className="px-3 py-2">
                  {r.suggest_negative && (
                    <Badge variant="destructive" className="rounded-sm gap-1 text-[10px]" data-testid={`neg-badge-${i}`}>
                      <Ban className="size-3" /> Negativa sugerida
                    </Badge>
                  )}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={9} className="px-3 py-8 text-center text-sm text-muted-foreground">
                  Sin datos
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
