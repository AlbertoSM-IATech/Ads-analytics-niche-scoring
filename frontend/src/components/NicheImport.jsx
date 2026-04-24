import { useRef, useState } from "react";
import { Upload, Loader2, FileCheck2 } from "lucide-react";
import { importNiche } from "../lib/api";
import { useData } from "../context/DataContext";
import { toast } from "sonner";
import { Button } from "./ui/button";

export default function NicheImport({ onDone }) {
  const { active, loadActive } = useData();
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  const handle = async (file) => {
    if (!file || !active) return;
    setBusy(true); setResult(null);
    try {
      const r = await importNiche(active.id, file);
      setResult(r.data);
      toast.success(`${r.data.matched_existing} coincidencias · ${r.data.created_new} nuevas`);
      await loadActive(active.id);
      onDone?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    } finally { setBusy(false); }
  };

  return (
    <div className="border border-dashed border-border rounded-lg p-5 bg-card" data-testid="niche-import">
      <div className="flex items-center gap-3">
        <Upload className="size-5 text-coral" />
        <div className="flex-1">
          <div className="text-sm font-semibold">Importar volumen/competidores (Helium10 / Publisher Rocket)</div>
          <div className="text-xs text-muted-foreground">
            Sube un CSV/XLSX con columnas "Keyword Phrase" + "Search Volume" + "Competing Products".
          </div>
        </div>
        <Button
          size="sm"
          onClick={() => inputRef.current?.click()}
          disabled={busy || !active}
          className="rounded-md bg-coral hover:bg-coral-500 text-white"
          data-testid="niche-import-btn"
        >
          {busy ? <Loader2 className="size-4 animate-spin" /> : "Elegir"}
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={(e) => handle(e.target.files?.[0])}
          data-testid="niche-file-input"
        />
      </div>
      {result && (
        <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
          <FileCheck2 className="size-3.5 text-green-600" />
          {result.rows_in_file} filas procesadas · {result.matched_existing} coinciden · {result.created_new} nuevas keywords creadas.
        </div>
      )}
    </div>
  );
}
