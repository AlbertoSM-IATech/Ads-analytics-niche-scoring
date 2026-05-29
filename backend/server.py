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
from market_score_v2 import (
    MARKET_DEFAULTS, get_defaults, merge_criteria, calc_market_score_v2,
    DEFAULT_WEIGHTS, merge_weights, WEIGHT_KEYS,
)
from kdp_economy import resolve_regalia_neta, compute_row_econ
from autopilot import aggregate_autopilot, parse_niche_csv

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
    mult_lanzamiento: float = 1.7
    mult_dominio: float = 1.2
    mult_beneficio: float = 0.5
    # ---- KDP V2 fields (all optional; absence keeps legacy behaviour) ----
    format_type: Optional[str] = None          # "EBOOK" | "PRINT"
    book_format: Optional[str] = None          # "PAPERBACK" | "HARDCOVER"
    interior_type: Optional[str] = None        # "BN" | "COLOR_PREMIUM" | "COLOR_STANDARD"
    book_size: Optional[str] = None            # "SMALL" | "LARGE"
    pages: Optional[int] = None
    iva_type: Optional[float] = None           # 4 | 21 (only applied in ES)
    royalty_rate_ebook: Optional[int] = None   # 70 | 35
    tamano_mb: Optional[float] = None
    cpc_referencia: Optional[float] = None
    margen_objetivo_pct: Optional[float] = None


class BookSettingsIn(BaseModel):
    info: BookInfo
    economy: BookEconomy


class KeywordOverrideIn(BaseModel):
    term: str
    campaign: Optional[str] = None
    campaigns: Optional[list[str]] = None   # multi-campaign assignment
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
    demand_check_flags: Optional[dict] = None   # {check_id: bool}
    competition_check_flags: Optional[dict] = None
    keyword_status: Optional[str] = None        # pending|validated|rejected|testing
    auto_spend: Optional[bool] = None           # if true, spend = clicks*cpc
    # Phase 2B — manual relevance label, for human review only.
    # Allowed: unreviewed | high | medium | low. Default: unreviewed.
    relevance: Optional[str] = None


ALLOWED_RELEVANCE = {"unreviewed", "high", "medium", "low"}


class MarketCriteriaIn(BaseModel):
    idealVolume: Optional[float] = None
    idealCompetitors: Optional[float] = None
    idealPrice: Optional[float] = None
    idealRoyalties: Optional[float] = None


class ScoreWeightsIn(BaseModel):
    volume: Optional[float] = None
    competitors: Optional[float] = None
    price: Optional[float] = None
    royalties: Optional[float] = None
    market_structure: Optional[float] = None
    catalog_signals: Optional[float] = None



class PhaseIn(BaseModel):
    phase: str  # lanzamiento | dominio | beneficio


class CampaignCreateIn(BaseModel):
    campaign: str
    ad_type: str = "SP"
    match_type: Optional[str] = None
    keywords: list[KeywordOverrideIn] = []


class CampaignPlanIn(BaseModel):
    name: str
    phase: str = "lanzamiento"
    target_acos: Optional[float] = None
    daily_budget: Optional[float] = None
    keyword_terms: list[str] = []
    notes: str = ""


class CampaignPlanUpdate(BaseModel):
    name: Optional[str] = None
    phase: Optional[str] = None
    target_acos: Optional[float] = None
    daily_budget: Optional[float] = None
    keyword_terms: Optional[list[str]] = None
    notes: Optional[str] = None


