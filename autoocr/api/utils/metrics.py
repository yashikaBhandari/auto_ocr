"""Simple in-memory metrics for AutoOCR."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any
from threading import Lock


@dataclass
class MetricState:
    requests: int = 0
    pages: int = 0
    modules_applied: int = 0


class MetricsRegistry:
    def __init__(self):
        self._lock = Lock()
        self.state = MetricState()

    def inc_request(self, pages: int, modules_applied: int):
        with self._lock:
            self.state.requests += 1
            self.state.pages += pages
            self.state.modules_applied += modules_applied

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return asdict(self.state)


metrics = MetricsRegistry()

__all__ = ["metrics"]