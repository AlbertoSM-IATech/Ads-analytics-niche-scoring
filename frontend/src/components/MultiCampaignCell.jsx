import { useEffect, useState } from "react";
import {
  Popover, PopoverContent, PopoverTrigger,
} from "./ui/popover";
import { Checkbox } from "./ui/checkbox";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Plus, Pencil, Megaphone } from "lucide-react";

/**
 * Inline editor for the campaigns column of the keywords table.
 * Receives the row's current `campaigns` array and the master `allCampaigns` list.
 * Calls `onSave(newArray)` after the popover closes if there were changes.
 */
export default function MultiCampaignCell({ campaigns = [], allCampaigns = [], onSave, testid }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(campaigns);
  const [newCamp, setNewCamp] = useState("");

  useEffect(() => { setDraft(campaigns); }, [campaigns, open]);

  const toggle = (c) => {
    setDraft((cur) => cur.includes(c) ? cur.filter((x) => x !== c) : [...cur, c]);
  };

  const addNew = () => {
    const v = newCamp.trim();
    if (!v) return;
    if (!draft.includes(v)) setDraft([...draft, v]);
    setNewCamp("");
  };

  const close = (apply) => {
    setOpen(false);
    if (!apply) return;
    const sortedNew = [...draft].sort();
    const sortedOld = [...campaigns].sort();
    if (sortedNew.length !== sortedOld.length || sortedNew.some((c, i) => c !== sortedOld[i])) {
      onSave?.(draft);
    }
  };

  // Merge for the checkbox list: union of all known campaigns + any draft additions
  const options = Array.from(new Set([...(allCampaigns || []), ...draft])).sort();

  return (
    <Popover open={open} onOpenChange={(o) => { if (!o) close(true); else setOpen(true); }}>
      <PopoverTrigger asChild>
        <button
          className="text-left max-w-[220px] group inline-flex items-center gap-1 hover:text-coral"
          data-testid={testid}
          title="Click para gestionar campañas"
        >
          {campaigns.length === 0 ? (
            <span className="text-muted-foreground italic text-xs">sin campaña</span>
          ) : campaigns.length === 1 ? (
            <span className="truncate">{campaigns[0]}</span>
          ) : (
            <span className="inline-flex items-center gap-1 flex-wrap">
              <Badge variant="outline" className="rounded-md text-[10px] py-0 px-1.5 max-w-[120px] truncate">{campaigns[0]}</Badge>
              <Badge variant="outline" className="rounded-md text-[10px] py-0 px-1.5 bg-muted">+{campaigns.length - 1}</Badge>
            </span>
          )}
          <Pencil className="size-3 opacity-0 group-hover:opacity-60 transition-opacity" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-72 p-0" align="start">
        <div className="p-3 border-b border-border">
          <div className="flex items-center gap-2">
            <Megaphone className="size-4 text-coral" />
            <span className="text-sm font-semibold">Campañas asignadas</span>
            <Badge variant="outline" className="ml-auto text-xs num">{draft.length}</Badge>
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">Marca todas las que apliquen.</div>
        </div>
        <div className="max-h-56 overflow-y-auto p-2 space-y-1">
          {options.length === 0 && (
            <div className="text-xs text-muted-foreground italic px-2 py-3 text-center">
              No hay campañas todavía. Crea una abajo.
            </div>
          )}
          {options.map((c) => {
            const on = draft.includes(c);
            return (
              <label
                key={c}
                className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-muted/60 cursor-pointer"
                data-testid={`mc-option-${c.slice(0, 25)}`}
              >
                <Checkbox checked={on} onCheckedChange={() => toggle(c)} />
                <span className="text-xs truncate flex-1">{c}</span>
              </label>
            );
          })}
        </div>
        <div className="p-2 border-t border-border flex items-center gap-1">
          <Input
            placeholder="Nueva campaña…"
            value={newCamp}
            onChange={(e) => setNewCamp(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addNew(); } }}
            className="rounded-md h-8 text-xs"
            data-testid="mc-new-campaign-input"
          />
          <Button
            size="icon" variant="ghost" className="h-8 w-8 shrink-0"
            onClick={addNew}
            disabled={!newCamp.trim()}
            data-testid="mc-add-campaign-btn"
          >
            <Plus className="size-4" />
          </Button>
        </div>
        <div className="p-2 border-t border-border flex items-center gap-2">
          <Button size="sm" variant="ghost" className="rounded-md flex-1" onClick={() => close(false)} data-testid="mc-cancel-btn">
            Cancelar
          </Button>
          <Button size="sm" className="rounded-md flex-1 bg-coral hover:bg-coral-500 text-white" onClick={() => close(true)} data-testid="mc-apply-btn">
            Aplicar
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
