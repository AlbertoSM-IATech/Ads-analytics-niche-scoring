from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, Optional
import uuid
from datetime import datetime, timezone

from amazon_ads import parse_ads_file, aggregate_by, compute_kpis
from acos_calc import (
    acos_equilibrio_pct, acos_actual_pct, acos_siguiente_click_pct,
    beneficio_ahora, beneficio_siguiente_click, conversion_pct,
    guias_fase, determinar_badge,
)
from market_score import (
    calculate_market_score, label_for_score, acos_siguiente_sin_venta_pct,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Publify Amazon Ads Analytics")
api = APIRouter(prefix="/api")


# ------------------- Models -------------------
class BookInfo(BaseModel):
    title: str = ""
    subtitle: str = ""
    description: str = ""
    categories: list[str] = []


class BookEconomy(BaseModel):
    precio_libro: float = 0.0
    regalias_por_venta: float = 0.0


class BookSettingsIn(BaseModel):
    info: BookInfo
    economy: BookEconomy


class KeywordOverrideIn(BaseModel):
    term: str
    campaign: Optional[str] = None
    impressions: Optional[float] = None
    clicks: Optional[float] = None
    cpc: Optional[float] = None
    spend: Optional[float] = None
    orders: Optional[float] = None
    sales: Optional[float] = None
    notes: Optional[str] = None
    match_type: Optional[str] = None
    ad_type: Optional[str] = None
    # Niche study fields (per-keyword)
    search_volume: Optional[float] = None
    competitors: Optional[float] = None
    kw_price: Optional[float] = None
    kw_royalties: Optional[float] = None
    demand_checks: Optional[int] = None         # 0..6
    competition_checks: Optional[int] = None    # 0..3
    keyword_status: Optional[str] = None        # pending|validated|rejected|testing
    auto_spend: Optional[bool] = None           # if true, spend = clicks*cpc


class CampaignCreateIn(BaseModel):
    campaign: str
    ad_type: str = "SP"
    match_type: Optional[str] = None
    keywords: list[KeywordOverrideIn] = []


# ------------------- Helpers -------------------
def _merge_rows_with_overrides(rows: list[dict], overrides: dict[str, dict], key: str) -> list[dict]:
    """Aggregate rows by `key`, then apply any per-term overrides."""
    agg = aggregate_by(rows, key)
    agg_map = {r[key]: r for r in agg}
    # Include manual-only terms
    for term, ov in overrides.items():
        if term not in agg_map:
            base = {key: term, "impressions": 0.0, "clicks": 0.0, "spend": 0.0,
                    "sales": 0.0, "orders": 0.0, "ctr": 0.0, "cpc": 0.0,
                    "acos": 0.0, "roas": 0.0, "cvr": 0.0}
            agg_map[term] = base
    # Apply overrides (replace only provided fields)
    out = []
    for term, row in agg_map.items():
        ov = overrides.get(term, {}) or {}
        merged = dict(row)
        for f in ("impressions", "clicks", "cpc", "spend", "sales", "orders",
                  "campaign", "notes", "match_type", "ad_type"):
            if ov.get(f) is not None:
                merged[f] = ov[f]
        # Auto-calc spend from clicks × cpc if auto_spend flag is on
        if ov.get("auto_spend") and ov.get("clicks") is not None and ov.get("cpc") is not None:
            merged["spend"] = round(float(ov["clicks"]) * float(ov["cpc"]), 2)
        merged["is_manual"] = bool(ov)
        merged["notes"] = ov.get("notes", "") if ov else ""
        # Expose niche data
        for f in ("search_volume", "competitors", "kw_price", "kw_royalties",
                  "demand_checks", "competition_checks", "keyword_status"):
            if ov.get(f) is not None:
                merged[f] = ov[f]
        # Recompute derived metrics
        imp = merged.get("impressions", 0) or 0
        clk = merged.get("clicks", 0) or 0
        spend = merged.get("spend", 0) or 0
        sales = merged.get("sales", 0) or 0
        orders = merged.get("orders", 0) or 0
        merged["ctr"] = round((clk / imp * 100) if imp else 0, 2)
        if ov.get("cpc") is None:
            merged["cpc"] = round((spend / clk) if clk else 0, 2)
        merged["acos"] = round((spend / sales * 100) if sales else 0, 2)
        merged["roas"] = round((sales / spend) if spend else 0, 2)
        merged["cvr"] = round((orders / clk * 100) if clk else 0, 2)
        out.append(merged)
    out.sort(key=lambda x: x.get("spend", 0), reverse=True)
    return out


# ------------------- Routes -------------------
@api.get("/")
async def root():
    return {"status": "ok", "service": "publify-ads"}


@api.post("/imports/upload")
async def upload_csv(
    file: UploadFile = File(...),
    marketplace: str = Form("us"),
    dataset_name: Optional[str] = Form(None),
):
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Archivo > 25MB. Divide el reporte.")
    try:
        parsed = parse_ads_file(content, file.filename or "report.csv")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el archivo: {e}")

    if parsed["row_count"] == 0:
        raise HTTPException(status_code=400, detail="El archivo no contiene filas.")

    dataset_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": dataset_id,
        "name": dataset_name or file.filename or "Importación",
        "marketplace": marketplace,
        "report_type": parsed["report_type"],
        "ad_type": parsed["ad_type"],
        "row_count": parsed["row_count"],
        "created_at": now,
        "kpis": parsed["kpis"],
        "header_mapping": parsed["header_mapping"],
        "headers_detected": parsed["headers_detected"],
        "rows": parsed["rows"],
        "book_info": {"title": "", "subtitle": "", "description": "", "categories": []},
        "book_economy": {"precio_libro": 0.0, "regalias_por_venta": 0.0},
        "overrides": {},
        "snapshots": {},
    }
    await db.datasets.insert_one(doc)
    return {k: v for k, v in doc.items() if k not in ("rows", "_id")}


