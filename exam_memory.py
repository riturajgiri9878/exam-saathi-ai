"""Conversation checkpointing helpers for the stateful Exam Saathi graph."""

from __future__ import annotations

import re
from collections import OrderedDict
from threading import Lock
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver


CHECKPOINTER = InMemorySaver()
MAX_MEMORY_THREADS = 250
_THREADS: OrderedDict[str, None] = OrderedDict()
_THREAD_LOCK = Lock()


def safe_thread_id(value: str | None) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]", "-", str(value or ""))[:120].strip("-")
    return cleaned or uuid4().hex


def register_thread(thread_id: str) -> None:
    """Bound checkpoint memory so a long-running free service cannot grow forever."""
    expired: list[str] = []
    with _THREAD_LOCK:
        _THREADS.pop(thread_id, None)
        _THREADS[thread_id] = None
        while len(_THREADS) > MAX_MEMORY_THREADS:
            old_thread, _ = _THREADS.popitem(last=False)
            expired.append(old_thread)
    for old_thread in expired:
        CHECKPOINTER.delete_thread(old_thread)
