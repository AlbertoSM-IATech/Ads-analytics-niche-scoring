import { useState } from "react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "./ui/dialog";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import { Plus, Trash2, Loader2, Megaphone, Check } from "lucide-react";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "./ui/select";
import { createCampaign } from "../lib/api";
import { useData } from "../context/DataContext";
import { toast } from "sonner";

const emptyKw = { term: "", clicks: 0, cpc: 0, orders: 0 };

export default function AddCampaignWizard({ open, onOpenChange, onCreated }) {
  const { active, loadActive } = useData();
  const [form, setForm] = useState({
    campaign: "",
    ad_type: "SP",
    match_type: "broad",
    keywords: [{ ...emptyKw }],
  });
  const [saving, setSaving] = useState(false);

  const addKw = () => setForm({ ...form, keywords: [...form.keywords, { ...emptyKw }] });
  const rmKw = (i) =>
    setForm({ ...form, keywords: form.keywords.filter((_, idx) => idx !== i) });
  const updKw = (i, patch) => {
    const arr = [...form.keywords];
    arr[i] = { ...arr[i], ...patch };
    setForm({ ...form, keywords: arr });
  };

  const submit = async () => {
    if (!active) return;
    if (!form.campaign.trim()) {
      toast.error("Nombre de campaña obligatorio");
      return;
    }
    const validKws = form.keywords.filter((k) => k.term.trim());
    if (!validKws.length) {
      toast.error("Añade al menos una keyword");
      return;
    }
    setSaving(true);
    try {
      const price = active.book_economy?.precio_libro || 0;
      const payload = {
        campaign: form.campaign.trim(),
        ad_type: form.ad_type,
        match_type: form.match_type,
        keywords: validKws.map((k) => {
          const clicks = Number(k.clicks) || 0;
          const cpc = Number(k.cpc) || 0;
          const orders = Number(k.orders) || 0;
          return {
            term: k.term.trim(),
            clicks,
            cpc,
            spend: clicks * cpc,
            orders,
            sales: orders * price,
            match_type: form.match_type,
            ad_type: form.ad_type,
          };
        }),
      };
      await createCampaign(active.id, payload);
      toast.success(`Campaña "${payload.campaign}" creada con ${validKws.length} keywords`);
      await loadActive(active.id);
      setForm({ campaign: "", ad_type: "SP", match_type: "broad", keywords: [{ ...emptyKw }] });
      onOpenChange(false);
      onCreated?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="add-campaign-wizard">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <Megaphone className="size-5 text-coral" /> Nueva campaña
          </DialogTitle>
          <DialogDescription>
            Crea una campaña y añade las keywords iniciales. El gasto y ventas se autocalcularán.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div>
            <Label className="text-xs">Nombre de campaña *</Label>
            <Input
              value={form.campaign}
              onChange={(e) => setForm({ ...form, campaign: e.target.value })}
              placeholder="SP - Mindfulness Broad ES"
              className="rounded-md mt-1"
              autoFocus
              data-testid="camp-name"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Tipo de anuncio</Label>
              <Select value={form.ad_type} onValueChange={(v) => setForm({ ...form, ad_type: v })}>
                <SelectTrigger className="rounded-md mt-1" data-testid="camp-adtype"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="SP">Sponsored Products</SelectItem>
                  <SelectItem value="SB">Sponsored Brands</SelectItem>
                  <SelectItem value="SBV">SB Video</SelectItem>
                  <SelectItem value="SD">Sponsored Display</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Match type</Label>
              <Select value={form.match_type} onValueChange={(v) => setForm({ ...form, match_type: v })}>
                <SelectTrigger className="rounded-md mt-1" data-testid="camp-match"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="broad">Broad</SelectItem>
                  <SelectItem value="phrase">Phrase</SelectItem>
                  <SelectItem value="exact">Exact</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="border border-border rounded-md bg-muted/30 p-3 space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs uppercase tracking-widest font-semibold">Keywords</Label>
              <Button size="sm" variant="outline" onClick={addKw} className="rounded-md h-7" data-testid="camp-add-kw">
                <Plus className="size-3.5 mr-1" /> Añadir
              </Button>
            </div>
            <div className="space-y-2">
              {form.keywords.map((k, i) => (
                <div key={i} className="grid grid-cols-[1fr_80px_80px_80px_32px] gap-2 items-center" data-testid={`camp-kw-${i}`}>
                  <Input
                    placeholder="keyword"
                    value={k.term}
                    onChange={(e) => updKw(i, { term: e.target.value })}
                    className="rounded-md"
                  />
                  <Input
                    type="number"
                    placeholder="clicks"
                    value={k.clicks}
                    onChange={(e) => updKw(i, { clicks: e.target.value })}
                    className="rounded-md num"
                  />
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="CPC"
                    value={k.cpc}
                    onChange={(e) => updKw(i, { cpc: e.target.value })}
                    className="rounded-md num"
                  />
                  <Input
                    type="number"
                    placeholder="pedidos"
                    value={k.orders}
                    onChange={(e) => updKw(i, { orders: e.target.value })}
                    className="rounded-md num"
                  />
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => rmKw(i)}
                    className="h-8 w-8"
                    disabled={form.keywords.length === 1}
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            onClick={submit}
            disabled={saving}
            className="rounded-md bg-coral hover:bg-coral-500 text-white w-full sm:w-auto"
            data-testid="camp-submit"
          >
            {saving ? <Loader2 className="size-4 animate-spin mr-2" /> : <Check className="size-4 mr-2" />}
            Crear campaña
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
