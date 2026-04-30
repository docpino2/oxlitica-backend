from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class DataAsset:
    name: str
    domain: str
    granularity: str
    required: bool = True
    notes: str = ""


@dataclass(frozen=True)
class Deliverable:
    name: str
    description: str


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    dimension: str
    formula_hint: str


@dataclass(frozen=True)
class SubprocessDefinition:
    identifier: str
    title: str
    objective: str
    strategic_value: str
    key_questions: tuple[str, ...]
    required_assets: tuple[DataAsset, ...]
    deliverables: tuple[Deliverable, ...]
    metrics: tuple[MetricDefinition, ...]
    downstream_dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class PipelineSpec:
    name: str
    purpose: str
    techniques: tuple[str, ...]
    source_domains: tuple[str, ...]
    outputs: tuple[str, ...]
    deployment_pattern: str


@dataclass(frozen=True)
class GovernancePolicy:
    principle: str
    control: str


@dataclass(frozen=True)
class UseCaseRequest:
    institution_type: str
    condition_focus: str
    population_scope: str
    business_goals: tuple[str, ...]
    available_assets: tuple[str, ...]
    requested_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionPhase:
    name: str
    objective: str
    subprocesses: tuple[str, ...]
    outputs: tuple[str, ...]


@dataclass
class ExecutionPlan:
    use_case: UseCaseRequest
    phases: list[ExecutionPhase] = field(default_factory=list)
    selected_subprocesses: list[SubprocessDefinition] = field(default_factory=list)
    recommended_pipelines: list[PipelineSpec] = field(default_factory=list)
    governance: list[GovernancePolicy] = field(default_factory=list)
    implementation_notes: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines: list[str] = []
        lines.append("# Plan de Ejecucion del Agente OxLER")
        lines.append("")
        lines.append(f"- Tipo de institucion: {self.use_case.institution_type}")
        lines.append(f"- Foco clinico: {self.use_case.condition_focus}")
        lines.append(f"- Alcance poblacional: {self.use_case.population_scope}")
        lines.append(f"- Objetivos: {', '.join(self.use_case.business_goals)}")
        lines.append("")
        lines.append("## Fases")
        for phase in self.phases:
            lines.append(f"### {phase.name}")
            lines.append(phase.objective)
            lines.append(f"- Subprocesos: {', '.join(phase.subprocesses)}")
            lines.append(f"- Salidas: {', '.join(phase.outputs)}")
        lines.append("")
        lines.append("## Pipelines Recomendados")
        for pipeline in self.recommended_pipelines:
            lines.append(f"### {pipeline.name}")
            lines.append(pipeline.purpose)
            lines.append(f"- Tecnicas: {', '.join(pipeline.techniques)}")
            lines.append(f"- Fuentes: {', '.join(pipeline.source_domains)}")
            lines.append(f"- Salidas: {', '.join(pipeline.outputs)}")
            lines.append(f"- Despliegue: {pipeline.deployment_pattern}")
        lines.append("")
        lines.append("## Gobierno")
        for item in self.governance:
            lines.append(f"- {item.principle}: {item.control}")
        lines.append("")
        lines.append("## Notas")
        for note in self.implementation_notes:
            lines.append(f"- {note}")
        return "\n".join(lines)


def unique_preserve_order(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return tuple(ordered)
