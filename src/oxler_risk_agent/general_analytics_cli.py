from __future__ import annotations

import sys

from .general_analytics import (
    build_general_analytics_report_pack,
    load_general_analytics_request,
    predict_with_general_analytics_pack,
    train_general_automl,
)


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) not in {1, 2, 4}:
        print("Uso: python -m oxler_risk_agent.general_analytics_cli path/to/request.json [output_dir]")
        print("O: python -m oxler_risk_agent.general_analytics_cli predict path/to/model.joblib path/to/input.csv path/to/output.csv")
        return 1
    if len(argv) == 4 and argv[0] == "predict":
        pack = predict_with_general_analytics_pack(argv[1], argv[2], argv[3])
        print(pack.to_dict())
        return 0
    request = load_general_analytics_request(argv[0])
    if len(argv) == 2:
        pack = build_general_analytics_report_pack(request, argv[1])
        print(pack.to_dict())
        return 0
    result = train_general_automl(request)
    print(result.to_markdown())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
