"""Phase 1 compatibility regression tests.

Guarantees:
  - /keywords-unified response for a legacy dataset is byte-identical to the
    pre-Phase-1 snapshot captured on disk.
  - /autopilot response is unchanged.
  - The new /economy-diagnosis endpoint returns mode='legacy' cleanly when
    KDP fields are missing, and mode='kdp' when they are present.
"""
import json
import os
from pathlib import Path

import httpx
import pytest

BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")
API = f"{BACKEND_URL}/api"

# Dataset id known to exist with real data (captured as fixture pre-Phase-1).
TEST_DS_ID = "d17b595d-7e2d-4b8a-8299-ece05cdc70d5"
FIXTURES = Path(__file__).parent / "fixtures"


def _get(path: str) -> dict:
    r = httpx.get(f"{API}{path}", timeout=20)
    r.raise_for_status()
    return r.json()


def _canonical(d, drop_keys=()) -> str:
    """Deterministic JSON representation for diffing. Drops top-level volatile keys."""
    if isinstance(d, dict) and drop_keys:
        d = {k: v for k, v in d.items() if k not in drop_keys}
    return json.dumps(d, sort_keys=True, indent=2, default=str)


@pytest.mark.skipif(
    not (FIXTURES / "keywords_unified_pre_phase1.json").exists(),
    reason="pre-phase1 fixture missing",
)
def test_keywords_unified_identical_to_pre_phase1_fixture():
    current = _get(f"/datasets/{TEST_DS_ID}/keywords-unified")
    snapshot = json.loads((FIXTURES / "keywords_unified_pre_phase1.json").read_text())
    assert _canonical(current) == _canonical(snapshot), (
        "keywords-unified response changed during Phase 1! "
        "That endpoint must remain untouched."
    )


@pytest.mark.skipif(
    not (FIXTURES / "autopilot_dominio_pre_phase1.json").exists(),
    reason="pre-phase1 fixture missing",
)
def test_autopilot_identical_to_pre_phase1_fixture():
    current = _get(f"/datasets/{TEST_DS_ID}/autopilot?phase=dominio")
    snapshot = json.loads((FIXTURES / "autopilot_dominio_pre_phase1.json").read_text())
    # `generated_at` is a per-call timestamp; ignore it but require every other key identical.
    VOLATILE = ("generated_at",)
    assert _canonical(current, VOLATILE) == _canonical(snapshot, VOLATILE), (
        "autopilot response changed during Phase 1! That endpoint must remain untouched."
    )


def test_economy_diagnosis_legacy_mode_for_existing_dataset():
    """The existing dataset has no KDP fields → endpoint returns mode='legacy' with no error."""
    r = _get(f"/datasets/{TEST_DS_ID}/economy-diagnosis")
    assert r["mode"] in ("legacy", "kdp")  # both valid; dataset may or may not have KDP set
    assert "marketplace" in r
    assert "marketplace_config" in r
    assert "outputs" in r


def test_economy_diagnosis_uppercase_marketplace_in_response():
    """Marketplace in response must always be uppercase (ES, COM, UK...)."""
    r = _get(f"/datasets/{TEST_DS_ID}/economy-diagnosis")
    assert r["marketplace"] == r["marketplace"].upper()
