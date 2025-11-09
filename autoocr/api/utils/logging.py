"""Structured JSON logging helper."""
from __future__ import annotations
import json
import logging
import os
from typing import Any

_LOGGER = None


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str = "autoocr") -> logging.Logger:
    global _LOGGER  # noqa: PLW0603
    if _LOGGER is not None:
        return _LOGGER.getChild(name)
    base = logging.getLogger("autoocr")
    level = os.environ.get("AUTOOCR_LOG_LEVEL", "INFO").upper()
    base.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    base.addHandler(handler)
    base.propagate = False
    _LOGGER = base
    return base.getChild(name)

__all__ = ["get_logger"]