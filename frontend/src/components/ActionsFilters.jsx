import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "./ui/select";
import { Button } from "./ui/button";
import { Switch } from "./ui/switch";
import { Label } from "./ui/label";
import { X } from "lucide-react";
import { ACTION_LABELS } from "../lib/recommendations";
import { InfoTooltip } from "./InfoTooltip";

const ACTION_OPTIONS = [
  "WAIT_FOR_DATA", "OBSERVE", "LOWER_BID", "HOLD", "SCALE",
  "MOVE_TO_EXACT", "NEGATIVE_EXACT_CANDIDATE", "NEGATIVE_PHRASE_CANDIDATE",
  "REVIEW_CAMPAIGN", "PAUSE_TARGET",
];

const RELEVANCE_OPTIONS = ["unreviewed", "high", "medium", "low"];
const RELEVANCE_LABEL = { unreviewed: "Sin revisar", high: "Alta", medium: "Media", low: "Baja" };

const PRI_OPTIONS = ["high", "medium", "low"];
const PRI_LABEL = { high: "Alta", medium: "Media", low: "Baja" };

const ALL = "__all__";

function FilterSelect({ label, value, onChange, options, labelMap, testid }) {
  return (
    <div className="flex flex-col gap-1">
      <Label className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</Label>
      <Select value={value || ALL} onValueChange={(v) => onChange(v === ALL ? "" : v)}>
        <SelectTrigger className="h-8 w-[150px] rounded-md text-xs" data-testid={testid}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>Todas</SelectItem>
          {options.map((o) => (
            <SelectItem key={o} value={o} data-testid={`${testid}-opt-${o}`}>
              {labelMap?.[o] ?? o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

export default function ActionsFilters({ value, onChange }) {
  const update = (patch) => onChange({ ...value, ...patch });
  const isDirty =
    value.priority || value.actionType || value.confidence || value.risk ||
    value.relevance || value.onlyWithOrders || value.onlyNegativeProfit;

  return (
    <div className="border border-border rounded-lg bg-card p-3 flex flex-wrap items-end gap-3" data-testid="actions-filters">
      <FilterSelect
        label="Prioridad"
        value={value.priority}
        onChange={(v) => update({ priority: v })}
        options={PRI_OPTIONS}
        labelMap={PRI_LABEL}
        testid="filter-priority"
      />
      <FilterSelect
        label="Acción"
        value={value.actionType}
        onChange={(v) => update({ actionType: v })}
        options={ACTION_OPTIONS}
        labelMap={ACTION_LABELS}
        testid="filter-action-type"
      />
      <FilterSelect
        label="Confianza"
        value={value.confidence}
        onChange={(v) => update({ confidence: v })}
        options={PRI_OPTIONS}
        labelMap={PRI_LABEL}
        testid="filter-confidence"
      />
      <FilterSelect
        label="Riesgo"
        value={value.risk}
        onChange={(v) => update({ risk: v })}
        options={PRI_OPTIONS}
        labelMap={PRI_LABEL}
        testid="filter-risk"
      />
      <FilterSelect
        label="Relevancia"
        value={value.relevance}
        onChange={(v) => update({ relevance: v })}
        options={RELEVANCE_OPTIONS}
        labelMap={RELEVANCE_LABEL}
        testid="filter-relevance"
      />

      <div className="flex flex-col gap-1">
        <Label className="text-[10px] uppercase tracking-widest text-muted-foreground inline-flex items-center gap-1">
          <span>Solo con ventas</span>
          <InfoTooltip content="only_with_orders" />
        </Label>
        <div className="flex items-center h-8">
          <Switch
            checked={!!value.onlyWithOrders}
            onCheckedChange={(v) => update({ onlyWithOrders: !!v })}
            data-testid="filter-with-orders"
          />
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <Label className="text-[10px] uppercase tracking-widest text-muted-foreground inline-flex items-center gap-1">
          <span>Solo en pérdida</span>
          <InfoTooltip content="only_negative_profit" />
        </Label>
        <div className="flex items-center h-8">
          <Switch
            checked={!!value.onlyNegativeProfit}
            onCheckedChange={(v) => update({ onlyNegativeProfit: !!v })}
            data-testid="filter-negative-profit"
          />
        </div>
      </div>

      {isDirty && (
        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            onChange({
              priority: "", actionType: "", confidence: "", risk: "",
              relevance: "", onlyWithOrders: false, onlyNegativeProfit: false,
            })
          }
          className="rounded-md h-8 gap-1.5"
          data-testid="filter-clear"
        >
          <X className="size-3.5" /> Limpiar
        </Button>
      )}
    </div>
  );
}
