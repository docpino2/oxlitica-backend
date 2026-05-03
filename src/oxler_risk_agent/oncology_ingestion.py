from __future__ import annotations

import base64
import csv
import json
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


SUPPORTED_UPLOAD_SUFFIXES = {".csv", ".xlsx"}


@dataclass(frozen=True)
class StoredUpload:
    file_id: str
    filename: str
    stored_path: str
    content_type: str
    size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "stored_path": self.stored_path,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True)
class ResolvedOncologyInput:
    source_label: str
    input_mode: str
    rows: list[dict[str, str]]
    resolved_path: str | None = None
    file_id: str | None = None


class LocalUploadStore:
    def __init__(self, base_dir: str | None = None) -> None:
        root = Path(base_dir) if base_dir else Path(tempfile.gettempdir()) / "oxlitica_uploads"
        root.mkdir(parents=True, exist_ok=True)
        self.base_dir = root

    def save_upload(self, *, filename: str, content: bytes, content_type: str | None = None) -> StoredUpload:
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_UPLOAD_SUFFIXES:
            raise ValueError("Solo se soportan archivos csv y xlsx para el pipeline oncologico.")
        file_id = f"upload_{uuid.uuid4().hex[:12]}"
        stored_path = self.base_dir / f"{file_id}{suffix}"
        stored_path.write_bytes(content)
        metadata = StoredUpload(
            file_id=file_id,
            filename=filename,
            stored_path=str(stored_path),
            content_type=content_type or _infer_content_type(suffix),
            size_bytes=len(content),
        )
        (self.base_dir / f"{file_id}.json").write_text(
            json.dumps(metadata.to_dict(), ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        return metadata

    def resolve_upload(self, file_id: str) -> StoredUpload:
        metadata_path = self.base_dir / f"{file_id}.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"No existe un upload registrado con file_id={file_id}")
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        stored = StoredUpload(**data)
        if not Path(stored.stored_path).exists():
            raise FileNotFoundError(f"El archivo asociado a file_id={file_id} ya no esta disponible")
        return stored


def extract_upload_payload(
    *,
    body: bytes,
    content_type: str | None,
    filename_hint: str | None = None,
) -> tuple[str, bytes, str]:
    normalized = (content_type or "").lower()
    if normalized.startswith("multipart/form-data"):
        return _parse_multipart_upload(body, content_type or "")
    if normalized.startswith("application/json"):
        payload = json.loads(body.decode("utf-8"))
        filename = str(payload.get("filename") or filename_hint or "upload.csv")
        encoded = payload.get("content_base64")
        if not encoded:
            raise ValueError("content_base64 es obligatorio cuando upload usa application/json")
        content = base64.b64decode(encoded)
        return filename, content, payload.get("content_type") or _infer_content_type(Path(filename).suffix.lower())
    if not body:
        raise ValueError("El cuerpo del upload esta vacio")
    filename = filename_hint or _default_filename_for_content_type(normalized)
    return filename, body, normalized or _infer_content_type(Path(filename).suffix.lower())


def resolve_oncology_input(
    payload: dict[str, Any],
    upload_store: LocalUploadStore,
) -> ResolvedOncologyInput:
    has_input_path = bool(payload.get("input_path"))
    has_file_id = bool(payload.get("file_id"))
    has_records = "records" in payload and payload.get("records") is not None

    provided = sum([has_input_path, has_file_id, has_records])
    if provided == 0:
        raise ValueError("Debe enviar input_path, file_id o records para el pipeline oncologico.")
    if provided > 1:
        raise ValueError("Envie solo una fuente de entrada entre input_path, file_id o records.")

    if has_input_path:
        input_path = str(payload["input_path"])
        return ResolvedOncologyInput(
            source_label=input_path,
            input_mode="input_path",
            rows=load_tabular_records(input_path),
            resolved_path=input_path,
        )

    if has_file_id:
        stored = upload_store.resolve_upload(str(payload["file_id"]))
        return ResolvedOncologyInput(
            source_label=f"upload:{stored.file_id}:{stored.filename}",
            input_mode="file_id",
            rows=load_tabular_records(stored.stored_path),
            resolved_path=stored.stored_path,
            file_id=stored.file_id,
        )

    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("records debe ser una lista de objetos.")
    return ResolvedOncologyInput(
        source_label="inline_records",
        input_mode="records",
        rows=normalize_inline_records(records),
    )


def load_tabular_records(path: str) -> list[dict[str, str]]:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        with file_path.open(newline="", encoding="utf-8") as handle:
            return [normalize_row(item) for item in csv.DictReader(handle)]
    if suffix == ".xlsx":
        frame = pd.read_excel(file_path)
        return [normalize_row(item) for item in frame.fillna("").to_dict(orient="records")]
    raise ValueError("El pipeline oncologico soporta archivos csv y xlsx.")


def normalize_inline_records(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("Cada elemento de records debe ser un objeto con llaves tabulares.")
        normalized.append(normalize_row(item))
    return normalized


def normalize_row(row: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in row.items():
        if value is None:
            normalized[str(key)] = ""
        else:
            normalized[str(key)] = str(value).strip()
    return normalized


def _parse_multipart_upload(body: bytes, content_type: str) -> tuple[str, bytes, str]:
    boundary_token = "boundary="
    if boundary_token not in content_type:
        raise ValueError("No se encontro boundary en multipart/form-data")
    boundary = content_type.split(boundary_token, 1)[1].strip().strip('"')
    boundary_bytes = f"--{boundary}".encode("utf-8")
    for part in body.split(boundary_bytes):
        chunk = part.strip()
        if not chunk or chunk in {b"--", b""}:
            continue
        if chunk.startswith(b"--"):
            chunk = chunk[2:]
        chunk = chunk.strip(b"\r\n")
        header_blob, separator, payload = chunk.partition(b"\r\n\r\n")
        if not separator:
            continue
        header_lines = header_blob.decode("utf-8", errors="ignore").split("\r\n")
        headers: dict[str, str] = {}
        for line in header_lines:
            if ":" in line:
                name, value = line.split(":", 1)
                headers[name.strip().lower()] = value.strip()
        disposition = headers.get("content-disposition", "")
        if "filename=" not in disposition:
            continue
        filename = _extract_disposition_value(disposition, "filename") or "upload.csv"
        part_content_type = headers.get("content-type") or _infer_content_type(Path(filename).suffix.lower())
        content = payload.rstrip(b"\r\n")
        return filename, content, part_content_type
    raise ValueError("No se encontro un archivo en el multipart upload")


def _extract_disposition_value(disposition: str, key: str) -> str | None:
    needle = f"{key}="
    for token in disposition.split(";"):
        piece = token.strip()
        if piece.startswith(needle):
            return piece.split("=", 1)[1].strip().strip('"')
    return None


def _default_filename_for_content_type(content_type: str) -> str:
    if "sheet" in content_type or "excel" in content_type:
        return "upload.xlsx"
    return "upload.csv"


def _infer_content_type(suffix: str) -> str:
    if suffix == ".xlsx":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return "text/csv"
