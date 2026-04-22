import { TrendingUp, RefreshCw, AlertTriangle, HelpCircle } from "lucide-react";
import { InfoTooltip } from "./InfoTooltip";
import { Link } from "react-router-dom";

const BLOCKS = [
  {
    key: "bajo-pe",
    label: "Bajo PE",
    icon: TrendingUp,
    desc: "badge_bajo_pe",
    cls: "border-green-200 bg-green-50 dark:bg-green-500/5 dark:border-green-500/30 text-green-700 dark:text-green-400",
  },
  {
    key: "recuperable",
    label: "Recuperable",
    icon: RefreshCw,
    desc: "badge_recuperable",
    cls: "border-amber-200 bg-amber-50 dark:bg-amber-500/5 dark:border-amber-500/30 text-amber-700 dark:text-amber-400",
  },
  {
    key: "en-perdida",
    label: "En pérdida",
    icon: AlertTriangle,
    desc: "badge_en_perdida",
    cls: "border-red-200 bg-red-50 dark:bg-red-500/5 dark:border-red-500/30 text-red-700 dark:text-red-400",
  },
  {
    key: "sin-datos",
    label: "Sin datos",
    icon: HelpCircle,
    desc: "badge_sin_datos",
    cls: "border-neutral-200 bg-neutral-50 dark:bg-neutral-500/10 dark:border-neutral-600 text-neutral-600 dark:text-neutral-400",
  },
];

export default function DashboardBlocks({ summary }) {
  const s = summary || {};
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4" data-testid="dashboard-blocks">
      {BLOCKS.map(({ key, label, icon: Icon, desc, cls }) => {
        const n = s[key] ?? 0;
        return (
          <Link
            key={key}
            to="/keywords"
            state={{ filterBadge: key }}
            className={`border rounded-lg p-5 transition-all hover:-translate-y-0.5 coral-card-hover ${cls}`}
            data-testid={`block-${key}`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Icon className="size-4" />
                <span className="text-sm font-semibold">{label}</span>
              </div>
              <InfoTooltip content={desc} />
            </div>
            <div className="num text-3xl font-bold mt-3">{n}</div>
            <div className="text-xs opacity-80 mt-1">keywords</div>
          </Link>
        );
      })}
    </div>
  );
}
