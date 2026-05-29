import { NavLink } from "react-router-dom";
import { BookOpen, Upload, Target, ListChecks, Download, ArrowRight, ChevronDown, ChevronRight, Sparkles } from "lucide-react";
import { useState, useEffect } from "react";

const STEPS = [
  {
    n: 1,
    icon: BookOpen,
    title: "Configura la economía del libro",
    desc: "Marketplace, formato, regalía neta y ACoS de equilibrio. Sin esto el motor solo puede esperar.",
    to: "/book",
    cta: "Ir a Libro",
    testid: "step-book",
  },
  {
    n: 2,
    icon: Upload,
    title: "Importa tus datos de Amazon Ads",
    desc: "CSV o XLSX del Search Term Report, Campaign Report o Helium10/Publisher Rocket.",
    to: "/import",
    cta: "Importar CSV",
    testid: "step-import",
  },
  {
    n: 3,
    icon: Target,
    title: "Revisa keywords y términos",
    desc: "Marca la relevancia, ajusta campañas y observa Consumo PE y Beneficio KDP por término.",
    to: "/keywords",
    cta: "Ver keywords",
    testid: "step-keywords",
  },
  {
    n: 4,
    icon: ListChecks,
    title: "Abre /acciones para priorizar decisiones",
    desc: "Recomendaciones priorizadas del motor: Bajar puja, Mantener, Pausar target, Revisar campaña...",
    to: "/acciones",
    cta: "Ir a Acciones",
    testid: "step-actions",
  },
  {
    n: 5,
    icon: Download,
    title: "Exporta la vista actual si quieres trabajar fuera",
    desc: "CSV informativo con las recomendaciones visibles. No es un archivo bulk listo para Amazon Ads.",
    to: "/acciones",
    cta: "Ir a Acciones",
    testid: "step-export",
  },
];

const STORAGE_KEY = "pn.gettingStarted.collapsed";

export default function GettingStartedCard({ defaultOpen = true, compact = false }) {
  const initial = (() => {
    if (compact) return false;
    try {
      const v = localStorage.getItem(STORAGE_KEY);
      if (v === "1") return false;
      if (v === "0") return true;
    } catch { /* SSR / private mode */ }
    return defaultOpen;
  })();
  const [open, setOpen] = useState(initial);
  useEffect(() => {
    if (compact) return;
    try { localStorage.setItem(STORAGE_KEY, open ? "0" : "1"); } catch { /* ignore */ }
  }, [open, compact]);

  return (
    <section
      className="border border-border rounded-lg bg-card overflow-hidden"
      data-testid="getting-started-card"
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-3 px-5 py-3 text-left hover:bg-muted/30 transition-colors"
        data-testid="getting-started-toggle"
        aria-expanded={open}
      >
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-coral" />
          <h2 className="font-heading text-base font-semibold">Guía rápida · Primeros pasos</h2>
          <span className="text-xs text-muted-foreground hidden sm:inline">5 pasos para sacar partido al módulo</span>
        </div>
        {open ? <ChevronDown className="size-4 text-muted-foreground" /> : <ChevronRight className="size-4 text-muted-foreground" />}
      </button>
      {open && (
        <div className="px-5 pb-5 pt-1 space-y-3" data-testid="getting-started-body">
          <ol className="grid md:grid-cols-2 gap-3">
            {STEPS.map((s) => {
              const Icon = s.icon;
              return (
                <li
                  key={s.n}
                  className="border border-border rounded-md p-4 bg-background flex items-start gap-3"
                  data-testid={s.testid}
                >
                  <div className="size-8 rounded-full bg-coral/10 text-coral flex items-center justify-center shrink-0 font-semibold num">
                    {s.n}
                  </div>
                  <div className="flex-1 min-w-0 space-y-2">
                    <div className="flex items-center gap-2 text-sm font-semibold">
                      <Icon className="size-4 text-coral shrink-0" />
                      <span className="truncate">{s.title}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">{s.desc}</p>
                    <NavLink
                      to={s.to}
                      className="inline-flex items-center gap-1 text-xs text-coral hover:underline"
                      data-testid={`${s.testid}-link`}
                    >
                      {s.cta} <ArrowRight className="size-3" />
                    </NavLink>
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      )}
    </section>
  );
}
