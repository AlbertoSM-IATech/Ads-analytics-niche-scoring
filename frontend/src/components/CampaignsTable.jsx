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
  { key: "orders", label: "Pedidos", type: "int" },
  { key: "cpc", label: "CPC", type: "money" },
  { key: "acos", label: "ACoS", type: "pct" },
  { key: "roas", label: "ROAS", type: "num" },
];

export default function CampaignsTable({ datasetId }) {
  const { marketplace } = useData();
  const sym = getMarketplace(marketplace).symbol;
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [sortKey, setSortKey] = useState("spend");
  const [sortDir, setSortDir] = useState("desc");

  useEffect(() => {
    if (!datasetId) return;
    getCampaigns(datasetId).then((r) => setRows(r.data || []));
  }, [datasetId]);

  const sorted = useMemo(() => {
    let data = rows.filter((r) =>
      (r.campaign || "").toLowerCase().includes(q.toLowerCase())
    );
    data.sort((a, b) => {
      const av = a[sortKey]; const bv = b[sortKey];
      if (typeof av === "number") return sortDir === "asc" ? av - bv : bv - av;
      return sortDir === "asc"
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
    return data;
  }, [rows, q, sortKey, sortDir]);

  const cellValue = (r, c) => {
    const v = r[c.key];
    switch (c.type) {
      case "int": return fmtInt(v);
      case "pct": return fmtPct(v);
      case "money": return fmtMoney(v, sym);
      case "num": return (v ?? 0).toFixed(2);
      default: return v;
    }
  };

  const toggleSort = (k) => {
    if (sortKey === k) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortKey(k); setSortDir("desc"); }
  };

  return (
    <div className="space-y-3" data-testid="campaigns-table">
      <div className="flex items-center justify-between">
        <Input
          placeholder="Filtrar campañas…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs rounded-sm"
          data-testid="campaign-filter"
        />
        <span className="text-xs text-muted-foreground mono">
          {sorted.length} campañas
        </span>
      </div>
      <div className="border border-border rounded-sm overflow-x-auto bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              {columns.map((c) => (
                <th
                  key={c.key}
                  onClick={() => toggleSort(c.key)}
                  className="text-left px-3 py-2 text-[10px] uppercase tracking-widest text-muted-foreground cursor-pointer select-none hover:text-foreground"
                  data-testid={`col-${c.key}`}
                >
                  <span className="inline-flex items-center gap-1">
                    {c.label}
                    <ArrowDownUp className="size-3 opacity-50" />
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => (
              <tr
                key={i}
                className="border-t border-border hover:bg-muted/30"
                data-testid={`campaign-row-${i}`}
              >
                {columns.map((c) => (
                  <td
                    key={c.key}
                    className={`px-3 py-2 ${c.type !== "str" ? "mono text-right" : ""}`}
                  >
                    {cellValue(r, c)}
                  </td>
                ))}
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="px-3 py-8 text-center text-sm text-muted-foreground">
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
