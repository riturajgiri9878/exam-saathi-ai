"""Deterministic fast answers that must not consume an LLM request.

The recogniser is intentionally strict.  It accepts only a complete arithmetic
expression (optionally wrapped in a small set of natural-language prefixes) or
one of Exam Saathi's curated stable facts.  Ambiguous STEM text, equations with
unknowns and current facts always continue to the full verified workflow.
"""

from __future__ import annotations

import ast
import math
import re
import time
from typing import Any

from answer_engine import (
    ENGINE_VERSION,
    _normalise_payload,
    _offline_stable_fact_answer,
    choose_tools,
)


_PREFIX = re.compile(
    r"^\s*(?:what\s+is|calculate|compute|evaluate|find\s+the\s+value\s+of|solve|"
    r"बताओ|हल\s+करो|मान\s+निकालो)\s*[:\-]?\s*",
    re.IGNORECASE,
)
_SUFFIX = re.compile(
    r"\s*(?:please|answer|kitna\s+hai|कितना\s+है|का\s+मान\s+क्या\s+है)\s*[?.!]*\s*$",
    re.IGNORECASE,
)
_PERCENT = re.compile(
    r"^\s*(?:what\s+is\s+|calculate\s+)?(-?\d+(?:\.\d+)?)\s*%\s*(?:of|का)\s*"
    r"(-?\d+(?:\.\d+)?)\s*[?.!]*\s*$",
    re.IGNORECASE,
)
_SOURCE_SCOPED = re.compile(
    r"\b(?:according\s+to|uploaded|upload|notes?|pdf|document|source|page)\b|"
    r"(?:नोट्स|पीडीएफ|दस्तावेज़|पेज|स्रोत)",
    re.IGNORECASE,
)
_ALLOWED_NAMES = {"pi": math.pi, "e": math.e}
_ALLOWED_FUNCTIONS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
}


class UnsafeArithmetic(ValueError):
    pass


def _prepare_expression(question: str) -> tuple[str, str] | None:
    raw = str(question or "").strip()
    if not raw or len(raw) > 160:
        return None
    percent = _PERCENT.fullmatch(raw)
    if percent:
        left, right = percent.groups()
        return f"({left} / 100) * {right}", f"{left}% of {right}"

    candidate = raw.replace("×", "*").replace("÷", "/").replace("−", "-")
    candidate = _PREFIX.sub("", candidate)
    candidate = _SUFFIX.sub("", candidate).strip().rstrip("?!.=").strip()
    candidate = candidate.replace("^", "**")
    if not candidate or not re.search(r"\d", candidate):
        return None
    if not re.fullmatch(r"[0-9eEpiPIqrtSQRTabsroundROUND\s+\-*/%().,]*", candidate):
        return None
    return candidate, candidate


def _safe_eval(expression: str) -> float | int:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as error:
        raise UnsafeArithmetic("Invalid arithmetic expression") from error
    if sum(1 for _ in ast.walk(tree)) > 40:
        raise UnsafeArithmetic("Expression is too complex for instant mode")

    def visit(node: ast.AST) -> float | int:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Name) and node.id.casefold() in _ALLOWED_NAMES:
            return _ALLOWED_NAMES[node.id.casefold()]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
        ):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                value = left + right
            elif isinstance(node.op, ast.Sub):
                value = left - right
            elif isinstance(node.op, ast.Mult):
                value = left * right
            elif isinstance(node.op, ast.Div):
                value = left / right
            elif isinstance(node.op, ast.FloorDiv):
                value = left // right
            elif isinstance(node.op, ast.Mod):
                value = left % right
            else:
                if abs(float(right)) > 12:
                    raise UnsafeArithmetic("Exponent is too large for instant mode")
                value = left ** right
            if isinstance(value, complex) or not math.isfinite(float(value)) or abs(float(value)) > 1e100:
                raise UnsafeArithmetic("Result is outside the safe instant range")
            return value
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id.casefold()
            if name not in _ALLOWED_FUNCTIONS or node.keywords or len(node.args) not in {1, 2}:
                raise UnsafeArithmetic("Function is not allowed in instant mode")
            values = [visit(argument) for argument in node.args]
            value = _ALLOWED_FUNCTIONS[name](*values)
            if not math.isfinite(float(value)):
                raise UnsafeArithmetic("Result is not finite")
            return value
        raise UnsafeArithmetic("Only safe arithmetic is allowed")

    return visit(tree)


