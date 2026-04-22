from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
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

from amazon_ads import (
    parse_ads_file, compute_kpis, aggregate_by, CANONICAL_FIELDS,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# MongoDB
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Amazon Ads Analytics")
api = APIRouter(prefix="/api")


# ------------------- Models -------------------
class DatasetMeta(BaseModel):
    id: str
    name: str
    marketplace: str
    report_type: str
    ad_type: str
    row_count: int
    created_at: str
    kpis: dict[str, Any]


class Recommendation(BaseModel):
    title: str
    severity: str  # info | warning | critical
    detail: str


# ------------------- Routes -------------------
@api.get("/")
async def root():
    return {"status": "ok", "service": "amazon-ads-analytics"}


@api.post("/imports/upload")
async def upload_csv(
    file: UploadFile = File(...),
    marketplace: str = Form("us"),
    dataset_name: Optional[str] = Form(None),
):
    content = await file.read()
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
    }
    await db.datasets.insert_one(doc)
    return {
        "id": dataset_id,
        "name": doc["name"],
        "marketplace": marketplace,
        "report_type": parsed["report_type"],
        "ad_type": parsed["ad_type"],
        "row_count": parsed["row_count"],
        "created_at": now,
        "kpis": parsed["kpis"],
        "header_mapping": parsed["header_mapping"],
        "headers_detected": parsed["headers_detected"],
    }


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


@api.get("/datasets/{dataset_id}/campaigns")
async def get_campaigns(dataset_id: str):
    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0, "rows": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return aggregate_by(doc["rows"], "campaign")


@api.get("/datasets/{dataset_id}/search-terms")
async def get_search_terms(dataset_id: str, min_clicks: int = 0):
    doc = await db.datasets.find_one({"id": dataset_id}, {"_id": 0, "rows": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    rows = doc["rows"]
    key = "customer_search_term" if any(
        r.get("customer_search_term") for r in rows
    ) else "targeting"
    agg = aggregate_by(rows, key)
    # attach negative-keyword suggestion flag
    for r in agg:
        r["suggest_negative"] = bool(
            r.get("clicks", 0) >= max(min_clicks, 6) and r.get("orders", 0) == 0
        )
    return {"key": key, "rows": agg}


@api.get("/datasets/{dataset_id}/timeseries")
async def get_timeseries(dataset_id: str):
    """Bucket by start_date (if present) or group by campaign as fallback."""
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
    # fallback: by campaign
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

    summary = {
        "report_type": doc["report_type"],
        "ad_type": doc["ad_type"],
        "marketplace": doc["marketplace"],
        "kpis": kpis,
        "top_campaigns": campaigns,
        "top_search_terms": terms,
    }

    system_msg = (
        "Eres un experto en optimización de Amazon Ads (Sponsored Products, Brands y Display). "
        "Analiza los datos y devuelve entre 4 y 8 recomendaciones concretas, accionables y cortas. "
        "Devuelve SIEMPRE JSON válido con el formato: "
        '{"recommendations":[{"title":"...","severity":"info|warning|critical","detail":"..."}]}. '
        "Considera ACoS, ROAS, CTR, CPC, keywords que gastan sin vender (negativas), "
        "campañas con mejor rendimiento para escalar y presupuesto."
    )

    chat = (
        LlmChat(api_key=api_key, session_id=f"ads-{dataset_id}",
                system_message=system_msg)
        .with_model("anthropic", "claude-sonnet-4-5-20250929")
    )
    msg = UserMessage(
        text=f"Datos agregados del reporte Amazon Ads:\n{summary}\n\n"
             f"Devuelve solo JSON con recomendaciones."
    )
    try:
        response = await chat.send_message(msg)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error en IA: {e}")

    text = response if isinstance(response, str) else str(response)
    # Extract JSON block
    import json, re
    match = re.search(r"\{.*\}", text, re.S)
    raw = match.group(0) if match else text
    try:
        data = json.loads(raw)
        recs = data.get("recommendations", [])
    except Exception:
        recs = [{"title": "Respuesta IA", "severity": "info", "detail": text[:1500]}]

    out = {"recommendations": recs, "generated_at":
           datetime.now(timezone.utc).isoformat()}
    await db.datasets.update_one(
        {"id": dataset_id}, {"$set": {"ai_recommendations": out}}
    )
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
