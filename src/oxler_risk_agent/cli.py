from __future__ import annotations

import json
import sys
from pathlib import Path

from .agent import build_default_agent
from .models import UseCaseRequest


def load_request(path: str) -> UseCaseRequest:
    payload = json.loads(Path(path).read_text())
    return UseCaseRequest(
        institution_type=payload["institution_type"],
        condition_focus=payload["condition_focus"],
        population_scope=payload["population_scope"],
        business_goals=tuple(payload["business_goals"]),
        available_assets=tuple(payload["available_assets"]),
        requested_capabilities=tuple(payload["requested_capabilities"]),
    )


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) != 1:
        print("Uso: python -m oxler_risk_agent.cli path/to/request.json")
        return 1

    request = load_request(argv[0])
    plan = build_default_agent().plan_request(request)
    print(plan.to_markdown())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
