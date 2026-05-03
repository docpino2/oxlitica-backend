from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from ..agent import build_default_agent
from ..case_memory import InMemoryCaseMemoryStore
from ..context_builder import build_context_packet
from ..contracts import load_oncology_contract
from ..general_analytics import (
    GeneralAnalyticsRequest,
    build_general_analytics_report_pack,
    detect_general_analytics_capabilities,
    predict_with_general_analytics_pack,
    preview_dataset_columns,
    train_general_automl,
)
from ..handoff_engine import build_handoff_preview
from ..intent_router import INTENT_CATALOG, route_intent
from ..models import UseCaseRequest
from ..oncology_entry_flow import analyze_oncology_entry_flow, analyze_oncology_entry_flow_rows
from ..oncology_financial_impact import analyze_oncology_financial_impact, analyze_oncology_financial_impact_rows
from ..oncology_ingestion import LocalUploadStore, extract_upload_payload, resolve_oncology_input
from ..oncology_mapping import map_oncology_csv
from ..oncology_pipeline import profile_oncology_cohort, profile_oncology_rows
from ..openrouter import OpenRouterChatRequest, chat_with_openrouter
from ..tool_registry import TOOL_REGISTRY


def build_app() -> Any:
    try:
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "FastAPI no esta instalado. Instale el extra de API con: pip install -e .[api]"
        ) from exc
    globals()["Request"] = Request

    app = FastAPI(
        title="OxLER Oncology Risk Agent API",
        version="0.1.0",
        description="MVP del agente institucional de analitica para cohortes oncologicas.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    agent = build_default_agent()
    case_store = InMemoryCaseMemoryStore()
    upload_store = LocalUploadStore()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "oxler-oncology-risk-agent"}

    @app.get("/contracts/oncology")
    def get_oncology_contract() -> dict[str, Any]:
        return load_oncology_contract()

    @app.get("/analytics/general/capabilities")
    def get_general_analytics_capabilities() -> dict[str, Any]:
        return detect_general_analytics_capabilities()

    @app.get("/orchestration/intents")
    def get_orchestration_intents() -> dict[str, Any]:
        return {"items": [item.to_dict() for item in INTENT_CATALOG]}

    @app.get("/orchestration/tools")
    def get_orchestration_tools() -> dict[str, Any]:
        return {"items": [item.to_dict() for item in TOOL_REGISTRY]}

    @app.post("/orchestration/route")
    def orchestration_route(payload: dict[str, Any]) -> dict[str, Any]:
        decision = route_intent(payload)
        return decision.to_dict()

    @app.post("/orchestration/context-preview")
    def orchestration_context_preview(payload: dict[str, Any]) -> dict[str, Any]:
        decision = route_intent(payload)
        state = _resolve_case_state(case_store, payload, decision.intent_id)
        packet = build_context_packet(decision.intent_id, payload, state)
        return {
            "route": decision.to_dict(),
            "case_state": state.to_dict() if state else None,
            "context_packet": packet.to_dict(),
        }

    @app.post("/orchestration/handoff-preview")
    def orchestration_handoff_preview(payload: dict[str, Any]) -> dict[str, Any]:
        decision = route_intent(payload)
        state = _resolve_case_state(case_store, payload, decision.intent_id)
        preview = build_handoff_preview(decision, payload, state)
        return {
            "route": decision.to_dict(),
            "case_state": state.to_dict() if state else None,
            "handoff": preview.to_dict() if preview else None,
        }

    @app.post("/analytics/general/preview")
    def general_analytics_preview(payload: dict[str, Any]) -> dict[str, Any]:
        dataset_path = payload.get("dataset_path")
        if not dataset_path:
            raise HTTPException(status_code=400, detail="dataset_path es obligatorio")
        return preview_dataset_columns(dataset_path)

    @app.post("/agent/plan")
    def plan_agent(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            request = UseCaseRequest(
                institution_type=payload["institution_type"],
                condition_focus=payload["condition_focus"],
                population_scope=payload["population_scope"],
                business_goals=tuple(payload["business_goals"]),
                available_assets=tuple(payload["available_assets"]),
                requested_capabilities=tuple(payload["requested_capabilities"]),
            )
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=f"Campo faltante: {exc.args[0]}") from exc

        plan = agent.plan_request(request)
        return {
            "use_case": asdict(plan.use_case),
            "phases": [asdict(item) for item in plan.phases],
            "selected_subprocesses": [asdict(item) for item in plan.selected_subprocesses],
            "recommended_pipelines": [asdict(item) for item in plan.recommended_pipelines],
            "governance": [asdict(item) for item in plan.governance],
            "implementation_notes": plan.implementation_notes,
            "markdown": plan.to_markdown(),
        }

    @app.post("/pipelines/upload")
    async def upload_pipeline_input(request: Request) -> dict[str, Any]:
        try:
            filename, content, detected_content_type = extract_upload_payload(
                body=await request.body(),
                content_type=request.headers.get("content-type"),
                filename_hint=request.headers.get("x-filename"),
            )
            stored = upload_store.save_upload(
                filename=filename,
                content=content,
                content_type=detected_content_type,
            )
        except (ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return stored.to_dict()

    @app.post("/pipelines/oncology/profile")
    def profile_pipeline(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            resolved = resolve_oncology_input(payload, upload_store)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        result = profile_oncology_rows(resolved.rows, source_label=resolved.source_label)
        return result.to_dict()

    @app.post("/pipelines/oncology/map")
    def map_pipeline(payload: dict[str, Any]) -> dict[str, Any]:
        input_path = payload.get("input_path")
        mapping_path = payload.get("mapping_path")
        output_path = payload.get("output_path")
        if not input_path or not mapping_path or not output_path:
            raise HTTPException(status_code=400, detail="input_path, mapping_path y output_path son obligatorios")
        result = map_oncology_csv(input_path, mapping_path, output_path)
        return result.to_dict()

    @app.post("/pipelines/oncology/entry-flow")
    def entry_flow_pipeline(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            resolved = resolve_oncology_input(payload, upload_store)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        result = analyze_oncology_entry_flow_rows(resolved.rows, source_label=resolved.source_label)
        return result.to_dict()

    @app.post("/pipelines/oncology/financial-impact")
    def financial_impact_pipeline(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            resolved = resolve_oncology_input(payload, upload_store)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        result = analyze_oncology_financial_impact_rows(resolved.rows, source_label=resolved.source_label)
        return result.to_dict()

    @app.post("/analytics/general/train")
    def general_analytics_train(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            request = GeneralAnalyticsRequest(
                dataset_path=payload["dataset_path"],
                target_column=payload["target_column"],
                task_type=payload["task_type"],
                problem_name=payload["problem_name"],
                engine=payload.get("engine", "auto"),
                metric=payload.get("metric"),
                test_size=payload.get("test_size", 0.2),
                random_state=payload.get("random_state", 42),
                categorical_features=tuple(payload.get("categorical_features", [])),
                numeric_features=tuple(payload.get("numeric_features", [])),
                drop_columns=tuple(payload.get("drop_columns", [])),
            )
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=f"Campo faltante: {exc.args[0]}") from exc
        try:
            result = train_general_automl(request)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return result.to_dict()

    @app.post("/analytics/general/report-pack")
    def general_analytics_report_pack(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            request = GeneralAnalyticsRequest(
                dataset_path=payload["dataset_path"],
                target_column=payload["target_column"],
                task_type=payload["task_type"],
                problem_name=payload["problem_name"],
                engine=payload.get("engine", "auto"),
                metric=payload.get("metric"),
                test_size=payload.get("test_size", 0.2),
                random_state=payload.get("random_state", 42),
                categorical_features=tuple(payload.get("categorical_features", [])),
                numeric_features=tuple(payload.get("numeric_features", [])),
                drop_columns=tuple(payload.get("drop_columns", [])),
            )
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=f"Campo faltante: {exc.args[0]}") from exc
        output_dir = payload.get("output_dir")
        if not output_dir:
            raise HTTPException(status_code=400, detail="output_dir es obligatorio")
        try:
            pack = build_general_analytics_report_pack(request, output_dir)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return pack.to_dict()

    @app.post("/analytics/general/predict")
    def general_analytics_predict(payload: dict[str, Any]) -> dict[str, Any]:
        model_joblib_path = payload.get("model_joblib_path")
        input_path = payload.get("input_path")
        output_path = payload.get("output_path")
        if not model_joblib_path or not input_path or not output_path:
            raise HTTPException(status_code=400, detail="model_joblib_path, input_path y output_path son obligatorios")
        try:
            pack = predict_with_general_analytics_pack(model_joblib_path, input_path, output_path)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return pack.to_dict()

    @app.post("/llm/chat")
    def llm_chat(payload: dict[str, Any]) -> dict[str, Any]:
        message = payload.get("message")
        if not message:
            raise HTTPException(status_code=400, detail="message es obligatorio")
        request = OpenRouterChatRequest(
            message=message,
            system_prompt=payload.get("system_prompt"),
            model=payload.get("model"),
            temperature=payload.get("temperature", 0.2),
            max_tokens=payload.get("max_tokens", 700),
            context=payload.get("context"),
        )
        try:
            response = chat_with_openrouter(request)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return response.to_dict()

    return app


def dataclass_to_dict(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return value


def _resolve_case_state(
    case_store: InMemoryCaseMemoryStore,
    payload: dict[str, Any],
    active_intent: str,
) -> Any:
    case_id = payload.get("case_id")
    tenant_id = payload.get("tenant_id", "tenant-demo")
    goal = payload.get("message") or payload.get("problem_name") or payload.get("population_scope")
    if not case_id or not goal:
        return None
    return case_store.get_or_create(
        case_id=case_id,
        tenant_id=tenant_id,
        current_goal=str(goal),
        active_intent=active_intent,
    )
