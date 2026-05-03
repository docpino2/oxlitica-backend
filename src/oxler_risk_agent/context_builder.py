from __future__ import annotations

from typing import Any

from .orchestration import CaseState, ContextPacket


def build_context_packet(
    intent_id: str,
    payload: dict[str, Any],
    case_state: CaseState | None = None,
) -> ContextPacket:
    facts = _extract_facts(payload, case_state)
    artifacts = tuple(_extract_artifacts(payload, case_state))
    constraints = (
        "Separar hechos confirmados de inferencias.",
        "Declarar limitaciones de datos cuando existan.",
        "Priorizar lenguaje institucional y accionable.",
    )

    if intent_id == "model_factory":
        return ContextPacket(
            context_type="automl_context",
            objective="Preparar, entrenar y sintetizar un pipeline de modelacion tabular.",
            facts=facts,
            artifacts=artifacts,
            constraints=constraints,
            guidance=(
                "Validar variable objetivo y naturaleza del problema.",
                "Explicar metricas y criterio de seleccion del mejor modelo.",
                "Sugerir siguiente paso de despliegue o scoring.",
            ),
        )

    if intent_id == "operational_friction":
        return ContextPacket(
            context_type="operational_friction_context",
            objective="Explicar cuellos de botella, negaciones y demoras en el flujo de entrada.",
            facts=facts,
            artifacts=artifacts,
            constraints=constraints,
            guidance=(
                "Priorizar autorizaciones, remisiones y tiempos medianos.",
                "Indicar impacto operativo y financiero cuando aplique.",
                "Sugerir intervencion concreta para EPS, IPS o red.",
            ),
        )

    if intent_id in {"heor_handoff", "audit_handoff"}:
        return ContextPacket(
            context_type="swarm_handoff_context",
            objective="Preparar un paquete claro para derivacion a otro agente del ecosistema.",
            facts=facts,
            artifacts=artifacts,
            constraints=constraints,
            guidance=(
                "Resumir hallazgo principal en una frase.",
                "Explicitar por que Oxlitica no debe resolver sola el siguiente paso.",
                "Enumerar artefactos y preguntas que recibe el agente destino.",
            ),
        )

    if intent_id == "executive_summary":
        return ContextPacket(
            context_type="executive_summary_context",
            objective="Sintetizar el caso para un lector directivo o comite.",
            facts=facts,
            artifacts=artifacts,
            constraints=constraints,
            guidance=(
                "Usar 3 a 5 hallazgos maximo.",
                "Cerrar con decision sugerida y riesgo si no se actua.",
                "No sobrecargar con detalle tecnico innecesario.",
            ),
        )

    return ContextPacket(
        context_type="cohort_analysis_context",
        objective="Entender la cohorte y establecer una lectura base accionable.",
        facts=facts,
        artifacts=artifacts,
        constraints=constraints,
        guidance=(
            "Priorizar tamano de cohorte, calidad de datos y concentraciones principales.",
            "Indicar que datos faltan para una lectura mas robusta.",
            "Cerrar con siguiente analisis sugerido.",
        ),
    )


def _extract_facts(payload: dict[str, Any], case_state: CaseState | None) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    for key in (
        "institution_type",
        "condition_focus",
        "population_scope",
        "dataset_path",
        "target_column",
        "task_type",
        "problem_name",
        "message",
    ):
        if key in payload:
            facts[key] = payload[key]
    if case_state:
        facts["case_id"] = case_state.case_id
        facts["tenant_id"] = case_state.tenant_id
        facts["current_goal"] = case_state.current_goal
        facts["active_intent"] = case_state.active_intent
    return facts


def _extract_artifacts(payload: dict[str, Any], case_state: CaseState | None) -> list[str]:
    artifacts: list[str] = []
    for key in ("dataset_path", "input_path", "mapping_path", "model_joblib_path", "output_dir"):
        if key in payload and payload[key]:
            artifacts.append(str(payload[key]))
    if case_state:
        artifacts.extend(case_state.artifacts)
    return artifacts
