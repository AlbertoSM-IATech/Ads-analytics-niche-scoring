import { useCallback, useRef, useState } from "react";
import { Upload, FileCheck2, AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { uploadCsv } from "../lib/api";
import { useData } from "../context/DataContext";
import { toast } from "sonner";

export default function ImportZone() {
  const { marketplace, refresh, loadActive } = useData();
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [name, setName] = useState("");
  const inputRef = useRef(null);

  const handle = useCallback(
    async (file) => {
      if (!file) return;
      setBusy(true);
      setResult(null);
      try {
        const r = await uploadCsv(file, marketplace, name || file.name);
        setResult({ ok: true, data: r.data });
        toast.success(`Importado: ${r.data.row_count} filas`);
        await refresh();
        await loadActive(r.data.id);
      } catch (e) {
        const msg = e?.response?.data?.detail || e.message;
        setResult({ ok: false, error: msg });
        toast.error(`Error al importar: ${msg}`);
      } finally {
        setBusy(false);
      }
    },
    [marketplace, name, refresh, loadActive]
  );

  const onDrop = (e) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handle(f);
  };

  return (
    <div className="space-y-5 animate-fade-in" data-testid="import-zone">
      <div className="grid md:grid-cols-[1fr_340px] gap-5">
        <div
          className={`dropzone ${drag ? "active" : ""} p-12 text-center cursor-pointer bg-card`}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          data-testid="dropzone"
        >
          <input
            ref={inputRef}
            type="file"
            accept=".csv,.xlsx,.xls,.txt"
            className="hidden"
            onChange={(e) => handle(e.target.files?.[0])}
            data-testid="file-input"
          />
          {busy ? (
            <div className="flex flex-col items-center gap-3 text-coral">
              <Loader2 className="size-12 animate-spin" />
              <div className="text-sm">Analizando informe…</div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="size-14 rounded-full bg-coral/10 flex items-center justify-center">
                <Upload className="size-6 text-coral" />
              </div>
              <div className="font-heading text-lg font-semibold">
                Arrastra tu CSV/XLSX de Amazon Ads
              </div>
              <div className="text-sm text-muted-foreground max-w-md mx-auto">
                Sponsored Products · Brands · Display — Search Term, Campaign, Placement (ES/EN/IT)
              </div>
              <Button className="mt-2 rounded-md bg-coral hover:bg-coral-500 text-white" data-testid="pick-file-btn">
                Elegir archivo
              </Button>
            </div>
          )}
        </div>
        <div className="space-y-3 border border-border p-5 rounded-lg bg-card">
          <div>
            <Label className="text-xs uppercase tracking-widest text-muted-foreground">
              Nombre del dataset
            </Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ej: Q1 SP España"
              className="rounded-md mt-1.5"
              data-testid="dataset-name-input"
            />
          </div>
          <div className="text-xs text-muted-foreground space-y-1.5">
            <div className="uppercase tracking-widest font-semibold text-foreground">Compatibilidad</div>
            <ul className="space-y-1 list-disc pl-4">
              <li>Auto-detección columnas ES/EN/IT</li>
              <li>Formatos: CSV, TSV, XLSX</li>
              <li>Símbolos €/$/£ y separadores UE</li>
              <li>ACoS, ROAS, CTR, CPC recalculados</li>
              <li>ACoS de Equilibrio + Siguiente Click</li>
            </ul>
          </div>
        </div>
      </div>

      {result?.ok && (
        <div className="border border-green-300 dark:border-green-500/40 bg-green-50 dark:bg-green-500/5 p-4 rounded-lg flex items-start gap-3 animate-scale-in">
          <FileCheck2 className="size-5 text-green-600 dark:text-green-400 mt-0.5" />
          <div className="text-sm flex-1">
            <div className="font-medium">Importación correcta</div>
            <div className="num text-xs text-muted-foreground mt-1">
              {result.data.row_count} filas · Tipo: {result.data.report_type} · Anuncio: {result.data.ad_type}
            </div>
            <div className="mt-2 text-xs">
              <span className="text-muted-foreground">Columnas detectadas:</span>
              <div className="mt-1.5 flex flex-wrap gap-1">
                {Object.entries(result.data.header_mapping || {}).map(([k, v]) => (
                  <span key={k} className="num text-[10px] border border-border bg-background px-2 py-0.5 rounded">
                    {k} → <span className="text-coral">{v}</span>
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
      {result && !result.ok && (
        <div className="border border-destructive/40 bg-destructive/5 p-4 rounded-lg flex items-start gap-3">
          <AlertTriangle className="size-5 text-destructive mt-0.5" />
          <div className="text-sm">
            <div className="font-medium">No se pudo importar</div>
            <div className="num text-xs text-muted-foreground">{result.error}</div>
          </div>
        </div>
      )}
    </div>
  );
}
