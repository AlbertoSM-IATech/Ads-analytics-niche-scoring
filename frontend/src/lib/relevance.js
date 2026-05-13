// Phase 2B — manual relevance dictionary used in table dot and detail selector.
// Keep aligned with backend ALLOWED_RELEVANCE in server.py.

export const RELEVANCE_OPTIONS = [
  { value: "unreviewed", label: "Sin revisar" },
  { value: "high",       label: "Alta" },
  { value: "medium",     label: "Media" },
  { value: "low",        label: "Baja" },
];

export const RELEVANCE_DOT = {
  unreviewed: { cls: "bg-neutral-300 dark:bg-neutral-600", label: "Sin revisar" },
  high:       { cls: "bg-green-500",                       label: "Relevancia: Alta" },
  medium:     { cls: "bg-amber-500",                       label: "Relevancia: Media" },
  low:        { cls: "bg-red-400",                         label: "Relevancia: Baja" },
};

export function getRelevanceDot(v) {
  return RELEVANCE_DOT[v] || RELEVANCE_DOT.unreviewed;
}
