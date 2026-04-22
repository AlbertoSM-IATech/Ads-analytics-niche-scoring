import { useData } from "../context/DataContext";
import { deleteDataset } from "../lib/api";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Trash2, CheckCircle2, Filter } from "lucide-react";
import { fmtInt, REPORT_LABELS, getMarketplace, MARKETPLACES } from "../lib/format";
import { toast } from "sonner";
import { useState } from "react";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "./ui/select";

export default function HistoryPanel() {
  const { datasets, refresh, loadActive, active, marketplace } = useData();
  const [filter, setFilter] = useState("current"); // current | all | <mp_id>

  const effective = filter === "current" ? marketplace : (filter === "all" ? null : filter);
  const shown = effective ? datasets.filter((d) => d.marketplace === effective) : datasets;

  const handleDelete = async (id) => {
    await deleteDataset(id);
    toast.success("Dataset eliminado");
    await refresh();
  };

  return (
    <div className="space-y-3 animate-fade-in" data-testid="history-panel">
      <div className="flex items-center gap-2">
        <Filter className="size-4 text-muted-foreground" />
        <span className="text-xs text-muted-foreground">Marketplace:</span>
        <Select value={filter} onValueChange={setFilter}>
          <SelectTrigger className="h-8 w-[220px] rounded-md" data-testid="history-mp-filter">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="current">Actual ({getMarketplace(marketplace).flag} {getMarketplace(marketplace).name})</SelectItem>
            <SelectItem value="all">Todos los marketplaces</SelectItem>
            {MARKETPLACES.map((m) => (
              <SelectItem key={m.id} value={m.id}>
                {m.flag} {m.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-xs text-muted-foreground ml-auto">{shown.length} datasets</span>
      </div>
      {shown.length === 0 && (
        <div className="border border-dashed border-border p-8 text-center text-sm text-muted-foreground rounded-lg bg-card">
          No hay importaciones para este marketplace.
        </div>
      )}
      {shown.map((d) => {
        const isActive = active?.id === d.id;
        const mp = getMarketplace(d.marketplace);
        return (
          <div
            key={d.id}
            className={`border p-4 rounded-lg flex items-center justify-between gap-4 ${
              isActive ? "border-coral bg-coral/5" : "border-border bg-card"
            }`}
            data-testid={`history-item-${d.id}`}
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                {isActive && <CheckCircle2 className="size-4 text-coral" />}
                <span className="font-medium text-sm truncate">{d.name}</span>
                <Badge variant="outline" className="rounded-md text-[10px]">
                  {mp.flag} {d.marketplace.toUpperCase()}
                </Badge>
                <Badge variant="outline" className="rounded-md text-[10px]">
                  {REPORT_LABELS[d.report_type] || d.report_type}
                </Badge>
                <Badge variant="outline" className="rounded-md text-[10px]">
                  {d.ad_type}
                </Badge>
              </div>
              <div className="text-[11px] text-muted-foreground num mt-1">
                {fmtInt(d.row_count)} filas · {new Date(d.created_at).toLocaleString()}
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Button
                size="sm"
                variant="outline"
                className="rounded-md"
                onClick={() => loadActive(d.id)}
                data-testid={`activate-${d.id}`}
                disabled={isActive}
              >
                {isActive ? "Activo" : "Activar"}
              </Button>
              <Button
                size="icon"
                variant="ghost"
                onClick={() => handleDelete(d.id)}
                data-testid={`delete-${d.id}`}
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
