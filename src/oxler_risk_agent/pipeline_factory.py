from __future__ import annotations

from .models import PipelineSpec, unique_preserve_order


PIPELINE_LIBRARY: dict[str, PipelineSpec] = {
    "cohort_profiling": PipelineSpec(
        name="Cohort Profiling Pipeline",
        purpose="Perfilar la cohorte, validar calidad del dato y segmentar poblacion inicial.",
        techniques=("EDA", "reglas de calidad", "outlier detection", "segmentacion descriptiva"),
        source_domains=("cohort", "clinical", "operations", "finance"),
        outputs=("ficha tecnica", "reporte de calidad", "segmentacion inicial"),
        deployment_pattern="batch diario o semanal",
    ),
    "entry_flow_anomaly_detection": PipelineSpec(
        name="Entry Flow Anomaly Detection",
        purpose="Detectar desviaciones en captacion, referencia y activacion temprana de la ruta.",
        techniques=("sequence mining", "unsupervised anomaly detection", "time-to-event analysis"),
        source_domains=("operations", "network", "clinical"),
        outputs=("casos atipicos", "brechas de oportunidad", "alertas de puerta de entrada"),
        deployment_pattern="micro-batch diario con alertas",
    ),
    "route_efficiency_engine": PipelineSpec(
        name="Route Efficiency Engine",
        purpose="Medir dispersion, concentracion y resolutividad de la red por cohorte y prestador.",
        techniques=("graph analytics", "path analysis", "provider concentration scoring"),
        source_domains=("operations", "network", "finance"),
        outputs=("ranking de nodos", "trayectorias eficientes", "fugas de valor"),
        deployment_pattern="batch semanal",
    ),
    "routing_kpi_monitor": PipelineSpec(
        name="Routing KPI Monitor",
        purpose="Monitorear KPIs operativos y semaforos para seguimiento institucional continuo.",
        techniques=("metric store", "business rules", "threshold alerting"),
        source_domains=("operations", "clinical", "network"),
        outputs=("dashboard kpi", "alertas", "scorecards por territorio"),
        deployment_pattern="streaming ligero o batch intradiario",
    ),
    "patient_journey_mapper": PipelineSpec(
        name="Patient Journey Mapper",
        purpose="Reconstruir travesias, identificar desperdicios y modelar valor en la ruta.",
        techniques=("process mining", "journey analytics", "bottleneck detection"),
        source_domains=("operations", "clinical", "network"),
        outputs=("journey maps", "cuellos de botella", "backlog de rediseno"),
        deployment_pattern="batch semanal o por corte analitico",
    ),
    "financial_impact_simulator": PipelineSpec(
        name="Financial Impact Simulator",
        purpose="Simular impacto economico de decisiones sobre red, oportunidad y tecnologia.",
        techniques=("scenario modeling", "sensitivity analysis", "cost attribution"),
        source_domains=("finance", "operations", "clinical", "network"),
        outputs=("escenarios de ahorro", "ROI", "caso de negocio"),
        deployment_pattern="batch bajo demanda",
    ),
    "risk_stratification_model": PipelineSpec(
        name="Risk Stratification Model",
        purpose="Priorizar pacientes o subcohortes por riesgo clinico, uso esperado y costo potencial.",
        techniques=("survival models", "gradient boosting", "calibrated classification"),
        source_domains=("clinical", "operations", "finance", "cohort"),
        outputs=("risk scores", "listas de priorizacion", "drivers de riesgo"),
        deployment_pattern="batch semanal con recertificacion mensual",
    ),
    "canonical_data_model_pipeline": PipelineSpec(
        name="Canonical Data Model Pipeline",
        purpose="Homologar fuentes institucionales al diccionario OxLER y aplicar controles de contrato de datos.",
        techniques=("schema mapping", "data contracts", "quality validation"),
        source_domains=("cohort", "clinical", "operations", "finance", "network"),
        outputs=("dataset canonico", "matriz de homologacion", "evidencia de calidad"),
        deployment_pattern="onboarding inicial y validacion recurrente",
    ),
}


def recommend_pipelines(subprocess_ids: list[str], requested_capabilities: tuple[str, ...]) -> list[PipelineSpec]:
    pipeline_names: list[str] = ["canonical_data_model_pipeline"]
    mapping = {
        "1.1": ("cohort_profiling", "risk_stratification_model"),
        "1.2": ("entry_flow_anomaly_detection",),
        "1.3": ("route_efficiency_engine",),
        "1.4": ("routing_kpi_monitor",),
        "1.5": ("patient_journey_mapper",),
        "1.6": ("financial_impact_simulator",),
        "1.7": ("canonical_data_model_pipeline",),
    }

    for subprocess_id in subprocess_ids:
        pipeline_names.extend(mapping.get(subprocess_id, ()))

    requested = " ".join(requested_capabilities).lower()
    if "model" in requested or "predic" in requested or "estrat" in requested:
        pipeline_names.append("risk_stratification_model")
    if "simul" in requested or "financ" in requested:
        pipeline_names.append("financial_impact_simulator")

    return [PIPELINE_LIBRARY[name] for name in unique_preserve_order(pipeline_names)]
