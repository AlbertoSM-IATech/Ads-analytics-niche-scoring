import { useData } from "../context/DataContext";
import { MARKETPLACES, getMarketplace, REPORT_LABELS } from "../lib/format";
import { Sun, Moon } from "lucide-react";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../components/ui/select";
import { Button } from "../components/ui/button";

export default function Header({ title, subtitle }) {
  const { marketplace, setMarketplace, theme, setTheme, active } = useData();
  const mp = getMarketplace(marketplace);

  return (
    <header
      className="h-14 border-b border-border flex items-center justify-between px-4 sticky top-0 bg-background/95 backdrop-blur z-10"
      data-testid="header"
    >
      <div className="flex items-baseline gap-3">
        <h1 className="text-base font-bold tracking-tight">{title}</h1>
        {subtitle && (
          <span className="text-xs text-muted-foreground">{subtitle}</span>
        )}
        {active && (
          <span className="text-[10px] uppercase tracking-widest border border-border px-2 py-0.5 rounded-sm">
            {REPORT_LABELS[active.report_type] || active.report_type} · {active.ad_type}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <Select value={marketplace} onValueChange={setMarketplace}>
          <SelectTrigger
            className="w-[170px] h-9 rounded-sm border-border"
            data-testid="marketplace-selector"
          >
            <SelectValue>
              <span className="flex items-center gap-2">
                <span>{mp.flag}</span>
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
                  <span className="text-muted-foreground text-xs">{m.currency}</span>
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          size="icon"
          className="h-9 w-9 rounded-sm"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          data-testid="theme-toggle"
        >
          {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
        </Button>
      </div>
    </header>
  );
}