# ------------------- Helpers -------------------
def _merge_rows_with_overrides(rows: list[dict], overrides: dict[str, dict], key: str) -> list[dict]:
    """Aggregate rows by `key`, then apply any per-term overrides.
    Also collects the set of distinct campaign names each term appears in."""
    agg = aggregate_by(rows, key)
    agg_map = {r[key]: r for r in agg}
    # Compute natural campaign memberships from raw rows
    natural_campaigns: dict[str, set[str]] = {}
    for raw in rows:
        t = (raw.get(key) or "").strip()
        c = (raw.get("campaign") or "").strip()
        if t and c:
            natural_campaigns.setdefault(t, set()).add(c)
    # Include manual-only terms
    for term, ov in overrides.items():
        if term not in agg_map:
            base = {key: term, "impressions": 0.0, "clicks": 0.0, "spend": 0.0,
                    "sales": 0.0, "orders": 0.0, "ctr": 0.0, "cpc": 0.0,
                    "acos": 0.0, "roas": 0.0, "cvr": 0.0}
            agg_map[term] = base
    out = []
    for term, row in agg_map.items():
        ov = overrides.get(term, {}) or {}
        merged = dict(row)
        for f in ("impressions", "clicks", "cpc", "spend", "sales", "orders",
                  "campaign", "notes", "match_type", "ad_type"):
            if ov.get(f) is not None:
                merged[f] = ov[f]
        if ov.get("auto_spend") and ov.get("clicks") is not None and ov.get("cpc") is not None:
            merged["spend"] = round(float(ov["clicks"]) * float(ov["cpc"]), 2)
        merged["is_manual"] = bool(ov)
        merged["notes"] = ov.get("notes", "") if ov else ""
        for f in ("search_volume", "competitors", "kw_price", "kw_royalties",
                  "demand_checks", "competition_checks", "keyword_status",
                  "demand_check_flags", "competition_check_flags",
                  "relevance"):
            if ov.get(f) is not None:
                merged[f] = ov[f]
        # Campaigns: union of natural + manual
        manual_camps = list(ov.get("campaigns") or [])
        all_camps = list(natural_campaigns.get(term, set()))
        for c in manual_camps:
            if c and c not in all_camps:
                all_camps.append(c)
        merged["campaigns"] = all_camps
        if not merged.get("campaign") and all_camps:
            merged["campaign"] = all_camps[0]
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
        "book_economy": {
            "precio_libro": 0.0, "regalias_por_venta": 0.0,
            "mult_lanzamiento": 1.7, "mult_dominio": 1.2, "mult_beneficio": 0.5,
        },
        "phase": "dominio",
        "market_criteria": {},
        "score_weights": {},
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
    # Use exclude_none so legacy datasets don't gain a flood of null KDP fields.
    r = await db.datasets.update_one(
        {"id": dataset_id},
        {"$set": {
            "book_info": payload.info.model_dump(),
            "book_economy": payload.economy.model_dump(exclude_none=True),
        }},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return {"ok": True}


@api.get("/datasets/{dataset_id}/economy-diagnosis")
async def economy_diagnosis(dataset_id: str):
    """Return the full KDP economy diagnosis for this dataset's book configuration.

    Phase 1: this endpoint is read-only and DOES NOT modify the dataset document.
    If the dataset has no KDP fields configured, returns mode='legacy' with
    the basic acos_pe / cpc_max derived from precio_libro + regalias_por_venta.
    """
    from kdp_economy import compute_full_diagnosis
    doc = await db.datasets.find_one(
        {"id": dataset_id}, {"_id": 0, "book_economy": 1, "marketplace": 1}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    book_eco = doc.get("book_economy") or {}
    mp = doc.get("marketplace") or "COM"
    return compute_full_diagnosis(book_eco, mp)


@api.get("/datasets/{dataset_id}/recommendations")
async def get_recommendations(dataset_id: str):
    """Phase 3A — read-only parallel recommendations engine.

    Reuses /keywords-unified row enrichment (Phase 2A metrics + Phase 2B relevance).
    Strictly READ-ONLY: zero DB writes; autopilot.py and suggest_negative remain
    untouched.
    """
    from recommendations import build_recommendations, summarize_by_action
    from kdp_economy import MARKETPLACE_CONFIG, normalize_mp
    unified = await get_keywords_unified(dataset_id)
    rows = unified.get("rows") or []
    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0, "marketplace": 1})
    mp = (doc or {}).get("marketplace") or "COM"
    try:
        sym = MARKETPLACE_CONFIG[normalize_mp(mp)]["symbol"]
    except Exception:
        sym = "$"
    recs = build_recommendations(
        rows,
        dataset_id=dataset_id,
        phase=unified.get("phase") or "dominio",
        regalia_source=unified.get("regalia_source") or "none",
        sym=sym,
    )
    return {
        "phase": unified.get("phase") or "dominio",
        "regalia_source": unified.get("regalia_source") or "none",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(recs),
        "by_action": summarize_by_action(recs),
        "recommendations": [r.model_dump() for r in recs],
    }