@api.get("/datasets")
async def list_datasets(marketplace: Optional[str] = None):
    query: dict[str, Any] = {}
    if marketplace:
        query["marketplace"] = marketplace
    items = await db.datasets.find(
        query,
        {"_id": 0, "rows": 0, "headers_detected": 0, "header_mapping": 0,
         "overrides": 0, "snapshots": 0},
    ).sort("created_at", -1).to_list(500)
    return items


@api.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str):
    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return doc


@api.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str):
    r = await db.datasets.delete_one({"id": dataset_id})
    return {"deleted": r.deleted_count}


@api.put("/datasets/{dataset_id}/book")
async def update_book(dataset_id: str, payload: BookSettingsIn):
    r = await db.datasets.update_one(
        {"id": dataset_id},
        {"$set": {
            "book_info": payload.info.model_dump(),
            "book_economy": payload.economy.model_dump(),
        }},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return {"ok": True}


# ---- Keyword overrides (inline edit + manual add) ----
@api.put("/datasets/{dataset_id}/keyword")
async def upsert_keyword(dataset_id: str, payload: KeywordOverrideIn):
    if not payload.term.strip():
        raise HTTPException(status_code=400, detail="El término no puede estar vacío")
    term = payload.term.strip()
    data = payload.model_dump(exclude_none=True)
    data.pop("term", None)
    r = await db.datasets.update_one(
        {"id": dataset_id},
        {"$set": {f"overrides.{term}": data}},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    # Recalc KPIs on top-level
    await _recalc_dataset_kpis(dataset_id)
    return {"ok": True, "term": term}


@api.delete("/datasets/{dataset_id}/keyword/{term}")
async def delete_keyword(dataset_id: str, term: str):
    r = await db.datasets.update_one(
        {"id": dataset_id},
        {"$unset": {f"overrides.{term}": ""}},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    await _recalc_dataset_kpis(dataset_id)
    return {"ok": True, "term": term}


@api.post("/datasets/{dataset_id}/campaign")
async def create_campaign(dataset_id: str, payload: CampaignCreateIn):
    if not payload.campaign.strip():
        raise HTTPException(status_code=400, detail="El nombre de campaña es obligatorio")
    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0, "overrides": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    overrides = doc.get("overrides", {}) or {}
    added = []
    for kw in payload.keywords:
        term = kw.term.strip()
        if not term:
            continue
        data = kw.model_dump(exclude_none=True)
        data.pop("term", None)
        data["campaign"] = payload.campaign.strip()
        if payload.ad_type:
            data["ad_type"] = payload.ad_type
        if payload.match_type and not data.get("match_type"):
            data["match_type"] = payload.match_type
        overrides[term] = data
        added.append(term)
    await db.datasets.update_one(
        {"id": dataset_id}, {"$set": {"overrides": overrides}}
    )
    await _recalc_dataset_kpis(dataset_id)
    return {"ok": True, "campaign": payload.campaign, "added": added}


async def _recalc_dataset_kpis(dataset_id: str):
    """Recompute top-level KPIs from rows + overrides so dashboard stays in sync."""
    doc = await db.datasets.find_one(
        {"id": dataset_id}, {"_id": 0, "rows": 1, "overrides": 1}
    )
    if not doc:
        return
    rows = doc.get("rows", []) or []
    overrides = doc.get("overrides", {}) or {}
    # Aggregate everything as keyword-level using customer_search_term or targeting
    key = "customer_search_term" if any(r.get("customer_search_term") for r in rows) else "targeting"
    merged = _merge_rows_with_overrides(rows, overrides, key)
    k = compute_kpis(merged)
    await db.datasets.update_one({"id": dataset_id}, {"$set": {"kpis": k}})


# ---- Snapshots ----
@api.post("/datasets/{dataset_id}/snapshot-all")
async def snapshot_all(dataset_id: str):
    """Append a time-stamped snapshot for every keyword term."""
    doc = await db.datasets.find_one(
        {"id": dataset_id},
        {"_id": 0, "rows": 1, "overrides": 1, "snapshots": 1, "book_economy": 1}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    rows = doc.get("rows", []) or []
    overrides = doc.get("overrides", {}) or {}
    eco = doc.get("book_economy", {}) or {}
    price = eco.get("precio_libro") or None
    key = "customer_search_term" if any(r.get("customer_search_term") for r in rows) else "targeting"
    merged = _merge_rows_with_overrides(rows, overrides, key)
    ts = datetime.now(timezone.utc).isoformat()
    snaps = doc.get("snapshots", {}) or {}
    for r in merged:
        term = r.get(key) or "—"
        entry = {
            "ts": ts,
            "clicks": r["clicks"],
            "impressions": r["impressions"],
            "spend": r["spend"],
            "sales": r["sales"],
            "orders": r["orders"],
            "cpc": r["cpc"],
            "acos_actual": acos_actual_pct(r["spend"], r["sales"]),
            "acos_siguiente": acos_siguiente_click_pct(r["spend"], r["cpc"], r["sales"], price),
        }
        bucket = snaps.setdefault(term, [])
        # replace today's entry if it exists
        today = ts[:10]
        bucket = [s for s in bucket if not str(s.get("ts", "")).startswith(today)]
        bucket.append(entry)
        bucket = sorted(bucket, key=lambda s: s.get("ts", ""))
        snaps[term] = bucket[-60:]  # cap at 60 days
    await db.datasets.update_one({"id": dataset_id}, {"$set": {"snapshots": snaps}})
    return {"ok": True, "terms": len(merged), "ts": ts}


@api.get("/datasets/{dataset_id}/snapshots/{term}")
async def get_snapshots(dataset_id: str, term: str):
    doc = await db.datasets.find_one(
        {"id": dataset_id}, {"_id": 0, "snapshots": 1}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return {"term": term, "snapshots": (doc.get("snapshots") or {}).get(term, [])}


@api.get("/datasets/{dataset_id}/keyword-detail")
async def keyword_detail(dataset_id: str, term: str):
    doc = await db.datasets.find_one(
        {"id": dataset_id},
        {"_id": 0, "rows": 1, "overrides": 1, "snapshots": 1, "book_economy": 1}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    rows = doc.get("rows", []) or []
    overrides = doc.get("overrides", {}) or {}
    eco = doc.get("book_economy", {}) or {}
    price = eco.get("precio_libro") or None
    roy = eco.get("regalias_por_venta")
    acos_eq = acos_equilibrio_pct(price, roy)
    key = "customer_search_term" if any(r.get("customer_search_term") for r in rows) else "targeting"
    merged = _merge_rows_with_overrides(rows, overrides, key)
    target = next((r for r in merged if (r.get(key) or "") == term), None)
    if not target:
        target = {
            key: term, "impressions": 0, "clicks": 0, "cpc": 0, "spend": 0,
            "sales": 0, "orders": 0, "ctr": 0, "roas": 0, "cvr": 0, "acos": 0,
            "is_manual": term in overrides, "notes": overrides.get(term, {}).get("notes", ""),
            "campaign": overrides.get(term, {}).get("campaign"),
        }
    acos_act = acos_actual_pct(target["spend"], target["sales"])
    acos_next = acos_siguiente_click_pct(target["spend"], target["cpc"], target["sales"], price)
    acos_next_sin = acos_siguiente_sin_venta_pct(target["spend"], target["cpc"], target["sales"])
    b_now = beneficio_ahora(target["sales"], target["spend"])
    b_next = beneficio_siguiente_click(target["orders"], price, target["spend"], target["cpc"])
    cvr = conversion_pct(target["orders"], target["clicks"])
    badge = determinar_badge(acos_eq, acos_act, acos_next)
    ms = calculate_market_score(
        target.get("search_volume"), target.get("competitors"),
        target.get("kw_price"), target.get("kw_royalties"),
        target.get("demand_checks", 0) or 0,
        target.get("competition_checks", 0) or 0,
    )
    snaps = (doc.get("snapshots") or {}).get(term, [])
    # Count underlying imported rows for this term (for UX)
    underlying = sum(1 for r in rows if (r.get(key) or "") == term)
    override = overrides.get(term)
    return {
        "term": term,
        "key": key,
        "metrics": {
            **{k: target.get(k) for k in ("impressions", "clicks", "cpc", "spend",
                                           "sales", "orders", "ctr", "roas", "cvr")},
            "acos_actual": acos_act,
            "acos_siguiente": acos_next,
            "acos_siguiente_sin_venta": acos_next_sin,
            "beneficio_ahora": b_now,
            "beneficio_siguiente": b_next,
            "cvr": cvr,
            "badge": badge,
            "campaign": target.get("campaign"),
            "match_type": target.get("match_type"),
            "ad_type": target.get("ad_type"),
            "notes": target.get("notes", ""),
            "is_manual": target.get("is_manual", False),
            "underlying_rows": underlying,
            # Niche
            "search_volume": target.get("search_volume") or 0,
            "competitors": target.get("competitors") or 0,
            "kw_price": target.get("kw_price") or 0,
            "kw_royalties": target.get("kw_royalties") or 0,
            "demand_checks": target.get("demand_checks", 0) or 0,
            "competition_checks": target.get("competition_checks", 0) or 0,
            "keyword_status": target.get("keyword_status") or "pending",
            "market_score": ms["total"],
            "market_score_breakdown": ms["breakdown"],
            "score_label": ms["label"],
        },
        "snapshots": snaps,
        "acos_equilibrio": acos_eq,
        "override": override,
    }


@api.get("/datasets/{dataset_id}/campaigns")
async def get_campaigns(dataset_id: str):
    doc = await db.datasets.find_one(
        {"id": dataset_id}, {"_id": 0, "rows": 1, "book_economy": 1, "overrides": 1}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    rows = doc.get("rows", []) or []
    overrides = doc.get("overrides", {}) or {}
    # For campaigns, we aggregate by campaign, considering overrides as virtual rows
    virtual_rows = list(rows)
    for term, ov in overrides.items():
        if ov.get("campaign"):
            virtual_rows.append({
                "campaign": ov["campaign"],
                "impressions": ov.get("impressions", 0) or 0,
                "clicks": ov.get("clicks", 0) or 0,
                "spend": ov.get("spend", 0) or 0,
                "sales": ov.get("sales", 0) or 0,
                "orders": ov.get("orders", 0) or 0,
            })
    agg = aggregate_by(virtual_rows, "campaign")
    eco = doc.get("book_economy", {}) or {}
    price = eco.get("precio_libro") or None
    roy = eco.get("regalias_por_venta")
    acos_eq = acos_equilibrio_pct(price, roy)
    for r in agg:
        r["acos_siguiente"] = acos_siguiente_click_pct(r["spend"], r["cpc"], r["sales"], price)
        r["badge"] = determinar_badge(acos_eq, r.get("acos") or None, r.get("acos_siguiente"))
    return agg


@api.get("/datasets/{dataset_id}/search-terms")
async def get_search_terms(dataset_id: str, min_clicks: int = 0):
    doc = await db.datasets.find_one(
        {"id": dataset_id}, {"_id": 0, "rows": 1, "book_economy": 1, "overrides": 1}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    rows = doc.get("rows", []) or []
    overrides = doc.get("overrides", {}) or {}
    key = "customer_search_term" if any(r.get("customer_search_term") for r in rows) else "targeting"
    agg = _merge_rows_with_overrides(rows, overrides, key)
    eco = doc.get("book_economy", {}) or {}
    price = eco.get("precio_libro") or None
    roy = eco.get("regalias_por_venta")
    acos_eq = acos_equilibrio_pct(price, roy)
    for r in agg:
        r["suggest_negative"] = bool(
            r.get("clicks", 0) >= max(min_clicks, 6) and r.get("orders", 0) == 0
        )
        r["acos_siguiente"] = acos_siguiente_click_pct(r["spend"], r["cpc"], r["sales"], price)
        r["badge"] = determinar_badge(acos_eq, r.get("acos") or None, r.get("acos_siguiente"))
    return {"key": key, "rows": agg, "acos_equilibrio": acos_eq}


@api.get("/datasets/{dataset_id}/keywords-unified")
async def get_keywords_unified(dataset_id: str):
    doc = await db.datasets.find_one(
        {"id": dataset_id},
        {"_id": 0, "rows": 1, "overrides": 1, "book_economy": 1}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    rows = doc.get("rows", []) or []
    overrides = doc.get("overrides", {}) or {}
    key = "customer_search_term" if any(r.get("customer_search_term") for r in rows) else "targeting"
    agg = _merge_rows_with_overrides(rows, overrides, key)
    eco = doc.get("book_economy", {}) or {}
    price = eco.get("precio_libro") or None
    roy = eco.get("regalias_por_venta")
    acos_eq = acos_equilibrio_pct(price, roy)
    fases = guias_fase(acos_eq)
    out_rows = []
    for r in agg:
        spend = r.get("spend") or 0
        sales = r.get("sales") or 0
        orders = r.get("orders") or 0
        clicks = r.get("clicks") or 0
        cpc = r.get("cpc") or 0
        acos_act = acos_actual_pct(spend, sales)
        acos_next = acos_siguiente_click_pct(spend, cpc, sales, price)
        acos_next_sin = acos_siguiente_sin_venta_pct(spend, cpc, sales)
        b_now = beneficio_ahora(sales, spend)
        b_next = beneficio_siguiente_click(orders, price, spend, cpc)
        cvr = conversion_pct(orders, clicks)
        badge = determinar_badge(acos_eq, acos_act, acos_next)
        ms = calculate_market_score(
            r.get("search_volume"), r.get("competitors"),
            r.get("kw_price"), r.get("kw_royalties"),
            r.get("demand_checks", 0) or 0,
            r.get("competition_checks", 0) or 0,
        )
        out_rows.append({
            "term": r.get(key) or "—",
            "campaign": r.get("campaign"),
            "is_manual": r.get("is_manual", False),
            "notes": r.get("notes", ""),
            "impressions": r.get("impressions", 0),
            "clicks": clicks,
            "ctr": r.get("ctr", 0),
            "cpc": cpc,
            "spend": spend,
            "sales": sales,
            "orders": orders,
            "acos_actual": acos_act,
            "acos_siguiente": acos_next,
            "acos_siguiente_sin_venta": acos_next_sin,
            "beneficio_ahora": b_now,
            "beneficio_siguiente": b_next,
            "cvr": cvr,
            "badge": badge,
            "match_type": r.get("match_type"),
            "ad_type": r.get("ad_type"),
            # Niche study
            "search_volume": r.get("search_volume"),
            "competitors": r.get("competitors"),
            "kw_price": r.get("kw_price"),
            "kw_royalties": r.get("kw_royalties"),
            "demand_checks": r.get("demand_checks", 0) or 0,
            "competition_checks": r.get("competition_checks", 0) or 0,
            "keyword_status": r.get("keyword_status") or "pending",
            "market_score": ms["total"],
            "score_label": ms["label"],
        })
    # Group summary for dashboard blocks
    summary = {"bajo-pe": 0, "recuperable": 0, "en-perdida": 0, "sin-datos": 0}
    for r in out_rows:
        summary[r["badge"]] = summary.get(r["badge"], 0) + 1
    return {
        "key": key,
        "rows": out_rows,
        "acos_equilibrio": acos_eq,
        "guias_fase": fases,
        "book_economy": eco,
        "summary": summary,
    }


@api.get("/datasets/{dataset_id}/timeseries")
async def get_timeseries(dataset_id: str):
    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0, "rows": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    rows = doc.get("rows", []) or []
    has_date = any(r.get("start_date") for r in rows)
    if has_date:
        buckets: dict[str, dict] = {}
        for r in rows:
            d = (r.get("start_date") or "").strip() or "—"
            b = buckets.setdefault(d, {
                "date": d, "impressions": 0.0, "clicks": 0.0,
                "spend": 0.0, "sales": 0.0, "orders": 0.0,
            })
            b["impressions"] += r.get("impressions", 0) or 0
            b["clicks"] += r.get("clicks", 0) or 0
            b["spend"] += r.get("spend", 0) or 0
            b["sales"] += r.get("sales", 0) or 0
            b["orders"] += r.get("orders", 0) or 0
        series = sorted(buckets.values(), key=lambda x: x["date"])
        for r in series:
            for f in ("impressions", "clicks", "spend", "sales", "orders"):
                r[f] = round(r[f], 2)
        return {"mode": "date", "points": series}
    camps = aggregate_by(rows, "campaign")[:12]
    return {"mode": "campaign", "points": [
        {"date": c["campaign"], "spend": c["spend"], "sales": c["sales"],
         "clicks": c["clicks"], "impressions": c["impressions"], "orders": c["orders"]}
        for c in camps
    ]}


@api.post("/datasets/{dataset_id}/ai-recommendations")
async def ai_recommendations(dataset_id: str):
    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")

    from emergentintegrations.llm.chat import LlmChat, UserMessage
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY no configurado")

    kpis = doc["kpis"]
    rows = doc.get("rows", []) or []
    overrides = doc.get("overrides", {}) or {}
    campaigns = aggregate_by(rows, "campaign")[:10]
    key = "customer_search_term" if any(r.get("customer_search_term") for r in rows) else "targeting"
    terms = _merge_rows_with_overrides(rows, overrides, key)[:15]
    eco = doc.get("book_economy", {})
    acos_eq = acos_equilibrio_pct(eco.get("precio_libro"), eco.get("regalias_por_venta"))

    summary = {
        "report_type": doc["report_type"],
        "ad_type": doc["ad_type"],
        "marketplace": doc["marketplace"],
        "kpis": kpis,
        "book_economy": eco,
        "acos_equilibrio": acos_eq,
        "top_campaigns": campaigns,
        "top_search_terms": terms,
    }

    system_msg = (
        "Eres experto en Amazon Ads para autores KDP y ecommerce. Analiza el resumen "
        "y devuelve 4-8 recomendaciones accionables considerando ACOS de equilibrio, "
        "ACOS actual, ACOS siguiente click, ROAS, CTR, CPC, palabras negativas y escalado. "
        "Responde SOLO JSON válido: "
        '{"recommendations":[{"title":"...","severity":"info|warning|critical","detail":"..."}]}'
    )

    import json, re
    chat = (
        LlmChat(api_key=api_key, session_id=f"ads-{dataset_id}", system_message=system_msg)
        .with_model("anthropic", "claude-sonnet-4-5-20250929")
    )
    msg = UserMessage(text=f"Resumen:\n{json.dumps(summary, default=str)}")
    try:
        response = await chat.send_message(msg)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error en IA: {e}")

    text = response if isinstance(response, str) else str(response)
    match = re.search(r"\{.*\}", text, re.S)
    raw = match.group(0) if match else text
    try:
        data = json.loads(raw)
        recs = data.get("recommendations", [])
    except Exception:
        recs = [{"title": "Respuesta IA", "severity": "info", "detail": text[:1500]}]

    out = {"recommendations": recs, "generated_at": datetime.now(timezone.utc).isoformat()}
    await db.datasets.update_one({"id": dataset_id}, {"$set": {"ai_recommendations": out}})
    return out


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
