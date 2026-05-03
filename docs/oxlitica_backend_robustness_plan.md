# Plan de Robustecimiento del Backend de Oxlitica

## Objetivo

Convertir el backend de `Oxlitica` en una capa robusta de orquestacion para:

- lectura de cohortes
- uso correcto de herramientas
- construccion de contexto
- memoria de caso
- handoff dentro del swarm OxLER

## Componentes iniciados

### 1. Intent Router

Modulo inicial:

- `src/oxler_risk_agent/intent_router.py`

Funcion actual:

- clasifica solicitudes en intents base
- sugiere herramientas
- define contrato de salida
- propone handoff cuando aplica

Intents incluidos:

- `cohort_analysis`
- `operational_friction`
- `model_factory`
- `executive_summary`
- `heor_handoff`
- `audit_handoff`

### 2. Tool Registry

Modulo inicial:

- `src/oxler_risk_agent/tool_registry.py`

Funcion actual:

- define inventario institucional de herramientas
- clasifica tools por grupo
- documenta inputs y outputs

### 3. Context Builder

Modulo inicial:

- `src/oxler_risk_agent/context_builder.py`

Funcion actual:

- construye paquetes de contexto por intent
- limita hechos, artefactos y restricciones
- prepara guidance para el LLM o sintetizador

Contextos incluidos:

- `cohort_analysis_context`
- `operational_friction_context`
- `automl_context`
- `executive_summary_context`
- `swarm_handoff_context`

### 4. Case Memory

Modulo inicial:

- `src/oxler_risk_agent/case_memory.py`

Funcion actual:

- estado en memoria por caso
- objetivo actual
- pasos completados
- artefactos
- preguntas abiertas
- handoffs candidatos

### 5. Handoff Engine

Modulo inicial:

- `src/oxler_risk_agent/handoff_engine.py`

Funcion actual:

- genera previsualizacion de handoff
- prepara payload minimo
- distingue derivacion a `PegaXus` y `OncoAgente Auditor`

## Endpoints nuevos

- `GET /orchestration/intents`
- `GET /orchestration/tools`
- `POST /orchestration/route`
- `POST /orchestration/context-preview`
- `POST /orchestration/handoff-preview`

## Siguiente fase recomendada

### Fase 2

- persistir memoria de caso en almacenamiento real
- versionar prompts y context packets
- agregar evaluacion por intent
- definir output contracts mas estrictos
- acoplar trazabilidad por `trace_id`

### Fase 3

- integrar swarm broker
- colas para tareas largas
- politicas de fallback por herramienta
- observabilidad por modulo y costo

### Fase 4

- decidir si vale la pena `fine-tuning` para:
  - clasificacion de intent
  - estilo institucional de resumen
  - handoff quality

## Decision actual

El camino recomendado sigue siendo:

1. contexto
2. tools
3. memoria
4. evaluacion
5. fine-tuning despues
