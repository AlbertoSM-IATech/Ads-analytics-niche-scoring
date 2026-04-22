import { useData } from "../context/DataContext";
import { deleteDataset } from "../lib/api";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Trash2, CheckCircle2 } from "lucide-react";
import { fmtInt, REPORT_LABELS } from "../lib/format";
import { toast } from "sonner";

export default function HistoryPanel() {
  const { datasets, refresh, loadActive, active } = useData();

  const handleDelete = async (id) => {
    await deleteDataset(id);
    toast.success("Dataset eliminado");
    await refresh();
  };

  return (
    <div className="space-y-2" data-testid="history-panel">
      {datasets.length === 0 && (
        <div className="border border-border p-8 text-center text-sm text-muted-foreground rounded-sm">
          No hay importaciones aún.
        </div>
      )}
      {datasets.map((d) => {
        const isActive = active?.id === d.id;
        return (
          <div
            key={d.id}
            className={`border p-3 rounded-sm flex items-center justify-between gap-4 ${
              isActive ? "border-primary bg-primary/5" : "border-border bg-card"
            }`}
            data-testid={`history-item-${d.id}`}
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                {isActive && <CheckCircle2 className="size-4 text-primary" />}
                <span className="font-medium text-sm truncate">{d.name}</span>
                <Badge variant="outline" className="rounded-sm text-[10px]">
                  {REPORT_LABELS[d.report_type] || d.report_type}
                </Badge>
                <Badge variant="outline" className="rounded-sm text-[10px]">
                  {d.ad_type}
                </Badge>
                <Badge variant="outline" className="rounded-sm text-[10px] uppercase">
                  {d.marketplace}
                </Badge>
              </div>
              <div className="text-[11px] text-muted-foreground mono mt-1">
                {fmtInt(d.row_count)} filas · {new Date(d.created_at).toLocaleString()}
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Button
                size="sm"
                variant="outline"
                className="rounded-sm"
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
