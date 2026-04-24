import { useEffect, useState } from "react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "./ui/dialog";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import { Settings, RotateCcw, Save, Loader2 } from "lucide-react";
import { getMarketCriteria, putMarketCriteria, resetMarketCriteria } from "../lib/api";
import { useData } from "../context/DataContext";
import { getMarketplace } from "../lib/format";
import { toast } from "sonner";

export default function MarketCriteriaModal({ open, onOpenChange, onSaved }) {
  const { active, marketplace } = useData();
  const mp = getMarketplace(marketplace);
  const [defaults, setDefaults] = useState({});
  const [effective, setEffective] = useState({});
  const [overrides, setOverrides] = useState({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open || !active) return;
    setLoading(true);
    getMarketCriteria(active.id, marketplace)
      .then((r) => {
        setDefaults(r.data.defaults);
        setEffective(r.data.effective);
        setOverrides(r.data.overrides || {});
      })
      .finally(() => setLoading(false));
  }, [open, active, marketplace]);

  const handleChange = (field, value) =>
    setOverrides((prev) => ({ ...prev, [field]: value === "" ? undefined : Number(value) }));

  const save = async () => {
    if (!active) return;
    setSaving(true);
    try {
      const payload = {};
      for (const k of ["idealVolume", "idealCompetitors", "idealPrice", "idealRoyalties"]) {
        if (overrides[k] != null && !Number.isNaN(overrides[k])) payload[k] = overrides[k];
      }
      const r = await putMarketCriteria(active.id, marketplace, payload);
      setEffective(r.data.effective);
      toast.success(`Criterios de ${mp.name} guardados`);
      onSaved?.();
      onOpenChange(false);
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    } finally { setSaving(false); }
  };

  const reset = async () => {
    if (!active) return;
    if (!window.confirm(`¿Restaurar valores por defecto para ${mp.name}?`)) return;
    const r = await resetMarketCriteria(active.id, marketplace);
    setEffective(r.data.effective);
    setOverrides({});
    toast.success("Valores restaurados");
    onSaved?.();
  };

  const fields = [
    { k: "idealVolume", label: "Volumen ideal", step: 100, hint: "Búsquedas mensuales objetivo" },
    { k: "idealCompetitors", label: "Competidores ideal", step: 100, hint: "Nº de resultados objetivo" },
    { k: "idealPrice", label: "Precio ideal", step: 0.5, hint: "Precio del libro objetivo" },
    { k: "idealRoyalties", label: "Regalías ideal", step: 0.5, hint: "Regalía por venta objetivo" },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg" data-testid="market-criteria-modal">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <Settings className="size-5 text-coral" />
            Criterios por mercado · {mp.flag} {mp.name}
          </DialogTitle>
          <DialogDescription>
            Ajusta los valores ideales usados para el Market Score y las recomendaciones de IA.
            Afecta sólo a este marketplace.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="py-8 flex justify-center"><Loader2 className="size-6 animate-spin text-coral" /></div>
        ) : (
          <div className="space-y-3">
            {fields.map(({ k, label, step, hint }) => (
              <div key={k}>
                <Label className="text-xs flex items-center justify-between">
                  <span>{label}</span>
                  <span className="text-[10px] text-muted-foreground num">
                    Default: {defaults[k]}
                  </span>
                </Label>
                <Input
                  type="number"
                  min={0}
                  step={step}
                  value={overrides[k] ?? effective[k] ?? ""}
                  onChange={(e) => handleChange(k, e.target.value)}
                  className="rounded-md mt-1 num"
                  placeholder={String(defaults[k] ?? "")}
                  data-testid={`mc-${k}`}
                />
                <div className="text-[10px] text-muted-foreground mt-1">{hint}</div>
              </div>
            ))}
          </div>
        )}

        <DialogFooter className="flex items-center justify-between">
          <Button variant="outline" onClick={reset} className="rounded-md" data-testid="mc-reset">
            <RotateCcw className="size-3.5 mr-1.5" /> Restaurar defaults
          </Button>
          <Button onClick={save} disabled={saving} className="rounded-md bg-coral hover:bg-coral-500 text-white" data-testid="mc-save">
            {saving ? <Loader2 className="size-4 animate-spin mr-2" /> : <Save className="size-4 mr-2" />}
            Guardar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
