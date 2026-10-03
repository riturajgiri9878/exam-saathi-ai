"""Deterministic post-checks for subject-specific answer claims."""
from __future__ import annotations

import re
from typing import Any


def validate_subject_answer(question: str, answer: dict[str, Any], subject: str) -> list[str]:
    issues: list[str] = []
    rendered = " ".join(str(answer.get(key, "")) for key in ("direct_answer", "exam_ready_answer", "title"))
    if subject == "Mathematics":
        if not answer.get("steps"):
            issues.append("A mathematics answer must show reproducible steps.")
    elif subject in {"Physics", "Chemistry"}:
        if re.search(r"(?i)\bcalculate|find|derive|equation|reaction\b", question) and not answer.get("steps"):
            issues.append(f"The {subject.lower()} solution is missing its working steps.")
        if subject == "Chemistry" and "->" in question and "->" not in rendered and "→" not in rendered:
            issues.append("The requested chemical conversion/equation is not visible in the final answer.")
    elif subject == "Geography":
        diagram = answer.get("diagram") or {}
        if not diagram:
            issues.append("Geography answer is missing a labelled map/process visual.")
        elif "schematic" not in str(diagram.get("accuracy_note", "")).casefold() and not answer.get("sources"):
            issues.append("Map precision is not source-backed or labelled schematic.")
    return issues
