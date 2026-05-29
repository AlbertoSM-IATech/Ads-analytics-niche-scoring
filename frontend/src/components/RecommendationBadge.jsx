import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from "./ui/tooltip";
import { useNavigate } from "react-router-dom";
import {
  ACTION_LABELS, ACTION_STYLES, confidenceLabel, riskLabel,
} from "../lib/recommendations";

/**
 * Compact badge that renders the dominant recommendation for a keyword row.
 * Returns null when no recommendation applies — never blocks the row.
 *
 * Phase 4A.1: clicking the badge deep-links to `/acciones?action_type=<TYPE>`.
 * The click stops propagation so the surrounding term button (which opens the
 * detail sheet) doesn't fire — clicking the term still opens the sheet.
 */
export function RecommendationBadge({ rec, testidSuffix }) {
  const navigate = useNavigate();
  if (!rec || !rec.action_type) return null;
  const style = ACTION_STYLES[rec.action_type] || ACTION_STYLES.WAIT_FOR_DATA;
  const label = ACTION_LABELS[rec.action_type] || rec.action_type;
  const score = typeof rec.priority_score === "number" ? Math.round(rec.priority_score) : "—";

  const goToActions = (e) => {
    e.preventDefault();
    e.stopPropagation();
    navigate(`/acciones?action_type=${encodeURIComponent(rec.action_type)}`);
  };

  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            role="button"
            tabIndex={0}
            onClick={goToActions}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") goToActions(e);
            }}
            className={`inline-flex items-center rounded-md border text-[10px] py-0 px-1.5 cursor-pointer hover:opacity-80 transition-opacity shrink-0 ${style.cls}`}
            data-testid={`rec-badge-${testidSuffix}`}
            data-action-type={rec.action_type}
            data-priority={rec.priority}
            title={`Ver todas las acciones «${label}»`}
          >
            {label}
          </span>
        </TooltipTrigger>
        <TooltipContent
          side="top"
          align="start"
          sideOffset={8}
          collisionPadding={12}
          className="z-[60] max-w-[320px] rounded-md border border-border bg-popover text-popover-foreground px-3 py-2 text-xs shadow-lg space-y-1.5"
        >
          <div className="font-semibold text-foreground">{label}</div>
          {rec.detected_problem && (
            <div className="text-muted-foreground italic leading-snug">{rec.detected_problem}</div>
          )}
          {rec.reason && <div className="leading-snug text-foreground/90">{rec.reason}</div>}
          <div className="text-muted-foreground text-[10px] flex flex-wrap gap-x-2 gap-y-0.5 pt-1.5 border-t border-border">
            <span>Confianza: <span className="text-foreground/90">{confidenceLabel(rec.confidence)}</span></span>
            <span>·</span>
            <span>Riesgo: <span className="text-foreground/90">{riskLabel(rec.risk)}</span></span>
            <span>·</span>
            <span className="num">Score <span className="text-foreground/90">{score}</span></span>
          </div>
          <div className="text-[10px] pt-1 border-t border-border text-coral">
            Click → ver todas las acciones «{label}»
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
