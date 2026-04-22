import Header from "../components/Header";
import KpiGrid from "../components/KpiGrid";
import ChartsPanel from "../components/ChartsPanel";
import AiPanel from "../components/AiPanel";
import ImportZone from "../components/ImportZone";
import HistoryPanel from "../components/HistoryPanel";
import CampaignsTable from "../components/CampaignsTable";
import BookInfoPanel from "../components/BookInfoPanel";
import KeywordsUnified from "../components/KeywordsUnified";
import { useData } from "../context/DataContext";
import { Routes, Route, useLocation } from "react-router-dom";

function Empty({ msg }) {
  return (
    <div className="border border-dashed border-border p-12 text-center rounded-lg bg-card animate-fade-in" data-testid="empty-state">
      <div className="text-sm text-muted-foreground">{msg}</div>
    </div>
  );
}

function DashboardView() {
  const { active } = useData();
  const pe = active?.book_economy?.precio_libro && active?.book_economy?.regalias_por_venta
    ? (active.book_economy.regalias_por_venta / active.book_economy.precio_libro) * 100
    : null;
  return (
    <div className="space-y-6 animate-fade-in" data-testid="view-dashboard">
      <KpiGrid kpis={active?.kpis} acosEquilibrio={pe} />
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
  if (path.startsWith("/book")) return { t: "Mi libro", s: "Economía y datos del libro" };
  if (path.startsWith("/keywords")) return { t: "Keywords unificadas", s: "con ACoS del siguiente click" };
  if (path.startsWith("/campaigns")) return { t: "Campañas", s: "análisis agregado" };
  if (path.startsWith("/ai")) return { t: "IA", s: "recomendaciones con Claude" };
  if (path.startsWith("/history")) return { t: "Historial", s: "datasets importados" };
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
            path="/ai"
            element={active ? <AiPanel datasetId={active.id} initialRecs={active.ai_recommendations} /> : <Empty msg="Importa un CSV para generar recomendaciones." />}
          />
          <Route path="/history" element={<HistoryPanel />} />
        </Routes>
      </div>
    </div>
  );
}
