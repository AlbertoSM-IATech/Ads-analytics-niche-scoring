import { useCallback, useRef, useState } from "react";
import { Upload, FileCheck2, AlertTriangle, Loader2, Megaphone, Compass } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { uploadCsv, importNiche } from "../lib/api";
import { useData } from "../context/DataContext";
import { toast } from "sonner";
import { InfoTooltip } from "./InfoTooltip";

export default function ImportZone() {
  const { marketplace, refresh, loadActive, active } = useData();
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [name, setName] = useState("");
  const inputRef = useRef(null);
  const nicheInputRef = useRef(null);
  const [nicheBusy, setNicheBusy] = useState(false);
  const [nicheResult, setNicheResult] = useState(null);

  const handleAds = useCallback(async (file) => {
    if (!file) return;
    setBusy(true); setResult(null);
    try {
      const r = await uploadCsv(file, marketplace, name || file.name);
      setResult({ ok: true, data: r.data });
      toast.success(`Importado: ${r.data.row_count} filas`);
      await refresh();
      await loadActive(r.data.id);
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message;
      setResult({ ok: false, error: msg });
      toast.error(`Error: ${msg}`);
    } finally { setBusy(false); }
  }, [marketplace, name, refresh, loadActive]);

  const handleNiche = async (file) => {
    if (!file || !active) return;
    setNicheBusy(true); setNicheResult(null);
    try {
      const r = await importNiche(active.id, file);
      setNicheResult({ ok: true, data: r.data });
      toast.success(`${r.data.matched_existing} match · ${r.data.created_new} nuevas`);
      await loadActive(active.id);
    } catch (e) {
      setNicheResult({ ok: false, error: e?.response?.data?.detail || e.message });
      toast.error(e?.response?.data?.detail || e.message);
    } finally { setNicheBusy(false); }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleAds(f);
  };

  return (
    <Tabs defaultValue="ads" className="animate-fade-in" data-testid="import-zone">
      <TabsList className="grid w-full max-w-md grid-cols-2">
        <TabsTrigger value="ads" className="gap-2" data-testid="tab-import-ads">
          <Megaphone className="size-4" /> Amazon Ads
        </TabsTrigger>
        <TabsTrigger value="niche" className="gap-2" data-testid="tab-import-niche">
          <Compass className="size-4" /> Nicho (H10 / BookBeam / Rocket)
        </TabsTrigger>
      </TabsList>

      <TabsContent value="ads" className="space-y-5 pt-5">
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
              onChange={(e) => handleAds(e.target.files?.[0])}
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
                <div className="font-heading text-lg font-semibold inline-flex items-center gap-2">
                  Arrastra tu CSV/XLSX de Amazon Ads
                  <InfoTooltip content="import_file_type" />
                </div>
                <div className="text-sm text-muted-foreground max-w-md mx-auto">
                  Sponsored Products · Brands · Display — Search Term, Campaign, Placement (ES/EN/IT)
                </div>
                <Button className="mt-2 rounded-md bg-coral hover:bg-coral-500 text-white" data-testid="pick-file-btn">Elegir archivo</Button>
              </div>
            )}
          </div>
          <div className="space-y-3 border border-border p-5 rounded-lg bg-card">
            <div>
              <Label className="text-xs flex items-center gap-1">
                Nombre del dataset
                <InfoTooltip content="Etiqueta interna para diferenciar esta importación de otras (ej. 'Q1-ES-SP' o '2026-03-Mindfulness'). Si lo dejas vacío se usa el nombre del archivo. Útil sobre todo al importar varios periodos consecutivos del mismo libro para distinguirlos en los backups." />
              </Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ej: Q1 SP España"
                className="rounded-md mt-1"
                data-testid="dataset-name-input"
              />
            </div>
            <div className="text-xs text-muted-foreground space-y-1.5">
              <div className="uppercase tracking-widest font-semibold text-foreground inline-flex items-center gap-1">
                Compatibilidad
                <InfoTooltip content="import_window" />
              </div>
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
          <div className="border border-green-300 dark:border-green-500/40 bg-green-50 dark:bg-green-500/5 p-4 rounded-lg flex items-start gap-3">
            <FileCheck2 className="size-5 text-green-600 dark:text-green-400 mt-0.5" />
            <div className="text-sm flex-1">
              <div className="font-medium">Importación correcta</div>
              <div className="num text-xs text-muted-foreground mt-1">
                {result.data.row_count} filas · Tipo: {result.data.report_type} · Anuncio: {result.data.ad_type}
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
      </TabsContent>

      <TabsContent value="niche" className="space-y-5 pt-5">
        <div className="border border-border rounded-lg bg-card p-6 space-y-4">
          <div className="flex items-start gap-3">
            <div className="size-12 rounded-full bg-coral/10 flex items-center justify-center">
              <Compass className="size-5 text-coral" />
            </div>
            <div>
              <div className="font-heading text-lg font-semibold">Importar datos de nicho</div>
              <div className="text-sm text-muted-foreground">
                Sube un CSV/XLSX de <span className="font-semibold">Helium10 Cerebro</span>, <span className="font-semibold">BookBeam</span>,
                <span className="font-semibold"> Publisher Rocket</span> o <span className="font-semibold">DataDive</span>.
                Auto-detecta las columnas de volumen de búsqueda y competidores.
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button
              onClick={() => nicheInputRef.current?.click()}
              disabled={!active || nicheBusy}
              className="rounded-md bg-coral hover:bg-coral-500 text-white"
              data-testid="niche-import-btn"
            >
              {nicheBusy ? <Loader2 className="size-4 animate-spin mr-2" /> : <Upload className="size-4 mr-2" />}
              Elegir archivo
            </Button>
            <input
              ref={nicheInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={(e) => handleNiche(e.target.files?.[0])}
              data-testid="niche-file-input"
            />
            {!active && <span className="text-xs text-muted-foreground">Importa primero un CSV de Ads.</span>}
          </div>
          <div className="text-xs text-muted-foreground">
            <div className="uppercase tracking-widest font-semibold text-foreground mb-1">Columnas compatibles</div>
            <ul className="grid grid-cols-2 gap-x-4 gap-y-0.5 pl-0 list-disc list-inside">
              <li>Keyword Phrase / Search Term / Término</li>
              <li>Search Volume / Volumen</li>
              <li>Competing Products / Competidores / Resultados</li>
              <li>Se hace match por keyword y actualiza el Market Score.</li>
            </ul>
          </div>
          {nicheResult?.ok && (
            <div className="border border-green-300 dark:border-green-500/40 bg-green-50 dark:bg-green-500/5 p-3 rounded-md text-sm flex items-center gap-2">
              <FileCheck2 className="size-4 text-green-600" />
              {nicheResult.data.rows_in_file} filas leídas · {nicheResult.data.matched_existing} coinciden · {nicheResult.data.created_new} nuevas.
            </div>
          )}
          {nicheResult && !nicheResult.ok && (
            <div className="border border-destructive/40 bg-destructive/5 p-3 rounded-md text-sm flex items-center gap-2">
              <AlertTriangle className="size-4 text-destructive" />
              {nicheResult.error}
            </div>
          )}
        </div>
      </TabsContent>
    </Tabs>
  );
}
