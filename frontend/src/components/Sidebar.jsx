import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Upload, Megaphone, Target, BookOpen, Zap,
  ChevronLeft, ChevronRight,
} from "lucide-react";
import { useState, useEffect } from "react";

const LOGO_URL = "https://customer-assets.emergentagent.com/job_amazon-ads-importer/artifacts/lak8zra2_Artboard%2026%402x.png";

const items = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, testid: "nav-dashboard" },
  { to: "/book", label: "Libro", icon: BookOpen, testid: "nav-book" },
  { to: "/import", label: "Importar", icon: Upload, testid: "nav-import" },
  { to: "/campaigns", label: "Campañas", icon: Megaphone, testid: "nav-campaigns" },
  { to: "/keywords", label: "Keywords", icon: Target, testid: "nav-keywords" },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("sidebar_collapsed") === "1"
  );
  useEffect(() => {
    localStorage.setItem("sidebar_collapsed", collapsed ? "1" : "0");
  }, [collapsed]);

  return (
    <aside
      className={`shrink-0 h-screen sticky top-0 flex flex-col bg-sidebar text-sidebar-foreground border-r border-sidebar-border transition-[width] duration-200 ${
        collapsed ? "w-[64px]" : "w-[232px]"
      }`}
      data-testid="sidebar"
      data-collapsed={collapsed ? "true" : "false"}
    >
      <div className="h-[72px] flex items-center gap-2 px-4 border-b border-sidebar-border justify-between">
        {collapsed ? (
          <div className="size-8 rounded bg-coral flex items-center justify-center mx-auto">
            <Zap className="size-4 text-white" />
          </div>
        ) : (
          <img src={LOGO_URL} alt="Publify" className="h-8 object-contain" data-testid="publify-logo" />
        )}
      </div>

      <nav className="flex-1 px-2 pt-4 space-y-0.5">
        {items.map(({ to, label, icon: Icon, testid }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            data-testid={testid}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              [
                "group flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-all",
                collapsed ? "justify-center" : "",
                "hover:bg-sidebar-accent hover:text-white",
                isActive
                  ? "bg-coral text-white shadow-[0_4px_14px_-4px_rgba(251,146,60,0.6)] font-medium"
                  : "text-sidebar-muted",
              ].join(" ")
            }
          >
            <Icon className="size-4 shrink-0" />
            {!collapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}
      </nav>

      <button
        onClick={() => setCollapsed(!collapsed)}
        className="m-3 h-8 rounded-md border border-sidebar-border text-sidebar-muted hover:text-white hover:border-coral flex items-center justify-center gap-1.5 text-xs"
        data-testid="sidebar-toggle"
        title={collapsed ? "Expandir" : "Colapsar"}
      >
        {collapsed ? <ChevronRight className="size-4" /> : <><ChevronLeft className="size-4" /> <span>Colapsar</span></>}
      </button>
    </aside>
  );
}
