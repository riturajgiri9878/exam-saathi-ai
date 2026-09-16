"""LangChain LCEL intake pipeline for safe, consistent question handling."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.runnables import RunnableLambda


EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{9}(?!\d)")
AADHAAR_PATTERN = re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)")
SECRET_PATTERN = re.compile(
    r"(?i)\b(?:api[_ -]?key|token|password|secret)\s*[:=]\s*[^\s,;]+"
)


def redact_sensitive_text(value: str) -> str:
    """Create a trace-safe copy; the real question still goes to the solver."""
    value = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
    value = PHONE_PATTERN.sub("[REDACTED_PHONE]", value)
    value = AADHAAR_PATTERN.sub("[REDACTED_ID]", value)
    return SECRET_PATTERN.sub("[REDACTED_SECRET]", value)


def _copy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return dict(payload or {})


def _normalise_payload(payload: dict[str, Any]) -> dict[str, Any]:
    question = " ".join(str(payload.get("question", "")).split()).strip()
    if not question:
        raise ValueError("Type one question before pressing Solve.")
    payload["question"] = question
    payload["trace_question"] = redact_sensitive_text(question)
    payload["language"] = str(payload.get("language") or "Hinglish").strip()
    payload["workflow_events"] = ["Input normalised by LangChain LCEL"]
    return payload


# A real LCEL pipeline: each runnable has one clear, testable responsibility.
INTAKE_CHAIN = RunnableLambda(_copy_payload) | RunnableLambda(_normalise_payload)


def prepare_intake(payload: dict[str, Any]) -> dict[str, Any]:
    return INTAKE_CHAIN.invoke(payload)

