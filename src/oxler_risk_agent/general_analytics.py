from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import pandas as pd

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")


TaskType = Literal["classification", "regression"]
EngineType = Literal["auto", "sklearn"]


@dataclass(frozen=True)
class GeneralAnalyticsRequest:
    dataset_path: str
    target_column: str
    task_type: TaskType
    problem_name: str
    engine: EngineType = "auto"
    metric: str | None = None
    test_size: float = 0.2
    random_state: int = 42
    categorical_features: tuple[str, ...] = ()
    numeric_features: tuple[str, ...] = ()
    drop_columns: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateModelResult:
    model_name: str
    metric_name: str
    validation_score: float


@dataclass(frozen=True)
class GeneralAnalyticsResult:
    request: GeneralAnalyticsRequest
    engine_used: str
    metric_name: str
    best_model: str
    best_score: float
    leaderboard: list[CandidateModelResult]
    training_rows: int
    test_rows: int
    feature_columns: tuple[str, ...]
    class_distribution: dict[str, int] | None
    target_summary: dict[str, float] | None
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": asdict(self.request),
            "engine_used": self.engine_used,
            "metric_name": self.metric_name,
            "best_model": self.best_model,
            "best_score": self.best_score,
            "leaderboard": [asdict(item) for item in self.leaderboard],
            "training_rows": self.training_rows,
            "test_rows": self.test_rows,
            "feature_columns": list(self.feature_columns),
            "class_distribution": self.class_distribution,
            "target_summary": self.target_summary,
            "notes": self.notes,
        }

    def to_markdown(self) -> str:
        lines = [
            "# General Analytics AutoML Result",
            "",
            f"- Problema: {self.request.problem_name}",
            f"- Tipo de tarea: {self.request.task_type}",
            f"- Dataset: {self.request.dataset_path}",
            f"- Engine: {self.engine_used}",
            f"- Mejor modelo: {self.best_model}",
            f"- {self.metric_name}: {self.best_score:.4f}",
            f"- Filas train: {self.training_rows}",
            f"- Filas test: {self.test_rows}",
            "",
            "## Leaderboard",
        ]
        for item in self.leaderboard:
            lines.append(f"- {item.model_name}: {item.metric_name}={item.validation_score:.4f}")
        if self.class_distribution:
            lines.append("")
            lines.append("## Class Distribution")
            for key, value in self.class_distribution.items():
                lines.append(f"- {key}: {value}")
        if self.target_summary:
            lines.append("")
            lines.append("## Target Summary")
            for key, value in self.target_summary.items():
                lines.append(f"- {key}: {value:.4f}")
        lines.append("")
        lines.append("## Notes")
        for note in self.notes:
            lines.append(f"- {note}")
        return "\n".join(lines)


@dataclass(frozen=True)
class GeneralAnalyticsReportPack:
    output_dir: str
    result_json_path: str
    result_markdown_path: str
    request_json_path: str
    manifest_json_path: str
    model_joblib_path: str
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_dir": self.output_dir,
            "result_json_path": self.result_json_path,
            "result_markdown_path": self.result_markdown_path,
            "request_json_path": self.request_json_path,
            "manifest_json_path": self.manifest_json_path,
            "model_joblib_path": self.model_joblib_path,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class GeneralAnalyticsPredictionPack:
    input_path: str
    output_path: str
    prediction_count: int
    columns: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_path": self.input_path,
            "output_path": self.output_path,
            "prediction_count": self.prediction_count,
            "columns": list(self.columns),
        }


@dataclass(frozen=True)
class _TrainingBundle:
    result: GeneralAnalyticsResult
    fitted_pipeline: Any


def train_general_automl(request: GeneralAnalyticsRequest) -> GeneralAnalyticsResult:
    if request.engine not in {"auto", "sklearn"}:
        raise ValueError(f"Engine no soportado: {request.engine}")
    engine = "sklearn"
    if engine == "sklearn":
        return _train_with_sklearn(request)
    raise ValueError("No se pudo resolver un engine de modelado")