# ---- Keyword overrides (inline edit + manual add) ----
@api.put("/datasets/{dataset_id}/keyword")
async def upsert_keyword(dataset_id: str, payload: KeywordOverrideIn):
    if not payload.term.strip():
        raise HTTPException(status_code=400, detail="El término no puede estar vacío")
    if payload.relevance is not None and payload.relevance not in ALLOWED_RELEVANCE:
        raise HTTPException(
            status_code=400,
            detail=f"relevance inválido. Permitidos: {', '.join(sorted(ALLOWED_RELEVANCE))}",
        )
    term = payload.term.strip()
    data = payload.model_dump(exclude_none=True)
    data.pop("term", None)
    # Use dotted per-field update so partial edits MERGE instead of replacing
    # the whole `overrides.{term}` sub-document.
    setdoc = {f"overrides.{term}.{k}": v for k, v in data.items()}
    if not setdoc:
        # no-op but keep the key present so downstream treats term as "manual"
        setdoc = {f"overrides.{term}": {}}
    r = await db.datasets.update_one({"id": dataset_id}, {"$set": setdoc})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
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
        {"_id": 0, "rows": 1, "overrides": 1, "snapshots": 1, "book_economy": 1,
         "marketplace": 1, "market_criteria": 1, "phase": 1}
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
    # Simulation: +1 click with sale (adds 1 click, 1 order)
    simulation = None
    if price and price > 0:
        c_next = (target.get("clicks") or 0) + 1
        o_next = (target.get("orders") or 0) + 1
        s_next_spend = (target.get("spend") or 0) + (target.get("cpc") or 0)
        s_next_sales = (target.get("sales") or 0) + price
        simulation = {
            "clicks_next": c_next,
            "orders_next": o_next,
            "spend_next": round(s_next_spend, 2),
            "sales_next": round(s_next_sales, 2),
            "acos_next_with_sale": round(
                (s_next_spend / s_next_sales * 100) if s_next_sales else 0, 2
            ),
            "acos_next_no_sale": (
                round(((target.get("spend") or 0) + (target.get("cpc") or 0)) /
                      (target.get("sales") or 1) * 100, 2)
                if (target.get("sales") or 0) > 0 else None
            ),
        }
    ms = calc_market_score_v2(
        target.get("search_volume"), target.get("competitors"),
        target.get("kw_price") or (eco.get("precio_libro") or None),
        target.get("kw_royalties") or (eco.get("regalias_por_venta") or None),
        market_structure_checks=target.get("demand_checks", 0) or 0,
        catalog_signals_checks=target.get("competition_checks", 0) or 0,
        criteria=merge_criteria(doc.get("marketplace") or "default",
                                 (doc.get("market_criteria") or {}).get(doc.get("marketplace") or "", {})),
        marketplace=doc.get("marketplace") or "default",
    )
    snaps = (doc.get("snapshots") or {}).get(term, [])
    # Count underlying imported rows for this term (for UX)
    underlying = sum(1 for r in rows if (r.get(key) or "") == term)
    override = overrides.get(term)
    # Phase 2 economic context (single keyword)
    mp = doc.get("marketplace") or "default"
    regalia_info = resolve_regalia_neta(eco, mp)
    multipliers = {
        "mult_lanzamiento": float(eco.get("mult_lanzamiento") or 1.7),
        "mult_dominio": float(eco.get("mult_dominio") or 1.2),
        "mult_beneficio": float(eco.get("mult_beneficio") or 0.5),
    }
    econ = compute_row_econ(
        clicks=target.get("clicks") or 0, spend=target.get("spend") or 0,
        orders=target.get("orders") or 0, sales=target.get("sales") or 0,
        regalia_neta=regalia_info["regalia_neta"], pvp=regalia_info["pvp"],
        cpc_referencia=eco.get("cpc_referencia"),
        phase=doc.get("phase") or "dominio", multipliers=multipliers,
    )
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
            "demand_check_flags": target.get("demand_check_flags", {}) or {},
            "competition_check_flags": target.get("competition_check_flags", {}) or {},
            "keyword_status": target.get("keyword_status") or "pending",
            "market_score": ms["total"],
            "market_score_breakdown": ms["breakdown"],
            "score_label": ms["label"],
            # Phase 2B — manual relevance (default "unreviewed").
            "relevance": target.get("relevance") or "unreviewed",
            # Phase 2 economic context
            **econ,
            "regalia_source": regalia_info["source"],
        },
        "snapshots": snaps,
        "acos_equilibrio": acos_eq,
        "override": override,
        "simulation": simulation,
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
        {"_id": 0, "rows": 1, "overrides": 1, "book_economy": 1,
         "marketplace": 1, "market_criteria": 1, "phase": 1, "score_weights": 1}
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
    mp = doc.get("marketplace") or "default"
    criteria_overrides = (doc.get("market_criteria") or {}).get(mp, {})
    effective_criteria = merge_criteria(mp, criteria_overrides)
    effective_weights = merge_weights(doc.get("score_weights") or {})
    NEG_MIN_CLICKS = 6
    # Phase-2 economy resolution (single dataset-level call; rows reuse the same regalía/pvp)
    regalia_info = resolve_regalia_neta(eco, mp)
    phase_global = doc.get("phase") or "dominio"
    multipliers = {
        "mult_lanzamiento": float(eco.get("mult_lanzamiento") or 1.7),
        "mult_dominio": float(eco.get("mult_dominio") or 1.2),
        "mult_beneficio": float(eco.get("mult_beneficio") or 0.5),
    }
    cpc_referencia = eco.get("cpc_referencia")
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
        ms = calc_market_score_v2(
            r.get("search_volume"), r.get("competitors"),
            r.get("kw_price") or (eco.get("precio_libro") or None),
            r.get("kw_royalties") or (eco.get("regalias_por_venta") or None),
            market_structure_checks=r.get("demand_checks", 0) or 0,
            catalog_signals_checks=r.get("competition_checks", 0) or 0,
            criteria=effective_criteria,
            marketplace=doc.get("marketplace") or "default",
            weights=effective_weights,
        )
        suggest_neg = bool(clicks >= NEG_MIN_CLICKS and (orders or 0) == 0)
        # Phase-2 economic context (per-row)
        econ = compute_row_econ(
            clicks=clicks, spend=spend, orders=orders, sales=sales,
            regalia_neta=regalia_info["regalia_neta"], pvp=regalia_info["pvp"],
            cpc_referencia=cpc_referencia,
            phase=phase_global, multipliers=multipliers,
        )
        out_rows.append({
            "term": r.get(key) or "—",
            "campaign": r.get("campaign"),
            "campaigns": r.get("campaigns") or [],
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
            # Preserve targeting alongside customer_search_term — never overwrite either.
            "customer_search_term": r.get("customer_search_term"),
            "targeting": r.get("targeting"),
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
            "score_breakdown": ms["breakdown"],
            "suggest_negative": suggest_neg,
            # Phase 2B — manual relevance (default "unreviewed").
            "relevance": r.get("relevance") or "unreviewed",
            # Phase-2 economy fields
            **econ,
            "regalia_source": regalia_info["source"],
        })
    # Group summary for dashboard blocks
    # Phase 4D — engine-derived suggest_negative (Opción B con fallback legacy).
    # When economy is resolved (regalia_source != "none"), the deterministic
    # engine becomes the single source of truth for negatives: only
    # NEGATIVE_EXACT_CANDIDATE and NEGATIVE_PHRASE_CANDIDATE flip the flag on.
    # Otherwise (no economy) the legacy heuristic (clicks≥6, orders=0) stays
    # active per-row as the fallback.
    if regalia_info["source"] != "none":
        from recommendations import build_recommendations
        _NEG_ACTIONS = {"NEGATIVE_EXACT_CANDIDATE", "NEGATIVE_PHRASE_CANDIDATE"}
        # build_recommendations needs `regalia_source` per row; out_rows already
        # carries it (set above via `regalia_info["source"]`).
        _engine = build_recommendations(
            out_rows, dataset_id=dataset_id, phase=phase_global,
            regalia_source=regalia_info["source"],
        )
        _engine_by_term = {r.term: r.action_type for r in _engine if r.term}
        for r in out_rows:
            at = _engine_by_term.get(r["term"])
            # term not in map → campaign-level rec only or no rec → False.
            r["suggest_negative"] = bool(at in _NEG_ACTIONS)

    summary = {"bajo-pe": 0, "recuperable": 0, "en-perdida": 0, "sin-datos": 0, "negativas": 0}
    for r in out_rows:
        summary[r["badge"]] = summary.get(r["badge"], 0) + 1
        if r.get("suggest_negative"):
            summary["negativas"] = summary.get("negativas", 0) + 1
    return {
        "key": key,
        "rows": out_rows,
        "acos_equilibrio": acos_eq,
        "guias_fase": fases,
        "book_economy": eco,
        "summary": summary,
        "weights": effective_weights,
        "regalia_source": regalia_info["source"],
        "regalia_neta_dataset": regalia_info["regalia_neta"],
        "phase": phase_global,
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
    mp = doc.get("marketplace") or "default"
    criteria = merge_criteria(mp, (doc.get("market_criteria") or {}).get(mp, {}))
    phase = doc.get("phase") or "dominio"

    summary = {
        "report_type": doc["report_type"],
        "ad_type": doc["ad_type"],
        "marketplace": doc["marketplace"],
        "phase": phase,
        "market_criteria": criteria,
        "kpis": kpis,
        "book_economy": eco,
        "acos_equilibrio": acos_eq,
        "top_campaigns": campaigns,
        "top_search_terms": terms,
    }

    system_msg = (
        "Eres experto en Amazon Ads para autores KDP. Analiza el resumen "
        "considerando SIEMPRE la Fase del libro (lanzamiento: ACoS objetivo 1.7×PE; "
        "dominio: 1.2×PE; beneficio: 0.5×PE) y los Criterios del Mercado activo "
        "(idealVolume, idealCompetitors, idealPrice, idealRoyalties). "
        "Devuelve 4-8 recomendaciones accionables; aplica criterios más estrictos en fase Beneficio. "
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


# ---- Campaign Plans ----
@api.get("/datasets/{dataset_id}/plans")
async def list_plans(dataset_id: str):
    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0, "plans": 1})
    if doc is None:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return doc.get("plans", {}) or {}


