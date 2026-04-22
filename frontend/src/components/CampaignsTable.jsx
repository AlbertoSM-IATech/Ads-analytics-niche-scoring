import { useEffect, useMemo, useState } from "react";
import { getCampaigns } from "../lib/api";
import { fmtInt, fmtPct, fmtMoney, getMarketplace } from "../lib/format";
import { useData } from "../context/DataContext";
import { Input } from "./ui/input";
import { ArrowDownUp } from "lucide-react";

const columns = [
  { key: "campaign", label: "Campaña", type: "str" },
  { key: "impressions", label: "Impr.", type: "int" },
  { key: "clicks", label: "Clicks", type: "int" },
  { key: "ctr", label: "CTR", type: "pct" },
  { key: "spend", label: "Gasto", type: "money" },
  { key: "sales", label: "Ventas", type: "money" },
  { key: "orders", label: "Ped.", type: "int" },
  { key: "cpc", label: "CPC", type: "money" },
  { key: "acos", label: "ACoS", type: "pct" },
  { key: "acos_siguiente", label: "ACoS +1", type: "pct" },
  { key: "roas", label: "ROAS", type: "num" },
];

export default function CampaignsTable({ datasetId }) {
  const { marketplace, active } = useData();
  const sym = getMarketplace(marketplace).symbol;
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [sortKey, setSortKey] = useState("spend");
  const [sortDir, setSortDir] = useState("desc");

  const pe = active?.book_economy?.precio_libro && active?.book_economy?.regalias_por_venta
    ? (active.book_economy.regalias_por_venta / active.book_economy.precio_libro) * 100
    : null;

  useEffect(() => {
    if (!datasetId) return;
    getCampaigns(datasetId).then((r) => setRows(r.data || []));
  }, [datasetId, active?.book_economy?.precio_libro, active?.book_economy?.regalias_por_venta]);

  const sorted = useMemo(() => {
    const data = rows.filter((r) => (r.campaign || "").toLowerCase().includes(q.toLowerCase()));
    data.sort((a, b) => {
      const av = a[sortKey] ?? 0; const bv = b[sortKey] ?? 0;
      if (typeof av === "number" || typeof bv === "number") {
        return sortDir === "asc" ? (av ?? 0) - (bv ?? 0) : (bv ?? 0) - (av ?? 0);
      }
      return sortDir === "asc"
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
    return data;
  }, [rows, q, sortKey, sortDir]);

  const toggleSort = (k) => {
    if (sortKey === k) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortKey(k); setSortDir("desc"); }
  };

  const acosColor = (v) => {
    if (v == null || v === 0) return "";
    if (pe == null) return v > 40 ? "text-destructive" : v > 25 ? "text-amber-500" : "text-green-600 dark:text-green-400";
    return v <= pe ? "text-green-600 dark:text-green-400" : "text-destructive";
  };

  const cellValue = (r, c) => {
    const v = r[c.key];
    if (v == null && c.key === "acos_siguiente") return "—";
    switch (c.type) {
      case "int": return <span className="num">{fmtInt(v)}</span>;
      case "pct": return <span className={`num ${c.key.startsWith("acos") ? acosColor(v) : ""}`}>{fmtPct(v)}</span>;
      case "money": return <span className="num">{fmtMoney(v, sym)}</span>;
      case "num": return <span className="num">{(v ?? 0).toFixed(2)}</span>;
      default: return v;
    }
  };

  return (
    <div className="space-y-4 animate-fade-in" data-testid="campaigns-table">
      <div className="flex items-center justify-between">
        <Input
          placeholder="Filtrar campañas…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs rounded-md"
          data-testid="campaign-filter"
        />
        <span className="text-xs text-muted-foreground num">{sorted.length} campañas</span>
      </div>
      <div className="border border-border rounded-lg overflow-x-auto bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              {columns.map((c) => (
                <th
                  key={c.key}
                  onClick={() => toggleSort(c.key)}
                  className="text-left px-3 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold cursor-pointer select-none hover:text-foreground whitespace-nowrap"
                  data-testid={`col-${c.key}`}
                >
                  <span className="inline-flex items-center gap-1">
                    {c.label}
                    <ArrowDownUp className="size-3 opacity-40" />
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => (
              <tr key={i} className="border-t border-border hover:bg-muted/30" data-testid={`campaign-row-${i}`}>
                {columns.map((c) => (
                  <td
                    key={c.key}
                    className={`px-3 py-2 ${c.type !== "str" ? "text-right" : ""}`}
                  >
                    {cellValue(r, c)}
                  </td>
                ))}
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="px-3 py-10 text-center text-sm text-muted-foreground">
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