def load_general_analytics_request(path: str) -> GeneralAnalyticsRequest:
    payload = json.loads(Path(path).read_text())
    return GeneralAnalyticsRequest(
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


def detect_general_analytics_capabilities() -> dict[str, Any]:
    capabilities: dict[str, Any] = {"pandas": True, "numpy": True}
    try:
        import sklearn  # noqa: F401
        capabilities["sklearn"] = True
    except ModuleNotFoundError:
        capabilities["sklearn"] = False
        capabilities["sklearn_install_hint"] = "pip install -e .[ml]"
    try:
        import openpyxl  # noqa: F401
        capabilities["openpyxl"] = True
    except ModuleNotFoundError:
        capabilities["openpyxl"] = False
        capabilities["openpyxl_install_hint"] = "pip install -e .[ml]"
    return capabilities


def build_general_analytics_report_pack(
    request: GeneralAnalyticsRequest,
    output_dir: str,
) -> GeneralAnalyticsReportPack:
    bundle = _train_general_automl_bundle(request)
    result = bundle.result
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    result_json_path = output_path / "result.json"
    result_markdown_path = output_path / "result.md"
    request_json_path = output_path / "request.json"
    manifest_json_path = output_path / "manifest.json"
    model_joblib_path = output_path / "model.joblib"

    result_json_path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=True))
    result_markdown_path.write_text(result.to_markdown(), encoding="utf-8")
    request_json_path.write_text(json.dumps(asdict(request), indent=2, ensure_ascii=True))
    _save_model_joblib(bundle.fitted_pipeline, model_joblib_path)

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "problem_name": request.problem_name,
        "task_type": request.task_type,
        "dataset_path": request.dataset_path,
        "target_column": request.target_column,
        "engine_used": result.engine_used,
        "best_model": result.best_model,
        "metric_name": result.metric_name,
        "best_score": result.best_score,
        "artifacts": {
            "result_json": str(result_json_path),
            "result_markdown": str(result_markdown_path),
            "request_json": str(request_json_path),
            "model_joblib": str(model_joblib_path),
        },
    }
    manifest_json_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True))

    summary = {
        "problem_name": request.problem_name,
        "best_model": result.best_model,
        "metric_name": result.metric_name,
        "best_score": result.best_score,
        "artifact_count": 5,
    }
    return GeneralAnalyticsReportPack(
        output_dir=str(output_path),
        result_json_path=str(result_json_path),
        result_markdown_path=str(result_markdown_path),
        request_json_path=str(request_json_path),
        manifest_json_path=str(manifest_json_path),
        model_joblib_path=str(model_joblib_path),
        summary=summary,
    )


def predict_with_general_analytics_pack(
    model_joblib_path: str,
    input_path: str,
    output_path: str,
) -> GeneralAnalyticsPredictionPack:
    model = _load_model_joblib(Path(model_joblib_path))
    frame = _load_dataframe(input_path)
    predictions = model.predict(frame)
    output_frame = frame.copy()
    output_frame["prediction"] = predictions
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(frame)
        if len(probabilities.shape) == 2:
            if probabilities.shape[1] == 2:
                output_frame["prediction_score"] = probabilities[:, 1]
            else:
                output_frame["prediction_score_max"] = probabilities.max(axis=1)
    _write_dataframe(output_frame, output_path)
    return GeneralAnalyticsPredictionPack(
        input_path=input_path,
        output_path=output_path,
        prediction_count=len(output_frame),
        columns=tuple(output_frame.columns),
    )


def preview_dataset_columns(path: str, limit: int = 10) -> dict[str, Any]:
    frame = _load_dataframe(path)
    headers = list(frame.columns)
    sample = frame.head(limit).fillna("").to_dict(orient="records")
    return {
        "path": path,
        "columns": headers,
        "row_count": len(frame),
        "sample_rows": sample,
    }


def _train_with_sklearn(request: GeneralAnalyticsRequest) -> GeneralAnalyticsResult:
    return _train_general_automl_bundle(request).result


