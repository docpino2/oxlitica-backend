# PROJECT_CONTEXT

## Proyecto

`Oxlitica Backend` es la capa API y de ejecucion analitica del agente autonomo
de OxLER para:

- gestion inteligente del riesgo
- gestion poblacional
- modelacion analitica avanzada

Este repositorio debe contener solo el backend Python del producto.

## Alcance

Incluye:

- API `FastAPI`
- motor de cohortes oncológicas
- pipelines de perfilamiento, mapeo, entry flow e impacto financiero
- modulo general de analitica / AutoML
- integracion backend con `OpenRouter`
- contratos, esquemas, ejemplos y pruebas

No incluye:

- frontend web de `Oxlitica`
- llaves API reales
- datos sensibles
- productos externos al backend del agente

## Identidad funcional

Este backend debe verse como:

- el runtime institucional del agente
- una capa de servicios reutilizable para frontend, clientes y automatizaciones
- una base desplegable para ambientes demo y productivos

## API actual

Endpoints principales:

- `GET /health`
- `GET /contracts/oncology`
- `GET /analytics/general/capabilities`
- `POST /analytics/general/preview`
- `POST /analytics/general/train`
- `POST /analytics/general/report-pack`
- `POST /analytics/general/predict`
- `POST /pipelines/oncology/map`
- `POST /pipelines/oncology/profile`
- `POST /pipelines/oncology/entry-flow`
- `POST /pipelines/oncology/financial-impact`
- `POST /agent/plan`
- `POST /llm/chat`

## Dependencias

La base del repo debe mantener estas capacidades operativas:

- `FastAPI`
- `Uvicorn`
- `pandas`
- `scikit-learn`
- `openpyxl`

La integracion con `OpenRouter` usa variables de entorno y no debe exponer
credenciales al cliente.

## Variables de entorno

Requeridas para LLM:

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`

Opcionales:

- `OPENROUTER_API_URL`
- `OPENROUTER_HTTP_REFERER`
- `OPENROUTER_APP_TITLE`

## Archivos clave

- `src/oxler_risk_agent/api/app.py`
- `src/oxler_risk_agent/openrouter.py`
- `src/oxler_risk_agent/general_analytics.py`
- `src/oxler_risk_agent/oncology_pipeline.py`
- `tests/test_risk_agent.py`
- `README.md`

## Criterios de evolucion

- no acoplar secretos al codigo
- mantener compatibilidad con despliegue manejado tipo `Render`
- preservar contratos y ejemplos
- mantener trazabilidad institucional en resultados

## Despliegue recomendado

- frontend en `Vercel`
- backend en `Render`

El backend debe permanecer preparado para despliegue independiente.
