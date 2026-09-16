"""Local regression checks and optional LangSmith dataset upload.

Running this file without an API key performs only local routing checks. It
never uploads student questions. An operator must explicitly set both
LANGSMITH_API_KEY and EXAM_SAATHI_ALLOW_EVAL_UPLOAD=true to create a dataset.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from exam_tools import plan_question


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET = BASE_DIR / "eval_dataset.jsonl"


def load_cases(path: str | Path = DEFAULT_DATASET) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(json.loads(line))
    return cases


def evaluate_routing(path: str | Path = DEFAULT_DATASET) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for case in load_cases(path):
        route = plan_question(case["question"])
        expected = case.get("expected_route", {})
        checks = {key: route.get(key) == value for key, value in expected.items()}
        results.append({"id": case["id"], "passed": all(checks.values()), "checks": checks})
    return {
        "passed": all(item["passed"] for item in results),
        "total": len(results),
        "passed_count": sum(1 for item in results if item["passed"]),
        "results": results,
    }


def upload_cases_to_langsmith(path: str | Path = DEFAULT_DATASET) -> str:
    if os.environ.get("EXAM_SAATHI_ALLOW_EVAL_UPLOAD", "false").casefold() != "true":
        raise RuntimeError("Set EXAM_SAATHI_ALLOW_EVAL_UPLOAD=true to permit dataset upload.")
    if not os.environ.get("LANGSMITH_API_KEY", "").strip():
        raise RuntimeError("LANGSMITH_API_KEY is not configured.")
    from langsmith import Client

    client = Client()
    dataset_name = os.environ.get("LANGSMITH_DATASET", "Exam Saathi v5 Regression")
    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
    except Exception:
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="Curated, non-private Exam Saathi routing regression cases.",
        )
    for case in load_cases(path):
        client.create_example(
            inputs={"question": case["question"]},
            outputs={"expected_route": case.get("expected_route", {})},
            dataset_id=dataset.id,
        )
    return str(dataset.id)


if __name__ == "__main__":
    print(json.dumps(evaluate_routing(), indent=2, ensure_ascii=False))