def _train_general_automl_bundle(request: GeneralAnalyticsRequest) -> _TrainingBundle:
    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor, RandomForestClassifier, RandomForestRegressor
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression, Ridge
        from sklearn.metrics import (
            accuracy_score,
            f1_score,
            mean_absolute_error,
            mean_squared_error,
            r2_score,
            roc_auc_score,
        )
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
        from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "El engine de modelado requiere scikit-learn. Instale el extra con: pip install -e .[ml]"
        ) from exc

    frame = _load_dataframe(request.dataset_path)
    if request.target_column not in frame.columns:
        raise ValueError(f"No existe la columna objetivo: {request.target_column}")

    if request.drop_columns:
        existing_drop = [column for column in request.drop_columns if column in frame.columns and column != request.target_column]
        if existing_drop:
            frame = frame.drop(columns=existing_drop)

    target = frame[request.target_column]
    features = frame.drop(columns=[request.target_column])
    categorical_features, numeric_features = _resolve_feature_types(features, request)

    X_train, X_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=request.test_size,
        random_state=request.random_state,
        stratify=target if request.task_type == "classification" and target.nunique() > 1 else None,
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_features,
            ),
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ],
    )

    metric_name = request.metric or _default_metric_for_task(request.task_type, target.nunique())
    candidates = _build_candidate_models(request.task_type, target.nunique())
    leaderboard: list[CandidateModelResult] = []
    best_payload: tuple[str, float, Any] | None = None
    for model_name, estimator in candidates:
        pipeline = Pipeline(steps=[("preprocess", preprocessor), ("model", estimator)])
        pipeline.fit(X_train, y_train)
        score = _evaluate_pipeline(
            pipeline=pipeline,
            task_type=request.task_type,
            metric_name=metric_name,
            X_test=X_test,
            y_test=y_test,
            y_train=y_train,
            accuracy_score=accuracy_score,
            f1_score=f1_score,
            roc_auc_score=roc_auc_score,
            mean_absolute_error=mean_absolute_error,
            mean_squared_error=mean_squared_error,
            r2_score=r2_score,
        )
        leaderboard.append(CandidateModelResult(model_name=model_name, metric_name=metric_name, validation_score=score))
        if best_payload is None or score > best_payload[1]:
            best_payload = (model_name, score, pipeline)

    leaderboard.sort(key=lambda item: item.validation_score, reverse=True)
    class_distribution = None
    target_summary = None
    if request.task_type == "classification":
        class_distribution = {str(key): int(value) for key, value in target.value_counts().to_dict().items()}
    else:
        target_summary = {
            "mean": float(target.mean()),
            "min": float(target.min()),
            "max": float(target.max()),
        }

    notes = [
        "El pipeline usa preprocesamiento automatico con imputacion y encoding para variables categoricas.",
        "El leaderboard actual compara un conjunto base de modelos de sklearn; puede ampliarse para casos especificos.",
        "Para uso institucional conviene congelar el mejor modelo y versionar datos, metricas y parametros.",
    ]
    if request.task_type == "classification" and target.nunique() > 2 and metric_name == "roc_auc":
        notes.append("En clasificacion multiclase se usa roc_auc_ovr para comparar candidatos.")

    assert best_payload is not None
    result = GeneralAnalyticsResult(
        request=request,
        engine_used="sklearn",
        metric_name=metric_name,
        best_model=best_payload[0],
        best_score=best_payload[1],
        leaderboard=leaderboard,
        training_rows=len(X_train),
        test_rows=len(X_test),
        feature_columns=tuple(features.columns),
        class_distribution=class_distribution,
        target_summary=target_summary,
        notes=notes,
    )
    return _TrainingBundle(result=result, fitted_pipeline=best_payload[2])


def _resolve_feature_types(features: pd.DataFrame, request: GeneralAnalyticsRequest) -> tuple[list[str], list[str]]:
    if request.categorical_features or request.numeric_features:
        categorical = [column for column in request.categorical_features if column in features.columns]
        numeric = [column for column in request.numeric_features if column in features.columns]
        remaining = [column for column in features.columns if column not in categorical and column not in numeric]
        for column in remaining:
            if pd.api.types.is_numeric_dtype(features[column]):
                numeric.append(column)
            else:
                categorical.append(column)
        return categorical, numeric

    categorical = [column for column in features.columns if not pd.api.types.is_numeric_dtype(features[column])]
    numeric = [column for column in features.columns if pd.api.types.is_numeric_dtype(features[column])]
    return categorical, numeric


