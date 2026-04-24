"""
Iteration 8: explicit edge-case regression for upsert_keyword MERGE behaviour.
Scenario per review request:
(1) PUT /keyword {term:T, campaign:'A'}
(2) PUT /keyword {term:T, match_type:'phrase'}
(3) PUT /keyword {term:T, clicks:99}
→ GET /keywords-unified row for T must have campaign='A' AND match_type='phrase' AND clicks=99
"""
import os
import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://amazon-ads-importer.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE_URL}/api"

CSV = (
    "Campaign Name,Ad Group Name,Customer Search Term,Keyword Text,Match Type,"
    "Impressions,Clicks,Click-Thru Rate (CTR),Cost Per Click (CPC),Spend,"
    "7 Day Total Sales,7 Day Total Orders (#),"
    "Total Advertising Cost of Sales (ACOS),Total Return on Advertising Spend (ROAS),Start Date\n"
    "Camp X,Grp 1,merge_term,x,broad,500,10,2.0%,0.50,5.00,50.00,2,10.00%,10.0,2025-01-01\n"
)


@pytest.fixture(scope="module")
def session():
    return requests.Session()


@pytest.fixture(scope="module")
def ds(session):
    files = {"file": ("iter8.csv", CSV.encode("utf-8"), "text/csv")}
    data = {"marketplace": "us", "dataset_name": "TEST_ITER8_MERGE"}
    r = session.post(f"{API}/imports/upload", files=files, data=data, timeout=60)
    assert r.status_code == 200, r.text
    j = r.json()
    yield j
    session.delete(f"{API}/datasets/{j['id']}", timeout=30)


def _row(session, ds_id, term):
    u = session.get(f"{API}/datasets/{ds_id}/keywords-unified", timeout=30).json()
    return next((r for r in u["rows"] if r["term"] == term), None)


class TestSequentialPartialUpdatesMerge:
    def test_three_sequential_partial_puts_merge(self, session, ds):
        term = "merge_term"
        # (1) campaign only
        r1 = session.put(f"{API}/datasets/{ds['id']}/keyword",
                         json={"term": term, "campaign": "A"}, timeout=30)
        assert r1.status_code == 200
        row1 = _row(session, ds["id"], term)
        assert row1 is not None
        assert row1["campaign"] == "A"

        # (2) match_type only → campaign must persist
        r2 = session.put(f"{API}/datasets/{ds['id']}/keyword",
                         json={"term": term, "match_type": "phrase"}, timeout=30)
        assert r2.status_code == 200
        row2 = _row(session, ds["id"], term)
        assert row2["campaign"] == "A", "campaign lost after match_type update"
        assert row2["match_type"] == "phrase"

        # (3) clicks only → both previous values must persist
        r3 = session.put(f"{API}/datasets/{ds['id']}/keyword",
                         json={"term": term, "clicks": 99}, timeout=30)
        assert r3.status_code == 200
        row3 = _row(session, ds["id"], term)
        assert row3["campaign"] == "A", "campaign lost after clicks update"
        assert row3["match_type"] == "phrase", "match_type lost after clicks update"
        assert row3["clicks"] == 99
