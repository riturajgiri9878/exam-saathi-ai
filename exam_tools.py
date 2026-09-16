"""Stable tool boundary between LangGraph and the existing Exam Saathi engine."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from answer_engine import choose_tools, create_answer_artifacts, solve_question


def plan_question(question: str, rag_context: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return a serialisable supervisor plan for one student question."""
    return asdict(choose_tools(question, rag_context))


def solve_with_verified_engine(
    question: str,
    *,
    language: str,
    rag_context: list[dict[str, Any]] | None,
    force_web: bool,
    subject_override: str | None,
    conversation_history: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    return solve_question(
        question,
        language=language,
        rag_context=rag_context,
        force_web=force_web,
        subject_override=subject_override,
        conversation_history=conversation_history,
    )


def generate_visual_pack(answer: dict[str, Any]) -> tuple[str, str]:
    return create_answer_artifacts(answer)

