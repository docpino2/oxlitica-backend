from __future__ import annotations

from typing import Any

from .orchestration import CaseState


class InMemoryCaseMemoryStore:
    def __init__(self) -> None:
        self._cases: dict[str, CaseState] = {}

    def get_or_create(
        self,
        case_id: str,
        tenant_id: str,
        current_goal: str,
        active_intent: str,
    ) -> CaseState:
        state = self._cases.get(case_id)
        if state is None:
            state = CaseState(
                case_id=case_id,
                tenant_id=tenant_id,
                current_goal=current_goal,
                active_intent=active_intent,
            )
            self._cases[case_id] = state
            return state

        state.current_goal = current_goal or state.current_goal
        state.active_intent = active_intent or state.active_intent
        return state

    def update(self, case_id: str, payload: dict[str, Any]) -> CaseState | None:
        state = self._cases.get(case_id)
        if state is None:
            return None

        state.completed_steps.extend(_as_list(payload.get("completed_steps")))
        state.artifacts.extend(_as_list(payload.get("artifacts")))
        state.open_questions.extend(_as_list(payload.get("open_questions")))
        state.candidate_handoffs.extend(_as_list(payload.get("candidate_handoffs")))
        state.last_outputs.extend(_as_list(payload.get("last_outputs")))

        state.completed_steps = _unique(state.completed_steps)
        state.artifacts = _unique(state.artifacts)
        state.open_questions = _unique(state.open_questions)
        state.candidate_handoffs = _unique(state.candidate_handoffs)
        state.last_outputs = _unique(state.last_outputs)
        return state

    def get(self, case_id: str) -> CaseState | None:
        return self._cases.get(case_id)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    return [str(value)]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output
