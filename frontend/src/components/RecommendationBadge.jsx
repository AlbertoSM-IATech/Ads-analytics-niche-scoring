import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from "./ui/tooltip";
import {
  ACTION_LABELS, ACTION_STYLES, confidenceLabel, riskLabel,
} from "../lib/recommendations";

/**
 * Compact badge that renders the dominant recommendation for a keyword row.
 * Returns null when no recommendation applies — never blocks the row.
 */
export function RecommendationBadge({ rec, testidSuffix }) {
  if (!rec || !rec.action_type) return null;
  const style = ACTION_STYLES[rec.action_type] || ACTION_STYLES.WAIT_FOR_DATA;
  const label = ACTION_LABELS[rec.action_type] || rec.action_type;
  const score = typeof rec.priority_score === "number" ? Math.round(rec.priority_score) : "—";
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className={`inline-flex items-center rounded-md border text-[10px] py-0 px-1.5 cursor-help shrink-0 ${style.cls}`}
            data-testid={`rec-badge-${testidSuffix}`}
            data-action-type={rec.action_type}
            data-priority={rec.priority}
          >
            {label}
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs text-xs space-y-1">
          <div className="font-semibold">{label}</div>
          {rec.detected_problem && (
            <div className="text-muted-foreground italic">{rec.detected_problem}</div>
          )}
          {rec.reason && <div>{rec.reason}</div>}
          <div className="text-muted-foreground text-[10px] flex gap-2 pt-1 border-t border-border/40">
            <span>Confianza: {confidenceLabel(rec.confidence)}</span>
            <span>·</span>
            <span>Riesgo: {riskLabel(rec.risk)}</span>
            <span>·</span>
            <span className="num">Score {score}</span>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
