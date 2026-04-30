from __future__ import annotations

import json
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]


def load_oncology_contract() -> dict[str, Any]:
    path = WORKSPACE_ROOT / "data_contracts" / "oncology_canonical_contract.json"
    return json.loads(path.read_text())


def load_oncology_request_schema() -> dict[str, Any]:
    path = WORKSPACE_ROOT / "schemas" / "oncology_request_schema.json"
    return json.loads(path.read_text())


def load_oncology_cohort_schema() -> dict[str, Any]:
    path = WORKSPACE_ROOT / "schemas" / "oncology_cohort_schema.json"
    return json.loads(path.read_text())


def load_oncology_mapping_schema() -> dict[str, Any]:
    path = WORKSPACE_ROOT / "schemas" / "oncology_mapping_schema.json"
    return json.loads(path.read_text())
