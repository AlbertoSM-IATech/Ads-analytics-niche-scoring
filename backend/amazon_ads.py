"""
Amazon Ads report parser.
Supports Sponsored Products / Brands / Display reports (Search Term, Campaign, Placement).
Auto-detects headers in ES / EN / IT.

IMPORT-2 stabilization:
  * Score-based header matcher (avoids false positives from generic substrings).
  * Match-type normalization ES/EN/IT → canonical {exact, phrase, broad, auto}.
  * ACoS/CTR/CVR fractional-vs-percent auto-detection.
  * Diagnostics payload: matched_fields, unmatched_headers, missing_critical,
    warnings, capabilities, confidence.
"""
from __future__ import annotations
import io
import re
from typing import Any
import pandas as pd


# Canonical fields we care about (internal schema)
CANONICAL_FIELDS = [
    "campaign",
    "ad_group",
    "portfolio",
    "match_type",
    "targeting",           # keyword/target/product expression
    "customer_search_term",
    "placement",
    "start_date",
    "end_date",
    "currency",
    "impressions",
    "clicks",
    "ctr",
    "cpc",
    "spend",
    "orders",
    "sales",
    "acos",
    "roas",
    "conversion_rate",
    "ad_type",             # SP, SB, SD
]


# Header aliases (lowercased, trimmed). More-specific aliases should be listed
# first inside each list to improve substring-scoring behaviour when needed.
HEADER_ALIASES: dict[str, list[str]] = {
    "campaign": [
        "campaign name", "nombre de la campaña", "nombre de campaña",
        "nome campagna",
        "campaign", "campaña", "campagna",
    ],
    "ad_group": [
        "ad group name", "grupo de anuncios", "gruppo di annunci",
        "ad group",
    ],
    "portfolio": [
        "portfolio name", "portfolio", "portafolio", "portafoglio",
    ],
    "match_type": [
        "match type", "tipo de concordancia", "tipo di corrispondenza",
        "concordancia",
    ],
    "targeting": [
        "targeting expression", "product targeting expression",
        "keyword text", "palabra clave", "parola chiave",
        "targeting", "orientación",
        "keyword",  # low-priority; last resort
    ],
    "customer_search_term": [
        "customer search term", "término de búsqueda",
        "termino de busqueda", "termine di ricerca", "consulta del cliente",
        "search term",  # generic; risky next to other columns → placed last
    ],
    "placement": [
        "placement", "ubicación", "posizionamento",
    ],
    "start_date": [
        "start date", "fecha de inicio", "data di inizio",
    ],
    "end_date": [
        "end date", "fecha de fin", "data di fine",
    ],
    "currency": [
        "currency", "moneda", "valuta",
    ],
    "impressions": [
        "impressions", "impresiones", "impressioni", "impr.", "impr",
    ],
    "clicks": [
        "clicks", "clics", "click", "clic",
    ],
    "ctr": [
        "click-thru rate (ctr)", "click-through rate (ctr)",
        "click-thru rate", "click-through rate",
        "tasa de clics", "porcentaje de clics",
        "tasso di clic (ctr)", "tasso di clic",
        "ctr",
    ],
    "cpc": [
        "cost per click (cpc)", "cost per click", "avg. cpc", "average cpc",
        "cpc medio", "coste por clic", "costo per clic",
        "cpc",
    ],
    "spend": [
        "spend", "gasto", "coste total", "costo totale",
        "inversión", "spesa",
        "coste", "costo",  # generic → last
    ],
    "orders": [
        "7 day total orders (#)", "14 day total orders (#)",
        "total orders", "orders", "pedidos totales",
        "pedidos de 7 días", "pedidos de 14 días",
        "pedidos",
        "ordini totali", "ordini", "acquisti",
    ],
    "sales": [
        "7 day total sales", "14 day total sales", "total sales", "sales",
        "ventas totales", "ventas de 7 días", "ventas de 14 días",
        "ventas",
        "vendite totali", "vendite",
    ],
    "acos": [
        "total advertising cost of sales (acos)",
        "advertising cost of sales (acos)",
        "acos total",
        "acos",
    ],
    "roas": [
        "total return on advertising spend (roas)",
        "return on advertising spend (roas)",
        "roas",
    ],
    "conversion_rate": [
        "7 day conversion rate", "conversion rate", "tasa de conversión",
        "tasso di conversione",
    ],
}