def _default_metric_for_task(task_type: TaskType, class_count: int) -> str:
    if task_type == "classification":
        return "roc_auc" if class_count == 2 else "f1_macro"
    return "neg_rmse"


def _build_candidate_models(task_type: TaskType, class_count: int) -> list[tuple[str, Any]]:
    from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor, RandomForestClassifier, RandomForestRegressor
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

    if task_type == "classification":
        logistic_kwargs = {"max_iter": 2000}
        if class_count > 2:
            logistic_kwargs["multi_class"] = "auto"
        return [
            ("logistic_regression", LogisticRegression(**logistic_kwargs)),
            ("random_forest_classifier", RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=1)),
            ("extra_trees_classifier", ExtraTreesClassifier(n_estimators=300, random_state=42, n_jobs=1)),
            ("hist_gradient_boosting_classifier", HistGradientBoostingClassifier(random_state=42)),
        ]
    return [
        ("ridge_regression", Ridge()),
        ("random_forest_regressor", RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=1)),
        ("extra_trees_regressor", ExtraTreesRegressor(n_estimators=300, random_state=42, n_jobs=1)),
        ("hist_gradient_boosting_regressor", HistGradientBoostingRegressor(random_state=42)),
    ]


def _evaluate_pipeline(
    pipeline: Any,
    task_type: TaskType,
    metric_name: str,
    X_test: Any,
    y_test: Any,
    y_train: Any,
    accuracy_score: Any,
    f1_score: Any,
    roc_auc_score: Any,
    mean_absolute_error: Any,
    mean_squared_error: Any,
    r2_score: Any,
) -> float:
    predictions = pipeline.predict(X_test)
    if task_type == "classification":
        if metric_name == "accuracy":
            return float(accuracy_score(y_test, predictions))
        if metric_name == "f1_macro":
            return float(f1_score(y_test, predictions, average="macro"))
        if metric_name == "roc_auc":
            if len(set(y_train)) > 2:
                probabilities = pipeline.predict_proba(X_test)
                return float(roc_auc_score(y_test, probabilities, multi_class="ovr"))
            probabilities = pipeline.predict_proba(X_test)[:, 1]
            return float(roc_auc_score(y_test, probabilities))
        raise ValueError(f"Metrica de clasificacion no soportada: {metric_name}")

    if metric_name == "r2":
        return float(r2_score(y_test, predictions))
    if metric_name == "neg_mae":
        return -float(mean_absolute_error(y_test, predictions))
    if metric_name == "neg_rmse":
        return -float(mean_squared_error(y_test, predictions, squared=False))
    raise ValueError(f"Metrica de regresion no soportada: {metric_name}")


def _save_model_joblib(model: Any, path: Path) -> None:
    try:
        import joblib
    except ModuleNotFoundError as exc:
        raise RuntimeError("joblib es requerido para serializar el modelo entrenado") from exc
    joblib.dump(model, path)


def _load_model_joblib(path: Path) -> Any:
    try:
        import joblib
    except ModuleNotFoundError as exc:
        raise RuntimeError("joblib es requerido para cargar el modelo entrenado") from exc
    return joblib.load(path)


def _load_dataframe(path: str) -> pd.DataFrame:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(file_path)
    if suffix == ".xlsx":
        try:
            return pd.read_excel(file_path)
        except ImportError as exc:
            raise RuntimeError(
                "Para leer archivos .xlsx se requiere openpyxl. Instale el extra con: pip install -e .[ml]"
            ) from exc
    raise ValueError("Formato no soportado. Use .csv o .xlsx")


def _write_dataframe(frame: pd.DataFrame, output_path: str) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    suffix = output.suffix.lower()
    if suffix == ".csv":
        frame.to_csv(output, index=False)
        return
    if suffix == ".xlsx":
        try:
            frame.to_excel(output, index=False)
            return
        except ImportError as exc:
            raise RuntimeError(
                "Para escribir archivos .xlsx se requiere openpyxl. Instale el extra con: pip install -e .[ml]"
            ) from exc
    raise ValueError("Formato de salida no soportado. Use .csv o .xlsx")
