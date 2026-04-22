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

from amazon_ads import parse_ads_file, aggregate_by
from acos_calc import (
    acos_equilibrio_pct, acos_actual_pct, acos_siguiente_click_pct,
    beneficio_ahora, beneficio_siguiente_click, conversion_pct,
    guias_fase, determinar_badge,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Publify Amazon Ads Analytics")
api = APIRouter(prefix="/api")


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
    }
    await db.datasets.insert_one(doc)
    out = {k: v for k, v in doc.items() if k not in ("rows", "_id")}
    return out


@api.get("/datasets")
async def list_datasets(marketplace: Optional[str] = None):
    query: dict[str, Any] = {}
    if marketplace:
        query["marketplace"] = marketplace
    items = await db.datasets.find(
        query,
        {"_id": 0, "rows": 0, "headers_detected": 0, "header_mapping": 0},
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


@api.get("/datasets/{dataset_id}/campaigns")
async def get_campaigns(dataset_id: str):
    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0, "rows": 1, "book_economy": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    agg = aggregate_by(doc["rows"], "campaign")
    eco = doc.get("book_economy", {})
    price = eco.get("precio_libro") or None
    roy = eco.get("regalias_por_venta")
    acos_eq = acos_equilibrio_pct(price, roy)
    for r in agg:
        r["acos_siguiente"] = acos_siguiente_click_pct(r["spend"], r["cpc"], r["sales"], price)
        r["badge"] = determinar_badge(acos_eq, r["acos"] if r["acos"] else None, r["acos_siguiente"])
    return agg


@api.get("/datasets/{dataset_id}/search-terms")
async def get_search_terms(dataset_id: str, min_clicks: int = 0):
    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0, "rows": 1, "book_economy": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    rows = doc["rows"]
    key = "customer_search_term" if any(r.get("customer_search_term") for r in rows) else "targeting"
    agg = aggregate_by(rows, key)
    eco = doc.get("book_economy", {})
    price = eco.get("precio_libro") or None
    roy = eco.get("regalias_por_venta")
    acos_eq = acos_equilibrio_pct(price, roy)
    for r in agg:
        r["suggest_negative"] = bool(
            r.get("clicks", 0) >= max(min_clicks, 6) and r.get("orders", 0) == 0
        )
        r["acos_siguiente"] = acos_siguiente_click_pct(r["spend"], r["cpc"], r["sales"], price)
        r["badge"] = determinar_badge(acos_eq, r["acos"] if r["acos"] else None, r["acos_siguiente"])
    return {"key": key, "rows": agg, "acos_equilibrio": acos_eq}


@api.get("/datasets/{dataset_id}/keywords-unified")
async def get_keywords_unified(dataset_id: str):
    """Unified keyword view: aggregates per term/targeting and applies
    BookEconomy calculations (acos_equilibrio, acos_siguiente, beneficio, badge)."""
    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0, "rows": 1, "book_economy": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    rows = doc["rows"]
    key = "customer_search_term" if any(r.get("customer_search_term") for r in rows) else "targeting"
    agg = aggregate_by(rows, key)

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
        b_ahora = beneficio_ahora(sales, spend)
        b_next = beneficio_siguiente_click(orders, price, spend, cpc)
        cvr = conversion_pct(orders, clicks)
        badge = determinar_badge(acos_eq, acos_act, acos_next)

        out_rows.append({
            "term": r.get(key) or "—",
            "campaign": None,
            "impressions": r.get("impressions", 0),
            "clicks": clicks,
            "ctr": r.get("ctr", 0),
            "cpc": cpc,
            "spend": spend,
            "sales": sales,
            "orders": orders,
            "acos_actual": acos_act,
            "acos_siguiente": acos_next,
            "beneficio_ahora": b_ahora,
            "beneficio_siguiente": b_next,
            "cvr": cvr,
            "badge": badge,
        })
    return {
        "key": key,
        "rows": out_rows,
        "acos_equilibrio": acos_eq,
        "guias_fase": fases,
        "book_economy": eco,
    }


@api.get("/datasets/{dataset_id}/timeseries")
async def get_timeseries(dataset_id: str):
    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0, "rows": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    rows = doc["rows"]
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
    rows = doc["rows"]
    campaigns = aggregate_by(rows, "campaign")[:10]
    key = "customer_search_term" if any(r.get("customer_search_term") for r in rows) else "targeting"
    terms = aggregate_by(rows, key)[:15]
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
