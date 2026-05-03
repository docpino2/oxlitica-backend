from __future__ import annotations

from typing import Any

from .orchestration import IntentDefinition, RouteDecision


INTENT_CATALOG: tuple[IntentDefinition, ...] = (
    IntentDefinition(
        identifier="cohort_analysis",
        title="Analisis de cohorte",
        description="Lectura poblacional, calidad de datos, distribucion y priorizacion inicial.",
        trigger_hints=("cohorte", "pacientes", "perfil", "poblacional", "segmentacion"),
        preferred_tools=("oncology_profile", "canonical_contract_reader"),
        output_contract=("resumen_ejecutivo", "hallazgos", "riesgos", "siguiente_accion"),
    ),
    IntentDefinition(
        identifier="operational_friction",
        title="Friccion operativa",
        description="Analisis de puertas de entrada, demoras, negaciones y perdidas tempranas.",
        trigger_hints=("autorizacion", "demora", "puerta", "ruta", "friccion", "negacion"),
        preferred_tools=("oncology_entry_flow", "oncology_financial_impact"),
        output_contract=("resumen_operativo", "cuellos_de_botella", "impacto", "intervencion_sugerida"),
    ),
    IntentDefinition(
        identifier="model_factory",
        title="Modelacion analitica",
        description="Entrenamiento, seleccion de modelo, scoring y empaquetado tecnico.",
        trigger_hints=("modelo", "prediccion", "clasificacion", "regresion", "automl", "scoring"),
        preferred_tools=("general_analytics_preview", "general_analytics_train", "general_analytics_report_pack"),
        output_contract=("objetivo_modelado", "mejor_modelo", "metricas", "despliegue_sugerido"),
    ),
    IntentDefinition(
        identifier="executive_summary",
        title="Resumen ejecutivo",
        description="Sintesis institucional para comites, direccion y clientes.",
        trigger_hints=("resumen", "comite", "directivo", "ejecutivo", "presentar"),
        preferred_tools=("llm_chat",),
        output_contract=("situacion", "hallazgos", "riesgos", "decision_sugerida"),
    ),
    IntentDefinition(
        identifier="heor_handoff",
        title="Derivacion a PegaXus",
        description="Caso que requiere HEOR, valor economico o narrativa de negocio ampliada.",
        trigger_hints=("heor", "costo-efectividad", "valor", "roi", "caso de negocio"),
        preferred_tools=("financial_impact_simulator", "swarm_handoff"),
        output_contract=("resumen_financiero", "pregunta_heor", "artefactos"),
        handoff_target="pegaxus",
    ),
    IntentDefinition(
        identifier="audit_handoff",
        title="Derivacion a OncoAgente Auditor",
        description="Caso que requiere auditoria clinica profunda o validacion especializada.",
        trigger_hints=("auditoria", "glosa", "consistencia clinica", "pertinencia", "caso auditor"),
        preferred_tools=("oncology_profile", "swarm_handoff"),
        output_contract=("hallazgos", "soportes", "pregunta_auditoria"),
        handoff_target="oncoagente_auditor",
    ),
)


def route_intent(payload: dict[str, Any]) -> RouteDecision:
    haystack = " ".join(_collect_strings(payload)).lower()
    scored: list[tuple[int, IntentDefinition, list[str]]] = []
    for intent in INTENT_CATALOG:
        hits = [hint for hint in intent.trigger_hints if hint in haystack]
        scored.append((len(hits), intent, hits))
    scored.sort(key=lambda item: item[0], reverse=True)

    best_score, best_intent, hits = scored[0]
    if best_score == 0:
        best_intent = _default_intent(payload)
        confidence = 0.45
        rationale = (
            "No hubo coincidencias directas en el texto de entrada.",
            f"Se asigno el intent por defecto: {best_intent.identifier}.",
        )
    else:
        confidence = min(0.55 + 0.12 * best_score, 0.94)
        rationale = (
            f"Se detectaron disparadores de intent: {', '.join(hits[:4])}.",
            f"El caso se enruto a {best_intent.identifier}.",
        )

    return RouteDecision(
        intent_id=best_intent.identifier,
        confidence=confidence,
        rationale=rationale,
        preferred_tools=best_intent.preferred_tools,
        suggested_handoff=best_intent.handoff_target,
        output_contract=best_intent.output_contract,
    )


def _collect_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        output: list[str] = []
        for item in value.values():
            output.extend(_collect_strings(item))
        return output
    if isinstance(value, (list, tuple, set)):
        output = []
        for item in value:
            output.extend(_collect_strings(item))
        return output
    return [str(value)]


def _default_intent(payload: dict[str, Any]) -> IntentDefinition:
    if "dataset_path" in payload or "target_column" in payload:
        return next(item for item in INTENT_CATALOG if item.identifier == "model_factory")
    return next(item for item in INTENT_CATALOG if item.identifier == "cohort_analysis")
