import { useEffect, useMemo, useState } from "react";
import { getKeywordsUnified } from "../lib/api";
import { useData } from "../context/DataContext";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { fmtInt } from "../lib/format";
import { Sparkles, Target, AlertCircle } from "lucide-react";
import KeywordDetailSheet from "./KeywordDetailSheet";
import { Link } from "react-router-dom";

const scoreColor = (n) =>
  n >= 80 ? "bg-green-500" : n >= 65 ? "bg-blue-500" : n >= 45 ? "bg-amber-500" : n >= 25 ? "bg-orange-500" : "bg-red-500";
const scoreBadge = (n) =>
  n >= 80 ? "border-green-300 bg-green-50 text-green-700 dark:bg-green-500/10 dark:border-green-500/30 dark:text-green-400"
  : n >= 65 ? "border-blue-300 bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:border-blue-500/30 dark:text-blue-400"
  : n >= 45 ? "border-amber-300 bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:border-amber-500/30 dark:text-amber-400"
  : n >= 25 ? "border-orange-300 bg-orange-50 text-orange-700 dark:bg-orange-500/10 dark:border-orange-500/30 dark:text-orange-400"
  : "border-red-300 bg-red-50 text-red-700 dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-400";

export default function NicheStudy({ datasetId }) {
  const { active } = useData();
  const [data, setData] = useState(null);
  const [q, setQ] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [selectedTerm, setSelectedTerm] = useState(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const load = () => {
    if (!datasetId) return;
    getKeywordsUnified(datasetId).then((r) => setData(r.data));
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [datasetId, active?.book_economy?.precio_libro]);

  const rows = useMemo(() => {
    if (!data) return [];
    return data.rows
      .filter((r) => (r.term || "").toLowerCase().includes(q.toLowerCase()))
      .filter((r) => (r.market_score || 0) >= minScore)
      .sort((a, b) => (b.market_score || 0) - (a.market_score || 0));
  }, [data, q, minScore]);

  const stats = useMemo(() => {
    if (!rows.length) return null;
    const avg = rows.reduce((a, r) => a + (r.market_score || 0), 0) / rows.length;
    const best = rows[0];
    const excellent = rows.filter((r) => (r.market_score || 0) >= 80).length;
    const good = rows.filter((r) => (r.market_score || 0) >= 65 && (r.market_score || 0) < 80).length;
    return { avg: Math.round(avg), best, excellent, good, total: rows.length };
  }, [rows]);

  const anyDataScored = data?.rows?.some((r) => r.search_volume || r.competitors);

  return (
    <div className="space-y-4 animate-fade-in" data-testid="niche-study">
      {!anyDataScored && (
        <div className="border border-amber-300 dark:border-amber-500/40 bg-amber-50 dark:bg-amber-500/5 p-3 rounded-md flex items-start gap-2 text-sm" data-testid="niche-empty-warning">
          <AlertCircle className="size-4 mt-0.5 text-amber-600" />
          <div>
            Ninguna keyword tiene datos de nicho todavía. Abre una keyword y completa el volumen, competidores y checks en la pestaña <span className="font-semibold">Estudio de KW</span>.
          </div>
        </div>
      )}

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="border border-border rounded-lg p-4 bg-card">
            <div className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">Score medio</div>
            <div className="num text-3xl font-semibold mt-1">{stats.avg}</div>
          </div>
          <div className="border border-border rounded-lg p-4 bg-card">
            <div className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">Excelentes (≥80)</div>
            <div className="num text-3xl font-semibold mt-1 text-green-600">{stats.excellent}</div>
          </div>
          <div className="border border-border rounded-lg p-4 bg-card">
            <div className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">Buenas (65-79)</div>
            <div className="num text-3xl font-semibold mt-1 text-blue-600">{stats.good}</div>
          </div>
          <div className="border border-border rounded-lg p-4 bg-card">
            <div className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">Mejor nicho</div>
            <div className="text-sm font-semibold truncate mt-1">{stats.best.term}</div>
            <div className="num text-xs text-muted-foreground">Score: {stats.best.market_score || 0}</div>
          </div>
        </div>
      )}

      <div className="flex items-center gap-3 flex-wrap">
        <Input placeholder="Buscar keyword…" value={q} onChange={(e) => setQ(e.target.value)} className="max-w-xs rounded-md" data-testid="niche-filter" />
        <div className="flex items-center gap-2 text-xs">
          <span className="text-muted-foreground">Score ≥</span>
          <input type="range" min={0} max={100} step={5} value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} className="w-32" data-testid="niche-score-slider" />
          <span className="num font-semibold w-8">{minScore}</span>
        </div>
        <span className="text-xs text-muted-foreground ml-auto num">{rows.length} keywords</span>
      </div>

      <div className="border border-border rounded-lg overflow-x-auto bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/40">
            <tr className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
              <th className="text-left px-3 py-2.5">Término</th>
              <th className="text-right px-3 py-2.5">Volumen</th>
              <th className="text-right px-3 py-2.5">Competidores</th>
              <th className="text-right px-3 py-2.5">Precio</th>
              <th className="text-right px-3 py-2.5">Regalía</th>
              <th className="text-center px-3 py-2.5">Demanda</th>
              <th className="text-center px-3 py-2.5">Competencia</th>
              <th className="text-left px-3 py-2.5">Score</th>
              <th className="text-left px-3 py-2.5">Estado</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-t border-border hover:bg-muted/30" data-testid={`niche-row-${i}`}>
                <td className="px-3 py-2">
                  <button onClick={() => { setSelectedTerm(r.term); setSheetOpen(true); }} className="font-medium hover:text-coral text-left" data-testid={`niche-term-${i}`}>
                    {r.term}
                  </button>
                </td>
                <td className="px-3 py-2 num text-right">{fmtInt(r.search_volume)}</td>
                <td className="px-3 py-2 num text-right">{fmtInt(r.competitors)}</td>
                <td className="px-3 py-2 num text-right">{(r.kw_price || 0).toFixed(2)}</td>
                <td className="px-3 py-2 num text-right">{(r.kw_royalties || 0).toFixed(2)}</td>
                <td className="px-3 py-2 num text-center">{r.demand_checks || 0}/6</td>
                <td className="px-3 py-2 num text-center">{r.competition_checks || 0}/3</td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                      <div className={`h-full ${scoreColor(r.market_score || 0)}`} style={{ width: `${r.market_score || 0}%` }} />
                    </div>
                    <span className="num font-semibold w-8">{r.market_score || 0}</span>
                  </div>
                </td>
                <td className="px-3 py-2">
                  <span className={`badge-pill border ${scoreBadge(r.market_score || 0)}`}>
                    {r.score_label ? r.score_label.replace("-", " ") : "—"}
                  </span>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={9} className="px-3 py-10 text-center text-sm text-muted-foreground">
                  Sin resultados.{" "}
                  {!anyDataScored && (
                    <Link to="/keywords" className="text-coral underline">
                      Ir a Keywords →
                    </Link>
                  )}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="text-[11px] text-muted-foreground flex items-center gap-1.5">
        <Sparkles className="size-3" /> El Market Score combina volumen, competidores, precio, regalías y tus checks de demanda/competencia.
      </p>

      <KeywordDetailSheet
        open={sheetOpen}
        onClose={() => { setSheetOpen(false); load(); }}
        term={selectedTerm}
        initialTab="nicho"
      />
    </div>
  );
}
