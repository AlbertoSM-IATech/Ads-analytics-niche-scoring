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

const PHASES = [
  { key: "lanzamiento", label: "Lanzamiento", icon: Rocket, desc: "1.7× PE · visibilidad", tip: "lanzamiento" },
  { key: "dominio", label: "Dominio", icon: Crown, desc: "1.2× PE · equilibrio", tip: "dominio" },
  { key: "beneficio", label: "Beneficio", icon: DollarSign, desc: "0.5× PE · rentabilidad", tip: "beneficio_fase" },
];

const DEFAULTS = {
  info: { title: "", subtitle: "", description: "", categories: [] },
  economy: { precio_libro: 9.99, regalias_por_venta: 3.5 },
};

const breakEven = (price, roy) =>
  !price || price <= 0 || roy == null ? null : (roy / price) * 100;

export default function BookInfoPanel() {
  const { active, loadActive, marketplace } = useData();
  const sym = getMarketplace(marketplace).symbol;
  const [info, setInfo] = useState(DEFAULTS.info);
  const [eco, setEco] = useState(DEFAULTS.economy);
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
      precio_libro: active.book_economy?.precio_libro || 0,
      regalias_por_venta: active.book_economy?.regalias_por_venta || 0,
    });
    setPhaseLocal(active.phase || "dominio");
  }, [active]);

  const pe = breakEven(Number(eco.precio_libro), Number(eco.regalias_por_venta));
  const fases = pe != null ? {
    lanzamiento: pe * 1.7,
    dominio: pe * 1.2,
    beneficio: pe * 0.5,
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
        },
      });
      await setPhase(active.id, phase);
      await loadActive(active.id);
      toast.success("Libro y fase guardados");
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  };

  const handlePhaseChange = async (newPhase) => {
    setPhaseLocal(newPhase);
    if (active) {
      try {
        await setPhase(active.id, newPhase);
        await loadActive(active.id);
        toast.success(`Fase: ${newPhase}`);
      } catch (e) { toast.error(e.message); }
    }
  };

  const restoreDefaults = () => {
    if (!window.confirm("¿Restaurar valores estándar del libro? (no se guarda hasta que pulses Guardar)")) return;
    setInfo(DEFAULTS.info);
    setEco(DEFAULTS.economy);
    setPhaseLocal("dominio");
    toast.info("Valores estándar cargados. Pulsa Guardar para persistir.");
  };

  if (!active) {
    return (
      <div className="border border-dashed border-border p-8 rounded-lg text-center text-sm text-muted-foreground bg-card">
        Importa un CSV para configurar tu libro.
      </div>
    );
  }

  return (
    <div className="space-y-5 animate-fade-in" data-testid="book-panel">
      {/* Global phase selector */}
      <div className="border border-border rounded-lg bg-card p-6 space-y-3" data-testid="phase-section">
        <div className="flex items-center justify-between">
          <h3 className="font-heading text-lg font-semibold flex items-center gap-2">
            Fase global del libro
            <InfoTooltip content="La fase determina el ACoS objetivo para todas las keywords y las recomendaciones de la IA." />
          </h3>
          <span className="text-xs text-muted-foreground">Aplica a todas las keywords</span>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {PHASES.map(({ key, label, icon: Icon, desc, tip }) => (
            <button
              key={key}
              onClick={() => handlePhaseChange(key)}
              className={`border rounded-lg p-4 text-left transition-all ${phase === key
                ? "border-coral bg-coral/10 ring-2 ring-coral"
                : "border-border bg-card hover:border-coral/40"}`}
              data-testid={`book-phase-${key}`}
            >
              <div className="flex items-center gap-2">
                <Icon className="size-4 text-coral" />
                <span className="font-semibold text-sm">{label}</span>
                <InfoTooltip content={tip} />
              </div>
              <div className="text-xs text-muted-foreground mt-1">{desc}</div>
              {fases && (
                <div className="num text-sm font-semibold text-coral mt-2">
                  Objetivo: {fmtPct(fases[key])}
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="grid lg:grid-cols-[1fr_420px] gap-5">
        <div className="border border-border rounded-lg bg-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BookOpen className="size-5 text-coral" />
              <h3 className="font-heading text-lg font-semibold">Información del libro</h3>
            </div>
            <Button variant="ghost" size="sm" onClick={restoreDefaults} className="rounded-md" data-testid="restore-defaults-btn">
              <RotateCcw className="size-3.5 mr-1.5" /> Restaurar estándar
            </Button>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <Label className="text-xs">Título</Label>
              <Input value={info.title} onChange={(e) => setInfo({ ...info, title: e.target.value })} className="rounded-md mt-1" placeholder="El poder del hábito" data-testid="book-title" />
            </div>
            <div>
              <Label className="text-xs">Subtítulo</Label>
              <Input value={info.subtitle} onChange={(e) => setInfo({ ...info, subtitle: e.target.value })} className="rounded-md mt-1" placeholder="Por qué hacemos lo que hacemos…" data-testid="book-subtitle" />
            </div>
          </div>
          <div>
            <Label className="text-xs">Categorías (separadas por comas)</Label>
            <Input value={(info.categories || []).join(", ")} onChange={(e) => setInfo({ ...info, categories: e.target.value.split(",").map((s) => s.trim()) })} className="rounded-md mt-1" placeholder="Autoayuda, Productividad" data-testid="book-categories" />
          </div>
          <div>
            <Label className="text-xs">Descripción</Label>
            <Textarea value={info.description} onChange={(e) => setInfo({ ...info, description: e.target.value })} className="rounded-md mt-1 min-h-[100px]" placeholder="Resumen de tu libro…" data-testid="book-description" />
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
                ACoS de Equilibrio
              </div>
              <div className="num text-3xl font-bold text-coral mt-1">
                {pe == null ? "—" : fmtPct(pe)}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                Por encima de este ACoS pierdes dinero por venta.
              </div>
            </div>
            {fases && (
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="border border-border rounded-md p-2 text-center">
                  <div className="text-muted-foreground">Lanzamiento</div>
                  <div className="num font-semibold">{fmtPct(fases.lanzamiento)}</div>
                </div>
                <div className="border border-border rounded-md p-2 text-center">
                  <div className="text-muted-foreground">Dominio</div>
                  <div className="num font-semibold">{fmtPct(fases.dominio)}</div>
                </div>
                <div className="border border-border rounded-md p-2 text-center">
                  <div className="text-muted-foreground">Beneficio</div>
                  <div className="num font-semibold">{fmtPct(fases.beneficio)}</div>
                </div>
              </div>
            )}
          </div>
          <Button onClick={handleSave} disabled={saving} className="w-full rounded-md bg-coral hover:bg-coral-500 text-white" data-testid="save-book-btn">
            <Save className="size-4 mr-2" /> Guardar cambios
          </Button>
        </div>
      </div>
    </div>
  );
}
