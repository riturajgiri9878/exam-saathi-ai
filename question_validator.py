"""Conservative question-quality checks; never invent missing facts."""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    severity: str
    message: str
    warnings: tuple[str, ...] = ()

    def as_dict(self):
        return asdict(self)


def validate_question(question: str) -> ValidationResult:
    text = " ".join(str(question or "").split()).strip()
    if not text:
        return ValidationResult(False, "BLOCK", "Type one complete question.")
    if len(text) > 12000:
        return ValidationResult(False, "BLOCK", "Question is too long. Upload the document or shorten it.")
    if len(text) < 2:
        return ValidationResult(False, "BLOCK", "Please enter a meaningful question.")

    warnings: list[str] = []
    pairs = [("(", ")"), ("[", "]"), ("{", "}")]
    for left, right in pairs:
        if text.count(left) != text.count(right):
            warnings.append(f"Unbalanced {left}{right} symbols detected; confirm the expression.")
    if re.search(r"(?i)\b(?:ignore|override)\s+(?:all\s+)?(?:previous|system)\s+instructions\b", text):
        warnings.append("Instruction-manipulation text was ignored; only the study question will be solved.")
    if re.search(r"(?i)\b(?:today|current|currently|latest|now|202[5-9])\b", text):
        warnings.append("This appears time-sensitive and requires live source verification.")
    if re.search(r"(?i)\b(?:always|guaranteed|100\s*%)\b", text):
        warnings.append("Absolute-certainty wording cannot itself prove the answer.")

    severity = "WARN" if warnings else "PASS"
    return ValidationResult(True, severity, "Question accepted.", tuple(warnings))
