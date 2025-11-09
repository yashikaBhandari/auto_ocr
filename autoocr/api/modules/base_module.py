"""Base module abstraction for preprocessing pipeline.

Design goals:
- Uniform interface for detection + processing.
- Each module declares `name` for logging/serialization.
- Keep modules stateless (any learned model handled externally / cached globally).

Return conventions:
- detect(image) -> (bool, dict)  # bool indicates whether processing should run
- process(image, detect_meta) -> (image, dict)

Images are assumed BGR (OpenCV default) unless otherwise noted.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any

class BaseModule(ABC):
    name: str = "base"

    @abstractmethod
    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Analyze image to decide if processing is required.

        Should be fast & avoid heavy transforms.
        Returns (should_run, metadata) where metadata may include scores.
        """
        raise NotImplementedError

    @abstractmethod
    def process(self, image, detect_meta: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """Apply transformation. Should rely on detect_meta where possible.
        Returns (new_image, process_meta) where process_meta holds stats.
        """
        raise NotImplementedError
