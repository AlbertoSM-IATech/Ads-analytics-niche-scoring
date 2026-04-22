import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Upload, Megaphone, Target, BookOpen, Sparkles, History, Compass, ListTree,
} from "lucide-react";

const LOGO_URL = "https://customer-assets.emergentagent.com/job_amazon-ads-importer/artifacts/lak8zra2_Artboard%2026%402x.png";

const items = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, testid: "nav-dashboard" },
  { to: "/import", label: "Importar", icon: Upload, testid: "nav-import" },
  { to: "/book", label: "Mi libro", icon: BookOpen, testid: "nav-book" },
  { to: "/keywords", label: "Keywords", icon: Target, testid: "nav-keywords" },
  { to: "/niche", label: "Estudio de nicho", icon: Compass, testid: "nav-niche" },
  { to: "/plans", label: "Planes", icon: ListTree, testid: "nav-plans" },
  { to: "/campaigns", label: "Campañas", icon: Megaphone, testid: "nav-campaigns" },
  { to: "/ai", label: "IA", icon: Sparkles, testid: "nav-ai" },
  { to: "/history", label: "Historial", icon: History, testid: "nav-history" },
];

export default function Sidebar() {
  return (
    <aside
      className="w-[232px] shrink-0 h-screen sticky top-0 flex flex-col bg-sidebar text-sidebar-foreground border-r border-sidebar-border"
      data-testid="sidebar"
    >
      <div className="h-[72px] flex items-center gap-2 px-5 border-b border-sidebar-border">
        <img
          src={LOGO_URL}
          alt="Publify"
          className="h-8 object-contain"
          data-testid="publify-logo"
        />
      </div>
      <div className="px-5 pt-5 pb-2 text-[10px] uppercase tracking-widest text-sidebar-muted font-semibold">
        Módulos
      </div>
      <nav className="flex-1 px-3 space-y-0.5">
        {items.map(({ to, label, icon: Icon, testid }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            data-testid={testid}
            className={({ isActive }) =>
              [
                "group flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-all",
                "hover:bg-sidebar-accent hover:text-white",
                isActive
                  ? "bg-coral text-white shadow-[0_4px_14px_-4px_rgba(251,146,60,0.6)] font-medium"
                  : "text-sidebar-muted",
              ].join(" ")
            }
          >
            <Icon className="size-4 shrink-0" />
            <span className="truncate">{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-sidebar-border">
        <div className="text-[10px] uppercase tracking-widest text-sidebar-muted">
          Amazon Ads · v1.1
        </div>
        <div className="mt-1 font-heading text-sm font-semibold text-white">
          Publify Analytics
        </div>
      </div>
    </aside>
  );
}
