"""Runtime provider health scoring used to avoid repeatedly selecting a bad endpoint."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, asdict


@dataclass
class ProviderStat:
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    latency_ms: float = 0.0
    last_error: str = ""
    updated_at: float = 0.0


class ProviderHealth:
    def __init__(self):
        self._stats: dict[str, ProviderStat] = {}
        self._lock = threading.Lock()

    def record(self, name: str, ok: bool, elapsed: float, error: str = "") -> None:
        with self._lock:
            stat = self._stats.setdefault(name, ProviderStat())
            stat.successes += int(ok)
            stat.failures += int(not ok)
            stat.consecutive_failures = 0 if ok else stat.consecutive_failures + 1
            sample = elapsed * 1000
            stat.latency_ms = sample if not stat.latency_ms else round(stat.latency_ms * .7 + sample * .3, 1)
            stat.last_error = "" if ok else error[:180]
            stat.updated_at = time.time()

    def score(self, name: str) -> float:
        with self._lock:
            stat = self._stats.get(name)
            if not stat:
                return 50.0
            reliability = (stat.successes + 1) / (stat.successes + stat.failures + 2)
            return round(reliability * 100 - min(40, stat.consecutive_failures * 15) - min(20, stat.latency_ms / 5000), 2)

    def snapshot(self):
        with self._lock:
            return {name: {**asdict(stat), "score": self.score_unlocked(stat)} for name, stat in self._stats.items()}

    @staticmethod
    def score_unlocked(stat: ProviderStat) -> float:
        reliability = (stat.successes + 1) / (stat.successes + stat.failures + 2)
        return round(reliability * 100 - min(40, stat.consecutive_failures * 15) - min(20, stat.latency_ms / 5000), 2)


PROVIDER_HEALTH = ProviderHealth()
