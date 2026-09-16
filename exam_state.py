"""Shared state carried through the Exam Saathi LangGraph workflow."""

from __future__ import annotations

from typing import Any, TypedDict


class ExamState(TypedDict, total=False):
    question: str
    trace_question: str
    language: str
    subject_override: str | None
    subject: str
    rag_context: list[dict[str, Any]]
    chat_history: list[dict[str, Any]]
    force_web: bool
    route: dict[str, Any]
    answer: dict[str, Any]
    verification: dict[str, Any]
    retry_count: int
    max_retries: int
    next_action: str
    human_review_required: bool
    html_file: str
    pdf_file: str
    workflow_events: list[str]

