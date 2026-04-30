from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

from .oncology_pipeline import load_tabular_records


@dataclass(frozen=True)
class EntryFlowResult:
    input_path: str
    total_records: int
    patients_with_suspicion: int
    patients_with_referral: int
    patients_with_treatment: int
    authorization_breakdown: list[dict[str, Any]]
    origin_provider_breakdown: list[dict[str, Any]]
    regional_breakdown: list[dict[str, Any]]
    timing_metrics: dict[str, float | None]
    funnel_metrics: dict[str, float | None]
    anomalies: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_path": self.input_path,
            "total_records": self.total_records,
            "patients_with_suspicion": self.patients_with_suspicion,
            "patients_with_referral": self.patients_with_referral,
            "patients_with_treatment": self.patients_with_treatment,
            "authorization_breakdown": self.authorization_breakdown,
            "origin_provider_breakdown": self.origin_provider_breakdown,
            "regional_breakdown": self.regional_breakdown,
            "timing_metrics": self.timing_metrics,
            "funnel_metrics": self.funnel_metrics,
            "anomalies": self.anomalies,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Analisis de Puertas de Entrada Oncologicas",
            "",
            f"- Archivo: {self.input_path}",
            f"- Registros: {self.total_records}",
            f"- Pacientes con sospecha: {self.patients_with_suspicion}",
            f"- Pacientes con remision: {self.patients_with_referral}",
            f"- Pacientes con inicio de tratamiento: {self.patients_with_treatment}",
            "",
            "## Funnel",
        ]
        for key, value in self.funnel_metrics.items():
            pretty = "N/A" if value is None else f"{value:.2%}"
            lines.append(f"- {key}: {pretty}")
        lines.append("")
        lines.append("## Tiempos")
        for key, value in self.timing_metrics.items():
            pretty = "N/A" if value is None else f"{value:.1f} dias"
            lines.append(f"- {key}: {pretty}")
        lines.append("")
        lines.append("## Distribuciones")
        if self.authorization_breakdown:
            formatted = ", ".join(f"{item['value']} ({item['count']})" for item in self.authorization_breakdown)
            lines.append(f"- Autorizaciones: {formatted}")
        if self.origin_provider_breakdown:
            formatted = ", ".join(f"{item['value']} ({item['count']})" for item in self.origin_provider_breakdown)
            lines.append(f"- Prestadores origen: {formatted}")
        if self.regional_breakdown:
            formatted = ", ".join(f"{item['value']} ({item['count']})" for item in self.regional_breakdown)
            lines.append(f"- Regiones: {formatted}")
        lines.append("")
        lines.append("## Anomalias")
        if self.anomalies:
            for item in self.anomalies:
                lines.append(f"- {item}")
        else:
            lines.append("- No se detectaron anomalias criticas con las reglas base.")
        return "\n".join(lines)


def analyze_oncology_entry_flow(path: str) -> EntryFlowResult:
    rows = load_tabular_records(path)
    total_records = len(rows)
    suspicion_count = sum(1 for row in rows if _parse_date(row.get("first_suspicion_date")))
    referral_count = sum(1 for row in rows if _parse_date(row.get("first_referral_date")))
    treatment_count = sum(1 for row in rows if _parse_date(row.get("treatment_start_date")))

    authorization_breakdown = _top_counts(rows, "authorization_status")
    origin_provider_breakdown = _top_counts(rows, "origin_provider")
    regional_breakdown = _top_counts(rows, "region")

    timing_metrics = {
        "median_days_suspicion_to_referral": _median_day_diff(rows, "first_suspicion_date", "first_referral_date"),
        "median_days_referral_to_treatment": _median_day_diff(rows, "first_referral_date", "treatment_start_date"),
        "median_days_suspicion_to_treatment": _median_day_diff(rows, "first_suspicion_date", "treatment_start_date"),
    }
    funnel_metrics = {
        "referral_from_suspicion_rate": _safe_rate(referral_count, suspicion_count),
        "treatment_from_referral_rate": _safe_rate(treatment_count, referral_count),
        "treatment_from_suspicion_rate": _safe_rate(treatment_count, suspicion_count),
    }
    anomalies = _detect_entry_flow_anomalies(rows, timing_metrics)

    return EntryFlowResult(
        input_path=path,
        total_records=total_records,
        patients_with_suspicion=suspicion_count,
        patients_with_referral=referral_count,
        patients_with_treatment=treatment_count,
        authorization_breakdown=authorization_breakdown,
        origin_provider_breakdown=origin_provider_breakdown,
        regional_breakdown=regional_breakdown,
        timing_metrics=timing_metrics,
        funnel_metrics=funnel_metrics,
        anomalies=anomalies,
    )


def _top_counts(rows: list[dict[str, str]], field: str, limit: int = 5) -> list[dict[str, Any]]:
    counts = Counter((row.get(field) or "").strip() for row in rows if (row.get(field) or "").strip())
    return [{"value": value, "count": count} for value, count in counts.most_common(limit)]


def _safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


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


def _detect_entry_flow_anomalies(rows: list[dict[str, str]], timing_metrics: dict[str, float | None]) -> list[str]:
    anomalies: list[str] = []
    if timing_metrics["median_days_suspicion_to_referral"] is not None and timing_metrics["median_days_suspicion_to_referral"] > 15:
        anomalies.append("mediana alta entre sospecha y remision; revisar cuellos de botella iniciales")
    if timing_metrics["median_days_referral_to_treatment"] is not None and timing_metrics["median_days_referral_to_treatment"] > 30:
        anomalies.append("mediana alta entre remision e inicio de tratamiento; revisar autorizacion y asignacion de red")

    denied = sum(1 for row in rows if (row.get("authorization_status") or "").strip().lower() in {"denied", "negada", "negado", "rechazada"})
    if denied:
        anomalies.append(f"se detectaron {denied} casos con autorizacion negada o rechazada")

    provider_denials: dict[str, int] = defaultdict(int)
    for row in rows:
        status = (row.get("authorization_status") or "").strip().lower()
        provider = (row.get("origin_provider") or "").strip()
        if provider and status in {"denied", "negada", "negado", "rechazada"}:
            provider_denials[provider] += 1
    if provider_denials:
        hotspot, hotspot_count = max(provider_denials.items(), key=lambda item: item[1])
        anomalies.append(f"prestador con mas negaciones en entrada: {hotspot} ({hotspot_count})")

    missing_suspicion = sum(1 for row in rows if not _parse_date(row.get("first_suspicion_date")))
    if missing_suspicion:
        anomalies.append(f"hay {missing_suspicion} registros sin fecha de sospecha; limita trazabilidad del ingreso")
    return anomalies


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
