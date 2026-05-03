import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from oxler_risk_agent.agent import build_default_agent
from oxler_risk_agent.api.app import build_app
from oxler_risk_agent.contracts import load_oncology_contract
from oxler_risk_agent.general_analytics import (
    GeneralAnalyticsRequest,
    build_general_analytics_report_pack,
    detect_general_analytics_capabilities,
    predict_with_general_analytics_pack,
    preview_dataset_columns,
    train_general_automl,
)
from oxler_risk_agent.models import UseCaseRequest
from oxler_risk_agent.oncology_entry_flow import analyze_oncology_entry_flow
from oxler_risk_agent.oncology_financial_impact import analyze_oncology_financial_impact
from oxler_risk_agent.oncology_ingestion import LocalUploadStore, resolve_oncology_input
from oxler_risk_agent.oncology_mapping import map_oncology_csv
from oxler_risk_agent.oncology_pipeline import profile_oncology_cohort
from oxler_risk_agent.openrouter import OpenRouterChatRequest, _build_openrouter_body
from oxler_risk_agent.context_builder import build_context_packet
from oxler_risk_agent.handoff_engine import build_handoff_preview
from oxler_risk_agent.intent_router import route_intent
from oxler_risk_agent.tool_registry import TOOL_REGISTRY
from fastapi.testclient import TestClient


