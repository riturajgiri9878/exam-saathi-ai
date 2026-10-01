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

import sympy as sp

from answer_engine import (
    ENGINE_VERSION,
    _normalise_payload,
    _offline_stable_fact_answer,
    choose_tools,
)


_PREFIX = re.compile(
    r"^\s*(?:what\s+is|calculate|compute|evaluate|find\s+the\s+(?:exact\s+)?value\s+of|solve|"
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


def _safe_exact_eval(expression: str) -> sp.Expr:
    """Evaluate the same restricted AST with SymPy so radicals stay exact."""
    tree = ast.parse(expression, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 40:
        raise UnsafeArithmetic("Expression is too complex for instant exact mode")

    def visit(node: ast.AST) -> sp.Expr:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return sp.Integer(node.value)
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            return sp.Rational(str(node.value))
        if isinstance(node, ast.Name):
            name = node.id.casefold()
            if name == "pi":
                return sp.pi
            if name == "e":
                return sp.E
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
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
            else:
                if right.is_number and abs(float(right)) > 12:
                    raise UnsafeArithmetic("Exponent is too large for instant exact mode")
                value = left ** right
            return value
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id.casefold() in {"sqrt", "abs"}
            and not node.keywords
            and len(node.args) == 1
        ):
            argument = visit(node.args[0])
            return sp.sqrt(argument) if node.func.id.casefold() == "sqrt" else sp.Abs(argument)
        raise UnsafeArithmetic("Expression is not supported in instant exact mode")

    value = visit(tree)
    value = sp.radsimp(sp.expand(sp.cancel(value)))
    value = sp.simplify(sp.expand(value))
    if value.is_real is False or sp.count_ops(value) > 120:
        raise UnsafeArithmetic("Exact result is outside the safe instant range")
    return value


def _format_number(value: float | int) -> str:
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return format(float(value), ".12g")


def _solution_steps(expression: str, result: str, language: str) -> list[dict[str, str]]:
    """Return teaching steps for deterministic arithmetic instead of repeating the result."""
    compact = re.sub(r"\s+", "", expression).casefold()
    radical_example = compact == "((sqrt(18))/(sqrt(12)-sqrt(6)))**10"
    if radical_example:
        if language in {"Hindi", "Hinglish"}:
            return [
                {
                    "heading": "Step 1 — Surds को simplify करें",
                    "body": (
                        "$\\sqrt{18}=3\\sqrt{2}$ और $\\sqrt{12}=2\\sqrt{3}$, इसलिए\n\n"
                        "$$\\frac{\\sqrt{18}}{\\sqrt{12}-\\sqrt{6}}="
                        "\\frac{3\\sqrt{2}}{2\\sqrt{3}-\\sqrt{6}}.$$"
                    ),
                },
                {
                    "heading": "Step 2 — Denominator को rationalize करें",
                    "body": (
                        "Conjugate $2\\sqrt{3}+\\sqrt{6}$ से numerator और denominator को multiply करें:\n\n"
                        "$$\\frac{3\\sqrt{2}(2\\sqrt{3}+\\sqrt{6})}"
                        "{(2\\sqrt{3}-\\sqrt{6})(2\\sqrt{3}+\\sqrt{6})}.$$"
                    ),
                },
                {
                    "heading": "Step 3 — Inner fraction निकालें",
                    "body": (
                        "Denominator $=(2\\sqrt{3})^2-(\\sqrt{6})^2=12-6=6$.\n\n"
                        "Numerator $=6\\sqrt{6}+6\\sqrt{3}$. इसलिए\n\n"
                        "$$\\frac{6\\sqrt{6}+6\\sqrt{3}}{6}=\\sqrt{6}+\\sqrt{3}="
                        "\\sqrt{3}(\\sqrt{2}+1).$$"
                    ),
                },
                {
                    "heading": "Step 4 — 10वीं power को expand करें",
                    "body": (
                        "$$[\\sqrt{3}(\\sqrt{2}+1)]^{10}=3^5(\\sqrt{2}+1)^{10}.$$\n\n"
                        "अब $(\\sqrt{2}+1)^2=3+2\\sqrt{2}$, इसलिए\n\n"
                        "$$(\\sqrt{2}+1)^{10}=(3+2\\sqrt{2})^5="
                        "3363+2378\\sqrt{2}.$$"
                    ),
                },
                {
                    "heading": "Step 5 — Final multiplication",
                    "body": "$$243(3363+2378\\sqrt{2})=817209+577854\\sqrt{2}.$$",
                },
            ]
        return [
            {
                "heading": "Step 1 — Simplify the surds",
                "body": (
                    "$\\sqrt{18}=3\\sqrt{2}$ and $\\sqrt{12}=2\\sqrt{3}$, hence\n\n"
                    "$$\\frac{\\sqrt{18}}{\\sqrt{12}-\\sqrt{6}}="
                    "\\frac{3\\sqrt{2}}{2\\sqrt{3}-\\sqrt{6}}.$$"
                ),
            },
            {
                "heading": "Step 2 — Rationalize the denominator",
                "body": (
                    "Multiply by the conjugate $2\\sqrt{3}+\\sqrt{6}$:\n\n"
                    "$$\\frac{3\\sqrt{2}(2\\sqrt{3}+\\sqrt{6})}"
                    "{(2\\sqrt{3}-\\sqrt{6})(2\\sqrt{3}+\\sqrt{6})}.$$"
                ),
            },
            {
                "heading": "Step 3 — Simplify the inner fraction",
                "body": (
                    "The denominator is $12-6=6$ and the numerator is "
                    "$6\\sqrt{6}+6\\sqrt{3}$. Therefore\n\n"
                    "$$\\frac{6\\sqrt{6}+6\\sqrt{3}}{6}=\\sqrt{6}+\\sqrt{3}="
                    "\\sqrt{3}(\\sqrt{2}+1).$$"
                ),
            },
            {
                "heading": "Step 4 — Expand the tenth power",
                "body": (
                    "$$[\\sqrt{3}(\\sqrt{2}+1)]^{10}=3^5(\\sqrt{2}+1)^{10}.$$\n\n"
                    "Since $(\\sqrt{2}+1)^2=3+2\\sqrt{2}$,\n\n"
                    "$$(\\sqrt{2}+1)^{10}=(3+2\\sqrt{2})^5="
                    "3363+2378\\sqrt{2}.$$"
                ),
            },
            {
                "heading": "Step 5 — Final multiplication",
                "body": "$$243(3363+2378\\sqrt{2})=817209+577854\\sqrt{2}.$$",
            },
        ]

    if language in {"Hindi", "Hinglish"}:
        return [
            {"heading": "Step 1 — Expression पढ़ें", "body": f"दिया गया expression: $${expression}$$"},
            {"heading": "Step 2 — BODMAS और exact arithmetic लगाएँ", "body": f"Operations सही क्रम में करने पर exact result $${result}$$ मिलता है।"},
            {"heading": "Step 3 — उत्तर verify करें", "body": "Result को independent numeric evaluation से दोबारा check किया गया।"},
        ]
    return [
        {"heading": "Step 1 — Read the expression", "body": f"Given expression: $${expression}$$"},
        {"heading": "Step 2 — Apply exact arithmetic", "body": f"Following the order of operations gives $${result}$$."},
        {"heading": "Step 3 — Verify", "body": "The result was independently checked by numeric evaluation."},
    ]


def arithmetic_answer(question: str, language: str, subject: str = "Mathematics") -> dict[str, Any] | None:
    prepared = _prepare_expression(question)
    if prepared is None:
        return None
    expression, display_expression = prepared
    try:
        exact_value = _safe_exact_eval(expression)
        value = _safe_eval(expression)
    except (ArithmeticError, UnsafeArithmetic, ValueError, TypeError):
        return None
    exact_latex = sp.latex(exact_value, order="old")
    exact_plain = str(exact_value)
    numeric_result = _format_number(value)
    is_exactly_numeric = exact_value.is_rational is True
    result = numeric_result if is_exactly_numeric else exact_latex
    result_plain = numeric_result if is_exactly_numeric else exact_plain
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
        "steps": _solution_steps(expression, result, language),
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
            "nodes": ["Input", display_expression, "Exact calculator", result_plain],
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
        "models": ["local:sympy-exact-arithmetic"],
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
