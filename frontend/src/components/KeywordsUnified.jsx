import { useEffect, useMemo, useState } from "react";
import { getKeywordsUnified } from "../lib/api";
import { useData } from "../context/DataContext";
import { Input } from "./ui/input";
import { Switch } from "./ui/switch";
import { Label } from "./ui/label";
import { fmtInt, fmtPct, fmtMoney, getMarketplace } from "../lib/format";
import { ArrowDownUp, AlertCircle } from "lucide-react";
import { Link } from "react-router-dom";

const BADGE_STYLES = {
  "bajo-pe": { cls: "bg-green-100 text-green-700 border-green-200 dark:bg-green-500/10 dark:text-green-400 dark:border-green-500/30", label: "Bajo PE", desc: "ACoS por debajo del equilibrio" },
  "recuperable": { cls: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/30", label: "Recuperable", desc: "El siguiente click con venta vuelve al equilibrio" },
  "en-perdida": { cls: "bg-red-100 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/30", label: "En pérdida", desc: "ACoS siguiente click > equilibrio" },
  "sin-datos": { cls: "bg-neutral-100 text-neutral-600 border-neutral-200 dark:bg-neutral-700/40 dark:text-neutral-400 dark:border-neutral-600", label: "Sin datos", desc: "Configura economía del libro" },
};

const Money = ({ v, sym, neg = false }) => (
  <span className={`num ${neg && v != null && v < 0 ? "text-destructive" : ""}`}>
    {v == null ? "—" : fmtMoney(v, sym)}
  </span>
);

const Pct = ({ v, color }) => (
  <span className={`num ${color || ""}`}>{v == null ? "—" : fmtPct(v)}</span>
);

const cols = [
  { k: "term", label: "Término" },
  { k: "impressions", label: "Impr." },
  { k: "clicks", label: "Clicks" },
  { k: "ctr", label: "CTR" },
  { k: "cpc", label: "CPC" },
  { k: "spend", label: "Gasto" },
  { k: "sales", label: "Ventas" },
  { k: "orders", label: "Ped." },
  { k: "cvr", label: "CVR" },
  { k: "acos_actual", label: "ACoS" },
  { k: "acos_siguiente", label: "ACoS +1 click" },
  { k: "beneficio_ahora", label: "Beneficio" },
  { k: "beneficio_siguiente", label: "Benef. +1 click" },
  { k: "badge", label: "Estado" },
];

export default function KeywordsUnified({ datasetId }) {
  const { marketplace } = useData();
  const sym = getMarketplace(marketplace).symbol;
  const [data, setData] = useState(null);
  const [q, setQ] = useState("");
  const [onlyLoss, setOnlyLoss] = useState(false);
  const [sortKey, setSortKey] = useState("spend");
  const [sortDir, setSortDir] = useState("desc");

  useEffect(() => {
    if (!datasetId) return;
    getKeywordsUnified(datasetId).then((r) => setData(r.data));
  }, [datasetId]);

  const rows = useMemo(() => {
    if (!data) return [];
    let arr = data.rows.filter((r) => (r.term || "").toLowerCase().includes(q.toLowerCase()));
    if (onlyLoss) arr = arr.filter((r) => r.badge === "en-perdida");
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
  }, [data, q, onlyLoss, sortKey, sortDir]);

  const toggleSort = (k) => {
    if (sortKey === k) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortKey(k); setSortDir("desc"); }
  };

  const pe = data?.acos_equilibrio;
  const acosColor = (v) =>
    v == null ? "" : pe == null ? "" : v <= pe ? "text-green-600 dark:text-green-400" : "text-destructive";

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
        <Input
          placeholder="Buscar keyword…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs rounded-md"
          data-testid="kw-filter"
        />
        <div className="flex items-center gap-5">
          {pe != null && (
            <div className="text-xs">
              <span className="text-muted-foreground mr-1">PE:</span>
              <span className="num font-semibold text-coral">{fmtPct(pe)}</span>
            </div>
          )}
          <div className="flex items-center gap-2">
            <Switch checked={onlyLoss} onCheckedChange={setOnlyLoss} id="only-loss" data-testid="toggle-only-loss" />
            <Label htmlFor="only-loss" className="text-xs">Solo en pérdida</Label>
          </div>
          <span className="text-xs text-muted-foreground num">{rows.length} keywords</span>
        </div>
      </div>

      <div className="border border-border rounded-lg overflow-x-auto bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 sticky top-0">
            <tr>
              {cols.map((c) => (
                <th
                  key={c.k}
                  onClick={() => toggleSort(c.k)}
                  className="text-left px-3 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold cursor-pointer select-none hover:text-foreground whitespace-nowrap"
                  data-testid={`kw-col-${c.k}`}
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
            {rows.map((r, i) => {
              const b = BADGE_STYLES[r.badge] || BADGE_STYLES["sin-datos"];
              return (
                <tr key={i} className="border-t border-border hover:bg-muted/30" data-testid={`kw-row-${i}`}>
                  <td className="px-3 py-2 max-w-[260px] truncate">{r.term}</td>
                  <td className="px-3 py-2 num text-right">{fmtInt(r.impressions)}</td>
                  <td className="px-3 py-2 num text-right">{fmtInt(r.clicks)}</td>
                  <td className="px-3 py-2 num text-right">{fmtPct(r.ctr)}</td>
                  <td className="px-3 py-2 num text-right">{fmtMoney(r.cpc, sym)}</td>
                  <td className="px-3 py-2 num text-right">{fmtMoney(r.spend, sym)}</td>
                  <td className="px-3 py-2 num text-right">{fmtMoney(r.sales, sym)}</td>
                  <td className="px-3 py-2 num text-right">{fmtInt(r.orders)}</td>
                  <td className="px-3 py-2 num text-right">{fmtPct(r.cvr)}</td>
                  <td className="px-3 py-2 text-right"><Pct v={r.acos_actual} color={acosColor(r.acos_actual)} /></td>
                  <td className="px-3 py-2 text-right" data-testid={`kw-acos-next-${i}`}><Pct v={r.acos_siguiente} color={acosColor(r.acos_siguiente)} /></td>
                  <td className="px-3 py-2 text-right"><Money v={r.beneficio_ahora} sym={sym} neg /></td>
                  <td className="px-3 py-2 text-right"><Money v={r.beneficio_siguiente} sym={sym} neg /></td>
                  <td className="px-3 py-2">
                    <span className={`badge-pill ${b.cls}`} title={b.desc} data-testid={`kw-badge-${i}`}>
                      {b.label}
                    </span>
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
    </div>
  );
}
