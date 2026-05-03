from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class IntentDefinition:
    identifier: str
    title: str
    description: str
    trigger_hints: tuple[str, ...]
    preferred_tools: tuple[str, ...]
    output_contract: tuple[str, ...]
    handoff_target: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ToolDefinition:
    identifier: str
    group: str
    title: str
    purpose: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContextPacket:
    context_type: str
    objective: str
    facts: dict[str, Any]
    artifacts: tuple[str, ...]
    constraints: tuple[str, ...]
    guidance: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["artifacts"] = list(self.artifacts)
        payload["constraints"] = list(self.constraints)
        payload["guidance"] = list(self.guidance)
        return payload


@dataclass
class CaseState:
    case_id: str
    tenant_id: str
    current_goal: str
    active_intent: str
    completed_steps: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    candidate_handoffs: list[str] = field(default_factory=list)
    last_outputs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "tenant_id": self.tenant_id,
            "current_goal": self.current_goal,
            "active_intent": self.active_intent,
            "completed_steps": list(self.completed_steps),
            "artifacts": list(self.artifacts),
            "open_questions": list(self.open_questions),
            "candidate_handoffs": list(self.candidate_handoffs),
            "last_outputs": list(self.last_outputs),
        }


@dataclass(frozen=True)
class RouteDecision:
    intent_id: str
    confidence: float
    rationale: tuple[str, ...]
    preferred_tools: tuple[str, ...]
    suggested_handoff: str | None
    output_contract: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["rationale"] = list(self.rationale)
        payload["preferred_tools"] = list(self.preferred_tools)
        payload["output_contract"] = list(self.output_contract)
        return payload


@dataclass(frozen=True)
class HandoffPreview:
    target_agent: str
    reason: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
