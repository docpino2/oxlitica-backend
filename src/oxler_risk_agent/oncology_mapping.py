from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .contracts import load_oncology_contract


@dataclass(frozen=True)
class MappingResult:
    input_path: str
    mapping_path: str
    output_path: str
    records_read: int
    records_written: int
    missing_required_sources: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_path": self.input_path,
            "mapping_path": self.mapping_path,
            "output_path": self.output_path,
            "records_read": self.records_read,
            "records_written": self.records_written,
            "missing_required_sources": self.missing_required_sources,
            "warnings": self.warnings,
        }


def map_oncology_csv(input_path: str, mapping_path: str, output_path: str) -> MappingResult:
    rows = _load_csv(input_path)
    mapping = json.loads(Path(mapping_path).read_text())
    field_rules = mapping["fields"]
    contract_fields = {
        item["name"]: item
        for item in load_oncology_contract()["minimum_variables"]
    }
    source_headers = set(rows[0].keys()) if rows else set()
    missing_required_sources = sorted(
        rule["source"]
        for target, rule in field_rules.items()
        if rule.get("required") and rule["source"] not in source_headers
    )

    warnings: list[str] = []
    canonical_rows: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=1):
        canonical_row: dict[str, str] = {}
        for target_field, rule in field_rules.items():
            raw_value = row.get(rule["source"], rule.get("default", ""))
            transform = rule.get("transform", "identity")
            normalized = _transform_value(raw_value, transform)
            if rule.get("required") and normalized == "":
                warnings.append(f"fila {index}: campo requerido vacio tras transformar -> {target_field}")
            canonical_row[target_field] = normalized
        for field_name in contract_fields:
            canonical_row.setdefault(field_name, "")
        canonical_rows.append(canonical_row)

    _write_csv(output_path, canonical_rows)
    return MappingResult(
        input_path=input_path,
        mapping_path=mapping_path,
        output_path=output_path,
        records_read=len(rows),
        records_written=len(canonical_rows),
        missing_required_sources=missing_required_sources,
        warnings=warnings,
    )


def _load_csv(path: str) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: str, rows: list[dict[str, str]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _transform_value(value: Any, transform: str) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text == "":
        return ""
    if transform in {"identity", "strip"}:
        return text
    if transform == "sex":
        normalized = text.lower()
        if normalized in {"f", "femenino", "female", "mujer"}:
            return "F"
        if normalized in {"m", "masculino", "male", "hombre"}:
            return "M"
        return text.upper()
    if transform == "date":
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return text
    if transform == "number":
        compact = text.replace(",", "").replace(" ", "")
        try:
            return str(float(compact))
        except ValueError:
            return text
    return text
