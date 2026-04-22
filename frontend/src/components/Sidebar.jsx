import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Upload, BarChart3, Target, Sparkles, History, Zap,
} from "lucide-react";
import { cn } from "../lib/utils";

const items = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, testid: "nav-dashboard" },
  { to: "/import", label: "Importar", icon: Upload, testid: "nav-import" },
  { to: "/campaigns", label: "Campañas", icon: BarChart3, testid: "nav-campaigns" },
  { to: "/search-terms", label: "Search Terms", icon: Target, testid: "nav-search-terms" },
  { to: "/ai", label: "IA", icon: Sparkles, testid: "nav-ai" },
  { to: "/history", label: "Historial", icon: History, testid: "nav-history" },
];

export default function Sidebar() {
  return (
    <aside
      className="w-[220px] shrink-0 border-r border-border h-screen sticky top-0 flex flex-col bg-card"
      data-testid="sidebar"
    >
      <div className="h-14 flex items-center gap-2 px-4 border-b border-border">
        <div className="size-7 rounded-sm bg-primary flex items-center justify-center">
          <Zap className="size-4 text-primary-foreground" />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-bold tracking-tight">ADS GURU</div>
          <div className="text-[10px] text-muted-foreground uppercase tracking-widest">
            Amazon Ads
          </div>
        </div>
      </div>
      <nav className="flex-1 p-2 space-y-0.5">
        {items.map(({ to, label, icon: Icon, testid }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            data-testid={testid}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2 text-sm rounded-sm transition-colors",
                "hover:bg-muted",
                isActive
                  ? "bg-foreground text-background font-medium"
                  : "text-muted-foreground"
              )
            }
          >
            <Icon className="size-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="p-3 border-t border-border text-[10px] text-muted-foreground uppercase tracking-widest">
        v1.0 · MVP
      </div>
    </aside>
  );
}
