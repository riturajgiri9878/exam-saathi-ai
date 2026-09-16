"""Deterministic quality gate used after the model-based answer review."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class VerificationReport:
    passed: bool
    score: int
    issues: list[str]
    retryable: bool
    human_review_required: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_answer(answer: dict[str, Any], route: dict[str, Any]) -> VerificationReport:
    issues: list[str] = []
    status = str(answer.get("verification_status", "REVIEW_NEEDED"))
    confidence = int(answer.get("confidence", 0) or 0)

    if not str(answer.get("direct_answer", "")).strip():
        issues.append("Direct answer is missing")
    if not str(answer.get("final_answer", "")).strip():
        issues.append("Exam-ready final answer is missing")
    if not answer.get("steps"):
        issues.append("Step-by-step explanation is missing")

    diagram = answer.get("diagram") if isinstance(answer.get("diagram"), dict) else {}
    if len(diagram.get("nodes", []) or []) < 3:
        issues.append("Question-specific diagram is incomplete")

    sources = answer.get("sources", []) or []
    if route.get("use_web") and len(sources) < 2:
        issues.append("Current fact needs at least two source references")
    if route.get("use_rag") and not sources:
        issues.append("Uploaded-note answer lost its source references")

    answer_route = answer.get("route") if isinstance(answer.get("route"), dict) else {}
    if route.get("use_code") and not answer_route.get("code_execution"):
        issues.append("Independent calculation was not completed")

    score = confidence
    score -= min(60, 12 * len(issues))
    score = max(0, min(100, score))
    passed = status == "VERIFIED" and score >= 80 and not issues
    note_text = " ".join(str(item) for item in answer.get("verification_notes", [])).casefold()
    blocked_provider = any(phrase in note_text for phrase in (
        "quota/rate limit", "api key is missing", "not configured", "not permitted",
    ))
    temporary_provider_issue = any(
        phrase in note_text for phrase in ("could not finish", "provider timed out", "timeout")
    )
    retryable = not passed and not blocked_provider and (temporary_provider_issue or bool(issues))
    return VerificationReport(
        passed=passed,
        score=score,
        issues=issues,
        retryable=retryable,
        human_review_required=not passed and not retryable,
    )
