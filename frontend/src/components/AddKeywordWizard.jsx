import { useMemo, useState } from "react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "./ui/dialog";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "./ui/select";
import { Plus, ChevronRight, ChevronLeft, Check, Loader2 } from "lucide-react";
import { upsertKeyword } from "../lib/api";
import { useData } from "../context/DataContext";
import { toast } from "sonner";
import { fmtPct, fmtMoney, getMarketplace } from "../lib/format";
import { InfoTooltip } from "./InfoTooltip";

const emptyForm = {
  term: "",
  campaign: "",
  match_type: "broad",
  ad_type: "SP",
  impressions: 0,
  clicks: 0,
  cpc: 0,
  spend: 0,
  orders: 0,
  sales: 0,
  notes: "",
};

function preview(form, price, royalties) {
  const clicks = Number(form.clicks) || 0;
  const impressions = Number(form.impressions) || 0;
  const cpc = Number(form.cpc) || 0;
  const orders = Number(form.orders) || 0;
  let spend = Number(form.spend);
  if (!spend && clicks && cpc) spend = clicks * cpc;
  let sales = Number(form.sales);
  if (!sales && orders && price) sales = orders * price;
  const ctr = impressions ? (clicks / impressions) * 100 : 0;
  const acos = sales ? (spend / sales) * 100 : 0;
  const roas = spend ? sales / spend : 0;
  const cvr = clicks ? (orders / clicks) * 100 : 0;
  const pe = price && royalties ? (royalties / price) * 100 : null;
  const acosNext =
    price && price > 0
      ? ((spend + cpc) / (sales + price)) * 100
      : null;
  let badge = "sin-datos";
  if (pe != null && acos) {
    if (acos <= pe) badge = "bajo-pe";
    else if (acosNext != null && acosNext <= pe) badge = "recuperable";
    else badge = "en-perdida";
  }
  return { spend, sales, ctr, acos, roas, cvr, pe, acosNext, badge };
}

