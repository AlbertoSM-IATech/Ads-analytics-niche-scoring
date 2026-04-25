import { useEffect, useState } from "react";
import { useData } from "../context/DataContext";
import { updateBook, setPhase } from "../lib/api";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Button } from "./ui/button";
import { BookOpen, Save, Scale, Rocket, Crown, DollarSign, RotateCcw } from "lucide-react";
import { fmtPct, getMarketplace } from "../lib/format";
import { toast } from "sonner";
import { InfoTooltip } from "./InfoTooltip";
import ScoreWeightsPanel from "./ScoreWeightsPanel";

const PHASES = [
  { key: "lanzamiento", label: "Lanzamiento", icon: Rocket, desc: "Visibilidad · más tolerancia", multKey: "mult_lanzamiento", tip: "lanzamiento" },
  { key: "dominio", label: "Dominio", icon: Crown, desc: "Equilibrio · posición", multKey: "mult_dominio", tip: "dominio" },
  { key: "beneficio", label: "Beneficio", icon: DollarSign, desc: "Rentabilidad · estricto", multKey: "mult_beneficio", tip: "beneficio_fase" },
];

const DEFAULT_ECO = {
  precio_libro: 9.99,
  regalias_por_venta: 3.5,
  mult_lanzamiento: 1.7,
  mult_dominio: 1.2,
  mult_beneficio: 0.5,
};
const DEFAULT_INFO = { title: "", subtitle: "", description: "", categories: [] };

const breakEven = (price, roy) =>
  !price || price <= 0 || roy == null ? null : (roy / price) * 100;

