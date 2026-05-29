import { NavLink } from "react-router-dom";
import { BookOpen, Upload, Target, ListChecks, Download, ArrowRight } from "lucide-react";

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

export default function GettingStartedCard() {
  return (
    <section
      className="border border-border rounded-lg bg-card p-5 space-y-4"
      data-testid="getting-started-card"
    >
      <header className="space-y-1">
        <h2 className="font-heading text-xl font-semibold">Primeros pasos</h2>
        <p className="text-sm text-muted-foreground">
          Sigue este flujo para sacar el máximo del módulo Ads + KDP Economy.
        </p>
      </header>
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
    </section>
  );
}
