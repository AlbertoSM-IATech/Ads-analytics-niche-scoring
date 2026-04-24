import { useRef, useState } from "react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { Download, Upload, Loader2, AlertTriangle } from "lucide-react";
import { backupUrl, restoreBackup } from "../lib/api";
import { useData } from "../context/DataContext";
import { toast } from "sonner";

export default function BackupModal({ open, onOpenChange }) {
  const { active, loadActive } = useData();
  const inputRef = useRef(null);
  const [restoring, setRestoring] = useState(false);

  const onFile = async (file) => {
    if (!file || !active) return;
    if (!window.confirm("Restaurar el backup sobrescribirá el dataset actual. ¿Continuar?")) return;
    setRestoring(true);
    try {
      await restoreBackup(active.id, file);
      await loadActive(active.id);
      toast.success("Dataset restaurado");
      onOpenChange(false);
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    } finally { setRestoring(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md" data-testid="backup-modal">
        <DialogHeader>
          <DialogTitle className="font-heading">Copia de seguridad</DialogTitle>
          <DialogDescription>
            Guarda o restaura el estado completo del libro, campañas, overrides y configuraciones.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <Button
            asChild
            className="w-full rounded-md bg-coral hover:bg-coral-500 text-white"
            data-testid="backup-export-btn"
          >
            <a href={active ? backupUrl(active.id) : "#"} download>
              <Download className="size-4 mr-2" /> Exportar backup (JSON)
            </a>
          </Button>

          <div className="border-t border-border pt-3">
            <Button
              variant="outline"
              className="w-full rounded-md"
              onClick={() => inputRef.current?.click()}
              disabled={restoring}
              data-testid="backup-import-btn"
            >
              {restoring ? <Loader2 className="size-4 animate-spin mr-2" /> : <Upload className="size-4 mr-2" />}
              Importar backup (JSON)
            </Button>
            <input
              ref={inputRef}
              type="file"
              accept=".json,application/json"
              className="hidden"
              onChange={(e) => onFile(e.target.files?.[0])}
              data-testid="backup-file-input"
            />
          </div>

          <div className="text-xs text-muted-foreground flex items-start gap-2">
            <AlertTriangle className="size-3.5 mt-0.5 shrink-0 text-amber-500" />
            <span>La restauración sobrescribe TODOS los datos del dataset actual. Exporta antes si quieres comparar.</span>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} className="rounded-md">Cerrar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