class RiskAnalyticsAgentTests(unittest.TestCase):
    def test_catalog_contains_all_eje1_subprocesses(self) -> None:
        agent = build_default_agent()
        self.assertEqual(sorted(agent.catalog.keys()), ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7"])

    def test_plan_for_institutional_client_includes_finance_and_monitoring(self) -> None:
        request = UseCaseRequest(
            institution_type="EPS",
            condition_focus="oncologia",
            population_scope="cohorte regional de cancer de mama",
            business_goals=("reducir tiempos de ingreso", "mejorar red", "medir impacto financiero"),
            available_assets=("RIPS", "autorizaciones", "costos", "facturacion"),
            requested_capabilities=("analitica de puertas de entrada", "KPIs de enrutamiento", "simulacion financiera"),
        )
        plan = build_default_agent().plan_request(request)
        selected_ids = [item.identifier for item in plan.selected_subprocesses]
        self.assertIn("1.2", selected_ids)
        self.assertIn("1.4", selected_ids)
        self.assertIn("1.6", selected_ids)
        self.assertTrue(any(pipeline.name == "Financial Impact Simulator" for pipeline in plan.recommended_pipelines))

    def test_oncology_contract_has_required_domains(self) -> None:
        contract = load_oncology_contract()
        self.assertEqual(
            contract["required_domains"],
            ["cohort", "clinical", "operations", "finance", "network"],
        )

    def test_profile_oncology_cohort_returns_summary(self) -> None:
        sample = Path("examples/oncology_sample_cohort.csv")
        result = profile_oncology_cohort(str(sample))
        self.assertEqual(result.records, 6)
        self.assertEqual(result.unique_patients, 6)
        self.assertTrue(result.top_tumor_types)
        self.assertIn("total_cost", result.cost_metrics)

    def test_resolve_oncology_input_supports_inline_records(self) -> None:
        with TemporaryDirectory() as temp_dir:
            resolved = resolve_oncology_input(
                {
                    "records": [
                        {
                            "patient_id": "P001",
                            "sex": "F",
                            "region": "Bogota",
                            "tumor_type": "Cancer de mama",
                        }
                    ]
                },
                LocalUploadStore(temp_dir),
            )
        self.assertEqual(resolved.input_mode, "records")
        self.assertEqual(resolved.source_label, "inline_records")
        self.assertEqual(resolved.rows[0]["patient_id"], "P001")

    def test_upload_store_persists_and_resolves_csv_file(self) -> None:
        sample = Path("examples/oncology_sample_cohort.csv").read_bytes()
        with TemporaryDirectory() as temp_dir:
            store = LocalUploadStore(temp_dir)
            stored = store.save_upload(filename="cohorte.csv", content=sample, content_type="text/csv")
            resolved = store.resolve_upload(stored.file_id)
            self.assertEqual(resolved.file_id, stored.file_id)
            self.assertTrue(Path(resolved.stored_path).exists())

    def test_upload_and_profile_endpoint_support_file_id_flow(self) -> None:
        client = TestClient(build_app())
        sample = Path("examples/oncology_sample_cohort.csv").read_bytes()
        boundary = "BoundaryOxlitica"
        body = (
            b"--BoundaryOxlitica\r\n"
            b'Content-Disposition: form-data; name="file"; filename="cohorte.csv"\r\n'
            b"Content-Type: text/csv\r\n\r\n"
            + sample
            + b"\r\n--BoundaryOxlitica--\r\n"
        )
        upload_response = client.post(
            "/pipelines/upload",
            content=body,
            headers={"content-type": f"multipart/form-data; boundary={boundary}"},
        )
        self.assertEqual(upload_response.status_code, 200)
        upload_payload = upload_response.json()
        self.assertIn("file_id", upload_payload)

        profile_response = client.post(
            "/pipelines/oncology/profile",
            json={"file_id": upload_payload["file_id"]},
        )
        self.assertEqual(profile_response.status_code, 200)
        profile_payload = profile_response.json()
        self.assertEqual(profile_payload["records"], 6)
        self.assertTrue(profile_payload["input_path"].startswith("upload:"))

    def test_entry_flow_endpoint_supports_inline_records(self) -> None:
        client = TestClient(build_app())
        response = client.post(
            "/pipelines/oncology/entry-flow",
            json={
                "records": [
                    {
                        "patient_id": "P001",
                        "sex": "F",
                        "region": "Bogota",
                        "tumor_type": "Cancer de mama",
                        "first_suspicion_date": "2025-01-01",
                        "first_referral_date": "2025-01-10",
                        "treatment_start_date": "2025-01-20",
                        "authorization_status": "Aprobada",
                        "origin_provider": "Clinica Norte",
                    }
                ]
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["patients_with_treatment"], 1)
        self.assertEqual(payload["input_path"], "inline_records")

    def test_map_oncology_csv_normalizes_source_columns(self) -> None:
        source = Path("examples/oncology_raw_source.csv")
        mapping = Path("examples/oncology_source_mapping.json")
        output = Path("outputs/test_oncology_mapped.csv")
        result = map_oncology_csv(str(source), str(mapping), str(output))
        self.assertEqual(result.records_read, 3)
        self.assertEqual(result.records_written, 3)
        self.assertFalse(result.missing_required_sources)
        mapped_rows = output.read_text().splitlines()
        self.assertIn("patient_id,sex,birth_date,region,tumor_type", mapped_rows[0])
        self.assertIn("RAW001,F,1977-03-11,Bogota,Cancer de mama", mapped_rows[1])

    def test_entry_flow_analysis_returns_funnel_and_anomalies(self) -> None:
        sample = Path("examples/oncology_sample_cohort.csv")
        result = analyze_oncology_entry_flow(str(sample))
        self.assertEqual(result.total_records, 6)
        self.assertEqual(result.patients_with_suspicion, 6)
        self.assertEqual(result.patients_with_referral, 6)
        self.assertEqual(result.patients_with_treatment, 6)
        self.assertIn("referral_from_suspicion_rate", result.funnel_metrics)
        self.assertTrue(any("autorizacion" in item for item in result.anomalies))

    def test_financial_impact_analysis_returns_savings_and_findings(self) -> None:
        sample = Path("examples/oncology_sample_cohort.csv")
        result = analyze_oncology_financial_impact(str(sample))
        self.assertEqual(result.total_records, 6)
        self.assertGreater(result.total_cost, 0)
        self.assertIn("base_case_total_savings", result.scenario_savings)
        self.assertTrue(result.findings)

    def test_general_analytics_capabilities_report_missing_sklearn(self) -> None:
        capabilities = detect_general_analytics_capabilities()
        self.assertTrue(capabilities["pandas"])
        self.assertIn("sklearn", capabilities)

    def test_general_analytics_preview_reads_dataset(self) -> None:
        preview = preview_dataset_columns("examples/general_analytics/churn_risk_sample.csv")
        self.assertEqual(preview["row_count"], 12)
        self.assertIn("high_risk_flag", preview["columns"])

    def test_general_analytics_preview_reads_xlsx_dataset(self) -> None:
        capabilities = detect_general_analytics_capabilities()
        if not capabilities.get("openpyxl"):
            self.skipTest("openpyxl no disponible en el entorno")
        preview = preview_dataset_columns("examples/general_analytics/churn_risk_sample.xlsx")
        self.assertEqual(preview["row_count"], 12)
        self.assertIn("high_risk_flag", preview["columns"])

    def test_general_analytics_training_requires_sklearn(self) -> None:
        request = GeneralAnalyticsRequest(
            dataset_path="examples/general_analytics/churn_risk_sample.csv",
            target_column="high_risk_flag",
            task_type="classification",
            problem_name="Prediccion de riesgo",
            drop_columns=("patient_id",),
        )
        capabilities = detect_general_analytics_capabilities()
        if capabilities.get("sklearn"):
            result = train_general_automl(request)
            self.assertEqual(result.engine_used, "sklearn")
            self.assertTrue(result.leaderboard)
        else:
            with self.assertRaises(RuntimeError):
                train_general_automl(request)

    def test_general_analytics_report_pack_builds_artifacts(self) -> None:
        capabilities = detect_general_analytics_capabilities()
        if not capabilities.get("sklearn"):
            self.skipTest("scikit-learn no disponible en el entorno")
        request = GeneralAnalyticsRequest(
            dataset_path="examples/general_analytics/churn_risk_sample.csv",
            target_column="high_risk_flag",
            task_type="classification",
            problem_name="Reporte de riesgo",
            drop_columns=("patient_id",),
        )
        output_dir = "outputs/general_analytics_report_pack"
        pack = build_general_analytics_report_pack(request, output_dir)
        self.assertEqual(pack.summary["artifact_count"], 5)
        self.assertTrue(Path(pack.result_json_path).exists())
        self.assertTrue(Path(pack.result_markdown_path).exists())
        self.assertTrue(Path(pack.request_json_path).exists())
        self.assertTrue(Path(pack.manifest_json_path).exists())
        self.assertTrue(Path(pack.model_joblib_path).exists())

    def test_general_analytics_prediction_pack_scores_rows(self) -> None:
        capabilities = detect_general_analytics_capabilities()
        if not capabilities.get("sklearn"):
            self.skipTest("scikit-learn no disponible en el entorno")
        request = GeneralAnalyticsRequest(
            dataset_path="examples/general_analytics/churn_risk_sample.csv",
            target_column="high_risk_flag",
            task_type="classification",
            problem_name="Prediccion de riesgo",
            drop_columns=("patient_id",),
        )
        pack = build_general_analytics_report_pack(request, "outputs/general_analytics_predict_pack")
        prediction_pack = predict_with_general_analytics_pack(
            pack.model_joblib_path,
            "examples/general_analytics/churn_risk_sample.csv",
            "outputs/general_analytics_predictions.csv",
        )
        self.assertEqual(prediction_pack.prediction_count, 12)
        self.assertIn("prediction", prediction_pack.columns)
        self.assertTrue(Path(prediction_pack.output_path).exists())

    def test_general_analytics_prediction_pack_writes_xlsx(self) -> None:
        capabilities = detect_general_analytics_capabilities()
        if not capabilities.get("sklearn") or not capabilities.get("openpyxl"):
            self.skipTest("Dependencias de ML/XLSX no disponibles en el entorno")
        request = GeneralAnalyticsRequest(
            dataset_path="examples/general_analytics/churn_risk_sample.xlsx",
            target_column="high_risk_flag",
            task_type="classification",
            problem_name="Prediccion de riesgo xlsx",
            drop_columns=("patient_id",),
        )
        pack = build_general_analytics_report_pack(request, "outputs/general_analytics_predict_pack_xlsx")
        prediction_pack = predict_with_general_analytics_pack(
            pack.model_joblib_path,
            "examples/general_analytics/churn_risk_sample.xlsx",
            "outputs/general_analytics_predictions.xlsx",
        )
        self.assertEqual(prediction_pack.prediction_count, 12)
        self.assertTrue(Path(prediction_pack.output_path).exists())

    def test_openrouter_body_includes_context_and_model(self) -> None:
        payload = OpenRouterChatRequest(
            message="Resume esta cohorte",
            system_prompt="Prioriza accion institucional",
            model="openai/test-model",
            context={"cohort": "oncologia", "records": 42},
        )
        body = _build_openrouter_body(payload, "openai/test-model")
        self.assertEqual(body["model"], "openai/test-model")
        self.assertEqual(len(body["messages"]), 2)
        self.assertIn("Oxlitica", body["messages"][0]["content"])
        self.assertIn("Prioriza accion institucional", body["messages"][0]["content"])
        self.assertIn("Contexto estructurado", body["messages"][1]["content"])
        self.assertIn('"records": 42', body["messages"][1]["content"])

    def test_intent_router_detects_model_factory_cases(self) -> None:
        route = route_intent(
            {
                "message": "Necesito entrenar un modelo de clasificacion para alto riesgo",
                "dataset_path": "examples/general_analytics/churn_risk_sample.csv",
                "target_column": "high_risk_flag",
            }
        )
        self.assertEqual(route.intent_id, "model_factory")
        self.assertIn("general_analytics_train", route.preferred_tools)

    def test_context_builder_returns_operational_context(self) -> None:
        packet = build_context_packet(
            "operational_friction",
            {
                "institution_type": "EPS",
                "condition_focus": "oncologia",
                "population_scope": "cohorte con demoras en autorizacion",
            },
        )
        self.assertEqual(packet.context_type, "operational_friction_context")
        self.assertIn("institution_type", packet.facts)
        self.assertTrue(packet.guidance)

    def test_handoff_preview_targets_pegaxus_when_heor_intent(self) -> None:
        route = route_intent({"message": "Necesito un caso HEOR y ROI para esta cohorte"})
        preview = build_handoff_preview(route, {"condition_focus": "oncologia", "case_id": "case-1"})
        self.assertIsNotNone(preview)
        assert preview is not None
        self.assertEqual(preview.target_agent, "pegaxus")
        self.assertEqual(preview.payload["case_id"], "case-1")

    def test_tool_registry_includes_swarm_handoff(self) -> None:
        tool_ids = [item.identifier for item in TOOL_REGISTRY]
        self.assertIn("swarm_handoff", tool_ids)


if __name__ == "__main__":
    unittest.main()
