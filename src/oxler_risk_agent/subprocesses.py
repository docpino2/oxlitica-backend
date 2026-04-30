from __future__ import annotations

from .models import DataAsset, Deliverable, MetricDefinition, SubprocessDefinition


def build_subprocess_catalog() -> dict[str, SubprocessDefinition]:
    common_assets = {
        "cohort_base": DataAsset(
            name="Base de pacientes",
            domain="cohort",
            granularity="paciente",
            notes="Incluye definicion operativa de cohorte y corte temporal.",
        ),
        "clinical_events": DataAsset(
            name="Eventos clinicos",
            domain="clinical",
            granularity="evento",
            notes="Diagnosticos, estadificacion, tratamiento y desenlaces.",
        ),
        "operational_events": DataAsset(
            name="Eventos operativos",
            domain="operations",
            granularity="evento",
            notes="Fechas clave, autorizaciones, remisiones y cambios de nodo.",
        ),
        "costs": DataAsset(
            name="Costos y facturacion",
            domain="finance",
            granularity="transaccion",
            notes="Costo directo, uso de tecnologia y consumo de servicios.",
        ),
        "network": DataAsset(
            name="Red y territorio",
            domain="network",
            granularity="prestador",
            notes="Nivel de atencion, nodo, ciudad, region y modalidad.",
        ),
    }

    catalog = {
        "1.1": SubprocessDefinition(
            identifier="1.1",
            title="Analisis Exploratorio de Cohortes",
            objective="Transformar bases heterogeneas en una lectura poblacional accionable y confiable.",
            strategic_value="Constituye la puerta analitica del modelo y la base para todos los demas subprocesos.",
            key_questions=(
                "Quienes son los pacientes y como se distribuyen?",
                "Que tan confiables son las fuentes?",
                "Donde estan las primeras senales de riesgo, costo y complejidad?",
            ),
            required_assets=(
                common_assets["cohort_base"],
                common_assets["clinical_events"],
                common_assets["operational_events"],
                common_assets["costs"],
            ),
            deliverables=(
                Deliverable("Ficha tecnica de cohorte", "Definicion, alcance, fuentes y reglas de negocio."),
                Deliverable("Reporte de calidad del dato", "Completitud, duplicados, consistencia y trazabilidad."),
                Deliverable("Segmentacion inicial", "Subgrupos por riesgo, costo, complejidad y territorio."),
            ),
            metrics=(
                MetricDefinition("% completitud critica", "calidad", "variables criticas completas / total esperado"),
                MetricDefinition("% trazabilidad", "integridad", "registros con fuente identificable / total"),
                MetricDefinition("% costo top 10", "concentracion", "costo top 10 segmentos / costo total"),
            ),
            downstream_dependencies=("1.2", "1.3", "1.6", "1.7"),
        ),
        "1.2": SubprocessDefinition(
            identifier="1.2",
            title="Analisis de Puertas de Entrada",
            objective="Evaluar si la captura y direccionamiento inicial del paciente funciona con oportunidad y pertinencia.",
            strategic_value="Reduce perdidas de valor tempranas y permite redisenar captacion, tamizaje y referencia.",
            key_questions=(
                "Por donde ingresa realmente el paciente?",
                "Que desvio existe entre la ruta disenada y la ruta observada?",
                "Donde aparecen anomalas, reprocesos o retrasos de activacion?",
            ),
            required_assets=(
                common_assets["cohort_base"],
                common_assets["operational_events"],
                common_assets["network"],
            ),
            deliverables=(
                Deliverable("Mapa de puertas de entrada", "Canales reales y formales de ingreso."),
                Deliverable("Analisis de anomalas de ingreso", "Casos, nodos o territorios atipicos."),
                Deliverable("Recomendaciones de reorganizacion", "Cambios de tamizaje, referencia y navegacion."),
            ),
            metrics=(
                MetricDefinition("Tiempo sospecha-remision", "oportunidad", "mediana entre sospecha y remision efectiva"),
                MetricDefinition("% remision adecuada", "eficiencia", "remisiones correctas al primer intento / total"),
                MetricDefinition("Tasa de reprocesos", "fragmentacion", "devoluciones y redireccionamientos / total"),
            ),
            downstream_dependencies=("1.3", "1.4", "1.5"),
        ),
        "1.3": SubprocessDefinition(
            identifier="1.3",
            title="Analisis de Rutas por Concentracion y Eficiencia",
            objective="Medir si el flujo asistencial concentra valor en nodos resolutivos y minimiza dispersion y desperdicio.",
            strategic_value="Permite redefinir red, priorizar prestadores y reducir fragmentacion operativa.",
            key_questions=(
                "Que tanto se dispersa la ruta?",
                "Que prestadores concentran volumen y resultado?",
                "Donde hay nodos de baja resolutividad o sobreuso?",
            ),
            required_assets=(
                common_assets["operational_events"],
                common_assets["network"],
                common_assets["costs"],
            ),
            deliverables=(
                Deliverable("Mapa de concentracion", "Nodos, volumen y resolutividad."),
                Deliverable("Ranking de eficiencia", "Prestadores y trayectorias priorizadas."),
                Deliverable("Hipotesis de optimizacion de red", "Cambios sugeridos de concentracion y derivacion."),
            ),
            metrics=(
                MetricDefinition("% concentracion en nodos priorizados", "concentracion", "ingresos o atenciones en nodos priorizados / total"),
                MetricDefinition("Nodos por paciente", "fragmentacion", "promedio de nodos recorridos por paciente"),
                MetricDefinition("Costo por ruta efectiva", "eficiencia", "costo total de rutas efectivas / total de rutas efectivas"),
            ),
            downstream_dependencies=("1.4", "1.5", "1.6"),
        ),
        "1.4": SubprocessDefinition(
            identifier="1.4",
            title="Analisis de Indicadores de Enrutamiento",
            objective="Construir indicadores que monitoreen direccionamiento, continuidad y oportunidad en tiempo casi real.",
            strategic_value="Convierte analitica retrospectiva en gestion operacional con alertas y seguimiento continuo.",
            key_questions=(
                "Que indicadores anticipan desviaciones de ruta?",
                "Que semaforos necesita el cliente institucional para operar?",
                "Como medir continuidad, direccionamiento y resolutividad?",
            ),
            required_assets=(
                common_assets["operational_events"],
                common_assets["network"],
                common_assets["clinical_events"],
            ),
            deliverables=(
                Deliverable("Catalogo de KPIs", "Definiciones, formulas y ventanas temporales."),
                Deliverable("Tablero operativo", "Semaforos y alertas por territorio, prestador y cohorte."),
                Deliverable("Reglas de monitoreo", "Umbrales para activar escalamiento o intervencion."),
            ),
            metrics=(
                MetricDefinition("% continuidad", "continuidad", "pacientes sin ruptura de secuencia / total"),
                MetricDefinition("Tiempo de activacion de ruta", "oportunidad", "mediana entre ingreso y atencion esperada"),
                MetricDefinition("% direccionamiento correcto", "calidad operativa", "casos con prestador adecuado / total"),
            ),
            downstream_dependencies=("1.5", "1.6"),
        ),
        "1.5": SubprocessDefinition(
            identifier="1.5",
            title="Mapa de Flujo de Valor y Travesia del Paciente",
            objective="Visualizar la experiencia y los desperdicios del paciente a lo largo de la ruta.",
            strategic_value="Hace visible el costo del tiempo, la friccion administrativa y los puntos de fuga de valor.",
            key_questions=(
                "Que pasos agregan valor clinico y cuales agregan friccion?",
                "Donde ocurren esperas, ciclos y duplicidades?",
                "Como vive la cohorte la ruta real frente a la deseada?",
            ),
            required_assets=(
                common_assets["operational_events"],
                common_assets["clinical_events"],
                common_assets["network"],
            ),
            deliverables=(
                Deliverable("Journey map", "Secuencia real del paciente con hitos y fricciones."),
                Deliverable("Mapa de desperdicios", "Esperas, bucles, traslados, negaciones y demoras."),
                Deliverable("Backlog de rediseno", "Oportunidades priorizadas por impacto y factibilidad."),
            ),
            metrics=(
                MetricDefinition("Lead time de ruta", "flujo", "tiempo total desde ingreso a hito objetivo"),
                MetricDefinition("% pasos sin valor", "desperdicio", "pasos sin aporte clinico o administrativo / total"),
                MetricDefinition("Reingresos al mismo nodo", "reproceso", "revisitas no planeadas / total de eventos"),
            ),
            downstream_dependencies=("1.6",),
        ),
        "1.6": SubprocessDefinition(
            identifier="1.6",
            title="Analisis de Impacto Financiero",
            objective="Cuantificar el efecto economico de las decisiones operativas, clinicas y de red sobre la cohorte.",
            strategic_value="Conecta la gestion del riesgo con sostenibilidad y costo-efectividad institucional.",
            key_questions=(
                "Cuanto cuesta la ineficiencia detectada?",
                "Que ahorro o retorno se espera con el rediseno?",
                "Que segmentos explican mas gasto evitable o gasto estrategico?",
            ),
            required_assets=(
                common_assets["costs"],
                common_assets["operational_events"],
                common_assets["clinical_events"],
                common_assets["network"],
            ),
            deliverables=(
                Deliverable("Linea base financiera", "Costo por segmento, ruta, tecnologia y territorio."),
                Deliverable("Escenarios de simulacion", "Ahorro, ROI y sensibilidad por intervencion."),
                Deliverable("Caso de negocio", "Narrativa ejecutiva para decision institucional."),
            ),
            metrics=(
                MetricDefinition("Costo evitable estimado", "finanzas", "gasto asociado a desperdicios y eventos evitables"),
                MetricDefinition("ROI de intervencion", "finanzas", "(beneficio esperado - costo implementacion) / costo implementacion"),
                MetricDefinition("PMPM o costo por cohorte", "sostenibilidad", "costo total / pacientes o meses cubiertos"),
            ),
            downstream_dependencies=(),
        ),
        "1.7": SubprocessDefinition(
            identifier="1.7",
            title="Adaptacion de la Matriz de Variables",
            objective="Estandarizar el modelo semantico y analitico que soporta todos los ejes del ecosistema.",
            strategic_value="Asegura interoperabilidad, trazabilidad y escalabilidad para nuevos clientes y nuevas cohortes.",
            key_questions=(
                "Que variables son minimas, opcionales y derivadas?",
                "Como se homologan fuentes heterogeneas?",
                "Que diccionario requiere el agente para operar de forma repetible?",
            ),
            required_assets=(
                common_assets["cohort_base"],
                common_assets["clinical_events"],
                common_assets["operational_events"],
                common_assets["costs"],
                common_assets["network"],
            ),
            deliverables=(
                Deliverable("Diccionario canonico", "Variables, definiciones, dominio y reglas de validacion."),
                Deliverable("Matriz de homologacion", "Mapeo fuente a modelo OxLER."),
                Deliverable("Contrato de datos", "Versionado, calidad minima y criterios de ingestion."),
            ),
            metrics=(
                MetricDefinition("% variables homologadas", "estandarizacion", "variables mapeadas al canon / variables esperadas"),
                MetricDefinition("% reglas validadas", "calidad", "reglas de validacion aprobadas / total reglas"),
                MetricDefinition("Tiempo de onboarding de nueva fuente", "operabilidad", "dias hasta ingestion utilizable"),
            ),
            downstream_dependencies=("1.1", "1.2", "1.3", "1.4", "1.5", "1.6"),
        ),
    }
    return catalog
