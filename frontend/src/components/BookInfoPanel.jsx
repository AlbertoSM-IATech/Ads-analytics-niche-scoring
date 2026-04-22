import { useEffect, useState } from "react";
import { useData } from "../context/DataContext";
import { updateBook } from "../lib/api";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Button } from "./ui/button";
import { BookOpen, Save, Scale } from "lucide-react";
import { fmtPct, getMarketplace } from "../lib/format";
import { toast } from "sonner";

const breakEven = (price, roy) =>
  !price || price <= 0 || roy == null ? null : (roy / price) * 100;

export default function BookInfoPanel() {
  const { active, loadActive, marketplace } = useData();
  const sym = getMarketplace(marketplace).symbol;
  const [info, setInfo] = useState({ title: "", subtitle: "", description: "", categories: [] });
  const [eco, setEco] = useState({ precio_libro: 0, regalias_por_venta: 0 });
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
      await loadActive(active.id);
      toast.success("Datos del libro guardados");
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  };

  if (!active) {
    return (
      <div className="border border-dashed border-border p-8 rounded-lg text-center text-sm text-muted-foreground bg-card">
        Importa un CSV para configurar tu libro.
      </div>
    );
  }

  return (
    <div className="grid lg:grid-cols-[1fr_420px] gap-5 animate-fade-in" data-testid="book-panel">
      <div className="border border-border rounded-lg bg-card p-6 space-y-4">
        <div className="flex items-center gap-2">
          <BookOpen className="size-5 text-coral" />
          <h3 className="font-heading text-lg font-semibold">Información del libro</h3>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <Label className="text-xs">Título</Label>
            <Input
              value={info.title}
              onChange={(e) => setInfo({ ...info, title: e.target.value })}
              className="rounded-md mt-1"
              placeholder="El poder del hábito"
              data-testid="book-title"
            />
          </div>
          <div>
            <Label className="text-xs">Subtítulo</Label>
            <Input
              value={info.subtitle}
              onChange={(e) => setInfo({ ...info, subtitle: e.target.value })}
              className="rounded-md mt-1"
              placeholder="Por qué hacemos lo que hacemos…"
              data-testid="book-subtitle"
            />
          </div>
        </div>
        <div>
          <Label className="text-xs">Categorías (separadas por comas)</Label>
          <Input
            value={(info.categories || []).join(", ")}
            onChange={(e) =>
              setInfo({ ...info, categories: e.target.value.split(",").map((s) => s.trim()) })
            }
            className="rounded-md mt-1"
            placeholder="Autoayuda, Productividad"
            data-testid="book-categories"
          />
        </div>
        <div>
          <Label className="text-xs">Descripción</Label>
          <Textarea
            value={info.description}
            onChange={(e) => setInfo({ ...info, description: e.target.value })}
            className="rounded-md mt-1 min-h-[100px]"
            placeholder="Resumen de tu libro…"
            data-testid="book-description"
          />
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
              <Input
                type="number"
                step="0.01"
                value={eco.precio_libro}
                onChange={(e) => setEco({ ...eco, precio_libro: e.target.value })}
                className="rounded-md mt-1 num"
                data-testid="book-price"
              />
            </div>
            <div>
              <Label className="text-xs">Regalías por venta ({sym})</Label>
              <Input
                type="number"
                step="0.01"
                value={eco.regalias_por_venta}
                onChange={(e) => setEco({ ...eco, regalias_por_venta: e.target.value })}
                className="rounded-md mt-1 num"
                data-testid="book-royalties"
              />
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
        <Button
          onClick={handleSave}
          disabled={saving}
          className="w-full rounded-md bg-coral hover:bg-coral-500 text-white"
          data-testid="save-book-btn"
        >
          <Save className="size-4 mr-2" /> Guardar
        </Button>
      </div>
    </div>
  );
}
