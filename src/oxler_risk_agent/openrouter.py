from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any
from urllib import error, request


@dataclass(frozen=True)
class OpenRouterChatRequest:
    message: str
    system_prompt: str | None = None
    model: str | None = None
    temperature: float = 0.2
    max_tokens: int = 700
    context: dict[str, Any] | None = None


@dataclass(frozen=True)
class OpenRouterChatResponse:
    model: str
    response_text: str
    request_id: str | None
    usage: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def chat_with_openrouter(payload: OpenRouterChatRequest) -> OpenRouterChatResponse:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY no esta configurada en el entorno")

    model = payload.model or os.getenv("OPENROUTER_MODEL")
    if not model:
        raise RuntimeError("Defina OPENROUTER_MODEL o envie model en la solicitud")

    endpoint = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    referer = os.getenv("OPENROUTER_HTTP_REFERER")
    title = os.getenv("OPENROUTER_APP_TITLE", "Oxlitica")
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-Title"] = title

    body = _build_openrouter_body(payload, model)
    encoded = json.dumps(body).encode("utf-8")
    http_request = request.Request(endpoint, data=encoded, headers=headers, method="POST")

    try:
        with request.urlopen(http_request, timeout=90) as response:
            raw_payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter respondio con error HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"No fue posible conectar con OpenRouter: {exc.reason}") from exc

    choice = ((raw_payload.get("choices") or [{}])[0]).get("message") or {}
    response_text = choice.get("content")
    if not response_text:
        raise RuntimeError("OpenRouter no devolvio contenido en la respuesta")

    return OpenRouterChatResponse(
        model=raw_payload.get("model", model),
        response_text=response_text,
        request_id=raw_payload.get("id"),
        usage=raw_payload.get("usage"),
    )


def _build_openrouter_body(payload: OpenRouterChatRequest, model: str) -> dict[str, Any]:
    messages: list[dict[str, str]] = []
    system_parts = [
        "Eres Oxlitica, el agente autonomo de OxLER para gestion inteligente del riesgo, gestion poblacional y modelacion analitica avanzada en salud.",
        "Responde en espanol claro, institucional y orientado a accion.",
    ]
    if payload.system_prompt:
        system_parts.append(payload.system_prompt.strip())
    messages.append({"role": "system", "content": "\n".join(system_parts)})

    user_content = payload.message.strip()
    if payload.context:
        user_content = f"{user_content}\n\nContexto estructurado:\n{json.dumps(payload.context, ensure_ascii=True, indent=2)}"
    messages.append({"role": "user", "content": user_content})

    return {
        "model": model,
        "messages": messages,
        "temperature": payload.temperature,
        "max_tokens": payload.max_tokens,
    }
