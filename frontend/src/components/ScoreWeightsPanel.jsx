import { useEffect, useState } from "react";
import { useData } from "../context/DataContext";
import { getScoreWeights, putScoreWeights, resetScoreWeights } from "../lib/api";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import { Sparkles, RotateCcw, Save, Loader2, Scale } from "lucide-react";
import { toast } from "sonner";
import { InfoTooltip } from "./InfoTooltip";

const BLOCKS = [
  { key: "volume", label: "Volumen", tip: "Peso del volumen de búsqueda. Mayor peso = más relevante el tamaño del nicho." },
  { key: "competitors", label: "Competidores", tip: "Peso de la cantidad de competidores. Mayor peso = penaliza más los nichos saturados." },
  { key: "price", label: "Precio", tip: "Peso del precio medio del nicho. Mayor peso = exige un precio acorde al ideal." },
  { key: "royalties", label: "Regalías", tip: "Peso de las regalías medias del nicho. Mayor peso = exige rentabilidad por venta." },
  { key: "market_structure", label: "Demanda", tip: "Peso de las 6 señales de demanda manuales (autocontenido, sugerido por Amazon, etc.)." },
  { key: "catalog_signals", label: "Competencia", tip: "Peso de las 3 señales de competencia + bonus auto si <3.000 resultados." },
];

export default function ScoreWeightsPanel() {
  const { active } = useData();
  const [defaults, setDefaults] = useState(null);
  const [weights, setWeights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!active?.id) return;
    setLoading(true);
    getScoreWeights(active.id)
      .then((r) => {
        setDefaults(r.data.defaults);
        setWeights({ ...r.data.effective });
      })
      .finally(() => setLoading(false));
  }, [active?.id]);

  if (!active || !weights) {
    return null;
  }

  const total = BLOCKS.reduce((s, b) => s + (Number(weights[b.key]) || 0), 0);

  const save = async () => {
    setSaving(true);
    try {
      const payload = {};
      BLOCKS.forEach((b) => { payload[b.key] = Number(weights[b.key]) || 0; });
      await putScoreWeights(active.id, payload);
      toast.success("Pesos guardados — el Market Score se ha recalculado.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    } finally { setSaving(false); }
  };

  const restore = async () => {
    if (!window.confirm("¿Restaurar los pesos del Market Score a los valores estándar?")) return;
    setSaving(true);
    try {
      const r = await resetScoreWeights(active.id);
      setWeights({ ...r.data.effective });
      toast.success("Pesos restaurados al estándar");
    } catch (e) { toast.error(e.message); }
    finally { setSaving(false); }
  };

  const setOne = (k, v) => setWeights({ ...weights, [k]: v });

  return (
    <div className="border border-border rounded-lg bg-card p-6 space-y-4" data-testid="score-weights-panel">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="font-heading text-lg font-semibold flex items-center gap-2">
          <Sparkles className="size-5 text-coral" />
          Pesos del Market Score
          <InfoTooltip content="Define cuánto pesa cada bloque (sobre 100) en el cálculo del Market Score del estudio de nicho. El score final se normaliza a 0-100 según la suma de los pesos." />
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            Suma actual: <span className={`num font-semibold ${total === 100 ? "text-green-600" : "text-amber-600"}`}>{total.toFixed(1)}</span>
            <InfoTooltip content="No es obligatorio que sumen 100; el score se normaliza automáticamente. Pero usar 100 facilita la lectura." />
          </span>
          <Button variant="ghost" size="sm" onClick={restore} disabled={saving} className="rounded-md" data-testid="restore-weights-btn">
            <RotateCcw className="size-3.5 mr-1.5" /> Restaurar estándar
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-6"><Loader2 className="size-5 animate-spin text-coral" /></div>
      ) : (
        <>
          <div className="grid md:grid-cols-3 gap-3">
            {BLOCKS.map((b) => {
              const def = defaults?.[b.key] ?? 0;
              const cur = Number(weights[b.key] ?? 0);
              const isCustom = Math.abs(cur - def) > 0.001;
              return (
                <div
                  key={b.key}
                  className={`border rounded-md p-3 transition-colors ${isCustom ? "border-coral/50 bg-coral/5" : "border-border bg-background"}`}
                  data-testid={`weight-block-${b.key}`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <Label className="text-xs flex items-center gap-1.5 font-semibold">
                      {b.label}
                      <InfoTooltip content={b.tip} />
                    </Label>
                    <button
                      onClick={() => setOne(b.key, def)}
                      className="text-[10px] text-muted-foreground hover:text-coral"
                      title="Restaurar al valor estándar"
                      data-testid={`weight-reset-${b.key}`}
                    >
                      default: {def}
                    </button>
                  </div>
                  <div className="flex items-center gap-2">
                    <Scale className="size-3.5 text-muted-foreground" />
                    <Input
                      type="number" min={0} max={100} step={1}
                      value={cur}
                      onChange={(e) => setOne(b.key, e.target.value)}
                      className="rounded-md num h-8 text-sm"
                      data-testid={`weight-input-${b.key}`}
                    />
                    <span className="text-xs text-muted-foreground">pts</span>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="pt-2 flex justify-end">
            <Button onClick={save} disabled={saving} className="rounded-md bg-coral hover:bg-coral-500 text-white" data-testid="save-weights-btn">
              {saving ? <Loader2 className="size-4 animate-spin mr-2" /> : <Save className="size-4 mr-2" />}
              Guardar pesos
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
