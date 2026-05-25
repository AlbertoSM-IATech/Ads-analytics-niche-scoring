// Phase 4B — Pure CSV exporter for the read-only recommendation engine output.
// This is NOT an Amazon Ads bulk sheet. The file is named explicitly to avoid
// any confusion ("publify_acciones_filtradas_YYYY-MM-DD.csv").
//
// - Separator: ';' (safer for Excel ES, also keeps commas inside `reason`/
//   `amazon_instruction` intact without forced quoting).
// - Encoding: UTF-8 with BOM so Excel detects encoding correctly.
// - Numeric fields use the dot as decimal separator (no locale formatting,
//   no currency symbol, no '%').
//
// Pure module: no React, no axios, no DOM-dependent side effects in build helpers.
// Only `downloadCsv` touches the DOM (Blob + anchor click).

import { ACTION_LABELS } from "./recommendations";

export const CSV_COLUMNS = [
  { key: "priority",                    type: "string" },
  { key: "priority_score",              type: "number2" },
  { key: "action_type",                 type: "string" },
  { key: "action_label",                type: "string" },
  { key: "term",                        type: "string" },
  { key: "campaign",                    type: "string" },
  { key: "targeting",                   type: "string" },
  { key: "customer_search_term",        type: "string" },
  { key: "match_type",                  type: "string" },
  { key: "clicks",                      type: "int" },
  { key: "spend",                       type: "number2" },
  { key: "sales",                       type: "number2" },
  { key: "orders",                      type: "int" },
  { key: "cpc_real",                    type: "number2" },
  { key: "cpc_source",                  type: "string" },
  { key: "acos",                        type: "number2" },
  { key: "acos_pe_kdp",                 type: "number2" },
  { key: "clicks_pe",                   type: "number2" },
  { key: "clicks_fase",                 type: "number2" },
  { key: "consumo_pe",                  type: "number4" },
  { key: "consumo_fase",                type: "number4" },
  { key: "beneficio_kdp",               type: "number2" },
  { key: "relevance",                   type: "string" },
  { key: "confidence",                  type: "string" },
  { key: "risk",                        type: "string" },
  { key: "is_recoverable_with_next_sale", type: "bool" },
  { key: "detected_problem",            type: "string" },
  { key: "reason",                      type: "string" },
  { key: "recommended_action",          type: "string" },
  { key: "amazon_instruction",          type: "string" },
];

function fmtNumber(v, decimals) {
  if (v == null || v === "") return "";
  const n = Number(v);
  if (!Number.isFinite(n)) return "";
  return n.toFixed(decimals);
}

function fmtInt(v) {
  if (v == null || v === "") return "";
  const n = Number(v);
  if (!Number.isFinite(n)) return "";
  return String(Math.trunc(n));
}

function fmtBool(v) {
  if (v === true) return "true";
  if (v === false) return "false";
  return "";
}

function valueFor(rec, key) {
  // Top-level fields on the Recommendation:
  if (key === "action_label") return ACTION_LABELS[rec.action_type] || rec.action_type || "";
  if (key === "is_recoverable_with_next_sale") return rec.is_recoverable_with_next_sale;
  if (
    key === "priority" || key === "priority_score" || key === "action_type" ||
    key === "term" || key === "campaign" || key === "targeting" ||
    key === "customer_search_term" || key === "match_type" ||
    key === "confidence" || key === "risk" || key === "detected_problem" ||
    key === "reason" || key === "recommended_action" || key === "amazon_instruction"
  ) {
    return rec[key];
  }
  // Everything else lives under metrics.
  return rec.metrics ? rec.metrics[key] : undefined;
}

function renderCell(rec, col) {
  const raw = valueFor(rec, col.key);
  switch (col.type) {
    case "int":     return fmtInt(raw);
    case "number2": return fmtNumber(raw, 2);
    case "number4": return fmtNumber(raw, 4);
    case "bool":    return fmtBool(raw);
    default:        return raw == null ? "" : String(raw);
  }
}

const SEP = ";";

function esc(cell) {
  if (cell == null) return "";
  const s = String(cell);
  // Quote when containing the separator, double quotes, or any newline.
  if (s.includes(SEP) || s.includes('"') || s.includes("\n") || s.includes("\r")) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

export function buildCsv(recs) {
  const header = CSV_COLUMNS.map((c) => esc(c.key)).join(SEP);
  const rows = (recs || []).map((rec) =>
    CSV_COLUMNS.map((c) => esc(renderCell(rec, c))).join(SEP)
  );
  // RFC 4180 line ending + UTF-8 BOM so Excel detects UTF-8 automatically.
  return "\ufeff" + [header, ...rows].join("\r\n") + "\r\n";
}

export function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function defaultExportFilename(date = todayIso()) {
  return `publify_acciones_filtradas_${date}.csv`;
}

export function downloadCsv(recs, filename = defaultExportFilename()) {
  const csv = buildCsv(recs);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Defer revoke so the browser has time to grab the blob.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return { rows: (recs || []).length, filename };
}
