from __future__ import annotations

from dataclasses import dataclass

from .models import ExecutionPhase, ExecutionPlan, GovernancePolicy, UseCaseRequest
from .pipeline_factory import recommend_pipelines
from .subprocesses import build_subprocess_catalog


@dataclass
class RiskAnalyticsAgent:
    name: str
    catalog: dict
    governance: tuple[GovernancePolicy, ...]

    def plan_request(self, request: UseCaseRequest) -> ExecutionPlan:
        selected_ids = self._select_subprocesses(request)
        selected = [self.catalog[subprocess_id] for subprocess_id in selected_ids]
        phases = self._build_phases(selected_ids)
        pipelines = recommend_pipelines(selected_ids, request.requested_capabilities)
        notes = self._build_notes(request, selected_ids)
        return ExecutionPlan(
            use_case=request,
            phases=phases,
            selected_subprocesses=selected,
            recommended_pipelines=pipelines,
            governance=list(self.governance),
            implementation_notes=notes,
        )

    def _select_subprocesses(self, request: UseCaseRequest) -> list[str]:
        assets = {value.lower() for value in request.available_assets}
        goals = " ".join(request.business_goals).lower()
        capabilities = " ".join(request.requested_capabilities).lower()

        selected = {"1.1", "1.7"}
        if any(word in goals or word in capabilities for word in ("capt", "entrada", "tamiz", "refer", "oportunidad")):
            selected.add("1.2")
        if any(word in goals or word in capabilities for word in ("red", "prestador", "eficien", "concentr")):
            selected.add("1.3")
        if any(word in goals or word in capabilities for word in ("kpi", "monitor", "alert", "enrut")):
            selected.add("1.4")
        if any(word in goals or word in capabilities for word in ("journey", "traves", "flujo", "desperdicio")):
            selected.add("1.5")
        if any(word in goals or word in capabilities for word in ("financ", "ahorro", "roi", "costo")):
            selected.add("1.6")

        if "rips" in assets or "mipres" in assets or "autorizaciones" in assets:
            selected.update({"1.2", "1.3", "1.4"})
        if "costos" in assets or "facturacion" in assets:
            selected.add("1.6")

        return sorted(selected)

    def _build_phases(self, subprocess_ids: list[str]) -> list[ExecutionPhase]:
        phases = [
            ExecutionPhase(
                name="Fase 0. Gobierno e Ingestion",
                objective="Asegurar contratos de datos, privacidad, trazabilidad y modelo canonico antes de analitica avanzada.",
                subprocesses=tuple(item for item in ("1.7", "1.1") if item in subprocess_ids),
                outputs=("diccionario canonico", "dataset confiable", "linea base de cohorte"),
            ),
            ExecutionPhase(
                name="Fase 1. Diagnostico del Riesgo",
                objective="Entender acceso, rutas, nodos y fricciones operativas de la cohorte.",
                subprocesses=tuple(item for item in ("1.2", "1.3", "1.5") if item in subprocess_ids),
                outputs=("mapa de puertas", "trayectorias", "desperdicios y fugas"),
            ),
            ExecutionPhase(
                name="Fase 2. Monitoreo y Valor",
                objective="Operacionalizar KPIs y cuantificar impacto financiero de las decisiones priorizadas.",
                subprocesses=tuple(item for item in ("1.4", "1.6") if item in subprocess_ids),
                outputs=("scorecards", "alertas", "simulaciones financieras"),
            ),
        ]
        return [phase for phase in phases if phase.subprocesses]

    def _build_notes(self, request: UseCaseRequest, subprocess_ids: list[str]) -> list[str]:
        notes = [
            "El agente debe desplegarse como copiloto institucional, no como sistema autonomo sin supervision clinica.",
            "Cada hallazgo ejecutivo debe etiquetarse como confirmatorio, exploratorio o incierto.",
            "La primera version debe priorizar un caso de uso vertical por cohorte antes de escalar a multipatologia.",
        ]
        if request.institution_type.lower() in {"eps", "asegurador", "pagador"}:
            notes.append("Para aseguradores conviene enfatizar autorizaciones, trazabilidad entre nodos y PMPM por cohorte.")
        if "1.6" in subprocess_ids:
            notes.append("La simulacion financiera debe usar escenarios conservador, base y agresivo para facilitar decision.")
        if "1.2" in subprocess_ids and "1.4" in subprocess_ids:
            notes.append("Las alertas de puerta de entrada deben convertirse en reglas operativas consumibles por navegacion o auditoria.")
        return notes


def build_default_agent() -> RiskAnalyticsAgent:
    governance = (
        GovernancePolicy("Privacidad", "Aplicar minimizacion de PHI, control de acceso por rol y auditoria de consultas."),
        GovernancePolicy("Seguridad", "Separar ingestion, feature store y capa conversacional; cifrar datos en reposo y transito."),
        GovernancePolicy("Validez clinica", "Ninguna recomendacion operativa critica se publica sin revision medico-analitica."),
        GovernancePolicy("Trazabilidad", "Versionar datasets, prompts, reglas y modelos para cada entrega a cliente institucional."),
        GovernancePolicy("Uso responsable de IA", "Explicar limites del dato y evitar decisiones automaticas de cobertura o tratamiento."),
    )
    return RiskAnalyticsAgent(
        name="OxLER Risk Analytics Agent",
        catalog=build_subprocess_catalog(),
        governance=governance,
    )
