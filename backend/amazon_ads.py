"""
Amazon Ads report parser.
Supports Sponsored Products / Brands / Display reports (Search Term, Campaign, Placement).
Auto-detects headers in ES / EN / IT.
"""
from __future__ import annotations
import io
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


# Header aliases (lowercased, trimmed). Order matters: more-specific first.
HEADER_ALIASES: dict[str, list[str]] = {
    "campaign": [
        "campaign name", "campaign", "nombre de la campaña", "nombre de campaña",
        "campaña", "campagna", "nome campagna",
    ],
    "ad_group": [
        "ad group name", "ad group", "grupo de anuncios", "gruppo di annunci",
    ],
    "portfolio": [
        "portfolio name", "portfolio", "portafolio", "portafoglio",
    ],
    "match_type": [
        "match type", "tipo de concordancia", "tipo di corrispondenza", "concordancia",
    ],
    "targeting": [
        "targeting", "keyword text", "keyword", "palabra clave", "orientación",
        "targeting expression", "parola chiave", "product targeting expression",
    ],
    "customer_search_term": [
        "customer search term", "search term", "término de búsqueda",
        "termino de busqueda", "termine di ricerca", "consulta del cliente",
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
        "clicks", "clics", "clic", "click",
    ],
    "ctr": [
        "click-thru rate (ctr)", "click-through rate (ctr)", "click-thru rate",
        "click-through rate", "ctr", "tasa de clics", "porcentaje de clics",
        "tasso di clic (ctr)", "tasso di clic",
    ],
    "cpc": [
        "cost per click (cpc)", "cost per click", "avg. cpc", "average cpc",
        "cpc", "cpc medio", "coste por clic", "costo per clic",
    ],
    "spend": [
        "spend", "gasto", "coste", "costo", "inversión", "spesa",
    ],
    "orders": [
        "7 day total orders (#)", "14 day total orders (#)",
        "total orders", "orders", "pedidos", "pedidos totales",
        "pedidos de 7 días", "pedidos de 14 días",
        "ordini", "ordini totali", "acquisti",
    ],
    "sales": [
        "7 day total sales", "14 day total sales", "total sales", "sales",
        "ventas", "ventas totales", "ventas de 7 días", "ventas de 14 días",
        "vendite", "vendite totali",
    ],
    "acos": [
        "total advertising cost of sales (acos)",
        "advertising cost of sales (acos)", "acos", "acos total",
    ],
    "roas": [
        "total return on advertising spend (roas)",
        "return on advertising spend (roas)", "roas",
    ],
    "conversion_rate": [
        "7 day conversion rate", "conversion rate", "tasa de conversión",
        "tasso di conversione",
    ],
}


def _normalize(s: str) -> str:
    return str(s).strip().lower().replace("\u00a0", " ")


def auto_map_headers(headers: list[str]) -> dict[str, str]:
    """Return mapping {original_header: canonical_field}. Unmapped headers are excluded."""
    result: dict[str, str] = {}
    used: set[str] = set()
    norm_headers = [(h, _normalize(h)) for h in headers]

    # Exact match first
    for h, nh in norm_headers:
        for field, aliases in HEADER_ALIASES.items():
            if field in used:
                continue
            if nh in aliases:
                result[h] = field
                used.add(field)
                break

    # Partial match for the rest
    for h, nh in norm_headers:
        if h in result:
            continue
        for field, aliases in HEADER_ALIASES.items():
            if field in used:
                continue
            if any(a in nh or nh in a for a in aliases):
                result[h] = field
                used.add(field)
                break
    return result


def detect_report_type(headers: list[str]) -> str:
    """Return 'search_term' | 'campaign' | 'placement' | 'unknown'."""
    norm = [_normalize(h) for h in headers]
    has_search_term = any(
        a in norm or any(a in h for h in norm)
        for a in HEADER_ALIASES["customer_search_term"]
    )
    has_placement = any(a in norm for a in HEADER_ALIASES["placement"])
    has_campaign = any(
        a in norm or any(a in h for h in norm) for a in HEADER_ALIASES["campaign"]
    )
    if has_search_term:
        return "search_term"
    if has_placement:
        return "placement"
    if has_campaign:
        return "campaign"
    return "unknown"


def detect_ad_type(headers: list[str], filename: str = "") -> str:
    """Try to detect SP / SB / SD from headers or filename hints."""
    blob = " ".join(_normalize(h) for h in headers) + " " + _normalize(filename)
    if "sponsored display" in blob or " sd " in blob or blob.endswith(" sd"):
        return "SD"
    if "sponsored brands" in blob or " sb " in blob or blob.endswith(" sb"):
        return "SB"
    if "sponsored products" in blob or " sp " in blob or blob.endswith(" sp"):
        return "SP"
    # Heuristic: SB reports usually have "keyword text" at campaign level;
    # SD reports have "targeting expression"
    if "targeting expression" in blob:
        return "SD"
    return "SP"


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
    if not s or s.lower() in ("nan", "null", "-", "n/a"):
        return 0.0
    # remove currency symbols, thousand separators, percent sign
    s = s.replace("\u00a0", "").replace(" ", "")
    s = s.replace("$", "").replace("€", "").replace("£", "").replace("¥", "")
    s = s.replace("%", "")
    # Handle european format: 1.234,56 -> 1234.56
    if "," in s and "." in s:
        # assume thousands is '.' and decimal is ','
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


def parse_ads_file(content: bytes, filename: str) -> dict[str, Any]:
    """Parse an uploaded Amazon Ads CSV/XLSX file and return normalized structure."""
    name_lower = filename.lower()
    buf = io.BytesIO(content)

    if name_lower.endswith(".xlsx") or name_lower.endswith(".xls"):
        df = pd.read_excel(buf)
    else:
        # Try utf-8, then latin-1, try sep=',' then sep=';' then '\t'
        raw = content
        last_err: Exception | None = None
        df = None
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            for sep in (",", ";", "\t"):
                try:
                    df = pd.read_csv(
                        io.BytesIO(raw), sep=sep, encoding=enc, engine="python",
                        dtype=str, keep_default_na=False,
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

    df.columns = [str(c).strip() for c in df.columns]
    headers = list(df.columns)
    mapping = auto_map_headers(headers)
    report_type = detect_report_type(headers)
    ad_type = detect_ad_type(headers, filename)

    # Rename columns to canonical names
    rename_map = {h: mapping[h] for h in headers if h in mapping}
    df2 = df.rename(columns=rename_map).copy()

    # Keep only canonical fields that exist
    keep = [c for c in df2.columns if c in CANONICAL_FIELDS]
    df2 = df2[keep]

    # Coerce numeric fields
    num_fields = ["impressions", "clicks", "ctr", "cpc", "spend", "orders",
                  "sales", "acos", "roas", "conversion_rate"]
    for f in num_fields:
        if f in df2.columns:
            df2[f] = df2[f].map(_to_number)

    # Coerce string fields
    str_fields = ["campaign", "ad_group", "portfolio", "match_type",
                  "targeting", "customer_search_term", "placement",
                  "start_date", "end_date", "currency"]
    for f in str_fields:
        if f in df2.columns:
            df2[f] = df2[f].astype(str).fillna("")

    # Attach ad_type to every row
    df2["ad_type"] = ad_type

    rows = df2.to_dict(orient="records")
    # Compute aggregates
    aggregates = compute_kpis(rows)

    return {
        "headers_detected": headers,
        "header_mapping": mapping,
        "report_type": report_type,
        "ad_type": ad_type,
        "row_count": len(rows),
        "rows": rows,
        "kpis": aggregates,
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