def _format_number(value: float | int) -> str:
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return format(float(value), ".12g")


def arithmetic_answer(question: str, language: str, subject: str = "Mathematics") -> dict[str, Any] | None:
    prepared = _prepare_expression(question)
    if prepared is None:
        return None
    expression, display_expression = prepared
    try:
        value = _safe_eval(expression)
    except (ArithmeticError, UnsafeArithmetic, ValueError, TypeError):
        return None
    result = _format_number(value)
    hindi_mode = language in {"Hindi", "Hinglish"}
    direct = f"उत्तर: **{result}**" if hindi_mode else f"Answer: **{result}**"
    explanation = (
        "यह एक सुरक्षित local calculation है; किसी AI provider या web search की जरूरत नहीं पड़ी।"
        if hindi_mode else
        "This is a safe local calculation; no AI provider or web search was required."
    )
    payload = _normalise_payload({
        "title": "Instant Calculation",
        "subject": subject,
        "direct_answer": f"$${display_expression} = {result}$$\n\n{direct}",
        "beginner_explanation": explanation,
        "steps": [
            {"heading": "Read the expression", "body": f"Expression: $${display_expression}$$"},
            {"heading": "Calculate safely", "body": f"$${display_expression} = {result}$$"},
        ],
        "worked_example": f"The same operation gives $${result}$$.",
        "key_facts": ["Calculated locally.", "No model quota was used."],
        "why_it_matters": "Simple calculations should be fast and deterministic.",
        "exam_perspective": "Write the operation and final value clearly.",
        "common_mistakes": ["Check brackets and the order of operations."],
        "final_answer": f"$${result}$$",
        "short_questions": [],
        "long_questions": [],
        "mcqs": [],
        "diagram": {
            "kind": "flow",
            "title": "Instant arithmetic route",
            "nodes": ["Input", display_expression, "Safe calculator", result],
            "edges": ["read", "calculate", "return"],
            "accuracy_note": "Deterministic local calculation.",
        },
        "verification_status": "VERIFIED",
        "confidence": 100,
        "verification_notes": ["Verified by Exam Saathi's restricted local arithmetic evaluator."],
    }, subject, language)
    payload.update({
        "question": question.strip(),
        "sources": [],
        "route": {
            "subject": subject,
            "web_grounding": False,
            "code_execution": True,
            "uploaded_evidence": False,
            "high_risk_fact": False,
            "geography_type": "Not applicable",
            "visual_type": "flow",
            "source_policy": "calculation",
            "freshness_required": False,
        },
        "models": ["local:safe-arithmetic"],
        "engine_version": ENGINE_VERSION,
        "checked_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "fast_path": True,
        "fast_path_type": "arithmetic",
    })
    return payload


def try_fast_answer(
    question: str,
    language: str,
    subject: str,
    route: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if _SOURCE_SCOPED.search(str(question or "")):
        return None
    arithmetic = arithmetic_answer(question, language, "Mathematics")
    if arithmetic is not None:
        return arithmetic
    route = route or {}
    if route.get("use_web") or route.get("use_rag") or route.get("freshness_required"):
        return None
    offline = _offline_stable_fact_answer(question, language, subject or "General Studies")
    if offline is None:
        return None
    answer, sources = offline
    answer.update({
        "question": question.strip(),
        "sources": [{"title": item["title"], "uri": item["uri"], "source_type": "Curated reference"} for item in sources],
        "route": {
            "subject": subject,
            "web_grounding": False,
            "code_execution": False,
            "uploaded_evidence": False,
            "high_risk_fact": False,
            "geography_type": "Not applicable",
            "visual_type": "flow",
            "source_policy": "curated_stable_fact",
            "freshness_required": False,
        },
        "models": ["local:curated-stable-facts"],
        "engine_version": ENGINE_VERSION,
        "checked_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "fast_path": True,
        "fast_path_type": "curated_stable_fact",
    })
    return answer


def fast_answer_available(question: str, rag_context: list[dict[str, Any]] | None = None) -> bool:
    if _SOURCE_SCOPED.search(str(question or "")):
        return False
    if _prepare_expression(question) is not None:
        try:
            expression, _ = _prepare_expression(question) or ("", "")
            _safe_eval(expression)
            return True
        except Exception:
            return False
    route = choose_tools(question, rag_context)
    if route.use_web or route.use_rag or route.freshness_required:
        return False
    return _offline_stable_fact_answer(question, "English", route.subject) is not None
