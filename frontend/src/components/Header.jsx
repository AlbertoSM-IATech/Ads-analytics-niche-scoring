import { useData } from "../context/DataContext";
import { MARKETPLACES, getMarketplace, REPORT_LABELS } from "../lib/format";
import { Sun, Moon } from "lucide-react";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "./ui/select";
import { Button } from "./ui/button";

export default function Header({ title, subtitle }) {
  const { marketplace, setMarketplace, theme, setTheme, active } = useData();
  const mp = getMarketplace(marketplace);

  return (
    <header
      className="h-[72px] border-b border-border flex items-center justify-between px-6 sticky top-0 bg-background/90 backdrop-blur z-10"
      data-testid="header"
    >
      <div className="flex flex-col">
        <div className="flex items-center gap-3">
          <h1 className="font-heading text-xl font-semibold tracking-tight">{title}</h1>
          {active && (
            <span className="badge-pill bg-coral-50 text-coral-700 border-coral-200 dark:bg-coral-500/10 dark:text-coral-400 dark:border-coral-500/30">
              {REPORT_LABELS[active.report_type] || active.report_type} · {active.ad_type}
            </span>
          )}
        </div>
        {subtitle && (
          <span className="text-xs text-muted-foreground">{subtitle}</span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <Select value={marketplace} onValueChange={setMarketplace}>
          <SelectTrigger
            className="w-[200px] h-10 rounded-md bg-card"
            data-testid="marketplace-selector"
          >
            <SelectValue>
              <span className="flex items-center gap-2">
                <span className="text-base">{mp.flag}</span>
                <span className="text-sm">{mp.name}</span>
              </span>
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {MARKETPLACES.map((m) => (
              <SelectItem key={m.id} value={m.id} data-testid={`mp-${m.id}`}>
                <span className="flex items-center gap-2">
                  <span>{m.flag}</span>
                  <span>{m.name}</span>
                  <span className="text-muted-foreground text-xs num">{m.currency}</span>
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          size="icon"
          className="h-10 w-10 rounded-md"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          data-testid="theme-toggle"
        >
          {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
        </Button>
      </div>
    </header>
  );
}