# Fields that MUST be present to consider the report reliable per report type.
CRITICAL_FIELDS_BY_TYPE: dict[str, list[str]] = {
    "search_term": ["clicks", "spend", "sales", "orders"],
    "targeting":   ["clicks", "spend", "sales", "orders"],
    "campaign":    ["campaign", "clicks", "spend", "sales", "orders"],
    "placement":   ["clicks", "spend", "sales", "orders"],
    # unknown: no critical set → we only warn.
    "unknown":     [],
}

# Term-carrier requirement: for search_term/targeting we also need at least
# one of these two fields to identify the row.
TERM_CARRIER_FIELDS = ("customer_search_term", "targeting")


def _normalize(s: str) -> str:
    return str(s).strip().lower().replace("\u00a0", " ")


def _strip_currency_paren(s: str) -> str:
    """`Coste total (EUR)` → `coste total`.

    Removes anything inside parentheses when the parenthesised content looks
    like a currency ISO code (3 letters) or currency symbol.
    """
    return re.sub(
        r"\s*\((?:eur|usd|gbp|jpy|mxn|cad|aud|inr|brl|[€$£¥])\)\s*",
        "",
        s,
        flags=re.IGNORECASE,
    ).strip()


def _canon_header(s: str) -> str:
    n = _normalize(s)
    # Strip currency parenthetical; this makes 'Coste total (EUR)' behave like
    # 'coste total', a fully-listed alias, avoiding the 'coste' substring trap.
    n = _strip_currency_paren(n)
    return n


def _score_alias_match(header_norm: str, alias: str) -> int:
    """Return an integer score for how well `alias` matches `header_norm`.

    Scoring tiers (higher wins):
      100 — exact match
       80 — header equals alias with only trailing punctuation/spaces
       60 — alias is a full-word token inside header
       40 — header is a prefix of alias, or alias is a prefix of header
        0 — no meaningful match
    Substring in either direction is intentionally NOT scored anymore because
    that was the P0 fragility (`coste` matching `coste total (eur)` AND
    `coste por clic`).
    """
    if not header_norm or not alias:
        return 0
    if header_norm == alias:
        return 100
    # Ignore trailing punctuation for equality-like matches.
    h_stripped = re.sub(r"[\s\.\,\-_:;]+$", "", header_norm)
    a_stripped = re.sub(r"[\s\.\,\-_:;]+$", "", alias)
    if h_stripped == a_stripped:
        return 80
    # Whole-word token match: alias must appear surrounded by non-word chars.
    if re.search(rf"(?:^|\W){re.escape(alias)}(?:\W|$)", header_norm):
        return 60
    # Prefix matches (short-token safety).
    if len(alias) >= 3 and (header_norm.startswith(alias + " ")
                            or alias.startswith(header_norm + " ")):
        return 40
    return 0


