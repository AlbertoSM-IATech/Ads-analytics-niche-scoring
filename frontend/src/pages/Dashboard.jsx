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
import GettingStartedCard from "../components/GettingStartedCard";
import { useData } from "../context/DataContext";
import { Routes, Route, useLocation, NavLink } from "react-router-dom";
import { useEffect, useState } from "react";
import { getKeywordsUnified } from "../lib/api";
import { Upload, BookOpen } from "lucide-react";

function Empty({ msg, actions }) {
  return (
    <div className="border border-dashed border-border p-12 text-center rounded-lg bg-card animate-fade-in space-y-3" data-testid="empty-state">
      <div className="text-sm text-muted-foreground max-w-md mx-auto">{msg}</div>
      {actions && <div className="flex items-center justify-center gap-2 flex-wrap">{actions}</div>}
    </div>
  );
}

function EmptyActionLink({ to, icon: Icon, children, testid }) {
  return (
    <NavLink
      to={to}
      className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs hover:border-coral hover:text-coral transition-colors"
      data-testid={testid}
    >
      {Icon && <Icon className="size-3.5" />}
      {children}
    </NavLink>
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
      {!active && <GettingStartedCard />}
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
        <Empty
          msg="Aún no hay datasets importados. Sube un reporte de Amazon Ads para empezar el análisis."
          actions={
            <>
              <EmptyActionLink to="/import" icon={Upload} testid="empty-cta-import">Importar CSV</EmptyActionLink>
              <EmptyActionLink to="/book" icon={BookOpen} testid="empty-cta-book">Configurar libro</EmptyActionLink>
            </>
          }
        />
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
            element={active ? <KeywordsUnified datasetId={active.id} /> : (
              <Empty
                msg="Aún no hay términos importados. Sube un reporte de Amazon Ads para empezar el análisis."
                actions={<EmptyActionLink to="/import" icon={Upload} testid="empty-keywords-import">Importar CSV</EmptyActionLink>}
              />
            )}
          />
          <Route
            path="/campaigns"
            element={active ? <CampaignsTable datasetId={active.id} /> : (
              <Empty
                msg="Sin datos de campañas todavía. Importa un reporte de Amazon Ads para ver el resumen agregado."
                actions={<EmptyActionLink to="/import" icon={Upload} testid="empty-camp-import">Importar CSV</EmptyActionLink>}
              />
            )}
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