export default function BookInfoPanel() {
  const { active, loadActive, marketplace } = useData();
  const sym = getMarketplace(marketplace).symbol;
  const [info, setInfo] = useState(DEFAULT_INFO);
  const [eco, setEco] = useState(DEFAULT_ECO);
  const [phase, setPhaseLocal] = useState("dominio");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!active) return;
    setInfo({
      title: active.book_info?.title || "",
      subtitle: active.book_info?.subtitle || "",
      description: active.book_info?.description || "",
      categories: active.book_info?.categories || [],
    });
    setEco({
      precio_libro: active.book_economy?.precio_libro ?? DEFAULT_ECO.precio_libro,
      regalias_por_venta: active.book_economy?.regalias_por_venta ?? DEFAULT_ECO.regalias_por_venta,
      mult_lanzamiento: active.book_economy?.mult_lanzamiento ?? DEFAULT_ECO.mult_lanzamiento,
      mult_dominio: active.book_economy?.mult_dominio ?? DEFAULT_ECO.mult_dominio,
      mult_beneficio: active.book_economy?.mult_beneficio ?? DEFAULT_ECO.mult_beneficio,
    });
    setPhaseLocal(active.phase || "dominio");
  }, [active]);

  const pe = breakEven(Number(eco.precio_libro), Number(eco.regalias_por_venta));
  const fases = pe != null ? {
    lanzamiento: pe * Number(eco.mult_lanzamiento || 1.7),
    dominio: pe * Number(eco.mult_dominio || 1.2),
    beneficio: pe * Number(eco.mult_beneficio || 0.5),
  } : null;

  const handleSave = async () => {
    if (!active) return;
    setSaving(true);
    try {
      await updateBook(active.id, {
        info: { ...info, categories: (info.categories || []).filter(Boolean) },
        economy: {
          precio_libro: Number(eco.precio_libro) || 0,
          regalias_por_venta: Number(eco.regalias_por_venta) || 0,
          mult_lanzamiento: Number(eco.mult_lanzamiento) || 1.7,
          mult_dominio: Number(eco.mult_dominio) || 1.2,
          mult_beneficio: Number(eco.mult_beneficio) || 0.5,
        },
      });
      await setPhase(active.id, phase);
      await loadActive(active.id);
      toast.success("Cambios guardados");
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    } finally { setSaving(false); }
  };

  const handlePhaseChange = async (newPhase) => {
    setPhaseLocal(newPhase);
    if (active) {
      try {
        await setPhase(active.id, newPhase);
        await loadActive(active.id);
      } catch (e) { toast.error(e.message); }
    }
  };

  const restoreDefaults = () => {
    if (!window.confirm("¿Restaurar todos los valores a los estándar? (no se guarda hasta pulsar Guardar)")) return;
    setInfo(DEFAULT_INFO);
    setEco(DEFAULT_ECO);
    setPhaseLocal("dominio");
    toast.info("Valores estándar cargados. Pulsa Guardar para persistir.");
  };

  const resetMultiplier = (k) => setEco({ ...eco, [k]: DEFAULT_ECO[k] });

  if (!active) {
    return (
      <div className="border border-dashed border-border p-8 rounded-lg text-center text-sm text-muted-foreground bg-card">
        Importa un CSV para configurar tu libro.
      </div>
    );
  }

  return (
    <div className="space-y-5 animate-fade-in" data-testid="book-panel">
      {/* Phase selector with editable multipliers */}
      <div className="border border-border rounded-lg bg-card p-6 space-y-4" data-testid="phase-section">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h3 className="font-heading text-lg font-semibold flex items-center gap-2">
            Fase global del libro
            <InfoTooltip content="La fase determina el ACoS objetivo global y las recomendaciones del Piloto Automático." />
          </h3>
          <Button variant="ghost" size="sm" onClick={restoreDefaults} className="rounded-md" data-testid="restore-defaults-btn">
            <RotateCcw className="size-3.5 mr-1.5" /> Restaurar estándar
          </Button>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {PHASES.map(({ key, label, icon: Icon, desc, multKey, tip }) => {
            const multValue = Number(eco[multKey] || DEFAULT_ECO[multKey]);
            const targetAcos = pe != null ? pe * multValue : null;
            return (
              <div
                key={key}
                className={`border rounded-lg p-4 transition-all ${phase === key
                  ? "border-coral bg-coral/10 ring-2 ring-coral"
                  : "border-border bg-card hover:border-coral/40"}`}
                data-testid={`book-phase-${key}`}
              >
                <button
                  onClick={() => handlePhaseChange(key)}
                  className="flex items-center gap-2 w-full text-left"
                  data-testid={`select-phase-${key}`}
                >
                  <Icon className="size-4 text-coral" />
                  <span className="font-semibold text-sm">{label}</span>
                  <InfoTooltip content={tip} />
                </button>
                <div className="text-xs text-muted-foreground mt-1">{desc}</div>

                <div className="mt-3 flex items-center gap-2">
                  <Label className="text-[10px] uppercase tracking-widest text-muted-foreground">Mult. ×PE</Label>
                  <button
                    onClick={() => resetMultiplier(multKey)}
                    className="text-[10px] text-muted-foreground hover:text-coral ml-auto"
                    title="Restaurar al valor estándar"
                    data-testid={`reset-mult-${key}`}
                  >
                    default: {DEFAULT_ECO[multKey]}
                  </button>
                </div>
                <Input
                  type="number" min={0.1} max={5} step={0.05}
                  value={eco[multKey]}
                  onChange={(e) => setEco({ ...eco, [multKey]: e.target.value })}
                  className="rounded-md mt-1 num h-8 text-sm"
                  data-testid={`mult-input-${key}`}
                />
                <div className="num text-sm font-semibold text-coral mt-2">
                  Objetivo: {targetAcos != null ? fmtPct(targetAcos) : "—"}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="grid lg:grid-cols-[1fr_420px] gap-5">
        <div className="border border-border rounded-lg bg-card p-6 space-y-4">
          <div className="flex items-center gap-2">
            <BookOpen className="size-5 text-coral" />
            <h3 className="font-heading text-lg font-semibold">Información del libro</h3>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <Label className="text-xs">Título</Label>
              <Input value={info.title} onChange={(e) => setInfo({ ...info, title: e.target.value })} className="rounded-md mt-1" placeholder="El poder del hábito" data-testid="book-title" />
            </div>
            <div>
              <Label className="text-xs">Subtítulo</Label>
              <Input value={info.subtitle} onChange={(e) => setInfo({ ...info, subtitle: e.target.value })} className="rounded-md mt-1" placeholder="Por qué hacemos…" data-testid="book-subtitle" />
            </div>
          </div>
          <div>
            <Label className="text-xs">Categorías (separadas por comas)</Label>
            <Input value={(info.categories || []).join(", ")} onChange={(e) => setInfo({ ...info, categories: e.target.value.split(",").map((s) => s.trim()) })} className="rounded-md mt-1" placeholder="Autoayuda, Productividad" data-testid="book-categories" />
          </div>
          <div>
            <Label className="text-xs">Descripción</Label>
            <Textarea value={info.description} onChange={(e) => setInfo({ ...info, description: e.target.value })} className="rounded-md mt-1 min-h-[100px]" placeholder="Resumen…" data-testid="book-description" />
          </div>
        </div>

        <div className="space-y-4">
          <div className="border border-border rounded-lg bg-card p-6 space-y-4">
            <div className="flex items-center gap-2">
              <Scale className="size-5 text-coral" />
              <h3 className="font-heading text-lg font-semibold">Economía del libro</h3>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Precio ({sym})</Label>
                <Input type="number" min={0} step={0.01} value={eco.precio_libro} onChange={(e) => setEco({ ...eco, precio_libro: e.target.value })} className="rounded-md mt-1 num" data-testid="book-price" />
              </div>
              <div>
                <Label className="text-xs">Regalías por venta ({sym})</Label>
                <Input type="number" min={0} step={0.01} value={eco.regalias_por_venta} onChange={(e) => setEco({ ...eco, regalias_por_venta: e.target.value })} className="rounded-md mt-1 num" data-testid="book-royalties" />
              </div>
            </div>
            <div className="bg-coral/10 border border-coral/30 rounded-md p-4" data-testid="acos-equilibrio">
              <div className="text-[10px] uppercase tracking-widest text-coral-700 dark:text-coral-300 font-semibold">
                ACoS de Equilibrio (PE)
              </div>
              <div className="num text-3xl font-bold text-coral mt-1">
                {pe == null ? "—" : fmtPct(pe)}
              </div>
              <div className="text-xs text-muted-foreground mt-1">Por encima pierdes dinero por cada venta.</div>
            </div>
          </div>
          <Button onClick={handleSave} disabled={saving} className="w-full rounded-md bg-coral hover:bg-coral-500 text-white" data-testid="save-book-btn">
            <Save className="size-4 mr-2" /> Guardar cambios
          </Button>
        </div>
      </div>

      <ScoreWeightsPanel />
    </div>
  );
}
