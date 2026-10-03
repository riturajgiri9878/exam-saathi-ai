"""Bounded, question-hash cache. Current facts and review-needed answers never enter it."""
from __future__ import annotations

import copy
import hashlib
import json
import threading
import time
from collections import OrderedDict
from typing import Any


class AnswerCache:
    def __init__(self, max_items: int = 128, ttl_seconds: int = 21600):
        self.max_items = max(8, max_items)
        self.ttl_seconds = max(60, ttl_seconds)
        self._items: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def key(question: str, language: str, subject: str, version: str) -> str:
        payload = json.dumps({"q":" ".join(question.casefold().split()),"l":language,"s":subject,"v":version}, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, key: str) -> dict[str, Any] | None:
        now = time.time()
        with self._lock:
            item = self._items.get(key)
            if not item:
                return None
            created, answer = item
            if now - created > self.ttl_seconds:
                self._items.pop(key, None)
                return None
            self._items.move_to_end(key)
            output = copy.deepcopy(answer)
            output["cache_hit"] = True
            return output

    def put(self, key: str, answer: dict[str, Any], route: dict[str, Any]) -> bool:
        if route.get("use_web") or route.get("high_risk_fact") or route.get("freshness_required"):
            return False
        if answer.get("verification_status") not in {"VERIFIED", "LOCALLY_VERIFIED"}:
            return False
        with self._lock:
            self._items[key] = (time.time(), copy.deepcopy(answer))
            self._items.move_to_end(key)
            while len(self._items) > self.max_items:
                self._items.popitem(last=False)
        return True


ANSWER_CACHE = AnswerCache()
