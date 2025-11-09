"""YAML configuration loader to override runtime thresholds/settings.

Search order:
  1. Explicit path passed to load_config(path)
  2. Environment variable AUTOOCR_CONFIG
  3. Default 'settings.yaml' in current working directory (optional)

Merges into a dict; caller can then map values onto config module variables.
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional
import os

try:
    import yaml  # type: ignore
except Exception:  # pylint: disable=broad-except
    yaml = None  # type: ignore


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    candidates = []
    if path:
        candidates.append(Path(path))
    env = os.environ.get("AUTOOCR_CONFIG")
    if env:
        candidates.append(Path(env))
    candidates.append(Path("settings.yaml"))

    for p in candidates:
        if p.exists() and p.is_file():
            if not yaml:
                raise RuntimeError("PyYAML not installed; add 'pyyaml' to requirements to use config files")
            with p.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                raise ValueError("Configuration root must be a mapping")
            return data
    return {}

__all__ = ["load_config"]
