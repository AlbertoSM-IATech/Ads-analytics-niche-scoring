import { useEffect, useState } from "react";
import {
  listPlans, createPlan, updatePlan, deletePlan, getPlanSummary, getKeywordsUnified,
} from "../lib/api";
import { useData } from "../context/DataContext";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Badge } from "./ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "./ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "./ui/dialog";
import {
  Plus, Trash2, Megaphone, Rocket, Crown, DollarSign, Loader2, Target,
} from "lucide-react";
import { fmtInt, fmtPct, fmtMoney, getMarketplace } from "../lib/format";
import { InfoTooltip } from "./InfoTooltip";
import { toast } from "sonner";

const PHASE_ICON = { lanzamiento: Rocket, dominio: Crown, beneficio: DollarSign };
const PHASE_COLOR = {
  lanzamiento: "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400 border-amber-300 dark:border-amber-500/30",
  dominio: "bg-blue-100 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400 border-blue-300 dark:border-blue-500/30",
  beneficio: "bg-green-100 text-green-700 dark:bg-green-500/10 dark:text-green-400 border-green-300 dark:border-green-500/30",
};
const PHASE_LABEL = { lanzamiento: "Lanzamiento", dominio: "Dominio", beneficio: "Beneficio" };

export default function CampaignPlans({ datasetId }) {
  const { marketplace } = useData();
  const sym = getMarketplace(marketplace).symbol;
  const [plans, setPlans] = useState({});
  const [summaries, setSummaries] = useState({});
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [availableTerms, setAvailableTerms] = useState([]);

  const load = async () => {
    if (!datasetId) return;
    const r = await listPlans(datasetId);
    setPlans(r.data || {});
    // Preload summaries
    const sums = {};
    for (const id of Object.keys(r.data || {})) {
      try {
        const s = await getPlanSummary(datasetId, id);
        sums[id] = s.data.totals;
      } catch (_) {}
    }
    setSummaries(sums);
  };

  useEffect(() => {
    if (!datasetId) return;
    getKeywordsUnified(datasetId).then((r) => {
      setAvailableTerms((r.data.rows || []).map((x) => x.term).filter(Boolean));
    });
    load();
    // eslint-disable-next-line
  }, [datasetId]);

  const openNew = () => {
    setEditing({
      id: null,
      name: "",
      phase: "lanzamiento",
      target_acos: "",
      daily_budget: "",
      keyword_terms: [],
      notes: "",
    });
    setOpen(true);
  };

  const openEdit = (plan) => {
    setEditing({
      id: plan.id,
      name: plan.name || "",
      phase: plan.phase || "lanzamiento",
      target_acos: plan.target_acos ?? "",
      daily_budget: plan.daily_budget ?? "",
      keyword_terms: plan.keyword_terms || [],
      notes: plan.notes || "",
    });
    setOpen(true);
  };

  const save = async () => {
    if (!editing?.name?.trim()) {
      toast.error("Nombre del plan obligatorio");
      return;
    }
    const payload = {
      name: editing.name.trim(),
      phase: editing.phase,
      target_acos: editing.target_acos === "" ? null : Number(editing.target_acos),
      daily_budget: editing.daily_budget === "" ? null : Number(editing.daily_budget),
      keyword_terms: editing.keyword_terms,
      notes: editing.notes,
    };
    try {
      if (editing.id) await updatePlan(datasetId, editing.id, payload);
      else await createPlan(datasetId, payload);
      toast.success("Plan guardado");
      setOpen(false);
      setEditing(null);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    }
  };

  const remove = async (id) => {
    if (!window.confirm("¿Eliminar plan?")) return;
    await deletePlan(datasetId, id);
    toast.success("Plan eliminado");
    load();
  };

  const toggleTerm = (term) => {
    setEditing((p) => ({
      ...p,
      keyword_terms: p.keyword_terms.includes(term)
        ? p.keyword_terms.filter((t) => t !== term)
        : [...p.keyword_terms, term],
    }));
  };

  const arr = Object.values(plans);

  return (
    <div className="space-y-5 animate-fade-in" data-testid="campaign-plans">
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Organiza tus keywords en planes con fase (Lanzamiento / Dominio / Beneficio) y presupuesto.
        </div>
        <Button onClick={openNew} className="rounded-md bg-coral hover:bg-coral-500 text-white" data-testid="new-plan-btn">
          <Plus className="size-4 mr-1.5" /> Nuevo plan
        </Button>
      </div>

      {arr.length === 0 ? (
        <div className="border border-dashed border-border p-12 text-center rounded-lg bg-card" data-testid="empty-plans">
          <Target className="size-10 text-muted-foreground mx-auto mb-3" />
          <div className="font-semibold">Aún no tienes planes</div>
          <div className="text-sm text-muted-foreground mt-1">Crea uno para agrupar keywords y asignarles presupuesto diario.</div>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {arr.map((plan) => {
            const s = summaries[plan.id] || {};
            const Icon = PHASE_ICON[plan.phase] || Megaphone;
            return (
              <div key={plan.id} className="border border-border rounded-lg bg-card p-5 space-y-3 coral-card-hover" data-testid={`plan-${plan.id}`}>
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-heading text-base font-semibold">{plan.name}</h3>
                    <Badge className={`mt-1 border ${PHASE_COLOR[plan.phase]}`}>
                      <Icon className="size-3 mr-1" /> {PHASE_LABEL[plan.phase]}
                    </Badge>
                  </div>
                  <div className="flex gap-1">
                    <Button size="icon" variant="ghost" onClick={() => openEdit(plan)} className="h-7 w-7" data-testid={`edit-plan-${plan.id}`}>
                      <Plus className="size-3.5 rotate-45" />
                    </Button>
                    <Button size="icon" variant="ghost" onClick={() => remove(plan.id)} className="h-7 w-7 text-destructive" data-testid={`delete-plan-${plan.id}`}>
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="border border-border rounded p-2">
                    <div className="text-muted-foreground text-[10px] uppercase">Keywords</div>
                    <div className="num font-semibold">{plan.keyword_terms?.length || 0}</div>
                  </div>
                  <div className="border border-border rounded p-2">
                    <div className="text-muted-foreground text-[10px] uppercase">Presup. día</div>
                    <div className="num font-semibold">
                      {plan.daily_budget != null ? fmtMoney(plan.daily_budget, sym) : "—"}
                    </div>
                  </div>
                  <div className="border border-border rounded p-2">
                    <div className="text-muted-foreground text-[10px] uppercase">ACoS objetivo</div>
                    <div className="num font-semibold">
                      {plan.target_acos != null ? fmtPct(plan.target_acos) : "—"}
                    </div>
                  </div>
                  <div className="border border-border rounded p-2">
                    <div className="text-muted-foreground text-[10px] uppercase flex items-center gap-1">
                      ACoS de fase <InfoTooltip content={plan.phase === "lanzamiento" ? "lanzamiento" : plan.phase === "dominio" ? "dominio" : "beneficio_fase"} />
                    </div>
                    <div className="num font-semibold">
                      {s.phase_target_acos != null ? fmtPct(s.phase_target_acos) : "—"}
                    </div>
                  </div>
                </div>

                {s.keywords_with_data > 0 && (
                  <div className="border-t border-border pt-3">
                    <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold mb-2">Rendimiento actual</div>
                    <div className="grid grid-cols-4 gap-2 text-xs">
                      <div><div className="text-muted-foreground text-[10px]">Gasto</div><div className="num font-semibold">{fmtMoney(s.spend, sym)}</div></div>
                      <div><div className="text-muted-foreground text-[10px]">Ventas</div><div className="num font-semibold">{fmtMoney(s.sales, sym)}</div></div>
                      <div><div className="text-muted-foreground text-[10px]">ACoS</div><div className="num font-semibold">{fmtPct(s.acos)}</div></div>
                      <div><div className="text-muted-foreground text-[10px]">Clicks</div><div className="num font-semibold">{fmtInt(s.clicks)}</div></div>
                    </div>
                  </div>
                )}

                {plan.notes && (
                  <div className="text-xs text-muted-foreground border-t border-border pt-2">{plan.notes}</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Editor dialog */}
      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) setEditing(null); }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="plan-editor">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <Target className="size-5 text-coral" />
              {editing?.id ? "Editar plan" : "Nuevo plan"}
            </DialogTitle>
            <DialogDescription>Define fase, presupuesto objetivo y keywords del plan.</DialogDescription>
          </DialogHeader>
          {editing && (
            <div className="space-y-3">
              <div>
                <Label className="text-xs">Nombre del plan *</Label>
                <Input value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} className="rounded-md mt-1" placeholder="Plan Lanzamiento Mindfulness" autoFocus data-testid="plan-name" />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <Label className="text-xs">Fase</Label>
                  <Select value={editing.phase} onValueChange={(v) => setEditing({ ...editing, phase: v })}>
                    <SelectTrigger className="rounded-md mt-1" data-testid="plan-phase"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="lanzamiento">Lanzamiento</SelectItem>
                      <SelectItem value="dominio">Dominio</SelectItem>
                      <SelectItem value="beneficio">Beneficio</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Presupuesto/día ({sym})</Label>
                  <Input type="number" min={0} step={0.01} value={editing.daily_budget} onChange={(e) => setEditing({ ...editing, daily_budget: e.target.value })} className="rounded-md mt-1 num" data-testid="plan-budget" />
                </div>
                <div>
                  <Label className="text-xs">ACoS objetivo (%)</Label>
                  <Input type="number" min={0} step={0.01} value={editing.target_acos} onChange={(e) => setEditing({ ...editing, target_acos: e.target.value })} className="rounded-md mt-1 num" data-testid="plan-target-acos" />
                </div>
              </div>
              <div>
                <Label className="text-xs">Notas</Label>
                <Textarea value={editing.notes} onChange={(e) => setEditing({ ...editing, notes: e.target.value })} className="rounded-md mt-1" rows={2} />
              </div>
              <div className="border border-border rounded-md p-3 max-h-64 overflow-y-auto">
                <Label className="text-xs flex items-center justify-between">
                  <span>Keywords en el plan</span>
                  <Badge variant="outline" className="text-xs">{editing.keyword_terms.length} seleccionadas</Badge>
                </Label>
                <div className="grid grid-cols-1 gap-1 mt-2">
                  {availableTerms.length === 0 && (
                    <div className="text-xs text-muted-foreground text-center py-2">No hay keywords disponibles</div>
                  )}
                  {availableTerms.map((t) => {
                    const on = editing.keyword_terms.includes(t);
                    return (
                      <label key={t} className={`flex items-center gap-2 p-1.5 rounded cursor-pointer text-sm ${on ? "bg-coral/10" : "hover:bg-muted/50"}`}>
                        <input type="checkbox" checked={on} onChange={() => toggleTerm(t)} data-testid={`plan-kw-${t}`} />
                        <span className="truncate">{t}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" className="rounded-md" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={save} className="rounded-md bg-coral hover:bg-coral-500 text-white" data-testid="save-plan-btn">Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
