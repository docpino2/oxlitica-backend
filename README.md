# Oxlitica Backend

Backend Python de `Oxlitica`, el agente autonomo de OxLER para gestion
inteligente del riesgo, gestion poblacional y modelacion analitica avanzada.

## Que contiene

- API `FastAPI`
- modulos de cohortes oncologicas
- modulo general de analitica / AutoML
- integracion backend con `OpenRouter`
- contratos, esquemas, ejemplos y pruebas

## Estructura

- `src/oxler_risk_agent/`: paquete principal
- `tests/`: suite de pruebas
- `examples/`: datasets y requests de ejemplo
- `schemas/`: esquemas JSON
- `data_contracts/`: contrato canonico
- `docs/`: documentacion base del agente
- `PROJECT_CONTEXT.md`: contexto de producto y repo

## Instalacion local

```bash
cd "/Users/oxler/Documents/New project/oxlitica-backend"
python3 -m pip install -e .
```

## Variables de entorno para LLM

```bash
export OPENROUTER_API_KEY="tu_api_key"
export OPENROUTER_MODEL="openai/gpt-4o-mini"
```

Opcionales:

```bash
export OPENROUTER_HTTP_REFERER="https://tu-dominio.com"
export OPENROUTER_APP_TITLE="Oxlitica"
```

## Correr la API localmente

```bash
cd "/Users/oxler/Documents/New project/oxlitica-backend"
PYTHONPATH=src python3 -m uvicorn oxler_risk_agent.api.app:build_app --factory --host 127.0.0.1 --port 8000
```

## Ejecutar pruebas

```bash
cd "/Users/oxler/Documents/New project/oxlitica-backend"
PYTHONPATH=src python3 -m unittest tests/test_risk_agent.py
```

## Endpoints principales

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

## Despliegue recomendado

Recomendacion actual:

- frontend en `Vercel`
- backend en `Render`

## Configuracion sugerida para Render

Build command:

```bash
pip install -e .
```

Start command:

```bash
PYTHONPATH=src uvicorn oxler_risk_agent.api.app:build_app --factory --host 0.0.0.0 --port $PORT
```

Variables de entorno minimas:

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`

## Publicacion a GitHub

```bash
cd "/Users/oxler/Documents/New project/oxlitica-backend"
git init
git add .
git commit -m "Initial Oxlitica backend"
git branch -M main
```