@api.post("/datasets/{dataset_id}/plans")
async def create_plan(dataset_id: str, payload: CampaignPlanIn):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="El nombre del plan es obligatorio")
    plan_id = str(uuid.uuid4())
    plan = payload.model_dump()
    plan["id"] = plan_id
    plan["created_at"] = datetime.now(timezone.utc).isoformat()
    r = await db.datasets.update_one(
        {"id": dataset_id}, {"$set": {f"plans.{plan_id}": plan}}
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return plan


@api.put("/datasets/{dataset_id}/plans/{plan_id}")
async def update_plan(dataset_id: str, plan_id: str, payload: CampaignPlanUpdate):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        return {"ok": True}
    setdoc = {f"plans.{plan_id}.{k}": v for k, v in updates.items()}
    r = await db.datasets.update_one({"id": dataset_id}, {"$set": setdoc})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    doc = await db.datasets.find_one(
        {"id": dataset_id}, {"_id": 0, f"plans.{plan_id}": 1}
    )
    return (doc.get("plans") or {}).get(plan_id, {"ok": True})


@api.delete("/datasets/{dataset_id}/plans/{plan_id}")
async def delete_plan(dataset_id: str, plan_id: str):
    r = await db.datasets.update_one(
        {"id": dataset_id}, {"$unset": {f"plans.{plan_id}": ""}}
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return {"ok": True, "deleted": plan_id}


@api.get("/datasets/{dataset_id}/plans/{plan_id}/summary")
async def plan_summary(dataset_id: str, plan_id: str):
    """Return aggregated metrics for all keywords in a plan."""
    doc = await db.datasets.find_one(
        {"id": dataset_id},
        {"_id": 0, "rows": 1, "overrides": 1, "plans": 1, "book_economy": 1}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    plan = (doc.get("plans") or {}).get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    rows = doc.get("rows", []) or []
    overrides = doc.get("overrides", {}) or {}
    key = "customer_search_term" if any(r.get("customer_search_term") for r in rows) else "targeting"
    merged = _merge_rows_with_overrides(rows, overrides, key)
    terms = set(plan.get("keyword_terms") or [])
    scoped = [r for r in merged if (r.get(key) or "") in terms]
    totals = {
        "impressions": sum(r.get("impressions", 0) or 0 for r in scoped),
        "clicks": sum(r.get("clicks", 0) or 0 for r in scoped),
        "spend": sum(r.get("spend", 0) or 0 for r in scoped),
        "sales": sum(r.get("sales", 0) or 0 for r in scoped),
        "orders": sum(r.get("orders", 0) or 0 for r in scoped),
    }
    eco = doc.get("book_economy", {}) or {}
    price = eco.get("precio_libro") or None
    roy = eco.get("regalias_por_venta")
    acos_eq = acos_equilibrio_pct(price, roy)
    totals["acos"] = round((totals["spend"] / totals["sales"] * 100) if totals["sales"] else 0, 2)
    totals["roas"] = round((totals["sales"] / totals["spend"]) if totals["spend"] else 0, 2)
    totals["keyword_count"] = len(terms)
    totals["keywords_with_data"] = len(scoped)
    # Phase target
    guide_map = {"lanzamiento": 1.7, "dominio": 1.2, "beneficio": 0.5}
    totals["phase_target_acos"] = (
        round(acos_eq * guide_map.get(plan.get("phase", "lanzamiento"), 1.0), 2)
        if acos_eq is not None else None
    )
    totals["acos_equilibrio"] = acos_eq
    totals["target_acos"] = plan.get("target_acos")
    return {"plan": plan, "totals": totals, "rows": scoped}


# ---- Export ----
@api.get("/datasets/{dataset_id}/autopilot")
async def get_autopilot(dataset_id: str, phase: str = "dominio"):
    """Return rule-based pause/scale/hold/investigate suggestions for the given phase."""
    if phase not in ("lanzamiento", "dominio", "beneficio"):
        raise HTTPException(status_code=400, detail="Fase inválida")
    doc = await db.datasets.find_one(
        {"id": dataset_id},
        {"_id": 0, "rows": 1, "overrides": 1, "book_economy": 1}
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    rows = doc.get("rows", []) or []
    overrides = doc.get("overrides", {}) or {}
    key = "customer_search_term" if any(r.get("customer_search_term") for r in rows) else "targeting"
    merged = _merge_rows_with_overrides(rows, overrides, key)
    eco = doc.get("book_economy", {}) or {}
    price = eco.get("precio_libro") or None
    roy = eco.get("regalias_por_venta")
    acos_eq = acos_equilibrio_pct(price, roy)
    enriched = []
    for r in merged:
        enriched.append({
            **r,
            "term": r.get(key) or "",
            "acos_actual": acos_actual_pct(r.get("spend"), r.get("sales")),
            "acos_siguiente": acos_siguiente_click_pct(
                r.get("spend"), r.get("cpc"), r.get("sales"), price
            ),
            "badge": determinar_badge(
                acos_eq,
                acos_actual_pct(r.get("spend"), r.get("sales")),
                acos_siguiente_click_pct(r.get("spend"), r.get("cpc"), r.get("sales"), price),
            ),
        })
    result = aggregate_autopilot(enriched, acos_eq, phase=phase)
    return {
        "acos_equilibrio": acos_eq,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **result,
    }


@api.get("/datasets/{dataset_id}/export/autopilot")
async def export_autopilot(dataset_id: str, phase: str = "dominio"):
    """CSV bulk sheet: pause keywords + scale bid +/- %."""
    data = await get_autopilot(dataset_id, phase=phase)
    from fastapi.responses import Response
    import csv
    from io import StringIO
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow([
        "Product", "Entity", "Operation", "Campaign Name", "Ad Group Name",
        "Keyword Text", "Match Type", "Bid Action", "Bid Delta %", "Rationale",
    ])
    actions = data["actions"]
    for r in actions.get("pause", []):
        w.writerow([
            "Sponsored Products", "Keyword", "Update",
            r.get("campaign") or "", "",
            r["term"], "", "Pause", "", r["rationale"],
        ])
    for r in actions.get("scale", []):
        w.writerow([
            "Sponsored Products", "Keyword", "Update",
            r.get("campaign") or "", "",
            r["term"], "", "Increase bid", r.get("bid_delta_pct"),
            r["rationale"],
        ])
    return Response(
        content=buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=autopilot_{dataset_id[:8]}.csv"},
    )


@api.post("/datasets/{dataset_id}/import-niche")
async def import_niche_csv(dataset_id: str, file: UploadFile = File(...)):
    """Upload Helium10 / Publisher Rocket CSV. Match by term, update niche data in overrides."""
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande")
    import pandas as pd
    import io
    try:
        if (file.filename or "").lower().endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(content))
        else:
            df = None
            for enc in ("utf-8-sig", "utf-8", "latin-1"):
                for sep in (",", ";", "\t"):
                    try:
                        df = pd.read_csv(io.BytesIO(content), sep=sep, encoding=enc, engine="python", dtype=str)
                        if df.shape[1] >= 2:
                            break
                    except Exception:
                        continue
                if df is not None and df.shape[1] >= 2:
                    break
            if df is None:
                raise ValueError("No se pudo leer el CSV")
        mapping = parse_niche_csv(df)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error leyendo archivo: {e}")
    if not mapping:
        raise HTTPException(status_code=400, detail="No se encontraron términos con volumen/competidores")

    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0, "rows": 1, "overrides": 1})
    if doc is None:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    rows = doc.get("rows", []) or []
    overrides = doc.get("overrides", {}) or {}
    key = "customer_search_term" if any(r.get("customer_search_term") for r in rows) else "targeting"
    existing_terms = set()
    for r in rows:
        t = (r.get(key) or "").strip()
        if t:
            existing_terms.add(t)
    existing_terms.update(overrides.keys())

    matched = 0
    created = 0
    for term, data in mapping.items():
        # find original-case term if present
        canonical = next((t for t in existing_terms if t.lower() == term), None)
        if canonical is None:
            canonical = term
            created += 1
        else:
            matched += 1
        ov = overrides.get(canonical, {}) or {}
        if "search_volume" in data:
            ov["search_volume"] = data["search_volume"]
        if "competitors" in data:
            ov["competitors"] = data["competitors"]
        overrides[canonical] = ov
    await db.datasets.update_one(
        {"id": dataset_id}, {"$set": {"overrides": overrides}}
    )
    return {
        "ok": True,
        "rows_in_file": len(mapping),
        "matched_existing": matched,
        "created_new": created,
    }


@api.get("/datasets/{dataset_id}/compare/{other_id}")
async def compare_datasets(dataset_id: str, other_id: str):
    """Compare KPIs + top term movers between two datasets (same marketplace recommended)."""
    a = await db.datasets.find_one({"id": dataset_id}, {"_id": 0})
    b = await db.datasets.find_one({"id": other_id}, {"_id": 0})
    if a is None or b is None:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")

    def _terms(d):
        rows = d.get("rows", []) or []
        overrides = d.get("overrides", {}) or {}
        key = "customer_search_term" if any(r.get("customer_search_term") for r in rows) else "targeting"
        merged = _merge_rows_with_overrides(rows, overrides, key)
        out = {(r.get(key) or ""): r for r in merged}
        return out, key

    ta, key_a = _terms(a)
    tb, key_b = _terms(b)
    all_terms = set(ta.keys()) | set(tb.keys())
    movers = []
    for term in all_terms:
        ra = ta.get(term, {})
        rb = tb.get(term, {})
        delta_spend = (rb.get("spend", 0) or 0) - (ra.get("spend", 0) or 0)
        delta_sales = (rb.get("sales", 0) or 0) - (ra.get("sales", 0) or 0)
        delta_acos = (rb.get("acos", 0) or 0) - (ra.get("acos", 0) or 0)
        movers.append({
            "term": term or "—",
            "a_spend": ra.get("spend", 0) or 0,
            "b_spend": rb.get("spend", 0) or 0,
            "a_sales": ra.get("sales", 0) or 0,
            "b_sales": rb.get("sales", 0) or 0,
            "a_acos": ra.get("acos", 0) or 0,
            "b_acos": rb.get("acos", 0) or 0,
            "delta_spend": round(delta_spend, 2),
            "delta_sales": round(delta_sales, 2),
            "delta_acos": round(delta_acos, 2),
        })
    movers.sort(key=lambda x: abs(x["delta_sales"]) + abs(x["delta_spend"]), reverse=True)

    def k(d): return d.get("kpis", {})
    return {
        "a": {"id": a["id"], "name": a["name"], "created_at": a.get("created_at"), "marketplace": a["marketplace"], "kpis": k(a)},
        "b": {"id": b["id"], "name": b["name"], "created_at": b.get("created_at"), "marketplace": b["marketplace"], "kpis": k(b)},
        "kpi_delta": {
            k2: round((k(b).get(k2, 0) or 0) - (k(a).get(k2, 0) or 0), 2)
            for k2 in ("impressions", "clicks", "spend", "sales", "orders", "acos", "roas", "ctr", "cpc")
        },
        "movers": movers[:30],
    }


@api.get("/datasets/{dataset_id}/export/negatives")
async def export_negatives(dataset_id: str, min_clicks: int = 6):
    """Return Amazon Bulk Sheet formatted CSV of negative keyword candidates.
    Candidates: terms with >= min_clicks and 0 orders."""
    doc = await db.datasets.find_one(
        {"id": dataset_id}, {"_id": 0, "rows": 1, "overrides": 1}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    from fastapi.responses import Response
    import csv
    from io import StringIO
    rows = doc.get("rows", []) or []
    overrides = doc.get("overrides", {}) or {}
    key = "customer_search_term" if any(r.get("customer_search_term") for r in rows) else "targeting"
    merged = _merge_rows_with_overrides(rows, overrides, key)
    buf = StringIO()
    writer = csv.writer(buf)
    # Amazon SP Bulk Sheet header (simplified for negative keywords)
    writer.writerow([
        "Product", "Entity", "Operation", "Campaign Id", "Ad Group Id",
        "Campaign Name", "Ad Group Name", "Match Type", "Keyword Text",
    ])
    for r in merged:
        term = r.get(key) or ""
        clicks = r.get("clicks", 0) or 0
        orders = r.get("orders", 0) or 0
        if clicks >= min_clicks and orders == 0 and term:
            writer.writerow([
                "Sponsored Products", "Negative Keyword", "Create",
                "", "",
                r.get("campaign") or "", "",
                "negativeExact", term,
            ])
    content = buf.getvalue()
    return Response(
        content=content, media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=negatives_{dataset_id[:8]}.csv"},
    )


# ---- Book phase / Market criteria / Backup ----
@api.put("/datasets/{dataset_id}/phase")
async def set_phase(dataset_id: str, payload: PhaseIn):
    if payload.phase not in ("lanzamiento", "dominio", "beneficio"):
        raise HTTPException(status_code=400, detail="Fase inválida")
    r = await db.datasets.update_one(
        {"id": dataset_id}, {"$set": {"phase": payload.phase}}
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return {"ok": True, "phase": payload.phase}


@api.get("/datasets/{dataset_id}/market-criteria/{marketplace}")
async def get_market_criteria(dataset_id: str, marketplace: str):
    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0, "market_criteria": 1})
    if doc is None:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    mc = (doc.get("market_criteria") or {}).get(marketplace, {}) or {}
    return {
        "marketplace": marketplace,
        "defaults": get_defaults(marketplace),
        "overrides": mc,
        "effective": merge_criteria(marketplace, mc),
    }


@api.put("/datasets/{dataset_id}/market-criteria/{marketplace}")
async def put_market_criteria(dataset_id: str, marketplace: str, payload: MarketCriteriaIn):
    data = payload.model_dump(exclude_none=True)
    setdoc = {f"market_criteria.{marketplace}.{k}": v for k, v in data.items()}
    if not setdoc:
        setdoc = {f"market_criteria.{marketplace}": {}}
    r = await db.datasets.update_one({"id": dataset_id}, {"$set": setdoc})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return {"ok": True, "marketplace": marketplace, "effective": merge_criteria(marketplace, data)}


@api.delete("/datasets/{dataset_id}/market-criteria/{marketplace}")
async def reset_market_criteria(dataset_id: str, marketplace: str):
    r = await db.datasets.update_one(
        {"id": dataset_id}, {"$unset": {f"market_criteria.{marketplace}": ""}}
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return {"ok": True, "marketplace": marketplace, "effective": get_defaults(marketplace)}


@api.get("/datasets/{dataset_id}/score-weights")
async def get_score_weights(dataset_id: str):
    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0, "score_weights": 1})
    if doc is None:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    overrides = doc.get("score_weights") or {}
    return {
        "defaults": DEFAULT_WEIGHTS,
        "overrides": overrides,
        "effective": merge_weights(overrides),
    }


