from __future__ import annotations

from .orchestration import ToolDefinition


TOOL_REGISTRY: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        identifier="canonical_contract_reader",
        group="data",
        title="Lector de contrato canonico",
        purpose="Consultar dominios, campos y reglas minimas del contrato oncológico.",
        inputs=("contract_name",),
        outputs=("contract_json",),
    ),
    ToolDefinition(
        identifier="oncology_profile",
        group="analytics",
        title="Perfilamiento de cohorte oncológica",
        purpose="Resumir distribucion, calidad y metrica base de una cohorte.",
        inputs=("input_path",),
        outputs=("cohort_profile",),
    ),
    ToolDefinition(
        identifier="oncology_entry_flow",
        group="analytics",
        title="Analisis de entry flow",
        purpose="Detectar friccion en sospecha, remision, autorizacion y tratamiento.",
        inputs=("input_path",),
        outputs=("entry_flow_summary",),
    ),
    ToolDefinition(
        identifier="oncology_financial_impact",
        group="analytics",
        title="Analisis de impacto financiero",
        purpose="Cuantificar concentracion de costo y escenarios de ahorro.",
        inputs=("input_path",),
        outputs=("financial_impact_summary",),
    ),
    ToolDefinition(
        identifier="general_analytics_preview",
        group="analytics",
        title="Preview de dataset",
        purpose="Inspeccionar columnas, filas y muestra de un dataset para modelado.",
        inputs=("dataset_path",),
        outputs=("dataset_preview",),
    ),
    ToolDefinition(
        identifier="general_analytics_train",
        group="analytics",
        title="Entrenamiento AutoML",
        purpose="Entrenar y seleccionar el mejor modelo tabular para clasificacion o regresion.",
        inputs=("dataset_path", "target_column", "task_type", "problem_name"),
        outputs=("training_result",),
    ),
    ToolDefinition(
        identifier="general_analytics_report_pack",
        group="document",
        title="Report pack analitico",
        purpose="Generar artefactos auditable de un experimento de modelado.",
        inputs=("dataset_path", "target_column", "task_type", "problem_name", "output_dir"),
        outputs=("report_pack",),
    ),
    ToolDefinition(
        identifier="llm_chat",
        group="document",
        title="Sintesis con LLM",
        purpose="Convertir resultados y contexto estructurado en respuesta institucional.",
        inputs=("message", "context", "system_prompt"),
        outputs=("llm_response",),
    ),
    ToolDefinition(
        identifier="swarm_handoff",
        group="swarm",
        title="Previsualizacion de handoff",
        purpose="Preparar un paquete de derivacion hacia otro agente del ecosistema OxLER.",
        inputs=("target_agent", "case_id", "goal", "artifacts"),
        outputs=("handoff_payload",),
    ),
)