export default function AddKeywordWizard({ open, onOpenChange, onCreated }) {
  const { active, loadActive, marketplace } = useData();
  const sym = getMarketplace(marketplace).symbol;
  const price = active?.book_economy?.precio_libro || 0;
  const royalties = active?.book_economy?.regalias_por_venta || 0;

  const [step, setStep] = useState(1);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  const pv = useMemo(() => preview(form, price, royalties), [form, price, royalties]);

  const reset = () => {
    setStep(1);
    setForm(emptyForm);
  };

  const submit = async () => {
    if (!active) return;
    if (!form.term.trim()) {
      toast.error("Escribe la keyword");
      setStep(1);
      return;
    }
    setSaving(true);
    try {
      await upsertKeyword(active.id, {
        term: form.term.trim(),
        campaign: form.campaign || null,
        match_type: form.match_type || null,
        ad_type: form.ad_type || null,
        impressions: Number(form.impressions) || 0,
        clicks: Number(form.clicks) || 0,
        cpc: Number(form.cpc) || 0,
        spend: pv.spend || 0,
        orders: Number(form.orders) || 0,
        sales: pv.sales || 0,
        notes: form.notes || "",
      });
      toast.success("Keyword añadida");
      await loadActive(active.id);
      reset();
      onOpenChange(false);
      onCreated?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  };

  const stepTitle = { 1: "1. Keyword y campaña", 2: "2. Métricas", 3: "3. Confirmación" };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => { onOpenChange(o); if (!o) reset(); }}
    >
      <DialogContent className="max-w-xl" data-testid="add-kw-wizard">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <Plus className="size-5 text-coral" /> Añadir keyword
          </DialogTitle>
          <DialogDescription>{stepTitle[step]}</DialogDescription>
        </DialogHeader>

        {step === 1 && (
          <div className="space-y-3">
            <div>
              <Label className="text-xs">Keyword *</Label>
              <Input
                value={form.term}
                onChange={(e) => setForm({ ...form, term: e.target.value })}
                placeholder="mindfulness para principiantes"
                className="rounded-md mt-1"
                autoFocus
                data-testid="wiz-term"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Campaña (opcional)</Label>
                <Input
                  value={form.campaign}
                  onChange={(e) => setForm({ ...form, campaign: e.target.value })}
                  placeholder="SP - Mindfulness Broad"
                  className="rounded-md mt-1"
                  data-testid="wiz-campaign"
                />
              </div>
              <div>
                <Label className="text-xs">Tipo de anuncio</Label>
                <Select value={form.ad_type} onValueChange={(v) => setForm({ ...form, ad_type: v })}>
                  <SelectTrigger className="rounded-md mt-1" data-testid="wiz-adtype">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="SP">Sponsored Products</SelectItem>
                    <SelectItem value="SB">Sponsored Brands</SelectItem>
                    <SelectItem value="SBV">Sponsored Brands Video</SelectItem>
                    <SelectItem value="SD">Sponsored Display</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label className="text-xs">Match type</Label>
              <Select value={form.match_type} onValueChange={(v) => setForm({ ...form, match_type: v })}>
                <SelectTrigger className="rounded-md mt-1" data-testid="wiz-match">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="broad">Broad</SelectItem>
                  <SelectItem value="phrase">Phrase</SelectItem>
                  <SelectItem value="exact">Exact</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-3">
            <div className="text-xs text-muted-foreground">
              Rellena los valores que tengas. Gasto y Ventas se autocalcularán si las dejas en 0.
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Impresiones</Label>
                <Input type="number" value={form.impressions} onChange={(e) => setForm({ ...form, impressions: e.target.value })} className="rounded-md mt-1 num" data-testid="wiz-impressions" />
              </div>
              <div>
                <Label className="text-xs">Clicks</Label>
                <Input type="number" value={form.clicks} onChange={(e) => setForm({ ...form, clicks: e.target.value })} className="rounded-md mt-1 num" data-testid="wiz-clicks" />
              </div>
              <div>
                <Label className="text-xs flex items-center gap-1">CPC <InfoTooltip content="cpc" /></Label>
                <Input type="number" step="0.01" value={form.cpc} onChange={(e) => setForm({ ...form, cpc: e.target.value })} className="rounded-md mt-1 num" data-testid="wiz-cpc" />
              </div>
              <div>
                <Label className="text-xs">Gasto (auto)</Label>
                <Input type="number" step="0.01" value={form.spend} onChange={(e) => setForm({ ...form, spend: e.target.value })} className="rounded-md mt-1 num" placeholder={(pv.spend || 0).toFixed(2)} data-testid="wiz-spend" />
              </div>
              <div>
                <Label className="text-xs">Pedidos</Label>
                <Input type="number" value={form.orders} onChange={(e) => setForm({ ...form, orders: e.target.value })} className="rounded-md mt-1 num" data-testid="wiz-orders" />
              </div>
              <div>
                <Label className="text-xs">Ventas (auto)</Label>
                <Input type="number" step="0.01" value={form.sales} onChange={(e) => setForm({ ...form, sales: e.target.value })} className="rounded-md mt-1 num" placeholder={(pv.sales || 0).toFixed(2)} data-testid="wiz-sales" />
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-3 animate-fade-in">
            <div className="border border-border rounded-md p-4 bg-muted/40">
              <div className="text-sm font-semibold">{form.term}</div>
              <div className="text-xs text-muted-foreground">
                {form.campaign || "Sin campaña"} · {form.ad_type} · {form.match_type}
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <PvTile label="Gasto" value={fmtMoney(pv.spend, sym)} />
              <PvTile label="Ventas" value={fmtMoney(pv.sales, sym)} />
              <PvTile label="CTR" value={fmtPct(pv.ctr)} />
              <PvTile label="CVR" value={fmtPct(pv.cvr)} />
              <PvTile label="ACoS" value={pv.acos ? fmtPct(pv.acos) : "—"} />
              <PvTile label="ROAS" value={(pv.roas || 0).toFixed(2)} />
              <PvTile label="ACoS +1" value={pv.acosNext ? fmtPct(pv.acosNext) : "—"} tooltip="acos_siguiente" />
              <PvTile label="PE" value={pv.pe ? fmtPct(pv.pe) : "—"} tooltip="pe" />
              <PvTile label="Estado" value={pv.badge} />
            </div>
          </div>
        )}

        <DialogFooter className="flex items-center justify-between mt-2">
          <div className="flex gap-2">
            {step > 1 && (
              <Button variant="outline" onClick={() => setStep(step - 1)} className="rounded-md" data-testid="wiz-back">
                <ChevronLeft className="size-4 mr-1" /> Atrás
              </Button>
            )}
          </div>
          <div>
            {step < 3 ? (
              <Button
                onClick={() => setStep(step + 1)}
                className="rounded-md bg-coral hover:bg-coral-500 text-white"
                data-testid="wiz-next"
              >
                Siguiente <ChevronRight className="size-4 ml-1" />
              </Button>
            ) : (
              <Button
                onClick={submit}
                disabled={saving}
                className="rounded-md bg-coral hover:bg-coral-500 text-white"
                data-testid="wiz-submit"
              >
                {saving ? <Loader2 className="size-4 animate-spin mr-2" /> : <Check className="size-4 mr-2" />}
                Crear keyword
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function PvTile({ label, value, tooltip }) {
  return (
    <div className="border border-border rounded-md p-2 bg-card">
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground flex items-center gap-1">
        {label} {tooltip && <InfoTooltip content={tooltip} />}
      </div>
      <div className="num text-sm font-semibold">{value}</div>
    </div>
  );
}
