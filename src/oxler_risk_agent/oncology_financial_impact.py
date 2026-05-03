from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Any

from .oncology_ingestion import load_tabular_records


@dataclass(frozen=True)
class FinancialImpactResult:
    input_path: str
    total_records: int
    total_cost: float
    average_cost: float | None
    median_cost: float | None
    max_cost: float | None
    denied_case_count: int
    denied_case_cost: float
    cost_concentration: dict[str, float | None]
    scenario_savings: dict[str, float]
    provider_cost_breakdown: list[dict[str, Any]]
    tumor_cost_breakdown: list[dict[str, Any]]
    findings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_path": self.input_path,
            "total_records": self.total_records,
            "total_cost": self.total_cost,
            "average_cost": self.average_cost,
            "median_cost": self.median_cost,
            "max_cost": self.max_cost,
            "denied_case_count": self.denied_case_count,
            "denied_case_cost": self.denied_case_cost,
            "cost_concentration": self.cost_concentration,
            "scenario_savings": self.scenario_savings,
            "provider_cost_breakdown": self.provider_cost_breakdown,
            "tumor_cost_breakdown": self.tumor_cost_breakdown,
            "findings": self.findings,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Impacto Financiero Oncologico OxLER",
            "",
            f"- Archivo: {self.input_path}",
            f"- Registros: {self.total_records}",
            f"- Costo total: {self.total_cost:.2f}",
            f"- Costo promedio: {self._pretty_number(self.average_cost)}",
            f"- Costo mediano: {self._pretty_number(self.median_cost)}",
            f"- Costo maximo: {self._pretty_number(self.max_cost)}",
            "",
            "## Concentracion",
        ]
        for key, value in self.cost_concentration.items():
            lines.append(f"- {key}: {self._pretty_percent(value)}")
        lines.append("")
        lines.append("## Friccion financiera")
        lines.append(f"- Casos negados: {self.denied_case_count}")
        lines.append(f"- Costo asociado a casos negados: {self.denied_case_cost:.2f}")
        lines.append("")
        lines.append("## Escenarios de ahorro")
        for key, value in self.scenario_savings.items():
            lines.append(f"- {key}: {value:.2f}")
        lines.append("")
        lines.append("## Hallazgos")
        if self.findings:
            for finding in self.findings:
                lines.append(f"- {finding}")
        else:
            lines.append("- Sin hallazgos financieros relevantes con las reglas base.")
        return "\n".join(lines)

    @staticmethod
    def _pretty_number(value: float | None) -> str:
        return "N/A" if value is None else f"{value:.2f}"

    @staticmethod
    def _pretty_percent(value: float | None) -> str:
        return "N/A" if value is None else f"{value:.2%}"


def analyze_oncology_financial_impact(path: str) -> FinancialImpactResult:
    rows = load_tabular_records(path)
    return analyze_oncology_financial_impact_rows(rows, source_label=path)


def analyze_oncology_financial_impact_rows(
    rows: list[dict[str, str]],
    source_label: str = "inline_records",
) -> FinancialImpactResult:
    costs = [value for value in (_parse_float(row.get("event_cost")) for row in rows) if value is not None]
    total_cost = sum(costs)
    average_cost = (total_cost / len(costs)) if costs else None
    median_cost = _median(costs)
    max_cost = max(costs) if costs else None

    denied_rows = [row for row in rows if (row.get("authorization_status") or "").strip().lower() in {"denied", "negada", "negado", "rechazada"}]
    denied_case_count = len(denied_rows)
    denied_case_cost = sum(_parse_float(row.get("event_cost")) or 0.0 for row in denied_rows)

    provider_cost_breakdown = _cost_breakdown(rows, "origin_provider")
    tumor_cost_breakdown = _cost_breakdown(rows, "tumor_type")
    cost_concentration = {
        "top_1_provider_share": _top_share(provider_cost_breakdown, 1, total_cost),
        "top_3_provider_share": _top_share(provider_cost_breakdown, 3, total_cost),
        "top_1_tumor_share": _top_share(tumor_cost_breakdown, 1, total_cost),
        "top_3_tumor_share": _top_share(tumor_cost_breakdown, 3, total_cost),
    }
    scenario_savings = _scenario_savings(rows, denied_case_cost)
    findings = _financial_findings(cost_concentration, denied_case_count, denied_case_cost, scenario_savings)

    return FinancialImpactResult(
        input_path=source_label,
        total_records=len(rows),
        total_cost=total_cost,
        average_cost=average_cost,
        median_cost=median_cost,
        max_cost=max_cost,
        denied_case_count=denied_case_count,
        denied_case_cost=denied_case_cost,
        cost_concentration=cost_concentration,
        scenario_savings=scenario_savings,
        provider_cost_breakdown=provider_cost_breakdown,
        tumor_cost_breakdown=tumor_cost_breakdown,
        findings=findings,
    )


def _cost_breakdown(rows: list[dict[str, str]], field: str, limit: int = 5) -> list[dict[str, Any]]:
    totals: Counter[str] = Counter()
    for row in rows:
        key = (row.get(field) or "").strip()
        value = _parse_float(row.get("event_cost"))
        if key and value is not None:
            totals[key] += value
    return [{"value": value, "cost": float(cost)} for value, cost in totals.most_common(limit)]


def _top_share(breakdown: list[dict[str, Any]], top_n: int, total_cost: float) -> float | None:
    if total_cost <= 0:
        return None
    return sum(item["cost"] for item in breakdown[:top_n]) / total_cost


def _scenario_savings(rows: list[dict[str, str]], denied_case_cost: float) -> dict[str, float]:
    delay_savings = 0.0
    friction_savings = denied_case_cost * 0.20
    for row in rows:
        diagnosis = _parse_date(row.get("diagnosis_date"))
        treatment = _parse_date(row.get("treatment_start_date"))
        cost = _parse_float(row.get("event_cost")) or 0.0
        if diagnosis and treatment:
            delay = (treatment - diagnosis).days
            if delay > 30:
                delay_savings += cost * 0.05
    return {
        "delay_reduction_savings": delay_savings,
        "authorization_friction_savings": friction_savings,
        "base_case_total_savings": delay_savings + friction_savings,
        "optimistic_total_savings": (delay_savings + friction_savings) * 1.5,
    }


def _financial_findings(
    cost_concentration: dict[str, float | None],
    denied_case_count: int,
    denied_case_cost: float,
    scenario_savings: dict[str, float],
) -> list[str]:
    findings: list[str] = []
    top_1_provider_share = cost_concentration.get("top_1_provider_share")
    if top_1_provider_share is not None and top_1_provider_share > 0.35:
        findings.append("alta concentracion de costo en un solo prestador de origen; revisar dependencia y capacidad de negociacion")
    top_1_tumor_share = cost_concentration.get("top_1_tumor_share")
    if top_1_tumor_share is not None and top_1_tumor_share > 0.40:
        findings.append("un tipo tumoral explica una proporcion dominante del gasto; priorizar gestion especifica por subcohorte")
    if denied_case_count > 0:
        findings.append(f"las negaciones representan {denied_case_count} casos y {denied_case_cost:.2f} de costo asociado en la cohorte observada")
    if scenario_savings["base_case_total_savings"] > 0:
        findings.append(
            f"el escenario base estima {scenario_savings['base_case_total_savings']:.2f} de ahorro potencial por mejorar oportunidad y friccion de autorizacion"
        )
    return findings


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


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
