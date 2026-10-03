"""Dependency-free structured events; LangSmith remains optional."""
from __future__ import annotations
import json, logging, time

LOGGER = logging.getLogger("exam_saathi")

def event(name: str, **fields) -> None:
    safe = {k: v for k, v in fields.items() if k not in {"question", "answer", "api_key", "token"}}
    safe.update({"event": name, "ts": time.time()})
    LOGGER.info(json.dumps(safe, ensure_ascii=False, default=str))