def auto_map_headers(
    headers: list[str],
) -> tuple[dict[str, str], list[str], list[str], list[str]]:
    """Return (mapping, unmatched_headers, ambiguous_warnings, all_warnings).

    * mapping: {original_header: canonical_field}
    * unmatched_headers: headers that scored 0 against every canonical
    * ambiguous_warnings: human-readable warnings for collisions (two headers
      competing for the same canonical, or a header with multiple candidates
      that had similar scores)
    """
    all_warnings: list[str] = []
    ambiguous_warnings: list[str] = []

    # Precompute canonical form + best score per (header, field).
    header_norms = [(h, _canon_header(h)) for h in headers]
    # Best (score, field) per header.
    best_per_header: dict[str, tuple[int, str | None, list[str]]] = {}
    for h, hn in header_norms:
        scored: list[tuple[int, str]] = []
        for field, aliases in HEADER_ALIASES.items():
            best = 0
            for a in aliases:
                s = _score_alias_match(hn, a)
                if s > best:
                    best = s
            if best > 0:
                scored.append((best, field))
        scored.sort(key=lambda x: (-x[0], x[1]))
        if not scored:
            best_per_header[h] = (0, None, [])
            continue
        top_score, top_field = scored[0]
        # Detect ambiguity: another field within 20 points of the top.
        rivals = [f for s, f in scored[1:] if s >= top_score - 20 and s >= 60]
        best_per_header[h] = (top_score, top_field, rivals)
        if rivals:
            ambiguous_warnings.append(
                f"Cabecera «{h}» podría mapear a {top_field} o a "
                f"{'/'.join(rivals)}; se ha elegido {top_field} por mayor "
                f"puntuación ({top_score})."
            )

    # Assign canonical → header, preferring the highest score for each
    # canonical. If two headers both point to the same canonical, keep the
    # highest-score and warn about the losers.
    best_for_field: dict[str, tuple[int, str]] = {}  # field → (score, header)
    for h, (score, field, _rivals) in best_per_header.items():
        if not field or score <= 0:
            continue
        prev = best_for_field.get(field)
        if prev is None or score > prev[0]:
            if prev is not None:
                ambiguous_warnings.append(
                    f"Cabeceras «{prev[1]}» y «{h}» compiten por el campo "
                    f"{field}; se ha elegido «{h}» (score {score} vs "
                    f"{prev[0]})."
                )
            best_for_field[field] = (score, h)
        else:
            ambiguous_warnings.append(
                f"Cabeceras «{best_for_field[field][1]}» y «{h}» compiten "
                f"por el campo {field}; se ha elegido "
                f"«{best_for_field[field][1]}» (score "
                f"{best_for_field[field][0]} vs {score})."
            )

    mapping: dict[str, str] = {h: f for f, (_s, h) in best_for_field.items()}
    unmatched = [h for h, (score, _f, _r) in best_per_header.items()
                 if score == 0]
    all_warnings.extend(ambiguous_warnings)
    return mapping, unmatched, ambiguous_warnings, all_warnings


def detect_report_type(headers: list[str], mapping: dict[str, str]) -> tuple[str, str]:
    """Return (report_type, confidence).

    Uses the resolved mapping when available, falls back to loose header
    inspection. Confidence: high | medium | low | unknown.
    """
    canonicals = set(mapping.values())
    has_search_term = "customer_search_term" in canonicals
    has_placement = "placement" in canonicals
    has_campaign = "campaign" in canonicals
    has_targeting = "targeting" in canonicals

    if has_search_term:
        # If we also have a keyword/targeting column it's still a Search Term
        # Report (canonical shape: campaign + ad group + keyword + search term).
        return "search_term", "high" if has_campaign else "medium"
    if has_placement:
        return "placement", "high" if has_campaign else "medium"
    if has_targeting and has_campaign:
        return "targeting", "medium"
    if has_campaign:
        return "campaign", "high"

    # No canonical anchor recognised.
    return "unknown", "low"


def detect_ad_type(headers: list[str], filename: str = "") -> str:
    """Try to detect SP / SB / SD from headers or filename hints."""
    blob = " ".join(_normalize(h) for h in headers) + " " + _normalize(filename)
    if "sponsored display" in blob or " sd " in blob or blob.endswith(" sd"):
        return "SD"
    if "sponsored brands" in blob or " sb " in blob or blob.endswith(" sb"):
        return "SB"
    if "sponsored products" in blob or " sp " in blob or blob.endswith(" sp"):
        return "SP"
    if "targeting expression" in blob:
        return "SD"
    return "SP"


# ---------------------------------------------------------------------------
# Match-type normalization (i18n canonicalization)
# ---------------------------------------------------------------------------

_MATCH_TYPE_MAP: dict[str, str] = {
    # English
    "exact": "exact", "exact match": "exact",
    "phrase": "phrase", "phrase match": "phrase",
    "broad": "broad", "broad match": "broad",
    "auto": "auto", "automatic": "auto", "automatic targeting": "auto",
    # Spanish
    "exacta": "exact", "exactas": "exact",
    "frase": "phrase", "frases": "phrase",
    "amplia": "broad", "amplias": "broad",
    "automática": "auto", "automatica": "auto",
    "automáticas": "auto", "automaticas": "auto",
    # Italian
    "esatta": "exact", "esatte": "exact",
    # "frase" already covered (same word in IT/ES for phrase)
    "ampia": "broad", "ampie": "broad",
    "generica": "broad", "generiche": "broad",
    # "automatica" already covered
}


