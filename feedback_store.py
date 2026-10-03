"""Privacy-minimised human feedback log for later evaluation and correction."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path

_LOCK = threading.Lock()


def save_feedback(question: str, answer: str, verdict: str, note: str = "") -> str:
    allowed = {"correct", "incorrect", "report"}
    verdict = str(verdict).strip().casefold()
    if verdict not in allowed:
        raise ValueError("Unknown feedback type.")
    digest = hashlib.sha256(question.strip().encode("utf-8")).hexdigest()[:20]
    record = {
        "question_hash": digest,
        "answer_excerpt": " ".join(str(answer).split())[:500],
        "verdict": verdict,
        "note": " ".join(str(note).split())[:1000],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    target = Path(os.environ.get("EXAM_SAATHI_DATA_DIR", Path(__file__).resolve().parent / "data")) / "answer_feedback.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, target.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    return "Feedback saved. Thank you—this answer is now marked for quality review."
