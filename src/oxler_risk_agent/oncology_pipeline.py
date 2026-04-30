from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = ("patient_id", "sex", "region", "tumor_type")
DATE_FIELDS = ("birth_date", "diagnosis_date", "treatment_start_date", "first_suspicion_date", "first_referral_date")


@dataclass(frozen=True)
class PipelineResult:
    input_path: str
    records: int
    unique_patients: int
    completeness_by_field: dict[str, float]
    top_tumor_types: list[dict[str, Any]]
    stage_distribution: list[dict[str, Any]]
    regional_distribution: list[dict[str, Any]]
    authorization_distribution: list[dict[str, Any]]
    quality_flags: list[str]
    timing_metrics: dict[str, float | None]
    cost_metrics: dict[str, float | None]

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_path": self.input_path,
            "records": self.records,
            "unique_patients": self.unique_patients,
            "completeness_by_field": self.completeness_by_field,
            "top_tumor_types": self.top_tumor_types,
            "stage_distribution": self.stage_distribution,
            "regional_distribution": self.regional_distribution,
            "authorization_distribution": self.authorization_distribution,
            "quality_flags": self.quality_flags,
            "timing_metrics": self.timing_metrics,
            "cost_metrics": self.cost_metrics,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Perfilamiento Oncologico OxLER",
            "",
            f"- Archivo: {self.input_path}",
            f"- Registros: {self.records}",
            f"- Pacientes unicos: {self.unique_patients}",
            "",
            "## Calidad del dato",
        ]
        for field, ratio in self.completeness_by_field.items():
            lines.append(f"- {field}: {ratio:.2%}")
        lines.append("")
        lines.append("## Hallazgos")
        if self.top_tumor_types:
            formatted = ", ".join(f"{item['value']} ({item['count']})" for item in self.top_tumor_types)
            lines.append(f"- Tumores mas frecuentes: {formatted}")
        if self.regional_distribution:
            formatted = ", ".join(f"{item['value']} ({item['count']})" for item in self.regional_distribution)
            lines.append(f"- Regiones mas frecuentes: {formatted}")
        if self.quality_flags:
            lines.append(f"- Alertas de calidad: {'; '.join(self.quality_flags)}")
        else:
            lines.append("- Alertas de calidad: no se detectaron hallazgos criticos con las reglas base.")
        lines.append("")
        lines.append("## Tiempos")
        for key, value in self.timing_metrics.items():
            pretty = "N/A" if value is None else f"{value:.1f} dias"
            lines.append(f"- {key}: {pretty}")
        lines.append("")
        lines.append("## Costos")
        for key, value in self.cost_metrics.items():
            pretty = "N/A" if value is None else f"{value:.2f}"
            lines.append(f"- {key}: {pretty}")
        return "\n".join(lines)


def load_tabular_records(path: str) -> list[dict[str, str]]:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix != ".csv":
        raise ValueError("El MVP actual soporta perfilamiento tabular desde archivos CSV.")
    with file_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def profile_oncology_cohort(path: str) -> PipelineResult:
    rows = load_tabular_records(path)
    record_count = len(rows)
    patient_ids = [row.get("patient_id", "").strip() for row in rows if row.get("patient_id", "").strip()]
    unique_patients = len(set(patient_ids))

    completeness = {
        field: _field_completeness(rows, field)
        for field in dict.fromkeys(REQUIRED_FIELDS + DATE_FIELDS + ("stage_at_diagnosis", "authorization_status", "event_cost"))
    }

    top_tumor_types = _top_counts(rows, "tumor_type")
    stage_distribution = _top_counts(rows, "stage_at_diagnosis")
    regional_distribution = _top_counts(rows, "region")
    authorization_distribution = _top_counts(rows, "authorization_status")
    quality_flags = _quality_flags(rows, unique_patients)
    timing_metrics = {
        "median_days_suspicion_to_diagnosis": _median_day_diff(rows, "first_suspicion_date", "diagnosis_date"),
        "median_days_diagnosis_to_treatment": _median_day_diff(rows, "diagnosis_date", "treatment_start_date"),
        "median_days_suspicion_to_referral": _median_day_diff(rows, "first_suspicion_date", "first_referral_date"),
    }
    cost_metrics = _cost_metrics(rows)

    return PipelineResult(
        input_path=path,
        records=record_count,
        unique_patients=unique_patients,
        completeness_by_field=completeness,
        top_tumor_types=top_tumor_types,
        stage_distribution=stage_distribution,
        regional_distribution=regional_distribution,
        authorization_distribution=authorization_distribution,
        quality_flags=quality_flags,
        timing_metrics=timing_metrics,
        cost_metrics=cost_metrics,
    )


def save_profile_result(result: PipelineResult, output_path: str) -> None:
    Path(output_path).write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=True))


def _field_completeness(rows: list[dict[str, str]], field: str) -> float:
    if not rows:
        return 0.0
    present = sum(1 for row in rows if (row.get(field) or "").strip())
    return present / len(rows)


def _top_counts(rows: list[dict[str, str]], field: str, limit: int = 5) -> list[dict[str, Any]]:
    counts = Counter((row.get(field) or "").strip() for row in rows if (row.get(field) or "").strip())
    return [{"value": value, "count": count} for value, count in counts.most_common(limit)]


def _quality_flags(rows: list[dict[str, str]], unique_patients: int) -> list[str]:
    flags: list[str] = []
    if not rows:
        return ["archivo vacio"]
    if unique_patients < len(rows):
        flags.append("existen multiples registros por paciente; validar si el grano es evento o paciente")
    missing_required = [field for field in REQUIRED_FIELDS if _field_completeness(rows, field) < 0.95]
    if missing_required:
        flags.append(f"campos criticos con completitud menor a 95%: {', '.join(missing_required)}")
    invalid_costs = sum(1 for row in rows if _parse_float(row.get("event_cost")) is not None and _parse_float(row.get("event_cost")) < 0)
    if invalid_costs:
        flags.append(f"se encontraron {invalid_costs} registros con costo negativo")
    reversed_dates = 0
    for row in rows:
        diagnosis = _parse_date(row.get("diagnosis_date"))
        treatment = _parse_date(row.get("treatment_start_date"))
        if diagnosis and treatment and treatment < diagnosis:
            reversed_dates += 1
    if reversed_dates:
        flags.append(f"se encontraron {reversed_dates} registros con tratamiento antes del diagnostico")
    return flags


def _median_day_diff(rows: list[dict[str, str]], start_field: str, end_field: str) -> float | None:
    diffs: list[int] = []
    for row in rows:
        start = _parse_date(row.get(start_field))
        end = _parse_date(row.get(end_field))
        if start and end and end >= start:
            diffs.append((end - start).days)
    if not diffs:
        return None
    diffs.sort()
    middle = len(diffs) // 2
    if len(diffs) % 2 == 1:
        return float(diffs[middle])
    return (diffs[middle - 1] + diffs[middle]) / 2


def _cost_metrics(rows: list[dict[str, str]]) -> dict[str, float | None]:
    values = [_parse_float(row.get("event_cost")) for row in rows]
    clean = [value for value in values if value is not None]
    if not clean:
        return {
            "total_cost": None,
            "average_cost": None,
            "max_cost": None,
        }
    total = sum(clean)
    return {
        "total_cost": total,
        "average_cost": total / len(clean),
        "max_cost": max(clean),
    }


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        parts = [int(item) for item in value.split("-")]
        return date(parts[0], parts[1], parts[2])
    except (ValueError, IndexError):
        return None


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