def normalize_match_type(value: Any) -> str | None:
    """Return canonical match_type in {exact, phrase, broad, auto} or None.

    Accepts EN / ES / IT variants case-insensitively. Preserves the raw value
    (returned as lowercase) when it can't be mapped, so downstream code can
    still surface it verbatim if needed.
    """
    if value is None:
        return None
    s = str(value).strip().lower()
    if not s or s in ("nan", "null", "-"):
        return None
    mapped = _MATCH_TYPE_MAP.get(s)
    if mapped is not None:
        return mapped
    # Some Amazon exports include the ad type prefix, e.g.
    # 'Sponsored Products Exact' → strip common prefixes.
    for prefix in ("sponsored products ", "sponsored brands ",
                   "sponsored display ", "sp ", "sb ", "sd "):
        if s.startswith(prefix):
            return normalize_match_type(s[len(prefix):])
    return s  # unknown label; caller decides


# ---------------------------------------------------------------------------
# Number normalisation
# ---------------------------------------------------------------------------

# Percent-shaped canonical fields (they represent percentages, e.g. 39.66
# means 39.66%).
_PERCENT_FIELDS = ("acos", "ctr", "conversion_rate")


def _to_number(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        try:
            if pd.isna(v):
                return 0.0
        except Exception:
            pass
        return float(v)
    s = str(v).strip()
    if not s or s.lower() in ("nan", "null", "-", "n/a", "—", "–"):
        return 0.0
    # remove currency symbols, thousand separators, percent sign
    s = s.replace("\u00a0", "").replace(" ", "")
    s = s.replace("$", "").replace("€", "").replace("£", "").replace("¥", "")
    s = s.replace("%", "")
    # Handle european format: 1.234,56 -> 1234.56
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        # only comma: treat as decimal separator
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _looks_like_percent_string(raw: Any) -> bool:
    return isinstance(raw, str) and "%" in raw


def _normalize_percent_column(
    df: pd.DataFrame, field: str
) -> tuple[bool, dict[str, Any]]:
    """Detect ACoS/CTR/CVR fractional-vs-percent shape and fix in place.

    Returns (was_fractional, info) where info is a small dict with `max`,
    `min`, `had_percent_sign_any` for warnings.
    """
    if field not in df.columns:
        return False, {}
    orig = df[field]
    had_pct = orig.astype(str).map(lambda x: "%" in x).any()
    # Convert to numeric first (bypass, we already coerced later, but we need
    # the values to decide).
    numeric = orig.map(_to_number)
    if numeric.empty:
        return False, {}
    max_v = float(numeric.max())
    min_v = float(numeric.min())
    # Heuristic: if max <= 1.0 AND max > 0 AND no '%' sign was present in any
    # row of the original text, assume the column is fractional (0..1) and
    # promote to percentage by ×100.
    if (not had_pct) and 0.0 < max_v <= 1.0:
        df[field] = numeric * 100.0
        return True, {"max": max_v, "min": min_v}
    df[field] = numeric
    return False, {"max": max_v, "min": min_v, "had_percent_sign": had_pct}


# ---------------------------------------------------------------------------
# Parse + diagnostics
# ---------------------------------------------------------------------------

def _read_dataframe(content: bytes, filename: str) -> pd.DataFrame:
    name_lower = filename.lower()
    if name_lower.endswith(".xlsx") or name_lower.endswith(".xls"):
        return pd.read_excel(io.BytesIO(content))
    last_err: Exception | None = None
    df = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        for sep in (",", ";", "\t"):
            try:
                df = pd.read_csv(
                    io.BytesIO(content), sep=sep, encoding=enc,
                    engine="python", dtype=str, keep_default_na=False,
                )
                if df.shape[1] >= 2:
                    last_err = None
                    break
            except Exception as e:
                last_err = e
                continue
        if df is not None and df.shape[1] >= 2:
            break
    if df is None:
        raise ValueError(f"No se pudo leer el archivo CSV: {last_err}")
    return df


def build_diagnostics(
    *,
    headers: list[str],
    mapping: dict[str, str],
    unmatched_headers: list[str],
    ambiguous_warnings: list[str],
    report_type: str,
    report_type_confidence: str,
    percent_notes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compute the diagnostics/capabilities/confidence payload."""
    matched_fields = sorted(set(mapping.values()))
    critical = CRITICAL_FIELDS_BY_TYPE.get(report_type, [])
    missing_critical = [f for f in critical if f not in matched_fields]

    # For search_term / targeting we also need at least one term carrier.
    if report_type in ("search_term", "targeting"):
        if not any(f in matched_fields for f in TERM_CARRIER_FIELDS):
            missing_critical.append("targeting_or_customer_search_term")

    warnings: list[str] = list(ambiguous_warnings)
    for field, note in percent_notes.items():
        if note.get("was_fractional"):
            warnings.append(
                f"El campo «{field}» estaba en formato fraccional "
                f"(0-1) sin símbolo %; se ha multiplicado por 100 para "
                f"interpretarlo como porcentaje. Rango detectado: "
                f"{note.get('min', 0):.4f}-{note.get('max', 0):.4f}."
            )
    if unmatched_headers:
        # Not a warning by itself, but surfaced explicitly to the caller.
        pass
    if report_type == "unknown":
        warnings.append(
            "No se ha reconocido el tipo de reporte a partir de las "
            "cabeceras. Revisa que sea un export válido de Amazon Ads "
            "(Search Term / Campaign / Placement)."
        )

    capabilities = {
        # Basic aggregations (impressions/clicks/spend/sales) — available
        # when at least clicks+spend are mapped.
        "ads_performance": all(f in matched_fields for f in ("clicks", "spend")),
        # Profitability calcs (ACoS/ROAS/CVR) — require sales+spend at least;
        # orders needed for CVR but not blocking.
        "profitability": all(f in matched_fields for f in ("spend", "sales")),
        # Negatives export — requires clicks + orders + (targeting|cst).
        "negatives": (
            "clicks" in matched_fields and "orders" in matched_fields
            and any(f in matched_fields for f in TERM_CARRIER_FIELDS)
        ),
        # Bid changes require current_bid — NOT captured yet (P1 in roadmap).
        "bid_changes": False,
        # TACOS requires total_sales (organic+ads) — NOT captured (P2).
        "tacos": False,
        # Bulk sheet requires Amazon IDs — NOT captured (P2).
        "bulk": False,
    }

    confidence = report_type_confidence
    if missing_critical and confidence in ("high", "medium"):
        confidence = "low"

    return {
        "report_type": report_type,
        "report_type_confidence": confidence,
        "matched_fields": matched_fields,
        "header_mapping": mapping,
        "unmatched_headers": unmatched_headers,
        "missing_critical": missing_critical,
        "warnings": warnings,
        "capabilities": capabilities,
    }


def parse_ads_file(
    content: bytes, filename: str, *, preview_rows: int = 0,
) -> dict[str, Any]:
    """Parse an uploaded Amazon Ads CSV/XLSX file and return normalized structure.

    When `preview_rows > 0`, the returned `rows` list is truncated to that
    length (the diagnostics payload still reflects the full file).
    """
    df = _read_dataframe(content, filename)
    df.columns = [str(c).strip() for c in df.columns]
    headers = list(df.columns)
    mapping, unmatched_headers, ambiguous_warnings, _ = auto_map_headers(headers)
    report_type, report_type_confidence = detect_report_type(headers, mapping)
    ad_type = detect_ad_type(headers, filename)

    # Rename columns to canonical names
    rename_map = {h: mapping[h] for h in headers if h in mapping}
    df2 = df.rename(columns=rename_map).copy()

    # Keep only canonical fields that exist
    keep = [c for c in df2.columns if c in CANONICAL_FIELDS]
    df2 = df2[keep]

    # Percent columns: detect fractional shape BEFORE the generic numeric
    # coercion overwrites the original text (we need to know if '%' was
    # present in the raw values).
    percent_notes: dict[str, dict[str, Any]] = {}
    for f in _PERCENT_FIELDS:
        if f in df2.columns:
            was_frac, info = _normalize_percent_column(df2, f)
            percent_notes[f] = {"was_fractional": was_frac, **info}

    # Coerce remaining numeric fields
    num_fields = ["impressions", "clicks", "cpc", "spend", "orders",
                  "sales", "roas"]
    for f in num_fields:
        if f in df2.columns:
            df2[f] = df2[f].map(_to_number)

    # Coerce string fields
    str_fields = ["campaign", "ad_group", "portfolio",
                  "targeting", "customer_search_term", "placement",
                  "start_date", "end_date", "currency"]
    for f in str_fields:
        if f in df2.columns:
            df2[f] = df2[f].astype(str).fillna("")

    # Normalize match_type (i18n canonicalization).
    if "match_type" in df2.columns:
        df2["match_type"] = df2["match_type"].map(normalize_match_type)

    # Attach ad_type to every row
    df2["ad_type"] = ad_type

    rows = df2.to_dict(orient="records")
    import uuid as _uuid
    for r in rows:
        r["id"] = str(_uuid.uuid4())
    aggregates = compute_kpis(rows)

    diagnostics = build_diagnostics(
        headers=headers,
        mapping=mapping,
        unmatched_headers=unmatched_headers,
        ambiguous_warnings=ambiguous_warnings,
        report_type=report_type,
        report_type_confidence=report_type_confidence,
        percent_notes=percent_notes,
    )

    result_rows = rows[:preview_rows] if preview_rows > 0 else rows

    return {
        "headers_detected": headers,
        "header_mapping": mapping,
        "report_type": report_type,
        "ad_type": ad_type,
        "row_count": len(rows),
        "rows": result_rows,
        "kpis": aggregates,
        "diagnostics": diagnostics,
    }


def compute_kpis(rows: list[dict]) -> dict[str, float]:
    imp = sum(r.get("impressions", 0) or 0 for r in rows)
    clk = sum(r.get("clicks", 0) or 0 for r in rows)
    spend = sum(r.get("spend", 0) or 0 for r in rows)
    sales = sum(r.get("sales", 0) or 0 for r in rows)
    orders = sum(r.get("orders", 0) or 0 for r in rows)
    ctr = (clk / imp * 100) if imp else 0.0
    cpc = (spend / clk) if clk else 0.0
    acos = (spend / sales * 100) if sales else 0.0
    roas = (sales / spend) if spend else 0.0
    cvr = (orders / clk * 100) if clk else 0.0
    return {
        "impressions": round(imp, 2),
        "clicks": round(clk, 2),
        "spend": round(spend, 2),
        "sales": round(sales, 2),
        "orders": round(orders, 2),
        "ctr": round(ctr, 2),
        "cpc": round(cpc, 2),
        "acos": round(acos, 2),
        "roas": round(roas, 2),
        "cvr": round(cvr, 2),
    }


def aggregate_by(rows: list[dict], key: str) -> list[dict]:
    """Group rows by a string key and sum metrics."""
    buckets: dict[str, dict] = {}
    for r in rows:
        k = (r.get(key) or "").strip() or "—"
        b = buckets.setdefault(k, {
            key: k, "impressions": 0.0, "clicks": 0.0, "spend": 0.0,
            "sales": 0.0, "orders": 0.0,
        })
        b["impressions"] += r.get("impressions", 0) or 0
        b["clicks"] += r.get("clicks", 0) or 0
        b["spend"] += r.get("spend", 0) or 0
        b["sales"] += r.get("sales", 0) or 0
        b["orders"] += r.get("orders", 0) or 0
    out = []
    for b in buckets.values():
        imp = b["impressions"]; clk = b["clicks"]; spend = b["spend"]; sales = b["sales"]; orders = b["orders"]
        b["ctr"] = round((clk / imp * 100) if imp else 0, 2)
        b["cpc"] = round((spend / clk) if clk else 0, 2)
        b["acos"] = round((spend / sales * 100) if sales else 0, 2)
        b["roas"] = round((sales / spend) if spend else 0, 2)
        b["cvr"] = round((orders / clk * 100) if clk else 0, 2)
        for f in ("impressions", "clicks", "spend", "sales", "orders"):
            b[f] = round(b[f], 2)
        out.append(b)
    out.sort(key=lambda x: x["spend"], reverse=True)
    return out
