from __future__ import annotations

from typing import Any

from .orchestration import CaseState, HandoffPreview, RouteDecision


def build_handoff_preview(
    route: RouteDecision,
    payload: dict[str, Any],
    case_state: CaseState | None = None,
) -> HandoffPreview | None:
    if not route.suggested_handoff:
        return None

    target = route.suggested_handoff
    reason = _reason_for_target(target)
    handoff_payload = {
        "target_agent": target,
        "case_id": payload.get("case_id") or (case_state.case_id if case_state else "case-unassigned"),
        "tenant_id": payload.get("tenant_id") or (case_state.tenant_id if case_state else "tenant-unassigned"),
        "current_goal": payload.get("message")
        or payload.get("problem_name")
        or payload.get("population_scope")
        or (case_state.current_goal if case_state else "objetivo no especificado"),
        "artifacts": _collect_artifacts(payload, case_state),
        "questions": _suggest_questions(target, payload),
    }
    return HandoffPreview(target_agent=target, reason=reason, payload=handoff_payload)


def _reason_for_target(target: str) -> str:
    if target == "pegaxus":
        return "El caso requiere expansion hacia HEOR, valor economico o caso de negocio institucional."
    return "El caso requiere auditoria clinica profunda o validacion especializada."


def _collect_artifacts(payload: dict[str, Any], case_state: CaseState | None) -> list[str]:
    artifacts: list[str] = []
    for key in ("dataset_path", "input_path", "mapping_path", "output_dir"):
        value = payload.get(key)
        if value:
            artifacts.append(str(value))
    if case_state:
        artifacts.extend(case_state.artifacts)
    return artifacts


def _suggest_questions(target: str, payload: dict[str, Any]) -> list[str]:
    condition = payload.get("condition_focus", "la cohorte")
    if target == "pegaxus":
        return [
            f"Cual es el caso HEOR o de valor institucional para {condition}?",
            "Que escenarios economicos requieren modelado o narrativa ampliada?",
        ]
    return [
        f"Que hallazgos de auditoria clinica deben validarse en {condition}?",
        "Que inconsistencias o alertas requieren soporte auditor especializado?",
    ]
