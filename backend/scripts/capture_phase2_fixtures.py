"""Capture importer response as fixture for Phase 2 regression tests.

Run BEFORE making any changes that could affect /imports/upload.
"""
import json
import os
import sys
from pathlib import Path

import httpx

API = (os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001").rstrip("/") + "/api"
FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

CSV_EN = (
    "Campaign Name,Ad Group Name,Customer Search Term,Keyword Text,Match Type,"
    "Impressions,Clicks,Click-Thru Rate (CTR),Cost Per Click (CPC),Spend,"
    "7 Day Total Sales,7 Day Total Orders (#),"
    "Total Advertising Cost of Sales (ACOS),Total Return on Advertising Spend (ROAS),Start Date\n"
    "Campaign Alpha,AdGroup A,mindfulness book,mindfulness,broad,1200,45,3.75%,$0.62,$27.90,$89.97,3,31.01%,3.23,2025-01-01\n"
    "Campaign Alpha,AdGroup A,buddha quotes,mindfulness,broad,800,20,2.50%,$0.50,$10.00,$0.00,0,0.00%,0,2025-01-02\n"
    "Campaign Beta,AdGroup B,yoga mat,yoga,exact,500,30,6.00%,$0.40,$12.00,$60.00,2,20.00%,5.0,2025-01-02\n"
    "Campaign Beta,AdGroup B,no sales term,yoga,broad,900,10,1.10%,$0.30,$3.00,$0.00,0,0.00%,0,2025-01-03\n"
)


def main():
    files = {"file": ("phase2_fixture.csv", CSV_EN.encode("utf-8"), "text/csv")}
    data = {"marketplace": "us", "dataset_name": "PHASE2_FIXTURE_DATASET"}
    r = httpx.post(f"{API}/imports/upload", files=files, data=data, timeout=60)
    r.raise_for_status()
    payload = r.json()
    # Drop volatile fields
    for k in ("id", "created_at"):
        payload.pop(k, None)
    FIXTURES.mkdir(exist_ok=True)
    target = FIXTURES / "import_response_pre_phase2.json"
    target.write_text(json.dumps(payload, sort_keys=True, indent=2))
    print(f"Captured importer fixture → {target}")
    # Also delete the just-created dataset to keep the DB clean
    if "id" in r.json():
        httpx.delete(f"{API}/datasets/{r.json()['id']}", timeout=10)


if __name__ == "__main__":
    sys.exit(main() or 0)
