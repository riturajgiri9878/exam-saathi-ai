"""Agentic orchestration layer for Exam Saathi v5.4.

The graph keeps the proven answer engine as the subject-solving tool and adds
state, routing, deterministic verification, bounded retry, checkpoint memory,
artifact generation and optional privacy-safe LangSmith observability.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from exam_memory import CHECKPOINTER, register_thread, safe_thread_id
from exam_prompts import prepare_intake
from exam_state import ExamState
from exam_tools import generate_visual_pack, plan_question, solve_with_verified_engine
from exam_verifier import inspect_answer
from fast_answer import try_fast_answer


GraphSolveFn = Callable[..., dict[str, Any]]
ArtifactFn = Callable[[dict[str, Any]], tuple[str, str]]


def _truthy(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().casefold() in {"1", "true", "yes", "on"}


def configure_langsmith_privacy() -> None:
    """Hide student content unless an operator explicitly allows trace content."""
    if _truthy("LANGSMITH_TRACING") and not _truthy("EXAM_SAATHI_TRACE_CONTENT"):
        os.environ.setdefault("LANGSMITH_HIDE_INPUTS", "true")
        os.environ.setdefault("LANGSMITH_HIDE_OUTPUTS", "true")
    os.environ.setdefault("LANGSMITH_PROJECT", "exam-saathi-v5-2")


configure_langsmith_privacy()


class ExamSaathiWorkflow:
    def __init__(
        self,
        solve_fn: GraphSolveFn = solve_with_verified_engine,
        artifact_fn: ArtifactFn = generate_visual_pack,
        max_retries: int | None = None,
        checkpointer: Any = CHECKPOINTER,
    ) -> None:
        self.solve_fn = solve_fn
        self.artifact_fn = artifact_fn
        configured = int(os.environ.get("EXAM_GRAPH_MAX_RETRIES", "0"))
        self.max_retries = max(0, min(2, configured if max_retries is None else max_retries))
        self.graph = self._build().compile(checkpointer=checkpointer)

    def _build(self) -> StateGraph:
        graph = StateGraph(ExamState)
        graph.add_node("intake", self._intake)
        graph.add_node("plan", self._plan)
        graph.add_node("solve", self._solve)
        graph.add_node("verify", self._verify)
        graph.add_node("human_review", self._human_review)
        graph.add_node("artifacts", self._artifacts)
        graph.add_edge(START, "intake")
        graph.add_edge("intake", "plan")
        graph.add_edge("plan", "solve")
        graph.add_edge("solve", "verify")
        graph.add_conditional_edges(
            "verify",
            self._after_verify,
            {"retry": "solve", "accept": "artifacts", "human_review": "human_review"},
        )
        graph.add_edge("human_review", "artifacts")
        graph.add_edge("artifacts", END)
        return graph

    @staticmethod
    def _events(state: ExamState, message: str) -> list[str]:
        return [*(state.get("workflow_events") or []), message]

    def _intake(self, state: ExamState) -> dict[str, Any]:
        prepared = prepare_intake(dict(state))
        return {
            **prepared,
            "answer": {},
            "verification": {},
            "retry_count": 0,
            "max_retries": self.max_retries,
            "human_review_required": False,
            "html_file": "",
            "pdf_file": "",
        }

    def _plan(self, state: ExamState) -> dict[str, Any]:
        route_dict = plan_question(state["question"], state.get("rag_context"))
        override = state.get("subject_override")
        if override and override != "Auto":
            route_dict["subject"] = str(override)
        return {
            "subject": route_dict["subject"],
            "route": route_dict,
            "workflow_events": self._events(
                state,
                "Supervisor routed question to " + route_dict["subject"],
            ),
        }

    def _solve(self, state: ExamState) -> dict[str, Any]:
        retry_count = int(state.get("retry_count", 0))
        force_web = bool(state.get("force_web"))
        if retry_count and state.get("route", {}).get("use_web"):
            force_web = True
        answer = None
        if retry_count == 0:
            answer = try_fast_answer(
                state["question"],
                state.get("language", "Hinglish"),
                state.get("subject", "General Studies"),
                state.get("route", {}),
            )
        if answer is None:
            answer = self.solve_fn(
                state["question"],
                language=state.get("language", "Hinglish"),
                rag_context=state.get("rag_context"),
                force_web=force_web,
                subject_override=state.get("subject_override"),
                conversation_history=state.get("chat_history"),
            )
        evidence = list(state.get("rag_context") or [])
        retrieval_engine = str(evidence[0].get("retrieval_engine") or "") if evidence else ""
        answer["agentic_workflow"] = {
            "name": "Exam Saathi Agentic Learning Graph",
            "retry_count": retry_count,
            "thread_memory": True,
            "retrieval_engine": retrieval_engine,
        }
        label = (
            "Instant local answer completed" if answer.get("fast_path") else
            ("Answer engine completed" if retry_count == 0 else f"Retry {retry_count} completed")
        )
        if retrieval_engine:
            label += f" with {retrieval_engine}"
        return {"answer": answer, "workflow_events": self._events(state, label)}

    def _verify(self, state: ExamState) -> dict[str, Any]:
        report = inspect_answer(state.get("answer", {}), state.get("route", {}))
        retry_count = int(state.get("retry_count", 0))
        max_retries = int(state.get("max_retries", self.max_retries))
        if report.passed:
            next_action = "accept"
        elif report.retryable and retry_count < max_retries:
            next_action = "retry"
        else:
            next_action = "human_review"
        return {
            "verification": report.as_dict(),
            "next_action": next_action,
            "retry_count": retry_count + (1 if next_action == "retry" else 0),
            "workflow_events": self._events(
                state,
                f"Deterministic verification score: {report.score}/100 ({next_action})",
            ),
        }

    @staticmethod
    def _after_verify(state: ExamState) -> str:
        return str(state.get("next_action", "human_review"))

    def _human_review(self, state: ExamState) -> dict[str, Any]:
        answer = dict(state.get("answer", {}))
        answer["verification_status"] = "REVIEW_NEEDED"
        answer["confidence"] = min(int(answer.get("confidence", 0) or 0), 69)
        notes = list(answer.get("verification_notes", []) or [])
        issues = state.get("verification", {}).get("issues", [])
        message = "Agentic quality gate requires human review"
        if issues:
            message += ": " + "; ".join(str(item) for item in issues)
        if message not in notes:
            notes.append(message)
        answer["verification_notes"] = notes
        return {
            "answer": answer,
            "human_review_required": True,
            "workflow_events": self._events(state, "Answer sent to human-review state"),
        }

    def _artifacts(self, state: ExamState) -> dict[str, Any]:
        if not state.get("generate_artifacts", True):
            return {
                "html_file": "",
                "pdf_file": "",
                "workflow_events": self._events(state, "Visual pack deferred until answer display"),
            }
        html_file, pdf_file = self.artifact_fn(state["answer"])
        return {
            "html_file": html_file,
            "pdf_file": pdf_file,
            "workflow_events": self._events(state, "Fresh PDF and HTML generated"),
        }

    def invoke(self, payload: dict[str, Any], thread_id: str | None = None) -> ExamState:
        resolved_thread_id = safe_thread_id(thread_id)
        register_thread(resolved_thread_id)
        config = {
            "configurable": {"thread_id": resolved_thread_id},
            "tags": ["exam-saathi", "v5.4", "student-question"],
            "metadata": {"workflow": "agentic-learning-graph", "content_logged": False},
        }
        return self.graph.invoke(payload, config=config)


DEFAULT_WORKFLOW = ExamSaathiWorkflow()


def run_exam_graph(
    question: str,
    language: str = "Hinglish",
    rag_context: list[dict[str, Any]] | None = None,
    force_web: bool = False,
    subject_override: str | None = None,
    chat_history: list[dict[str, Any]] | None = None,
    thread_id: str | None = None,
    generate_artifacts: bool = True,
) -> ExamState:
    return DEFAULT_WORKFLOW.invoke(
        {
            "question": question,
            "language": language,
            "rag_context": list(rag_context or []),
            "force_web": bool(force_web),
            "subject_override": subject_override,
            "chat_history": list(chat_history or []),
            "workflow_events": [],
            "generate_artifacts": bool(generate_artifacts),
        },
        thread_id=thread_id,
    )
