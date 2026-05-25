import Header from "../components/Header";
import KpiGrid from "../components/KpiGrid";
import ChartsPanel from "../components/ChartsPanel";
import AiPanel from "../components/AiPanel";
import ImportZone from "../components/ImportZone";
import CampaignsTable from "../components/CampaignsTable";
import BookInfoPanel from "../components/BookInfoPanel";
import KeywordsUnified from "../components/KeywordsUnified";
import DashboardBlocks from "../components/DashboardBlocks";
import DistributionChart from "../components/DistributionChart";
import ActionsPage from "../components/ActionsPage";
import { useData } from "../context/DataContext";
import { Routes, Route, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { getKeywordsUnified } from "../lib/api";

function Empty({ msg }) {
  return (
    <div className="border border-dashed border-border p-12 text-center rounded-lg bg-card animate-fade-in" data-testid="empty-state">
      <div className="text-sm text-muted-foreground">{msg}</div>
    </div>
  );
}

function DashboardView() {
  const { active } = useData();
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    if (!active?.id) { setSummary(null); return; }
    getKeywordsUnified(active.id).then((r) => setSummary(r.data.summary || null));
  }, [active?.id, active?.book_economy?.precio_libro, active?.book_economy?.regalias_por_venta]);

  const pe = active?.book_economy?.precio_libro && active?.book_economy?.regalias_por_venta
    ? (active.book_economy.regalias_por_venta / active.book_economy.precio_libro) * 100
    : null;
  return (
    <div className="space-y-6 animate-fade-in" data-testid="view-dashboard">
      <KpiGrid kpis={active?.kpis} acosEquilibrio={pe} />
      {active && (
        <>
          <DashboardBlocks summary={summary} />
          <DistributionChart summary={summary} />
        </>
      )}
      {active ? (
        <>
          <ChartsPanel datasetId={active.id} />
          <AiPanel datasetId={active.id} initialRecs={active.ai_recommendations} />
        </>
      ) : (
        <Empty msg="Importa un CSV de Amazon Ads para empezar." />
      )}
    </div>
  );
}

const titleFor = (path) => {
  if (path.startsWith("/import")) return { t: "Importar datos", s: "Amazon Ads CSV/XLSX" };
  if (path.startsWith("/book")) return { t: "Libro", s: "Fase, economía e información" };
  if (path.startsWith("/keywords")) return { t: "Keywords", s: "edición inline + panel lateral" };
  if (path.startsWith("/campaigns")) return { t: "Campañas", s: "análisis agregado" };
  if (path.startsWith("/acciones")) return { t: "Acciones", s: "recomendaciones priorizadas (read-only)" };
  return { t: "Dashboard", s: "resumen de rendimiento" };
};

export default function Dashboard() {
  const location = useLocation();
  const { active } = useData();
  const { t, s } = titleFor(location.pathname);
  return (
    <div className="flex-1 min-w-0">
      <Header title={t} subtitle={s} />
      <div className="p-6">
        <Routes>
          <Route path="/" element={<DashboardView />} />
          <Route path="/import" element={<ImportZone />} />
          <Route path="/book" element={<BookInfoPanel />} />
          <Route
            path="/keywords"
            element={active ? <KeywordsUnified datasetId={active.id} /> : <Empty msg="Importa un CSV para ver tus keywords." />}
          />
          <Route
            path="/campaigns"
            element={active ? <CampaignsTable datasetId={active.id} /> : <Empty msg="Importa un CSV para ver campañas." />}
          />
          <Route
            path="/acciones"
            element={<ActionsPage datasetId={active?.id} />}
          />
        </Routes>
      </div>
    </div>
  );
}