@api.put("/datasets/{dataset_id}/score-weights")
async def put_score_weights(dataset_id: str, payload: ScoreWeightsIn):
    data = payload.model_dump(exclude_none=True)
    # Validate
    for k, v in list(data.items()):
        if k not in WEIGHT_KEYS:
            data.pop(k, None)
            continue
        try:
            data[k] = max(0.0, float(v))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"Peso inválido: {k}")
    setdoc = {f"score_weights.{k}": v for k, v in data.items()}
    if not setdoc:
        setdoc = {"score_weights": {}}
    r = await db.datasets.update_one({"id": dataset_id}, {"$set": setdoc})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return {"ok": True, "effective": merge_weights(data)}


@api.delete("/datasets/{dataset_id}/score-weights")
async def reset_score_weights(dataset_id: str):
    r = await db.datasets.update_one(
        {"id": dataset_id}, {"$set": {"score_weights": {}}}
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return {"ok": True, "effective": dict(DEFAULT_WEIGHTS)}


@api.get("/datasets/{dataset_id}/campaigns-list")
async def campaigns_list(dataset_id: str):
    """Return list of unique campaign names (natural + from overrides)."""
    doc = await db.datasets.find_one(
        {"id": dataset_id}, {"_id": 0, "rows": 1, "overrides": 1}
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    names: set[str] = set()
    for r in doc.get("rows", []) or []:
        c = (r.get("campaign") or "").strip()
        if c:
            names.add(c)
    for ov in (doc.get("overrides") or {}).values():
        if ov.get("campaign"):
            names.add(ov["campaign"])
        for c in ov.get("campaigns") or []:
            if c:
                names.add(c)
    return sorted(names)


@api.get("/datasets/{dataset_id}/backup")
async def backup_dataset(dataset_id: str):
    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0})
    if doc is None:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    from fastapi.responses import Response
    import json as _json
    content = _json.dumps({"version": "publify-backup-1", "dataset": doc}, default=str, ensure_ascii=False, indent=2)
    name = (doc.get("name") or "dataset").replace(" ", "_")
    return Response(
        content=content, media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=publify_backup_{name}_{dataset_id[:8]}.json"},
    )


@api.post("/datasets/{dataset_id}/restore")
async def restore_dataset(dataset_id: str, file: UploadFile = File(...)):
    import json as _json
    content = await file.read()
    try:
        payload = _json.loads(content.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"JSON inválido: {e}")
    src = payload.get("dataset") if isinstance(payload, dict) else None
    if not src or not isinstance(src, dict):
        raise HTTPException(status_code=400, detail="Formato de backup no reconocido")
    # Overwrite everything except the id of the current dataset
    src["id"] = dataset_id
    src.pop("_id", None)
    r = await db.datasets.replace_one({"id": dataset_id}, src, upsert=False)
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return {"ok": True, "restored": dataset_id}


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
